"""Unresolved reference records are retained but excluded from ordinary retrieval."""

from unittest.mock import MagicMock
from pathlib import Path

import pytest

from app.services.document_trust import public_source_searchable, quarantine_candidate
from app.services.data_overview import document_inventory
from scripts.quarantine_unresolved_documents import plan_quarantine, apply_changes


def row(**changes):
    return {
        "store": "horizon_documents",
        "id": "example",
        "title": "Legacy guide",
        "file_hash": "hash",
        "status": "active",
        "created_by": None,
        "metadata": {},
        **changes,
    }


@pytest.mark.parametrize("status", ["verified_exact_bytes", "verified_official_download"])
def test_verified_historical_editions_remain_searchable(status):
    metadata = {"provenance": {"status": status}, "programme_year": "2021"}
    assert public_source_searchable(metadata)
    assert not plan_quarantine([row(metadata=metadata)], "today")


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        {"provenance": {"status": "unverified"}},
        {"provenance": {"status": "verified_official_metadata_only"}},
        {"provenance": {"status": "verified_exact_bytes"}, "review_state": "pending"},
        {"provenance": {"status": "verified_exact_bytes"}, "retrieval_status": "quarantined"},
        {"provenance": {"status": "verified_exact_bytes"}, "superseded_by": "new"},
    ],
)
def test_public_retrieval_fails_closed(metadata):
    assert not public_source_searchable(metadata)


def test_pending_reviews_and_user_documents_are_not_quarantined():
    assert not plan_quarantine([row(metadata={"review_state": "pending"})], "today")
    assert not plan_quarantine([row(created_by="user-id")], "today")


def test_quarantine_is_idempotent_and_keeps_the_original_state():
    before = row(metadata={"provenance": {"status": "source_unknown"}})
    plan = plan_quarantine([before], "today")
    assert len(plan) == 1
    after = plan[0]
    assert before["status"] == after["status"] == "active"
    assert after["status_after"] == "archived"
    assert after["metadata_after"]["retrieval_status"] == "quarantined"
    assert not plan_quarantine(
        [{**after, "status": "archived", "metadata": after["metadata_after"]}], "tomorrow"
    )


def test_stale_record_rolls_back_and_restore_checks_quarantined_state():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.rowcount = 0
    changes = plan_quarantine([row()], "today")
    with pytest.raises(ValueError, match="changed"):
        apply_changes(conn, changes)
    assert conn.__exit__.call_args.args[0] is ValueError
    cursor.rowcount = 1
    apply_changes(conn, changes, restore=True)
    sql, params = cursor.execute.call_args.args
    assert "created_by IS NULL" in sql and "status=%s" in sql
    assert params[1] == "active"
    assert params[-1] == "archived"
    assert params[-2].adapted == changes[0]["metadata_after"]


def test_shared_quarantine_is_visible_as_archived_in_dashboard():
    inventory = document_inventory(
        [],
        [
            {
                "id": 1,
                "title": "Retained old decision",
                "chunks": 4,
                "metadata": {"retrieval_status": "quarantined"},
            }
        ],
    )
    assert inventory["searchable"] == 0
    assert inventory["archived"] == 1
    assert inventory["documents"][0]["status"] == "archived"


def test_all_retrieval_rpcs_apply_trust_before_candidate_limits():
    sql = Path("scripts/sql/20261109_verified_document_retrieval.sql").read_text()
    assert sql.count("public.mapit_public_source_searchable(active_doc.metadata)") == 2
    assert sql.count("public.mapit_public_source_searchable(d.metadata)") == 3
    assert "created_by IS NOT NULL" in sql


def test_unverified_active_public_record_is_pending_in_dashboard():
    inventory = document_inventory(
        [{"id": "new", "title": "New import", "status": "active", "chunks": 5, "metadata": {}}], []
    )
    assert inventory["searchable"] == 0
    assert inventory["pending"] == 1


