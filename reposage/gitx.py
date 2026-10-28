from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def _run(args: list, root: Path, timeout: int = 10) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def repo_root(path: Path) -> Optional[Path]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    if not out:
        return None
    return Path(out)


def repo_meta(root: Path) -> Optional[dict]:
    if repo_root(root) is None:
        return None
    remote = _run(["config", "--get", "remote.origin.url"], root)
    branch = _run(["rev-parse", "--abbrev-ref", "HEAD"], root)
    commit = _run(["rev-parse", "--short", "HEAD"], root)
    date = _run(["log", "-1", "--format=%cI"], root)
    if remote is None and branch is None and commit is None:
        return None
    repo = ""
    if remote:
        repo = remote.rstrip("/")
        if repo.endswith(".git"):
            repo = repo[:-4]
    return {
        "remote": repo or None,
        "branch": branch,
        "commit": commit,
        "last_commit_date": date,
    }


def changed_files(root: Path) -> Optional[set]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    changed = set()
    for args in (
        ["diff", "--name-only", "HEAD"],
        ["diff", "--cached", "--name-only", "HEAD"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        out = _run(args, root)
        if out:
            changed.update(l.replace("\\", "/") for l in out.splitlines() if l.strip())
    return changed


def is_ignored(root: Path, rel: str) -> Optional[bool]:
    proc = None
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", rel],
            cwd=str(root),
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.returncode == 0
