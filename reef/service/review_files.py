"""Read-only file previews and local Cursor links for a versioned harness."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit


@dataclass(frozen=True)
class FilePreview:
    path: str
    cursor_url: str


def cursor_url(path: Path, ssh_url: str = "") -> str:
    """Use Cursor's Remote SSH connection authority, including the user and custom port."""
    if not ssh_url:
        return "cursor://file" + quote(str(path), safe="/")
    remote = urlsplit(ssh_url)
    if (
        remote.scheme != "ssh"
        or not remote.hostname
        or remote.password
        or remote.path not in ("", "/")
        or remote.query
        or remote.fragment
    ):
        raise ValueError("Review SSH destination must be ssh://[user@]host[:port]")
    connection: dict[str, str | int] = {"hostName": remote.hostname}
    if remote.username:
        connection["user"] = remote.username
    if remote.port is not None:
        connection["port"] = remote.port
    authority = json.dumps(connection, separators=(",", ":"), ensure_ascii=False).encode().hex()
    # Cursor treats a remote protocol path as a folder unless it ends with a line number.
    return "cursor://vscode-remote/ssh-remote+" + authority + quote(str(path), safe="/") + ":1"


def prepare_previews(files: Mapping[str, str], paths: Sequence[str], *, ssh_url: str = "") -> dict[str, FilePreview]:
    """Copy selected version files and their Skill support files; never open the repository's writable cache."""
    selected = [PurePosixPath(path) for path in paths if path in files]
    if not selected:
        return {}
    # Validate before allocating a directory, including the SSH port and destination.
    cursor_url(Path("/preview"), ssh_url)
    for path in selected:
        if path.is_absolute() or any(part in ("..", ".git") for part in path.parts):
            raise ValueError("Preview paths must stay inside the harness")
    root = Path(tempfile.mkdtemp(prefix="reef-review-")).resolve()
    for name, content in files.items():
        path = PurePosixPath(name)
        keep = any(
            path == target or (target.name == "SKILL.md" and target.parent in path.parents) for target in selected
        )
        if not keep:
            continue
        if path.is_absolute() or any(part in ("..", ".git") for part in path.parts):
            raise ValueError("Preview paths must stay inside the harness")
        target = root.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))
        target.chmod(0o444)
    for directory, _, _ in os.walk(root, topdown=False):
        Path(directory).chmod(0o555)
    return {
        path.as_posix(): FilePreview(str(root.joinpath(*path.parts)), cursor_url(root.joinpath(*path.parts), ssh_url))
        for path in selected
    }