def test_new_download_retains_prior_pdf_and_uses_content_specific_key(tmp_path, monkeypatch):
    import hashlib
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app.services.call_document_service import CallDocumentService

    service = CallDocumentService.__new__(CallDocumentService)
    service.shared_docs_dir = tmp_path
    service._check_document_exists = Mock(return_value=None)
    service._store_document = Mock(return_value=42)
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    service.db_pool = SimpleNamespace(getconn=lambda: connection, putconn=lambda c: None)
    response = Mock()
    payload = b"%PDF-new-official-download"
    response.iter_content.return_value = iter([payload])
    monkeypatch.setattr("app.services.call_document_service.requests.get", lambda *a, **k: response)
    monkeypatch.setitem(
        sys.modules,
        "scripts.manual_document_upload",
        SimpleNamespace(
            SimpleDocumentParser=lambda: SimpleNamespace(
                parse_pdf=lambda p: {"full_text": "parsed", "metadata": {}}
            ),
            SimpleChunker=lambda: SimpleNamespace(chunk_document=lambda *a: []),
        ),
    )
    original = tmp_path / "guide.pdf"
    original.write_bytes(b"%PDF-retained-original")
    assert (
        service._download_and_process_document(
            {
                "url": "https://ec.europa.eu/guide.pdf",
                "key": "guide",
                "title": "Guide",
                "type": "guidance",
                "scope": "global",
            }
        )
        == 42
    )
    stored = service._store_document.call_args.kwargs
    assert original.read_bytes() == b"%PDF-retained-original"
    assert stored["doc_key"] == "guide_" + hashlib.sha256(payload).hexdigest()
    assert Path(stored["file_path"]) != original
    assert Path(stored["file_path"]).read_bytes() == payload


def test_web_upload_cannot_assert_verified_origin():
    from unittest.mock import Mock
    from app.services.ingestion_service import DocumentIngestionService

    service = DocumentIngestionService.__new__(DocumentIngestionService)
    service.processor = Mock()
    service.processor.scrape_web_page.return_value = (
        "Example web content",
        {"page_title": "Example"},
    )
    service.supabase = Mock()
    service.supabase.insert_document.return_value = {"id": "new"}
    service._complete_ingestion_pipeline = Mock(return_value={"success": True})
    service.ingest_web_page(
        "https://example.org/source", metadata={"provenance": {"status": "verified_exact_bytes"}}
    )
    inserted = service.supabase.insert_document.call_args.args[0]
    assert inserted["metadata"]["provenance"]["status"] == "unverified"


def test_duplicate_call_import_preserves_existing_metadata_and_chunks():
    from types import SimpleNamespace
    from app.services.call_document_service import CallDocumentService

    service = CallDocumentService.__new__(CallDocumentService)
    cursor = MagicMock()
    cursor.fetchone.side_effect = [None, (42,)]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    service.db_pool = SimpleNamespace(getconn=lambda: conn, putconn=lambda c: None)
    result = service._store_document(
        "guide_hash",
        "guidance",
        "Guide",
        "global",
        None,
        "/retained/new.pdf",
        "hash",
        "https://ec.europa.eu/guide.pdf",
        {"full_text": "text", "metadata": {}},
        [],
    )
    assert result == 42
    statements = [c.args[0] for c in cursor.execute.call_args_list]
    assert "ON CONFLICT (document_key) DO NOTHING" in statements[0]
    assert not any("DELETE FROM" in sql or "DO UPDATE" in sql for sql in statements)


def test_quarantine_reason_is_available_without_exposing_internal_metadata():
    inventory = document_inventory(
        [],
        [
            {
                "id": 1,
                "title": "Old publication",
                "chunks": 4,
                "metadata": {
                    "retrieval_status": "quarantined",
                    "origin_quarantine": {
                        "reason": "Origin could not be established",
                        "internal_path": "/private",
                    },
                },
            }
        ],
    )
    doc = inventory["documents"][0]
    assert doc["source_warning"] == "Origin could not be established"
    assert "metadata" not in doc and "internal_path" not in doc
