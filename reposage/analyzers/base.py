from __future__ import annotations

from typing import Optional

from ..context import Context


class Analyzer:
    name = ""
    title = ""
    description = ""

    def run(self, ctx: Context) -> dict:
        raise NotImplementedError


class FileAnalyzer(Analyzer):
    exts: set = set()
    names: set = set()

    def matches(self, rel: str) -> bool:
        from pathlib import PurePosixPath
        name = PurePosixPath(rel).name
        if name in self.names:
            return True
        suffix = PurePosixPath(rel).suffix.lower()
        return suffix in self.exts

    def analyze_file(self, rel: str, text: str, ctx: Context):
        raise NotImplementedError

    def build_section(self, per_file: dict, ctx: Context) -> dict:
        raise NotImplementedError
