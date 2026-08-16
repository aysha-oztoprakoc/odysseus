"""
Unit tests for odysseus/routes/reins_routes.py endpoints.
Verifies admin gating and proper forwarding to mcp_client.call_tool.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from routes.reins_routes import setup_reins_routes
import routes.reins_routes as reins_routes_module


@pytest.fixture
def app_and_client(monkeypatch: pytest.MonkeyPatch):
    # Disable actual admin check by default for route testing, but we will test admin rejection separately
    monkeypatch.setattr(reins_routes_module, "require_admin", lambda request: None)
    
    app = FastAPI()
    app.include_router(setup_reins_routes())
    client = TestClient(app)
    return app, client


def test_coord_status_endpoint(app_and_client, monkeypatch: pytest.MonkeyPatch):
    _, client = app_and_client
    
    async def mock_call_tool(tool_name: str, **kwargs):
        assert tool_name == "coord_status"
        return {"slots": []}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    response = client.get("/api/reins/coord/status")
    assert response.status_code == 200
    assert response.json() == {"slots": []}


def test_coord_load_endpoint(app_and_client, monkeypatch: pytest.MonkeyPatch):
    _, client = app_and_client

    async def mock_call_tool(tool_name: str, **kwargs):
        assert tool_name == "coord_load"
        assert kwargs == {"model": "qwen2.5-coder-7b"}
        return {"status": "loaded"}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    response = client.post("/api/reins/coord/load", json={"model": "qwen2.5-coder-7b"})
    assert response.status_code == 200
    assert response.json() == {"status": "loaded"}


def test_hardware_scan_endpoint(app_and_client, monkeypatch: pytest.MonkeyPatch):
    _, client = app_and_client

    async def mock_call_tool(tool_name: str, **kwargs):
        assert tool_name == "hardware_scan"
        return {"vram_gb": 16.0}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    response = client.get("/api/reins/hardware/scan")
    assert response.status_code == 200
    assert response.json() == {"vram_gb": 16.0}


def test_dataset_export_endpoint(app_and_client, monkeypatch: pytest.MonkeyPatch):
    _, client = app_and_client

    async def mock_call_tool(tool_name: str, **kwargs):
        assert tool_name == "dataset_export"
        assert kwargs["out_path"] == "/tmp/dataset.jsonl"
        return {"records": 42}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    response = client.post("/api/reins/dataset/export", json={"out_path": "/tmp/dataset.jsonl"})
    assert response.status_code == 200
    assert response.json() == {"records": 42}


def test_train_status_endpoint(app_and_client, monkeypatch: pytest.MonkeyPatch):
    _, client = app_and_client

    async def mock_call_tool(tool_name: str, **kwargs):
        assert tool_name == "train_status"
        return {"qlora_capable": True}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    response = client.get("/api/reins/train/status")
    assert response.status_code == 200
    assert response.json() == {"qlora_capable": True}


def test_admin_gating(monkeypatch: pytest.MonkeyPatch):
    def enforce_admin_fail(request: Request):
        raise HTTPException(status_code=403, detail="Admin required")

    monkeypatch.setattr(reins_routes_module, "require_admin", enforce_admin_fail)

    app = FastAPI()
    app.include_router(setup_reins_routes())
    client = TestClient(app)

    response = client.get("/api/reins/coord/status")
    assert response.status_code == 403


def test_page_update_uses_the_mcp_update_contract(app_and_client, monkeypatch: pytest.MonkeyPatch):
    # Given
    _, client = app_and_client
    calls = []

    async def mock_call_tool(tool_name: str, **kwargs):
        calls.append((tool_name, kwargs))
        return {"slug": kwargs["slug"]}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    _, client = app_and_client

    # When
    response = client.put(
        "/api/reins/wiki/pages/safe-page",
        json={"title": "Safe", "content": "updated"},
    )

    # Then
    assert response.status_code == 200
    assert calls == [
        (
            "wiki_update_page",
            {
                "slug": "safe-page",
                "title": "Safe",
                "content": "updated",
                "category": "general",
                "fmt": "md",
                "metadata_json": "{}",
            },
        )
    ]


def test_memory_revision_retains_old_record_through_mcp(app_and_client, monkeypatch: pytest.MonkeyPatch):
    # Given
    _, client = app_and_client

    async def mock_call_tool(tool_name: str, **kwargs):
        assert tool_name == "wiki_revise_memory"
        assert kwargs["uid"] == "old-uid"
        return {"old_uid": "old-uid", "new_uid": "new-uid", "old_retained": True}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    _, client = app_and_client

    # When
    response = client.post(
        "/api/reins/wiki/memories/old-uid/revisions",
        json={"text": "replacement fact", "category": "facts"},
    )

    # Then
    assert response.status_code == 201
    assert response.json()["old_retained"] is True


def test_wiki_pagination_is_bounded_before_mcp_call(app_and_client) -> None:
    # Given
    _, client = app_and_client

    # When
    response = client.get("/api/reins/wiki/memories?limit=201")

    # Then
    assert response.status_code == 422


def test_cli_requests_return_task_trail_operation_id(app_and_client, monkeypatch: pytest.MonkeyPatch):
    # Given
    _, client = app_and_client

    async def mock_call_tool(tool_name: str, **kwargs):
        assert tool_name == "trail_queue"
        assert kwargs["task_type"] == "odysseus:cli:backup"
        return {"task_id": "operation-123"}

    monkeypatch.setattr(reins_routes_module, "call_tool", mock_call_tool)
    _, client = app_and_client

    # When
    response = client.post("/api/reins/cli/backup")

    # Then
    assert response.status_code == 202
    assert response.json() == {"operation_id": "operation-123"}


def test_secret_revelation_route_does_not_exist(app_and_client) -> None:
    # Given
    _, client = app_and_client

    # When
    response = client.post(
        "/api/reins/system/secret",
        json={"name": "ANY_SECRET", "password": "non-empty"},
    )

    # Then
    assert response.status_code == 404
