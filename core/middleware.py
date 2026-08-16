# src/middleware.py
# Shared middleware, decorators, and request helpers

import os
import secrets
import sys

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Per-process token that lets the in-app tool layer hit admin-gated
# routes via HTTP loopback (the agent's tool calls don't carry the
# admin user's session cookie). Set once at import; tools read the
# same value from this module. Never persisted or exposed externally.
INTERNAL_TOOL_TOKEN = os.environ.get("ODYSSEUS_INTERNAL_TOKEN") or secrets.token_hex(32)
INTERNAL_TOOL_HEADER = "X-Odysseus-Internal-Token"
# Pseudo-username on in-process tool-loopback requests; require_admin trusts it and it is reserved.
INTERNAL_TOOL_USER = "internal-tool"


def is_loopback_bound() -> bool:
    """True only when the app server is bound to the loopback interface.

    Mirrors the APP_BIND host the ``__main__`` block passes to uvicorn
    (default ``127.0.0.1``). A server listening on ``0.0.0.0`` / ``::`` /
    a non-loopback address is network-exposed, and single-operator-style
    trusts (e.g. "auth unconfigured -> implicit admin", legacy shell tool
    gating, LOCALHOST_BYPASS) must fail CLOSED there. True for a comma/
    space-separated binding string only when every entry is a loopback
    address or ``localhost``.
    """
    raw = os.getenv("APP_BIND", "127.0.0.1")
    # Keep parsing constant-time/shape-stable; this is config, not a secret.
    entries = [e.strip().lower() for e in raw.replace(",", " ").split() if e.strip()]
    if not entries:
        return True  # reset to servant-safe default
    return all(e in ("127.0.0.1", "::1", "localhost") for e in entries)


AUTH_DISABLED_CONFIRM_ENV = "ODYSSEUS_ALLOW_AUTH_DISABLED_EXPOSED"


def gate_auth_disabled_exposed(bind_host=None):
    """Fail-closed deployment gate for ``AUTH_ENABLED=false``.

    Auth-disabled is a legitimate single-user convenience ONLY on loopback.
    Binding an auth-disabled instance to a non-loopback address would silently
    expose every route/endpoint without authentication. Rather than start
    unsafely, this gate refuses to boot unless the operator explicitly
    confirms the auth-disabled, network-exposed configuration:

    * interactive TTY  -> an explicit yes/no prompt (the "first-run prompt"),
    * non-interactive  -> the env sentinel
      ``ODYSSEUS_ALLOW_AUTH_DISABLED_EXPOSED=1`` (best for systemd/docker/CI),
    * otherwise        -> abort with a clear error (fail closed).

    Loopback-bound auth-disabled startups pass through untouched so single-user
    local development keeps working. Returns True to proceed, False to abort.
    """
    if os.getenv("AUTH_ENABLED", "true").lower() != "false":
        return True  # auth on; nothing to gate

    host = bind_host if bind_host is not None else os.getenv("APP_BIND", "127.0.0.1")
    entries = [e.strip().lower() for e in str(host).replace(",", " ").split() if e.strip()]
    loopback = all(e in ("127.0.0.1", "::1", "localhost") for e in entries) if entries else True
    if loopback:
        return True  # safe local single-user mode

    sentinel = os.getenv(AUTH_DISABLED_CONFIRM_ENV, "")
    if sentinel.strip().lower() in ("1", "true", "yes", "y"):
        return True

    try:
        interactive = sys.stdin.isatty()
    except Exception:
        interactive = False

    if interactive:
        print(
            "\nWARNING: Odyssey is about to start with AUTH_ENABLED=false on a "
            f"network-exposed interface ({host}). All routes will be UNPROTECTED.\n",
            file=sys.stderr,
        )
        try:
            answer = input("Type 'DISABLE' to confirm auth-disabled exposed startup: ")
        except EOFError:
            answer = ""
        if answer.strip().lower() == "disable":
            print("Confirmed. Starting auth-disabled (network-exposed).", file=sys.stderr)
            return True
        print(
            "Aborting: auth-disabled network-exposed startup was not confirmed. "
            "Set AUTH_ENABLED=true or run loopback-only.",
            file=sys.stderr,
        )
        return False

    print(
        f"REFUSED to start: AUTH_ENABLED=false is being bound to exposed host {host!r}, "
        "which would disable authentication for all remote callers. To proceed you "
        "MUST explicitly confirm this unsafe config by setting "
        f"{AUTH_DISABLED_CONFIRM_ENV}=1 (non-interactive), answer the prompt on a "
        "TTY, or run loopback-only.",
        file=sys.stderr,
    )
    return False


