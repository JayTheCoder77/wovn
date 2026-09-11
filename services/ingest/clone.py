from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ingest.sandbox.limits import CLONE_TIMEOUT_SECONDS, MAX_REPO_BYTES

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


class CloneError(Exception):
    pass


@dataclass(frozen=True)
class ParsedRepo:
    owner: str
    name: str
    https_url: str


def parse_github_url(url: str) -> ParsedRepo:
    raw = url.strip()
    match = GITHUB_URL_RE.match(raw)
    if not match:
        raise CloneError("Only https://github.com/<owner>/<repo> URLs are supported.")
    owner, name = match.group(1), match.group(2)
    if name == "." or owner == ".":
        raise CloneError("Invalid GitHub repository URL.")
    return ParsedRepo(owner=owner, name=name, https_url=f"https://github.com/{owner}/{name}.git")


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != ".git"]
        for filename in files:
            file_path = Path(root) / filename
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
            if total > MAX_REPO_BYTES:
                return total
    return total


def clone_repo(url: str, dest: Path, access_token: str | None = None) -> ParsedRepo:
    parsed = parse_github_url(url)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    env["GCM_INTERACTIVE"] = "never"

    cmd = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "protocol.file.allow=never",
    ]
    if access_token:
        # Git's HTTPS endpoint expects Basic x-access-token, not REST-style Bearer.
        # A rejected Bearer header makes GitHub 404 even public repos.
        credential = base64.b64encode(f"x-access-token:{access_token}".encode("ascii")).decode("ascii")
        cmd.extend(["-c", f"http.extraHeader=Authorization: Basic {credential}"])
    cmd.extend(
        [
            "clone",
            "--depth=1",
            "--single-branch",
            "--no-tags",
            parsed.https_url,
            str(dest),
        ]
    )
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError("Clone timed out. The repository may be too large.") from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        stderr = (exc.stderr or "").strip()
        if "Repository not found" in stderr or "Authentication failed" in stderr:
            raise CloneError(
                "Repository not found or you do not have access. Reconnect GitHub if this is a private repo."
            ) from exc
        raise CloneError("Failed to clone repository.") from exc

    size = _dir_size_bytes(dest)
    if size > MAX_REPO_BYTES:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError("Repository exceeds the 80MB snapshot size limit.")
    return parsed
