"""Dashboard privacy, source classification, deduplication and failure states."""

import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.services.data_overview import document_inventory, document_programme, public_url


def document(id, **kwargs):
    metadata = kwargs.pop("metadata", {})
    metadata = {"programme": "horizon_europe", "provenance": {"status": "verified_exact_bytes"}, **metadata}
    return {
        "id": id,
        "title": "Health programme",
        "status": "active",
        "chunks": 12,
        "metadata": metadata,
        **kwargs,
    }


def test_shared_rules_and_unassigned_records_are_not_claimed_as_one_programme():
    assert (
        document_programme(
            {
                "title": "AGA",
                "source_url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/common/aga.pdf",
                    }
        )
        == "shared"
    )
    assert document_programme({"title": "European Health Data Space"}) == "shared"
    assert document_programme({"title": "Creative Europe Work Programme"}) == "creative_europe"
    assert document_programme({"title": "Unknown legacy record"}) == "unassigned"


def test_only_explicit_copies_merge_and_pending_and_archived_records_stay_distinct():
    general = [
        document("a", file_hash="same"),
        document("old", file_hash="old", status="archived"),
        document("pending", chunks=0, metadata={"programme": "life", "review_state": "pending"}),
    ]
    shared = [
        document("copy", chunks=5, metadata={"horizon_document_id": "a"}),
        document("different-edition", file_hash="different", title="Health programme"),
    ]
    result = document_inventory(general, shared)
    assert result["records"] == 4
    assert result["searchable"] == 2 and result["pending"] == 1 and result["archived"] == 1
    merged = next(d for d in result["documents"] if d["id"] == "a")
    assert merged["chunks"] == 17 and merged["stores"] == ["general", "call_library"]


def test_inventory_does_not_expose_private_paths_or_metadata():
    result = document_inventory(
        [
            document(
                "one",
                file_path="/private/file.pdf",
                metadata={"programme": "life", "internal_secret": "secret"},
                source_url="https://example.com/private?token=secret",
            )
        ],
        [],
    )
    row = result["documents"][0]
    assert row["source_url"] is None and "metadata" not in row and "file_path" not in row
    assert public_url("https://ec.europa.eu@evil.example/document.pdf") is None
    assert public_url("https://ec.europa.eu/document.pdf") == "https://ec.europa.eu/document.pdf"


@pytest.mark.asyncio
async def test_graph_outage_is_unavailable_not_a_zero_count(monkeypatch):
    import app.services.data_overview as service

    monkeypatch.setattr(
        service, "postgres_overview", lambda: {"status": "available", "projects": {"count": 4}}
    )

    def unavailable():
        raise OSError("private database connection information")

    monkeypatch.setattr(service, "graph_overview", unavailable)
    result = await service.data_overview()
    assert result["status"] == "partial" and result["database"]["projects"]["count"] == 4
    assert result["graph"]["status"] == "unavailable" and "connections" not in result["graph"]
    assert "private database" not in str(result)


def test_endpoint_requires_authentication_even_when_result_is_cached(monkeypatch):
    from app.api import data_overview_routes as routes
    from app.core.auth import get_current_user, User

    app = FastAPI()
    app.include_router(routes.router)
    monkeypatch.setattr(routes, "_cache", {"status": "available", "checked_at": "synthetic"})
    monkeypatch.setattr(routes, "_cache_until", float("inf"))
    client = TestClient(app)
    assert client.get("/api/data-overview").status_code == 401
    app.dependency_overrides[get_current_user] = lambda: User(id="synthetic", roles=["viewer"])
    response = client.get("/api/data-overview")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
