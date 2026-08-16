from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Annotated, Never

from fastapi import APIRouter, File, Header, HTTPException, Query, Request, UploadFile
from anyio.to_thread import run_sync
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from core.middleware import require_admin
from routes.files_archive import extract_archive
from routes.files_security import (
    BROWSE_LIMIT,
    BROWSE_SCAN_LIMIT,
    TEXT_LIMIT,
    UPLOAD_LIMIT,
    CapabilityStore,
    FilePolicyError,
    WorkspacePolicy,
)


logger = logging.getLogger(__name__)
CAPABILITY_HEADER = "X-Odysseus-Files-Capability"


class ReauthenticateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    password: str = Field(min_length=1, max_length=1024)


class WriteRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str = Field(min_length=1, max_length=4096)
    content: str = Field(max_length=TEXT_LIMIT)


class PathRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str = Field(min_length=1, max_length=4096)
    confirm_path: str | None = Field(default=None, max_length=4096)


def _raise_http(error: FilePolicyError) -> Never:
    raise HTTPException(error.status_code, error.detail) from error


def _open_nofollow(path: Path, flags: int, mode: int = 0o600) -> int:
    return os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), mode)


def setup_files_routes(
    policy: WorkspacePolicy | None = None,
    capabilities: CapabilityStore | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/files", tags=["files-admin"])
    workspace = policy or WorkspacePolicy.from_environment()
    grants = capabilities or CapabilityStore()

    def admin_user(request: Request) -> str:
        require_admin(request)
        username = str(getattr(request.state, "current_user", "") or "")
        auth_manager = getattr(request.app.state, "auth_manager", None)
        if not username or auth_manager is None or not auth_manager.is_admin(username):
            raise HTTPException(403, "Fresh admin authentication is required")
        return username

    def authorize(request: Request, capability: str) -> str:
        username = admin_user(request)
        if not grants.authorize(capability, username):
            raise HTTPException(403, "File administration capability is missing or expired")
        return username

    def resolve(raw_path: str, *, must_exist: bool = True) -> Path:
        try:
            return workspace.resolve(raw_path, must_exist=must_exist)
        except FilePolicyError as error:
            _raise_http(error)

    def audit(action: str, username: str, path: Path) -> None:
        logger.info(
            "files_admin.action",
            extra={"action": action, "username": username, "workspace_path": workspace.label(path)},
        )

    @router.post("/capability")
    async def issue_capability(body: ReauthenticateRequest, request: Request) -> dict[str, str | float]:
        username = admin_user(request)
        auth_manager = request.app.state.auth_manager
        valid = await run_sync(auth_manager.verify_password, username, body.password)
        if not valid:
            raise HTTPException(401, "Invalid credentials")
        token, expires_at = grants.issue(username)
        logger.info("files_admin.capability_issued", extra={"username": username})
        return {"capability": token, "expires_at": expires_at}

    @router.get("/browse")
    def browse(
        request: Request,
        path: str = Query(default=""),
        limit: Annotated[int, Query(ge=1, le=BROWSE_LIMIT)] = 50,
        offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
        capability: Annotated[str, Header(alias=CAPABILITY_HEADER)] = "",
    ) -> dict[str, object]:
        username = authorize(request, capability)
        target = resolve(path or str(workspace.roots[0]))
        if not target.is_dir():
            raise HTTPException(400, "Path is not a directory")
        items: list[dict[str, object]] = []
        scanned = 0
        with os.scandir(target) as entries:
            for entry in entries:
                scanned += 1
                if scanned > BROWSE_SCAN_LIMIT:
                    raise HTTPException(413, "Directory contains too many entries")
                if entry.is_symlink():
                    continue
                item_path = resolve(entry.path)
                item_stat = entry.stat(follow_symlinks=False)
                is_directory = entry.is_dir(follow_symlinks=False)
                items.append(
                    {
                        "name": entry.name,
                        "path": str(item_path),
                        "is_dir": is_directory,
                        "size": 0 if is_directory else item_stat.st_size,
                        "mtime": item_stat.st_mtime,
                    }
                )
        items.sort(key=lambda item: (not bool(item["is_dir"]), str(item["name"]).casefold()))
        audit("browse", username, target)
        return {
            "path": str(target),
            "parent": str(target.parent) if target not in workspace.roots else None,
            "items": items[offset : offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }

    @router.get("/read")
    def read_file(
        request: Request,
        path: str = Query(min_length=1, max_length=4096),
        capability: Annotated[str, Header(alias=CAPABILITY_HEADER)] = "",
    ) -> dict[str, str]:
        username = authorize(request, capability)
        target = resolve(path)
        if not target.is_file():
            raise HTTPException(404, "File not found")
        if target.stat().st_size > TEXT_LIMIT:
            raise HTTPException(413, "Text file exceeds 2 MiB")
        descriptor = _open_nofollow(target, os.O_RDONLY)
        with os.fdopen(descriptor, "r", encoding="utf-8") as source:
            try:
                content = source.read(TEXT_LIMIT + 1)
            except UnicodeDecodeError as error:
                raise HTTPException(400, "File is binary or not UTF-8") from error
        if len(content.encode("utf-8")) > TEXT_LIMIT:
            raise HTTPException(413, "Text file exceeds 2 MiB")
        audit("read", username, target)
        return {"content": content}

    @router.post("/write")
    def write_file(
        body: WriteRequest,
        request: Request,
        capability: Annotated[str, Header(alias=CAPABILITY_HEADER)] = "",
    ) -> dict[str, str]:
        username = authorize(request, capability)
        target = resolve(body.path)
        if not target.is_file():
            raise HTTPException(404, "File not found")
        encoded = body.content.encode("utf-8")
        if len(encoded) > TEXT_LIMIT:
            raise HTTPException(413, "Text content exceeds 2 MiB")
        descriptor = _open_nofollow(target, os.O_WRONLY | os.O_TRUNC)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(encoded)
        audit("write", username, target)
        return {"status": "ok"}

    @router.post("/delete")
    def delete_path(
        body: PathRequest,
        request: Request,
        capability: Annotated[str, Header(alias=CAPABILITY_HEADER)] = "",
    ) -> dict[str, str]:
        username = authorize(request, capability)
        target = resolve(body.path)
        if target in workspace.roots:
            raise HTTPException(403, "Workspace roots cannot be deleted")
        if target.is_dir():
            if body.confirm_path != str(target):
                raise HTTPException(409, "Recursive deletion requires exact-path confirmation")
            shutil.rmtree(target)
        else:
            target.unlink()
        audit("delete", username, target)
        return {"status": "ok"}

    @router.post("/extract")
    def extract(
        body: PathRequest,
        request: Request,
        capability: Annotated[str, Header(alias=CAPABILITY_HEADER)] = "",
    ) -> dict[str, str]:
        username = authorize(request, capability)
        target = resolve(body.path)
        if not target.is_file():
            raise HTTPException(404, "Archive not found")
        try:
            destination = extract_archive(target, workspace)
        except FilePolicyError as error:
            _raise_http(error)
        audit("extract", username, target)
        return {"status": "ok", "extract_dir": str(destination)}

    @router.get("/download")
    def download(
        request: Request,
        path: str = Query(min_length=1, max_length=4096),
        capability: Annotated[str, Header(alias=CAPABILITY_HEADER)] = "",
    ) -> StreamingResponse:
        username = authorize(request, capability)
        target = resolve(path)
        if not target.is_file():
            raise HTTPException(404, "File not found")
        descriptor = _open_nofollow(target, os.O_RDONLY)

        def stream():
            with os.fdopen(descriptor, "rb") as source:
                while chunk := source.read(1024 * 1024):
                    yield chunk

        audit("download", username, target)
        headers = {"Content-Disposition": f'attachment; filename="{target.name}"'}
        return StreamingResponse(stream(), media_type="application/octet-stream", headers=headers)

    @router.post("/upload")
    async def upload(
        request: Request,
        dir_path: str = Query(min_length=1, max_length=4096),
        file: UploadFile = File(...),
        capability: Annotated[str, Header(alias=CAPABILITY_HEADER)] = "",
    ) -> dict[str, str]:
        username = authorize(request, capability)
        target_directory = resolve(dir_path)
        if not target_directory.is_dir():
            raise HTTPException(400, "Target is not a directory")
        filename = file.filename or ""
        if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise HTTPException(400, "Upload filename is not safe")
        target = resolve(str(target_directory / filename), must_exist=False)
        if target.exists():
            raise HTTPException(409, "Upload target already exists")
        payload = bytearray()
        while chunk := await file.read(1024 * 1024):
            payload.extend(chunk)
            if len(payload) > UPLOAD_LIMIT:
                raise HTTPException(413, "Upload exceeds 25 MiB")
        descriptor = _open_nofollow(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(payload)
        audit("upload", username, target)
        return {"status": "ok", "path": str(target)}

    return router
