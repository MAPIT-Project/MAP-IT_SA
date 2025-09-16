import os
import pytest
from fastapi.testclient import TestClient

# Ensure app is importable
from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_open_calls_routes_to_search_calls(client):
    # Use a random conversation id to avoid context side-effects
    conversation_id = 987654
    payload = {"message": "Search for open calls for clean energy please", "include_context": False}

    resp = client.post(f"/api/conversation/{conversation_id}/message", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    # Now we expose routing metadata; assert SEARCH_CALLS directly
    assert data.get("routing_decision") == "SEARCH_CALLS"
    assert isinstance(data.get("response", ""), str)


def test_projects_routes_to_search_projects(client):
    conversation_id = 987655
    payload = {"message": "Show me Horizon Europe projects on battery recycling", "include_context": False}

    resp = client.post(f"/api/conversation/{conversation_id}/message", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data.get("routing_decision") == "SEARCH_PROJECTS"
    assert isinstance(data.get("response", ""), str)


def test_faq_routes_to_faq(client):
    conversation_id = 987656
    payload = {"message": "How do I apply on the EU Funding & Tenders portal?", "include_context": False}

    resp = client.post(f"/api/conversation/{conversation_id}/message", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data.get("routing_decision") == "FAQ"
    assert isinstance(data.get("response", ""), str)


def test_capabilities_question(client):
    conversation_id = 987657
    payload = {"message": "What can you help me with?", "include_context": False}

    resp = client.post(f"/api/conversation/{conversation_id}/message", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    # Should route to FAQ and contain capabilities text
    assert data.get("routing_decision") in ("FAQ", None)  # conversation layer may not set routing for direct answer
    assert "open funding opportunities" in data.get("response", "").lower()


