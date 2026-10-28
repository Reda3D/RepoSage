from __future__ import annotations

from collections import defaultdict

from .base import Analyzer

MAX_TREE_DEPTH = 5
MAX_TREE_CHILDREN = 40
MAX_MODULES = 30


class StructureAnalyzer(Analyzer):
    name = "structure"
    title = "Structure"
    description = "Directory tree and module map."

    def run(self, ctx):
        tree = {}
        for fi in ctx.files:
            node = tree
            parts = fi.rel.split("/")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node.setdefault(parts[-1], None)
        tree_text = self._render(tree, "", 0)
        modules = self._modules(ctx)
        return {"tree": tree_text, "modules": modules}

    def _render(self, node: dict, prefix: str, depth: int) -> list:
        lines = []
        entries = sorted(node.items(), key=lambda kv: (kv[1] is not None, kv[0].lower()))
        total = len(entries)
        shown = entries[:MAX_TREE_CHILDREN]
        for idx, (name, children) in enumerate(shown):
            is_last = idx == len(shown) - 1 and len(shown) == total
            connector = "`-- " if is_last else "|-- "
            if children is None:
                lines.append(prefix + connector + name)
            elif depth >= MAX_TREE_DEPTH:
                count = self._file_count(children)
                lines.append(prefix + connector + name + "/  (%d files)" % count)
            else:
                count = self._file_count(children)
                lines.append(prefix + connector + name + "/" + ("  (%d files)" % count if count > 1 else ""))
                child_prefix = prefix + ("    " if is_last else "|   ")
                lines.extend(self._render(children, child_prefix, depth + 1))
        if len(shown) < total:
            lines.append(prefix + "`-- ... (%d more)" % (total - len(shown)))
        return lines

    def _file_count(self, node: dict) -> int:
        count = 0
        for value in node.values():
            if value is None:
                count += 1
            else:
                count += self._file_count(value)
        return count

    def _modules(self, ctx):
        dirs: dict = {}
        for fi in ctx.files:
            parts = fi.rel.split("/")
            if len(parts) < 2:
                continue
            dirname = "/".join(parts[:-1])
            entry = dirs.setdefault(dirname, {"files": 0, "loc": 0, "langs": defaultdict(int)})
            entry["files"] += 1
            entry["loc"] += fi.loc
            entry["langs"][fi.lang or "Other"] += 1
        modules = []
        for dirname, info in sorted(dirs.items(), key=lambda kv: -kv[1]["files"]):
            if info["files"] < 3:
                continue
            main_lang = max(info["langs"].items(), key=lambda kv: kv[1])[0]
            modules.append({"dir": dirname, "files": info["files"], "loc": info["loc"], "lang": main_lang})
            if len(modules) >= MAX_MODULES:
                break
        return modules
