from __future__ import annotations

import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from collections.abc import Iterable
from typing import IO

from routes.files_security import (
    ARCHIVE_ENTRY_LIMIT,
    ARCHIVE_EXPANDED_LIMIT,
    FilePolicyError,
    WorkspacePolicy,
)


def _safe_member_path(name: str) -> PurePosixPath:
    if "\\" in name:
        raise FilePolicyError(400, "Archive member uses an unsafe path separator")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise FilePolicyError(400, "Archive member escapes the extraction directory")
    return path


def _validate_limits(entries: int, expanded_size: int) -> None:
    if entries > ARCHIVE_ENTRY_LIMIT:
        raise FilePolicyError(413, "Archive contains too many entries")
    if expanded_size > ARCHIVE_EXPANDED_LIMIT:
        raise FilePolicyError(413, "Archive expands beyond the allowed size")


def _copy_bounded(source: IO[bytes], destination: IO[bytes], budget: int) -> int:
    copied = 0
    while chunk := source.read(min(1024 * 1024, budget - copied + 1)):
        copied += len(chunk)
        if copied > budget:
            raise FilePolicyError(413, "Archive expands beyond the allowed size")
        destination.write(chunk)
    return copied


def _publish(stage: Path, destination: Path, top_levels: Iterable[str]) -> None:
    names = tuple(sorted(set(top_levels)))
    for name in names:
        if (destination / name).exists():
            raise FilePolicyError(409, "Archive extraction would overwrite an existing path")
    for name in names:
        os.replace(stage / name, destination / name)


def _extract_zip(archive: Path, destination: Path, policy: WorkspacePolicy, stage: Path) -> None:
    with zipfile.ZipFile(archive) as reader:
        entries = reader.infolist()
        _validate_limits(len(entries), sum(entry.file_size for entry in entries))
        validated: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
        for entry in entries:
            member = _safe_member_path(entry.filename)
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise FilePolicyError(400, "Archive links are not allowed")
            policy.resolve(str(destination.joinpath(*member.parts)), must_exist=False)
            validated.append((entry, member))
        copied = 0
        for entry, member in validated:
            output = stage.joinpath(*member.parts)
            if entry.is_dir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            with reader.open(entry) as source, output.open("xb") as target:
                copied += _copy_bounded(source, target, ARCHIVE_EXPANDED_LIMIT - copied)
        _publish(stage, destination, (member.parts[0] for _, member in validated))


def _extract_tar(archive: Path, destination: Path, policy: WorkspacePolicy, stage: Path) -> None:
    with tarfile.open(archive, "r:*") as reader:
        entries = reader.getmembers()
        _validate_limits(len(entries), sum(entry.size for entry in entries))
        validated: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
        for entry in entries:
            member = _safe_member_path(entry.name)
            if not (entry.isfile() or entry.isdir()):
                raise FilePolicyError(400, "Archive links and devices are not allowed")
            policy.resolve(str(destination.joinpath(*member.parts)), must_exist=False)
            validated.append((entry, member))
        copied = 0
        for entry, member in validated:
            output = stage.joinpath(*member.parts)
            if entry.isdir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            source = reader.extractfile(entry)
            if source is None:
                raise FilePolicyError(400, "Archive member could not be read")
            output.parent.mkdir(parents=True, exist_ok=True)
            with source, output.open("xb") as target:
                copied += _copy_bounded(source, target, ARCHIVE_EXPANDED_LIMIT - copied)
        _publish(stage, destination, (member.parts[0] for _, member in validated))


def extract_archive(archive: Path, policy: WorkspacePolicy) -> Path:
    destination = archive.parent
    stage = Path(tempfile.mkdtemp(prefix=".ody-extract-", dir=destination))
    try:
        if archive.suffix.casefold() == ".zip":
            _extract_zip(archive, destination, policy, stage)
        elif archive.name.casefold().endswith((".tar", ".tar.gz", ".tgz")):
            _extract_tar(archive, destination, policy, stage)
        else:
            raise FilePolicyError(400, "Unsupported archive format")
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return destination
