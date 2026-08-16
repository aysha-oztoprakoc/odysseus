from __future__ import annotations

import hashlib
import os
import secrets
import stat
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


TEXT_LIMIT = 2 * 1024 * 1024
UPLOAD_LIMIT = 25 * 1024 * 1024
ARCHIVE_ENTRY_LIMIT = 5_000
ARCHIVE_EXPANDED_LIMIT = 250 * 1024 * 1024
BROWSE_LIMIT = 200
BROWSE_SCAN_LIMIT = 10_000
CAPABILITY_TTL_SECONDS = 300.0

_DEFAULT_ROOTS = (Path("/home/amdy/data_rein"), Path("/home/amdy/data-workspace"))
_DENIED_PARTS = frozenset(
    {
        ".env",
        ".git-credentials",
        ".gnupg",
        ".secrets.enc",
        ".ssh",
        "api_keys.json",
        "auth.json",
        "credentials",
        "keys",
        "sessions.json",
        "vault",
    }
)
_DENIED_SUFFIXES = (".key", ".pem", ".p12", ".pfx", ".kdbx")


@dataclass(frozen=True, slots=True)
class FilePolicyError(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    username: str
    expires_at: float


class CapabilityStore:
    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        ttl_seconds: float = CAPABILITY_TTL_SECONDS,
    ) -> None:
        self._clock = clock
        self._ttl_seconds = ttl_seconds
        self._grants: dict[bytes, CapabilityGrant] = {}
        self._lock = threading.Lock()

    def issue(self, username: str) -> tuple[str, float]:
        token = secrets.token_urlsafe(32)
        expires_at = self._clock() + self._ttl_seconds
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        with self._lock:
            self._grants[digest] = CapabilityGrant(username, expires_at)
        return token, expires_at

    def authorize(self, token: str, username: str) -> bool:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        now = self._clock()
        with self._lock:
            grant = self._grants.get(digest)
            if grant is None:
                return False
            if grant.expires_at <= now:
                self._grants.pop(digest, None)
                return False
            return secrets.compare_digest(grant.username, username)


class WorkspacePolicy:
    def __init__(self, roots: tuple[Path, ...]) -> None:
        resolved = tuple(root.expanduser().resolve() for root in roots)
        if not resolved:
            raise FilePolicyError(503, "No file administration roots are configured")
        self.roots = resolved

    @classmethod
    def from_environment(cls) -> WorkspacePolicy:
        raw = os.getenv("ODYSSEUS_FILES_ADMIN_ROOTS", "")
        roots = tuple(Path(value) for value in raw.split(os.pathsep) if value.strip())
        return cls(roots or _DEFAULT_ROOTS)

    def resolve(self, raw_path: str, *, must_exist: bool = True) -> Path:
        candidate = Path(raw_path.strip()).expanduser()
        if not candidate.is_absolute():
            candidate = self.roots[0] / candidate
        candidate = Path(os.path.abspath(candidate))
        root = self._containing_root(candidate)
        relative = candidate.relative_to(root)
        self._reject_secret_path(relative)
        current = root
        for part in relative.parts:
            current = current / part
            if current.exists() or current.is_symlink():
                if stat.S_ISLNK(current.lstat().st_mode):
                    raise FilePolicyError(403, "Symbolic links are not allowed")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise FilePolicyError(403, "Path escapes the configured workspace roots")
        if must_exist and not resolved.exists():
            raise FilePolicyError(404, "Path not found")
        return resolved

    def label(self, path: Path) -> str:
        root = self._containing_root(path)
        return f"{root.name}/{path.relative_to(root).as_posix()}"

    def _containing_root(self, candidate: Path) -> Path:
        for root in self.roots:
            if candidate == root or candidate.is_relative_to(root):
                return root
        raise FilePolicyError(403, "Path escapes the configured workspace roots")

    def _reject_secret_path(self, relative: Path) -> None:
        for part in relative.parts:
            lowered = part.casefold()
            if lowered in _DENIED_PARTS or lowered.startswith(".env."):
                raise FilePolicyError(403, "Sensitive paths are not available")
            if lowered.endswith(_DENIED_SUFFIXES):
                raise FilePolicyError(403, "Sensitive paths are not available")
