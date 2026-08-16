from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Annotated

import httpx
from fastapi import APIRouter, HTTPException, Path as ApiPath, Request
from pydantic import BaseModel, ConfigDict, Field

from core.middleware import require_admin
from integrations.reins.mcp_client import call_tool
from routes.reins_wiki_routes import setup_reins_wiki_routes


logger = logging.getLogger(__name__)
OMNIGENT_STATE_DIR = Path("/host-omnigent")


class BudgetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cpu_pct: int | None = Field(default=None, ge=1, le=100)
    gpu_vram_gb: float | None = Field(default=None, ge=0, le=1024)


class ModelInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model: str = Field(min_length=1, max_length=500)


class DatasetExportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    out_path: str = Field(min_length=1, max_length=4096)
    categories: str = Field(default="", max_length=4096)
    modality: str = Field(default="", max_length=100)
    kind: str = Field(default="completion", pattern="^(completion|memories)$")
    min_chars: int = Field(default=64, ge=1, le=1_000_000)
    limit: int = Field(default=0, ge=0, le=1_000_000)


class DigestInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str = Field(min_length=1, max_length=4096)


def setup_reins_routes() -> APIRouter:
    router = APIRouter(prefix="/api/reins", tags=["reins"])

    async def call(name: str, **kwargs: Any) -> Any:
        try:
            return await call_tool(name, **kwargs)
        except Exception as error:
            logger.error("reins tool failed", extra={"tool": name, "error_type": type(error).__name__})
            raise HTTPException(502, "Harness unreachable") from error

    @router.get("/trail")
    async def trail(request: Request, status: str = "") -> Any:
        require_admin(request)
        return await call("trail_list", status=status)

    @router.get("/agents")
    async def agents(request: Request) -> dict[str, Any]:
        require_admin(request)
        return {"status": await call("agent_status"), "budgets": await call("agent_budgets")}

    @router.post("/agents/{name}/budget")
    async def set_budget(request: Request, name: str, body: BudgetInput) -> Any:
        require_admin(request)
        return await call(
            "set_agent_budget",
            agent_name=name,
            cpu_pct=body.cpu_pct if body.cpu_pct is not None else -1,
            gpu_vram_gb=body.gpu_vram_gb if body.gpu_vram_gb is not None else -1.0,
        )

    @router.get("/tokens")
    async def tokens(request: Request, provider: str = "") -> Any:
        require_admin(request)
        return await call("token_usage_status", provider=provider)

    @router.get("/omnigent/status")
    async def omnigent_status(request: Request) -> dict[str, Any]:
        require_admin(request)
        try:
            lines = (OMNIGENT_STATE_DIR / "local_server.pid").read_text(encoding="utf-8").splitlines()
            port = int(lines[1].strip())
        except (OSError, ValueError, IndexError):
            return {"reachable": False, "port": None}
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"http://host.docker.internal:{port}/health")
            reachable = response.status_code == 200
        except httpx.HTTPError:
            reachable = False
        return {"reachable": reachable, "port": port}

    @router.get("/coord/status")
    async def coord_status(request: Request) -> Any:
        require_admin(request)
        return await call("coord_status")

    @router.post("/coord/load")
    async def coord_load(request: Request, body: ModelInput) -> Any:
        require_admin(request)
        return await call("coord_load", model=body.model)

    @router.post("/coord/unload")
    async def coord_unload(request: Request, body: ModelInput) -> Any:
        require_admin(request)
        return await call("coord_unload", model=body.model)

    @router.get("/hardware/scan")
    async def hardware_scan(request: Request) -> Any:
        require_admin(request)
        return await call("hardware_scan")

    @router.get("/hardware/gaps")
    async def hardware_gaps(request: Request) -> Any:
        require_admin(request)
        return await call("hardware_gaps")

    @router.post("/dataset/export")
    async def dataset_export(request: Request, body: DatasetExportInput) -> Any:
        require_admin(request)
        return await call("dataset_export", **body.model_dump())

    @router.get("/train/status")
    async def train_status(request: Request) -> Any:
        require_admin(request)
        return await call("train_status")

    @router.get("/system/directive")
    async def system_directive(request: Request) -> Any:
        require_admin(request)
        return await call("system_directive")

    @router.get("/system/paths")
    async def system_paths(request: Request) -> Any:
        require_admin(request)
        return await call("system_paths")

    @router.get("/cli/{cmd}", status_code=202)
    async def queue_cli(
        request: Request,
        cmd: Annotated[str, ApiPath(pattern="^(models|ody|bin|local)$")],
    ) -> dict[str, Any]:
        require_admin(request)
        suffix = {"models": "", "ody": " status", "bin": " list", "local": " status"}[cmd]
        result = await call(
            "trail_queue",
            goal=f"Run reins {cmd}{suffix} and record the bounded result",
            context="Requested by the Odysseus admin dashboard",
            task_type=f"odysseus:cli:{cmd}",
            node="amdy",
        )
        return {"operation_id": result["task_id"]}

    @router.post("/cli/digest", status_code=202)
    async def queue_digest(request: Request, body: DigestInput) -> dict[str, Any]:
        require_admin(request)
        result = await call(
            "trail_queue",
            goal=f"Run reins digest for the selected path: {body.path}",
            context="Requested by the Odysseus admin dashboard",
            task_type="odysseus:cli:digest",
            node="amdy",
        )
        return {"operation_id": result["task_id"]}

    @router.post("/cli/backup", status_code=202)
    async def queue_backup(request: Request) -> dict[str, Any]:
        require_admin(request)
        result = await call(
            "trail_queue",
            goal="Run reins backup and record the bounded result",
            context="Requested by the Odysseus admin dashboard",
            task_type="odysseus:cli:backup",
            node="amdy",
        )
        return {"operation_id": result["task_id"]}

    router.include_router(setup_reins_wiki_routes(call, require_admin))
    return router
