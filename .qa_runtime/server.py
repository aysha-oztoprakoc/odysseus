from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = str((ROOT / ".qa_runtime" / "workspace").resolve())


def render(*, enabled: bool) -> str:
    html = INDEX.replace("{{CSP_NONCE}}", "").replace(
        "{{FILES_ADMIN_ENABLED}}", str(enabled).lower()
    )
    if not enabled:
        html = re.sub(
            r"<!-- FILES_ADMIN_START -->.*?<!-- FILES_ADMIN_END -->",
            "",
            html,
            flags=re.DOTALL,
        )
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    if enabled:
        html = html.replace(
            "</body>",
            '<script type="module" src="/static/js/filesExplorer.js"></script></body>',
        )
    return html


app = FastAPI()
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
def disabled() -> str:
    return render(enabled=False)


@app.get("/enabled", response_class=HTMLResponse)
def enabled() -> str:
    return render(enabled=True)


@app.post("/api/files/capability")
async def capability(request: Request) -> JSONResponse:
    body = await request.json()
    if body.get("password") != "qa-password":
        return JSONResponse({"detail": "denied"}, status_code=403)
    return JSONResponse({"capability": "qa-five-minute-capability"})


@app.get("/api/files/browse")
def browse() -> dict[str, object]:
    return {
        "path": WORKSPACE,
        "parent": None,
        "items": [
            {
                "name": "<img src=x onerror=alert(1)>.txt",
                "path": f"{WORKSPACE}/<img src=x onerror=alert(1)>.txt",
                "is_dir": False,
                "size": 13,
            },
            {
                "name": "safe-note.txt",
                "path": f"{WORKSPACE}/safe-note.txt",
                "is_dir": False,
                "size": 19,
            },
        ],
        "total": 2,
    }


@app.get("/api/files/read")
def read_file() -> dict[str, str]:
    return {"content": "manual QA content\n"}
