from __future__ import annotations

import re

from .base import FileAnalyzer
from ..lang import is_code

TODO_RE = re.compile(r"(?i)(?:^|[^:\w])(TODO|FIXME|HACK|XXX|BUG|TBD)(?::|\s|$)(.*)")
MAX_MESSAGE = 80


class TodosAnalyzer(FileAnalyzer):
    name = "todos"
    title = "TODOs & Tech Debt"
    description = "TODO/FIXME/HACK markers with file and line."

    def matches(self, rel):
        return is_code(rel) or rel.endswith(".md")

    def analyze_file(self, rel, text, ctx):
        findings = []
        for idx, line in enumerate(text.splitlines(), start=1):
            match = TODO_RE.search(line)
            if not match:
                continue
            message = match.group(2).strip()[:MAX_MESSAGE]
            findings.append({
                "file": rel,
                "line": idx,
                "tag": match.group(1).upper(),
                "text": message,
            })
            if len(findings) >= 30:
                return findings
        return findings

    def build_section(self, per_file, ctx):
        todos = []
        for rel, entry in per_file.items():
            todos.extend(entry.get(self.name) or [])
        todos.sort(key=lambda t: (t["file"], t["line"]))
        truncated = len(todos) > ctx.config.max_todos
        todos = todos[:ctx.config.max_todos]
        return {"todos": todos, "count": len(todos), "truncated": truncated}
