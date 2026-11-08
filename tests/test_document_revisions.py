"""Regression checks for source integrity and year-correct document revisions."""

import hashlib
import json

import pytest

from app.services.call_document_service import CallDocumentService, document_period
from scripts.apply_document_refresh import validate_source


def test_framework_period_is_not_document_edition():
    assert document_period("https://ec.europa.eu/docs/2021-2027/common/guidance/aga_en.pdf") is None
    assert (
        document_period(
            "https://ec.europa.eu/docs/2021-2027/horizon/wp-call/2026-2027/wp-4-health.pdf"
        )
        == "2026-2027"
    )


@pytest.mark.parametrize("part,cluster", [(4, 1), (7, 4), (9, 6)])
def test_work_programme_part_numbers_are_not_cluster_numbers(part, cluster):
    service = CallDocumentService.__new__(CallDocumentService)
    result = service._classify_document_from_url(
        f"https://ec.europa.eu/docs/2021-2027/horizon/wp-call/2026-2027/wp-{part}-test.pdf",
        "Work Programme",
    )
    assert result["scope_identifier"] == f"CLUSTER-{cluster}"
    assert "2026-2027" in result["key"]


def test_new_european_bauhaus_is_not_general_annexes():
    service = CallDocumentService.__new__(CallDocumentService)
    result = service._classify_document_from_url(
        "https://ec.europa.eu/horizon/wp-call/2025/wp-13-new-european-bauhaus-facility.pdf",
        "Work Programme",
    )
    assert result["type"] != "general_annexes"
    assert service._extract_cluster_from_call_id("HORIZON-HLTH-2027-03-TOOL-08") == "CLUSTER-1"


@pytest.fixture
def staged_source(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-test fixture")
    text = tmp_path / "pages.json"
    pages = ["Official source content. " * 30]
    text.write_text(json.dumps(pages))
    return {
        "url": "https://ec.europa.eu/source.pdf",
        "download_file": str(pdf),
        "page_text_file": str(text),
        "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "page_text_sha256": hashlib.sha256(
            json.dumps(pages, ensure_ascii=False).encode()
        ).hexdigest(),
    }


@pytest.mark.parametrize("field", ["sha256", "page_text_sha256"])
def test_changed_pdf_or_extraction_cannot_be_published(staged_source, field):
    assert validate_source(staged_source)
    with pytest.raises(ValueError, match="differs"):
        validate_source({**staged_source, field: "tampered"})


def test_external_source_cannot_be_approved(staged_source):
    with pytest.raises(ValueError, match="official HTTPS"):
        validate_source({**staged_source, "url": "https://ec.europa.eu.example.org/source.pdf"})
