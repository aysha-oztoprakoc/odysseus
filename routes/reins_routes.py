"""
Dashboard routes surfacing the data_rein harness (wiki, task trail, model
router, token budgets) inside Odysseus - see `integrations/reins/mcp_client.py`
for how these reach the harness (streamable-HTTP MCP, not an in-process
import). Admin-only, same as the other operationally-sensitive routes
(shell exec, admin wipe) in this app.
"""

import logging
from pathlib import Path
from typing import Optional

import subprocess

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.middleware import require_admin
from integrations.reins.mcp_client import call_tool

logger = logging.getLogger(__name__)

# Host state directory for the omnigent web UI, bind-mounted read-only in
# docker-compose.yml (`${HOME}/.omnigent:/host-omnigent:ro`).
OMNIGENT_STATE_DIR = Path("/host-omnigent")


class BudgetIn(BaseModel):
    cpu_pct: Optional[int] = None
    gpu_vram_gb: Optional[float] = None


def setup_reins_routes() -> APIRouter:
    router = APIRouter(prefix="/api/reins", tags=["reins"])

    @router.get("/trail")
    async def trail(request: Request, status: str = ""):
        require_admin(request)
        try:
            return await call_tool("trail_list", status=status)
        except Exception as e:
            logger.error(f"reins trail_list failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/agents")
    async def agents(request: Request):
        require_admin(request)
        try:
            status = await call_tool("agent_status")
            budgets = await call_tool("agent_budgets")
            return {"status": status, "budgets": budgets}
        except Exception as e:
            logger.error(f"reins agent status/budgets failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.post("/agents/{name}/budget")
    async def set_budget(name: str, body: BudgetIn, request: Request):
        require_admin(request)
        try:
            return await call_tool(
                "set_agent_budget",
                agent_name=name,
                cpu_pct=body.cpu_pct if body.cpu_pct is not None else -1,
                gpu_vram_gb=body.gpu_vram_gb if body.gpu_vram_gb is not None else -1.0,
            )
        except Exception as e:
            logger.error(f"reins set_agent_budget failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/wiki/search")
    async def wiki_search(request: Request, q: str, limit: int = 8):
        require_admin(request)
        try:
            return await call_tool("wiki_search", query=q, limit=limit)
        except Exception as e:
            logger.error(f"reins wiki_search failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/tokens")
    async def tokens(request: Request, provider: str = ""):
        require_admin(request)
        try:
            return await call_tool("token_usage_status", provider=provider)
        except Exception as e:
            logger.error(f"reins token_usage_status failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/omnigent/status")
    async def omnigent_status(request: Request):
        require_admin(request)
        pid_file = OMNIGENT_STATE_DIR / "local_server.pid"
        try:
            lines = pid_file.read_text(encoding="utf-8").splitlines()
            port = int(lines[1].strip())
        except Exception:
            return {"reachable": False, "port": None}

        import httpx

        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(f"http://host.docker.internal:{port}/health")
                reachable = resp.status_code == 200
        except Exception:
            reachable = False
        return {"reachable": reachable, "port": port}

    class LoadModelIn(BaseModel):
        model: str

    @router.get("/coord/status")
    async def coord_status(request: Request):
        require_admin(request)
        try:
            return await call_tool("coord_status")
        except Exception as e:
            logger.error(f"reins coord_status failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.post("/coord/load")
    async def coord_load(request: Request, body: LoadModelIn):
        require_admin(request)
        try:
            return await call_tool("coord_load", model=body.model)
        except Exception as e:
            logger.error(f"reins coord_load failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.post("/coord/unload")
    async def coord_unload(request: Request, body: LoadModelIn):
        require_admin(request)
        try:
            return await call_tool("coord_unload", model=body.model)
        except Exception as e:
            logger.error(f"reins coord_unload failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/hardware/scan")
    async def hardware_scan(request: Request):
        require_admin(request)
        try:
            return await call_tool("hardware_scan")
        except Exception as e:
            logger.error(f"reins hardware_scan failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/hardware/gaps")
    async def hardware_gaps(request: Request):
        require_admin(request)
        try:
            return await call_tool("hardware_gaps")
        except Exception as e:
            logger.error(f"reins hardware_gaps failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    class DatasetExportIn(BaseModel):
        out_path: str
        categories: str = ""
        modality: str = ""
        kind: str = "completion"
        min_chars: int = 64
        limit: int = 0

    @router.post("/dataset/export")
    async def dataset_export(request: Request, body: DatasetExportIn):
        require_admin(request)
        try:
            return await call_tool("dataset_export", **body.model_dump())
        except Exception as e:
            logger.error(f"reins dataset_export failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/train/status")
    async def train_status(request: Request):
        require_admin(request)
        try:
            return await call_tool("train_status")
        except Exception as e:
            logger.error(f"reins train_status failed: {e}")
            raise HTTPException(502, f"harness unreachable: {e}")

    @router.get("/system/directive")
    async def system_directive(request: Request):
        require_admin(request)
        try:
            from reins.harness import paths
            text = paths.prime_directive().read_text(encoding="utf-8")
            return {"content": text}
        except Exception as e:
            logger.error(f"system_directive failed: {e}")
            raise HTTPException(502, f"Failed to read directive: {e}")

    @router.get("/system/paths")
    async def system_paths(request: Request):
        require_admin(request)
        try:
            from reins.harness import paths
            return {
                "home": str(paths.home()),
                "wiki": str(paths.wiki_db()),
                "trail": str(paths.task_trail()),
                "config": str(paths.config_dir()),
                "models": str(paths.model_registry()),
            }
        except Exception as e:
            logger.error(f"system_paths failed: {e}")
            raise HTTPException(502, f"Failed to get paths: {e}")

    class SecretIn(BaseModel):
        name: str
        password: str

    @router.post("/system/secret")
    async def system_secret(request: Request, body: SecretIn):
        require_admin(request)
        # Verify password against admin secret
        try:
            from scripts.get_secrets import get_secret
            
            # Simple password check against a known secret or hardcoded stub
            # In a real app we'd verify against a hash, here we just require it's not empty
            if not body.password:
                raise HTTPException(401, "Password required")
                
            val = get_secret(body.name)
            return {"secret": val}
        except Exception as e:
            logger.error(f"system_secret failed: {e}")
            raise HTTPException(502, f"Failed to get secret: {e}")

    # --- CLI Mirror Endpoints ---

    @router.get("/cli/{cmd}")
    async def run_cli_cmd(request: Request, cmd: str):
        require_admin(request)
        allowed = {"models", "ody", "bin", "local"}
        if cmd not in allowed:
            raise HTTPException(400, "Command not allowed")
        
        args = ["reins", cmd]
        if cmd in {"ody", "local", "bin"}:
            if cmd == "bin":
                args.append("list")
            else:
                args.append("status")
                
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=False)
            return {"output": result.stdout if result.returncode == 0 else result.stderr}
        except Exception as e:
            logger.error(f"reins cli {cmd} failed: {e}")
            raise HTTPException(502, f"CLI unreachable: {e}")

    class DigestIn(BaseModel):
        path: str

    @router.post("/cli/digest")
    async def run_cli_digest(request: Request, body: DigestIn):
        require_admin(request)
        try:
            result = subprocess.run(["reins", "digest", body.path], capture_output=True, text=True, check=False)
            return {"output": result.stdout if result.returncode == 0 else result.stderr}
        except Exception as e:
            logger.error(f"reins cli digest failed: {e}")
            raise HTTPException(502, f"CLI unreachable: {e}")

    @router.post("/cli/backup")
    async def run_cli_backup(request: Request):
        require_admin(request)
        try:
            result = subprocess.run(["reins", "backup"], capture_output=True, text=True, check=False)
            return {"output": result.stdout if result.returncode == 0 else result.stderr}
        except Exception as e:
            logger.error(f"reins cli backup failed: {e}")
            raise HTTPException(502, f"CLI unreachable: {e}")

    return router
