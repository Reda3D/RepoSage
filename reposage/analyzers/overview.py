from __future__ import annotations

from datetime import datetime, timezone

from .base import Analyzer

LICENSE_HINTS = {
    "MIT": ["mit license", "permission is hereby granted"],
    "Apache-2.0": ["apache license", "apache software license"],
    "GPL-3.0": ["gnu general public license", "version 3"],
    "GPL-2.0": ["gnu general public license", "version 2"],
    "BSD-3-Clause": ["redistribution and use in source and binary forms", "neither the name"],
    "BSD-2-Clause": ["redistribution and use in source and binary forms"],
    "MPL-2.0": ["mozilla public license"],
    "ISC": ["permission to use, copy, modify"],
    "Unlicense": ["this is free and unencumbered software"],
}


class OverviewAnalyzer(Analyzer):
    name = "overview"
    title = "Overview"
    description = "Repository identity, git status, size and language mix."

    def run(self, ctx):
        lang_stats = ctx.lang_stats()
        total_loc = ctx.loc_total()
        ranked = sorted(lang_stats.items(), key=lambda kv: -kv[1]["loc"])
        top = [(lang, info["loc"], info["files"]) for lang, info in ranked[:10]]
        kinds = ctx.file_kinds()
        git = ctx.git or {}
        name = ctx.config.name or (git.get("remote", "").split("/")[-1] if git.get("remote") else ctx.root.name)
        license_name = self._detect_license(ctx)
        return {
            "name": name,
            "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            "git": git,
            "license": license_name,
            "total_files": len(ctx.files),
            "total_loc": total_loc,
            "languages": top,
            "file_kinds": kinds,
            "largest_files": [(f.rel, f.size) for f in ctx.largest_files()],
            "truncated": ctx.truncated,
        }

    def _detect_license(self, ctx) -> str:
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"):
            path = ctx.root / name
            if not path.is_file():
                continue
            try:
                head = path.read_text(encoding="utf-8", errors="replace")[:4000].lower()
            except OSError:
                continue
            for license_name, hints in LICENSE_HINTS.items():
                if all(h in head for h in hints):
                    return license_name
            return "Custom (see LICENSE)"
        return "Not found"
