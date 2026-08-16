from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from routes.files_routes import setup_files_routes
from routes.files_security import CapabilityStore


class FakeAuthManager:
    is_configured = True

    def is_admin(self, username: str) -> bool:
        return username == "admin"

    def verify_password(self, username: str, password: str) -> bool:
        return username == "admin" and password == "correct-password"


@pytest.fixture
def files_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ODYSSEUS_FILES_ADMIN_ROOTS", str(tmp_path))
    app = FastAPI()
    app.state.auth_manager = FakeAuthManager()

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        request.state.current_user = "admin"
        return await call_next(request)

    app.include_router(setup_files_routes())
    return TestClient(app)


def _unlock(client: TestClient) -> str:
    response = client.post(
        "/api/files/capability",
        json={"password": "correct-password"},
    )
    assert response.status_code == 200
    return str(response.json()["capability"])


def test_files_capability_requires_fresh_admin_password(files_client: TestClient) -> None:
    # Given
    body = {"password": "wrong-password"}

    # When
    response = files_client.post("/api/files/capability", json=body)

    # Then
    assert response.status_code == 401
    assert "capability" not in response.text


def test_browse_requires_scoped_capability(files_client: TestClient) -> None:
    # Given
    no_capability_headers: dict[str, str] = {}

    # When
    response = files_client.get("/api/files/browse", headers=no_capability_headers)

    # Then
    assert response.status_code == 403


def test_capability_cannot_escape_root_or_follow_symlink(
    files_client: TestClient,
    tmp_path: Path,
) -> None:
    # Given
    outside = tmp_path.parent / "outside-files-admin.txt"
    outside.write_text("blocked", encoding="utf-8")
    (tmp_path / "escape-link").symlink_to(outside)
    headers = {"X-Odysseus-Files-Capability": _unlock(files_client)}

    # When
    traversal = files_client.get(
        "/api/files/read",
        params={"path": str(outside)},
        headers=headers,
    )
    symlink = files_client.get(
        "/api/files/read",
        params={"path": str(tmp_path / "escape-link")},
        headers=headers,
    )

    # Then
    assert traversal.status_code == 403
    assert symlink.status_code == 403


def test_secret_paths_and_upload_filename_traversal_are_denied(
    files_client: TestClient,
    tmp_path: Path,
) -> None:
    # Given
    secret_file = tmp_path / ".env"
    secret_file.write_text("TOKEN=secret", encoding="utf-8")
    headers = {"X-Odysseus-Files-Capability": _unlock(files_client)}

    # When
    secret_response = files_client.get(
        "/api/files/read",
        params={"path": str(secret_file)},
        headers=headers,
    )
    upload_response = files_client.post(
        "/api/files/upload",
        params={"dir_path": str(tmp_path)},
        files={"file": ("../escape.txt", b"blocked", "text/plain")},
        headers=headers,
    )

    # Then
    assert secret_response.status_code == 403
    assert upload_response.status_code == 400
    assert not (tmp_path.parent / "escape.txt").exists()


def test_archive_traversal_is_rejected_without_partial_extraction(
    files_client: TestClient,
    tmp_path: Path,
) -> None:
    # Given
    archive = tmp_path / "hostile.zip"
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("safe.txt", "safe")
        writer.writestr("../escape.txt", "blocked")
    headers = {"X-Odysseus-Files-Capability": _unlock(files_client)}

    # When
    response = files_client.post(
        "/api/files/extract",
        json={"path": str(archive)},
        headers=headers,
    )

    # Then
    assert response.status_code == 400
    assert not (tmp_path / "safe.txt").exists()
    assert not (tmp_path.parent / "escape.txt").exists()


def test_files_explorer_never_interpolates_server_names_into_html() -> None:
    # Given
    source = Path("static/js/filesExplorer.js").read_text(encoding="utf-8")

    # When
    unsafe_sink_present = ".innerHTML" in source

    # Then
    assert unsafe_sink_present is False


def test_files_upload_rejects_payload_over_25_mib(
    files_client: TestClient,
    tmp_path: Path,
) -> None:
    # Given
    headers = {"X-Odysseus-Files-Capability": _unlock(files_client)}
    payload = io.BytesIO(b"x" * (25 * 1024 * 1024 + 1))

    # When
    response = files_client.post(
        "/api/files/upload",
        params={"dir_path": str(tmp_path)},
        files={"file": ("oversized.bin", payload, "application/octet-stream")},
        headers=headers,
    )

    # Then
    assert response.status_code == 413
    assert not (tmp_path / "oversized.bin").exists()


def test_files_capability_expires_after_five_minutes() -> None:
    # Given
    now = [100.0]
    capabilities = CapabilityStore(clock=lambda: now[0])
    token, _ = capabilities.issue("admin")

    # When
    valid_before_expiry = capabilities.authorize(token, "admin")
    now[0] += 301.0
    valid_after_expiry = capabilities.authorize(token, "admin")

    # Then
    assert valid_before_expiry is True
    assert valid_after_expiry is False


def test_wiki_ui_uses_put_specific_reads_and_no_inline_handlers() -> None:
    # Given
    source = Path("static/js/harness.js").read_text(encoding="utf-8")

    # When
    unsafe_inline_handlers = "onclick=" in source

    # Then
    assert unsafe_inline_handlers is False
    assert "method: 'PUT'" in source
    assert "/wiki/memories/${encodeURIComponent(id)}" in source
    assert "_get(`/api/reins/wiki/memories`)" not in source
