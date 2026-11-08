import hashlib
import json

import pytest

from scripts.record_document_source_reviews import validate_evidence
from app.services.tools.document_search import search_documents_execute


def test_notice_cannot_invent_a_publication_date(tmp_path):
    file = tmp_path / "register.json"
    file.write_text(
        json.dumps({"reference": "C(2026)4323", "date": "2026-06-25", "version": "final"})
    )
    row = {
        "kind": "metadata_notice",
        "source_url": "https://ec.europa.eu/register/example",
        "file_path": str(file),
        "file_hash": hashlib.sha256(file.read_bytes()).hexdigest(),
        "evidence_fields": {"date": "2026-06-25", "version": "final"},
    }
    validate_evidence(row)
    with pytest.raises(ValueError, match="official metadata"):
        validate_evidence({**row, "evidence_fields": {"date": "2026-11-08"}})


def test_unreviewed_file_change_is_rejected(tmp_path):
    file = tmp_path / "source.pdf"
    file.write_bytes(b"%PDF-reviewed")
    row = {
        "kind": "candidate",
        "source_url": "https://ec.europa.eu/example.pdf",
        "file_path": str(file),
        "file_hash": hashlib.sha256(file.read_bytes()).hexdigest(),
    }
    file.write_bytes(b"%PDF-changed")
    with pytest.raises(ValueError, match="changed since review"):
        validate_evidence(row)


@pytest.mark.asyncio
async def test_replaced_source_review_does_not_keep_warning_users(monkeypatch):
    from types import SimpleNamespace

    class Query:
        def select(self, *args):
            return self

        def contains(self, *args):
            return self

        def limit(self, *args):
            return self

        def execute(self):
            return SimpleNamespace(
                data=[
                    {
                        "title": "Replaced candidate",
                        "source_url": "https://ec.europa.eu/old.pdf",
                        "metadata": {"programme": "horizon_europe", "superseded_by": "approved-id"},
                    },
                    {
                        "title": "Pending candidate",
                        "source_url": "https://ec.europa.eu/current.pdf",
                        "metadata": {
                            "programme": "horizon_europe",
                            "provenance": {"warning": "Date is unconfirmed"},
                        },
                    },
                ]
            )

    class Vector:
        supabase = SimpleNamespace(client=SimpleNamespace(table=lambda *args: Query()))

        def hybrid_search(self, **kwargs):
            return []

    monkeypatch.setattr("app.services.vector_search_service.VectorSearchService", Vector)
    result = await search_documents_execute("Horizon Europe unit costs")
    assert [row["title"] for row in result["pending_source_reviews"]] == ["Pending candidate"]
    assert result["source_instruction"]
