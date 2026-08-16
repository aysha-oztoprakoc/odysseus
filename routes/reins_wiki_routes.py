from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field


logger = logging.getLogger(__name__)
ToolCall = Callable[..., Awaitable[Any]]
AdminCheck = Callable[[Request], None]


class PageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=2 * 1024 * 1024)
    slug: str = Field(default="", max_length=200)
    category: str = Field(default="general", min_length=1, max_length=200)
    fmt: str = Field(default="md", min_length=1, max_length=32)
    metadata_json: str = Field(default="{}", min_length=1, max_length=64 * 1024)


class MemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    text: str = Field(min_length=1, max_length=2 * 1024 * 1024)
    category: str = Field(default="general", min_length=1, max_length=200)


def setup_reins_wiki_routes(call_tool: ToolCall, require_admin: AdminCheck) -> APIRouter:
    router = APIRouter(prefix="/wiki")

    async def call(name: str, **kwargs: Any) -> Any:
        try:
            result = await call_tool(name, **kwargs)
        except Exception as error:
            logger.error("reins wiki tool failed", extra={"tool": name, "error_type": type(error).__name__})
            raise HTTPException(502, "Harness unreachable") from error
        if isinstance(result, dict) and result.get("error"):
            status = {"not_found": 404, "conflict": 409, "invalid": 422}.get(str(result.get("code")), 502)
            raise HTTPException(status, str(result["error"]))
        return result

    @router.get("/search")
    async def search(
        request: Request,
        q: Annotated[str, Query(min_length=1, max_length=500)],
        limit: Annotated[int, Query(ge=1, le=50)] = 15,
    ) -> Any:
        require_admin(request)
        return await call("wiki_search", query=q, limit=limit)

    @router.get("/pages")
    async def list_pages(
        request: Request,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    ) -> Any:
        require_admin(request)
        return await call("wiki_list_pages", limit=limit, offset=offset)

    @router.get("/pages/{slug}")
    async def get_page(request: Request, slug: str) -> Any:
        require_admin(request)
        return await call("wiki_get_page", slug=slug)

    @router.post("/pages", status_code=201)
    async def create_page(request: Request, body: PageInput) -> Any:
        require_admin(request)
        return await call("wiki_create_page", **body.model_dump())

    @router.put("/pages/{slug}")
    async def update_page(request: Request, slug: str, body: PageInput) -> Any:
        require_admin(request)
        values = body.model_dump(exclude={"slug"})
        return await call("wiki_update_page", slug=slug, **values)

    @router.delete("/pages/{slug}")
    async def delete_page(request: Request, slug: str) -> Any:
        require_admin(request)
        return await call("wiki_delete_page", slug=slug)

    @router.get("/memories")
    async def list_memories(
        request: Request,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    ) -> Any:
        require_admin(request)
        return await call("wiki_list_memories", limit=limit, offset=offset)

    @router.get("/memories/{uid}")
    async def get_memory(request: Request, uid: str) -> Any:
        require_admin(request)
        return await call("wiki_get_memory", uid=uid)

    @router.post("/memories", status_code=201)
    async def create_memory(request: Request, body: MemoryInput) -> Any:
        require_admin(request)
        return await call("wiki_create_memory", **body.model_dump())

    @router.post("/memories/{uid}/revisions", status_code=201)
    async def revise_memory(request: Request, uid: str, body: MemoryInput) -> Any:
        require_admin(request)
        return await call("wiki_revise_memory", uid=uid, **body.model_dump())

    @router.delete("/memories/{uid}")
    async def delete_memory(request: Request, uid: str) -> Any:
        require_admin(request)
        return await call("wiki_delete_memory", uid=uid)

    return router
