"""CORDIS Data Extraction Tool client based on its published OpenAPI contract.

API keys are required in the query string by CORDIS. Never log request URLs,
provider response bodies, or original transport exceptions. No cancellation or
deletion operation is exposed by this client.
"""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit, unquote
from urllib.request import HTTPRedirectHandler, Request, build_opener


class CordisError(RuntimeError):
    pass


def cordis_url(url):
    try:
        p = urlsplit(url)
        return (
            p.scheme == "https"
            and p.hostname in {"cordis.europa.eu", "s3.cordis.europa.eu"}
            and p.port in (None, 443)
            and not p.username
            and not p.password
        )
    except ValueError:
        return False


class NoApiRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CordisError("CORDIS API redirect refused")


class CordisDownloadRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not cordis_url(newurl):
            raise CordisError("CORDIS download redirect outside the allowed origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def finished(task):
    return str(task.get("progress", "")).strip().upper() in {
        "COMPLETED",
        "COMPLETE",
        "FINISHED",
        "DONE",
        "CANCELLED",
        "CANCELED",
        "FAILED",
        "ERROR",
    }


def successful(task):
    return str(task.get("progress", "")).strip().upper() in {
        "COMPLETED",
        "COMPLETE",
        "FINISHED",
        "DONE",
    }


class CordisClient:
    BASE = "https://cordis.europa.eu/api/dataextractions/"

    def __init__(self, api_key, *, opener=None, download_opener=None):
        key = api_key.get_secret_value() if hasattr(api_key, "get_secret_value") else api_key
        if not isinstance(key, str) or not key.strip():
            raise CordisError("CORDIS_API_KEY is not configured")
        self._key = key.strip()
        self._opener = opener or build_opener(NoApiRedirects())
        self._download_opener = download_opener or build_opener(CordisDownloadRedirects())

    def __repr__(self):
        return "CordisClient(api_key=<redacted>)"

    def safe_task(self, task):
        # The destination URI can contain a download token; never print it.
        return {
            field: str(task[field]).replace(self._key, "<redacted>")[:300]
            for field in ("taskID", "progress", "numberOfRecords", "numberOfProcessedRecords")
            if field in task
        }

    def _call(self, operation, **params):
        if operation not in {"listExtractions", "getExtraction", "getExtractionStatus"}:
            raise CordisError("Unsupported CORDIS operation")
        url = self.BASE + operation + "?" + urlencode({**params, "key": self._key})
        try:
            with self._opener.open(
                Request(url, headers={"Accept": "application/json"}), timeout=30
            ) as response:
                body = response.read(2 * 1024 * 1024 + 1)
                if len(body) > 2 * 1024 * 1024:
                    raise CordisError("CORDIS API response exceeded the size limit")
                result = json.loads(body)
        except HTTPError as error:
            raise CordisError(f"CORDIS API returned HTTP {error.code}") from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise CordisError("CORDIS API request failed or returned invalid JSON") from None
        if (
            not isinstance(result, dict)
            or not (result.get("status") is True or result.get("status") == "true")
            or not isinstance(result.get("payload"), dict)
        ):
            raise CordisError("CORDIS did not confirm a successful response")
        return result["payload"]

    def list_extractions(self):
        result = self._call("listExtractions").get("result")
        if not isinstance(result, list) or any(not isinstance(task, dict) for task in result):
            raise CordisError("Invalid CORDIS task list")
        # The live list endpoint uses taskId, while the status endpoint and
        # published schema use taskID. Normalize without exposing export URLs.
        return [
            {**task, "taskID": task.get("taskID", task.get("taskId"))}
            for task in result
        ]

    def create_extraction(self, query, output_format="csv"):
        if not query or len(query) > 10000:
            raise CordisError("A nonempty CORDIS query of at most 10000 characters is required")
        if output_format not in {"csv", "json", "xml", "xlsx", "summary"}:
            raise CordisError("Unsupported CORDIS output format")
        # A new DET extraction can cancel another running extraction. Never
        # proceed if a listed task's completion cannot be established.
        if any(not finished(task) for task in self.list_extractions()):
            raise CordisError(
                "An active or unrecognised CORDIS extraction exists; no new extraction started"
            )
        task = self._call(
            "getExtraction", query=query, outputFormat=output_format, archived="false"
        )
        cancelled = task.get("cancelledExtraction")
        if cancelled and (not isinstance(cancelled, dict) or cancelled.get("taskID")):
            raise CordisError(
                "CORDIS reported a concurrent extraction cancellation; stop and inspect the account"
            )
        if not isinstance(task.get("taskID"), int) or task["taskID"] <= 0:
            raise CordisError("CORDIS returned an invalid extraction task ID")
        return task

    def extraction_status(self, task_id):
        if not isinstance(task_id, int) or task_id <= 0:
            raise CordisError("A positive extraction task ID is required")
        result = self._call("getExtractionStatus", taskId=task_id)
        if str(result.get("taskID")) != str(task_id):
            raise CordisError("CORDIS returned a different extraction task")
        return result

    def wait(self, task_id, *, timeout=600, interval=15):
        deadline = time.monotonic() + timeout
        while True:
            task = self.extraction_status(task_id)
            if task.get("destinationFileUri") and successful(task):
                return task
            if finished(task):
                raise CordisError("CORDIS extraction ended without a downloadable file")
            if time.monotonic() >= deadline:
                raise CordisError("CORDIS extraction is still pending; resume using its task ID")
            time.sleep(min(interval, max(0, deadline - time.monotonic())))

    def download(self, task_id, output, *, limit=250 * 1024 * 1024):
        task = self.extraction_status(task_id)
        uri = task.get("destinationFileUri")
        if not successful(task) or not isinstance(uri, str) or not uri:
            raise CordisError("CORDIS extraction is not confirmed ready for download")
        url = urljoin("https://cordis.europa.eu/", uri)
        if not cordis_url(url):
            raise CordisError("CORDIS returned a download URL outside its HTTPS origin")
        if unquote(urlsplit(url).path).rstrip("/") in {
            "/api/dataextractions/getExtraction",
            "/api/dataextractions/cancelExtraction",
            "/api/dataextractions/deleteExtraction",
        }:
            raise CordisError("A CORDIS modifying operation cannot be used as a download URL")
        output = Path(output)
        if output.exists():
            raise CordisError("Output already exists; choose another file")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with self._download_opener.open(Request(url), timeout=60) as response:
                with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                    digest = hashlib.sha256()
                    size = 0
                    while block := response.read(256 * 1024):
                        size += len(block)
                        if size > limit:
                            raise CordisError("CORDIS export exceeded the download size limit")
                        handle.write(block)
                        digest.update(block)
            if not size:
                raise CordisError("CORDIS export was empty")
            # link() refuses a concurrently created destination instead of
            # overwriting another export. Both paths are on the same filesystem.
            os.link(temporary, output)
            return {
                "task_id": task_id,
                "bytes": size,
                "sha256": digest.hexdigest(),
                "file": str(output),
            }
        except HTTPError as error:
            raise CordisError(f"CORDIS download returned HTTP {error.code}") from None
        except (URLError, TimeoutError, OSError):
            raise CordisError("CORDIS download failed; no existing export was replaced") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
