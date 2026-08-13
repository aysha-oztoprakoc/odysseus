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
