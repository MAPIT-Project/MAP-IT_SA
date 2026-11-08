import hashlib

from scripts.check_pending_document_sources import compare_pdf, unpublished_library_candidates


def test_changed_bytes_require_review_not_automatic_approval():
    original = b"%PDF-original"
    digest = hashlib.sha256(original).hexdigest()
    assert compare_pdf(original, digest)["status"] == "unchanged_pending"
    assert compare_pdf(b"%PDF-revised", digest)["status"] == "changed_requires_review"


def test_existing_annex_renamed_in_library_is_not_a_new_main_document():
    identifier = "8add8eee-106e-4e6a-9481-36b06495136c"
    payload = {
        "data": [
            {
                "id": identifier,
                "name": "C(2026)4323 renamed.PDF",
                "properties": {"currentUserHasAccess": "true", "mimetype": "application/pdf"},
            }
        ]
    }
    assert (
        unpublished_library_candidates(
            payload, [f"https://circabc.europa.eu/sd/a/{identifier}/old.pdf"]
        )
        == []
    )
    assert len(unpublished_library_candidates(payload, [])) == 1
