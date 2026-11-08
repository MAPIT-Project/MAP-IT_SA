import io
import json
import traceback
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from app.services.cordis_api import CordisClient, CordisError

KEY = "synthetic-secret-for-test"


class Opener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, **kwargs):
        self.requests.append(request)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return io.BytesIO(json.dumps({"status": True, "payload": value}).encode())


def test_key_is_server_query_parameter_and_not_client_representation():
    opener = Opener({"result": []})
    client = CordisClient(KEY, opener=opener)
    assert client.list_extractions() == []
    request = opener.requests[0]
    assert request.full_url.startswith(
        "https://cordis.europa.eu/api/dataextractions/listExtractions?"
    )
    assert parse_qs(urlsplit(request.full_url).query)["key"] == [KEY]
    assert KEY not in repr(client)


def test_transport_error_does_not_expose_key_in_traceback():
    error = HTTPError("https://cordis.europa.eu/api?key=" + KEY, 401, "Unauthorized", {}, None)
    client = CordisClient(KEY, opener=Opener(error))
    try:
        client.list_extractions()
    except CordisError:
        formatted = traceback.format_exc()
        assert KEY not in formatted
        assert "HTTP 401" in formatted
    else:
        pytest.fail("Expected authentication failure")


@pytest.mark.parametrize("progress", ["RUNNING", "QUEUED", "unknown"])
def test_active_or_unknown_task_prevents_starting_an_extraction(progress):
    opener = Opener({"result": [{"taskID": 10, "progress": progress}]})
    client = CordisClient(KEY, opener=opener)
    with pytest.raises(CordisError, match="no new extraction started"):
        client.create_extraction("contenttype=project")
    assert len(opener.requests) == 1


def test_creation_uses_published_parameter_names():
    opener = Opener({"result": []}, {"taskID": 17, "cancelledExtraction": None})
    assert CordisClient(KEY, opener=opener).create_extraction("contenttype=project")["taskID"] == 17
    params = parse_qs(urlsplit(opener.requests[1].full_url).query)
    assert params["outputFormat"] == ["csv"] and params["archived"] == ["false"]


def test_external_export_uri_is_rejected_before_download(tmp_path):
    client = CordisClient(
        KEY,
        opener=Opener(
            {
                "taskID": 17,
                "progress": "COMPLETED",
                "destinationFileUri": "https://evil.example/export",
            }
        ),
    )
    with pytest.raises(CordisError, match="outside"):
        client.download(17, tmp_path / "export")
    assert not list(tmp_path.iterdir())


def test_failed_task_cannot_be_downloaded_as_a_complete_export(tmp_path):
    client = CordisClient(
        KEY,
        opener=Opener(
            {
                "taskID": 17,
                "progress": "FAILED",
                "destinationFileUri": "https://cordis.europa.eu/file",
            }
        ),
    )
    with pytest.raises(CordisError, match="not confirmed ready"):
        client.download(17, tmp_path / "export")


def test_task_summary_does_not_expose_download_token():
    client = CordisClient(KEY)
    assert client.safe_task(
        {
            "taskID": 17,
            "progress": KEY,
            "destinationFileUri": "https://cordis.europa.eu/file?token=private",
        }
    ) == {"taskID": "17", "progress": "<redacted>"}


def test_cordis_setting_is_masked_and_blank_is_unconfigured():
    from app.core.config import Settings

    settings = Settings(_env_file=None, cordis_api_key=KEY)
    assert settings.cordis_api_key.get_secret_value() == KEY
    assert KEY not in repr(settings)
    assert Settings(_env_file=None, cordis_api_key="  ").cordis_api_key is None


def test_download_cannot_be_redirected_to_a_task_cancellation(tmp_path):
    client = CordisClient(
        KEY,
        opener=Opener(
            {
                "taskID": 17,
                "progress": "COMPLETED",
                "destinationFileUri": "https://cordis.europa.eu/api/dataextractions/cancelExtraction?taskId=20",
            }
        ),
    )
    with pytest.raises(CordisError, match="modifying operation"):
        client.download(17, tmp_path / "export")


def test_live_list_normalizes_task_identifier():
    client = CordisClient(KEY, opener=Opener({"result": [{"taskId": "17", "progress": "Finished"}]}))
    assert client.safe_task(client.list_extractions()[0])["taskID"] == "17"


def test_live_creation_accepts_literal_string_true():
    class LiveOpener(Opener):
        def open(self, request, **kwargs):
            if "getExtraction?" in request.full_url:
                return io.BytesIO(json.dumps({"status": "true", "payload": {"taskID": 17}}).encode())
            return super().open(request, **kwargs)
    assert CordisClient(KEY, opener=LiveOpener({"result": []})).create_extraction("contenttype=project")["taskID"] == 17


def test_download_origin_allows_only_exact_cordis_storage_host():
    from app.services.cordis_api import cordis_url
    assert cordis_url("https://s3.cordis.europa.eu/export.zip")
    assert not cordis_url("https://s3.cordis.europa.eu.evil.example/export.zip")
