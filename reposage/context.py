from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import Config
from .lang import classify, count_loc


@dataclass
class FileInfo:
    rel: str
    path: Path
    size: int
    hash: str = ""
    loc: int = 0
    binary: bool = False

    @property
    def lang(self) -> str:
        return classify(self.rel)


class Context:
    def __init__(self, root: Path, config: Config, git: Optional[dict]):
        self.root = root
        self.config = config
        self.git = git
        self.files: list[FileInfo] = []
        self.truncated = False
        self.skipped_large = 0
        self._content: dict = {}
        self._budget = config.read_budget_mb * 1024 * 1024
        self._spent = 0

    def populate(self, changed: Optional[set] = None):
        for fi in self.files:
            if changed is not None and fi.rel not in changed:
                continue
            self._ingest(fi)

    def _ingest(self, fi: FileInfo):
        if self._spent + fi.size > self._budget:
            self.truncated = True
            return
        try:
            data = fi.path.read_bytes()
        except OSError:
            return
        self._spent += fi.size
        fi.hash = hashlib.sha1(data).hexdigest()
        if b"\x00" in data[:8192]:
            fi.binary = True
            fi.loc = 0
            return
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
            except UnicodeDecodeError:
                fi.binary = True
                fi.loc = 0
                return
        fi.loc = count_loc(text)
        self._content[fi.rel] = text

    def text(self, fi: FileInfo) -> str:
        return self._content.get(fi.rel, "")

    def loc_total(self) -> int:
        return sum(fi.loc for fi in self.files)

    def lang_stats(self) -> dict:
        stats: dict = {}
        for fi in self.files:
            lang = fi.lang or "Other"
            entry = stats.setdefault(lang, {"files": 0, "loc": 0})
            entry["files"] += 1
            entry["loc"] += fi.loc
        return stats

    def file_kinds(self) -> dict:
        kinds = {"code": 0, "test": 0, "config": 0, "docs": 0, "other": 0}
        for fi in self.files:
            low = fi.rel.lower()
            if any(seg in low.split("/") for seg in ("test", "tests", "spec", "__tests__")) \
                    or ".test." in low or low.endswith("_test.go") or low.endswith("_test.py"):
                kinds["test"] += 1
            elif low.endswith((".md", ".markdown", ".rst", ".txt", ".adoc")):
                kinds["docs"] += 1
            elif low.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".lock", ".xml", ".csv")):
                kinds["config"] += 1
            elif fi.lang:
                kinds["code"] += 1
            else:
                kinds["other"] += 1
        return kinds

    def largest_files(self, n: int = 5) -> list:
        return sorted(self.files, key=lambda f: -f.size)[:n]

    def is_enabled(self, name: str) -> bool:
        return name in self.config.plugins
