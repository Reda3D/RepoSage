from __future__ import annotations

import os
import re
from pathlib import Path

from .config import Config

DEFAULT_IGNORES = [
    ".git", ".hg", ".svn", ".bzr",
    ".idea", ".vscode", ".vs", ".fleet",
    "__pycache__", "*.pyc", "*.pyo", "*.pyd", "*.egg-info",
    "node_modules", "bower_components", "jspm_packages",
    "venv", ".venv", "env",
    "dist", "build", "out", "target", "*.egg-info",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox",
    ".next", ".nuxt", ".cache", ".parcel-cache", ".turbo",
    "coverage", ".coverage", "htmlcov",
    "*.log", ".DS_Store", "Thumbs.db",
    "*.min.js", "*.min.css",
    "vendor", "third_party", "packages",
]


def _pat_to_regex(pattern: str) -> tuple[bool, re.Pattern, bool]:
    negated = False
    if pattern.startswith("!"):
        negated = True
        pattern = pattern[1:]
    pattern = pattern.lstrip("/")
    dir_only = pattern.endswith("/")
    pattern = pattern.rstrip("/")
    if not pattern:
        return negated, re.compile(r"^$"), dir_only
    anchored = "/" in pattern
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern[i + 1:i + 2] == "*":
                if pattern[i + 2:i + 3] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
                continue
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            end = pattern.find("]", i)
            if end == -1:
                out.append(r"\[")
                i += 1
            else:
                out.append(pattern[i:end + 1])
                i = end + 1
        else:
            out.append(re.escape(c))
            i += 1
    body = "".join(out)
    if not anchored:
        body = "(?:.*/)?" + body
    rx = re.compile("^" + body + "$")
    return negated, rx, dir_only


class IgnoreRules:
    def __init__(self, root: Path, config: Config, out_dir: str):
        self.rules: list[tuple[bool, re.Pattern, bool]] = []
        self._add_patterns(DEFAULT_IGNORES)
        self._add_patterns([out_dir.rstrip("/\\") + "/", ".reposage.toml"])
        self._load_ignore_file(root / ".gitignore")
        self._load_ignore_file(root / ".reposageignore")
        self._add_patterns(config.extra_ignore)

    def _load_ignore_file(self, path: Path):
        if not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        patterns = [l.strip() for l in text.splitlines()
                    if l.strip() and not l.strip().startswith("#")]
        self._add_patterns(patterns)

    def _add_patterns(self, patterns: list):
        for pattern in patterns:
            try:
                self.rules.append(_pat_to_regex(pattern))
            except re.error:
                continue

    def ignored(self, rel: str, is_dir: bool) -> bool:
        rel = rel.replace(os.sep, "/").lstrip("/")
        candidates = [rel]
        if is_dir:
            candidates.append(rel + "/")
        else:
            parts = rel.split("/")
            candidates.extend("/".join(parts[:i]) for i in range(1, len(parts)))
        decision = None
        for negated, rx, dir_only in self.rules:
            if dir_only and not is_dir:
                targets = candidates[1:]
            else:
                targets = candidates
            if any(rx.match(p) is not None for p in targets):
                decision = not negated
        return decision is True


def scan(root: Path, config: Config) -> tuple[list, int, bool]:
    rules = IgnoreRules(root, config, config.out_dir)
    files = []
    skipped = 0
    depth_truncated = False
    max_kb = config.max_file_kb
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        depth = rel_dir.count(os.sep) if rel_dir else 0
        if depth >= config.max_depth:
            dirnames[:] = []
            depth_truncated = True
            continue
        kept = []
        for name in dirnames:
            rel = name if not rel_dir else rel_dir + os.sep + name
            if not rules.ignored(rel, True):
                kept.append(name)
        dirnames[:] = sorted(kept)
        for name in filenames:
            rel = name if not rel_dir else rel_dir + os.sep + name
            if rules.ignored(rel, False):
                continue
            path = Path(dirpath) / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > max_kb * 1024:
                skipped += 1
                continue
            if len(files) >= config.max_files:
                skipped += 1
                return files, skipped, depth_truncated
            files.append((rel.replace(os.sep, "/"), path, size))
    files.sort(key=lambda f: f[0])
    return files, skipped, depth_truncated