def is_cors_preflight(method: str, headers) -> bool:
    """True for a genuine CORS preflight: an OPTIONS request carrying the
    Access-Control-Request-Method header. Such requests are credential-less by
    design and must reach CORSMiddleware to be answered -- gating them on auth
    401s the preflight and breaks every cross-origin browser/WebView client.
    Pure so it can be unit-tested without standing up the app."""
    return method == "OPTIONS" and "access-control-request-method" in headers


def require_admin(request: Request):
    """Raise 403 if the current user isn't an admin.
    Allows access when auth is explicitly disabled, or when the request carries
    the in-process internal-tool token used by loopback agent tools.
    """
    # In-process bypass for tool-layer loopback calls. Two paths:
    # (a) header-direct (caller set X-Odysseus-Internal-Token), or
    # (b) the auth middleware already validated the token and stamped
    #     request.state.current_user = "internal-tool".
    try:
        hdr = request.headers.get(INTERNAL_TOOL_HEADER)
        if hdr and secrets.compare_digest(hdr, INTERNAL_TOOL_TOKEN):
            return
        if getattr(request.state, "current_user", None) == INTERNAL_TOOL_USER:
            return
    except Exception:
        pass

    auth_mgr = getattr(request.app.state, "auth_manager", None)
    if os.getenv("AUTH_ENABLED", "true").lower() == "false":
        # Single-user mode is a local development convenience: only loopback
        # callers may bypass auth. A remote caller hitting an auth-disabled
        # instance is a misconfiguration and must fail closed (audit residual).
        client = getattr(request, "client", None)
        host = (client.host if client else "") or ""
        if host in ("127.0.0.1", "::1", "localhost"):
            return
        raise HTTPException(403, "Auth disabled; remote access denied")
    if not auth_mgr or not auth_mgr.is_configured:
        raise HTTPException(403, "Admin only")
    user = getattr(request.state, "current_user", None)
    if not user or not auth_mgr.is_admin(user):
        raise HTTPException(403, "Admin only")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate a per-request nonce for inline scripts
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce

        response = await call_next(request)
        path = request.url.path

        # Tool render endpoints
        is_tool_render = path.startswith("/api/tools/") and path.endswith("/render")
        # Document library PDF preview endpoint
        is_document_pdf_preview = path.startswith("/api/document/") and path.endswith("/render-pdf")
        # Visual report pages are self-contained HTML — need inline scripts + external images
        is_report = path.startswith("/api/research/report/")

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"

        is_https = (
            request.url.scheme == "https"
            or request.headers.get("X-Forwarded-Proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if is_report:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "font-src 'self'; "
                "img-src 'self' data: blob: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        elif is_tool_render:
            # Skip framing headers for tools.
            pass
        elif is_document_pdf_preview:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'self'"
            )
        else:
            response.headers["X-Frame-Options"] = "DENY"
            # NOTE: `style-src 'unsafe-inline'` is intentionally retained.
            # `static/index.html` and `static/login.html` ship inline <style>
            # blocks, and several JS modules build runtime `style=""` attrs.
            # Migrating to nonce-only requires templating the HTML files +
            # auditing every JS-set style attribute. Since inline styles
            # don't execute script, the residual risk is visual-only.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob: https:; "
                "media-src 'self' blob:; "
                "connect-src 'self'; "
                "frame-src 'self'; "
                "frame-ancestors 'none'"
            )
        return response
