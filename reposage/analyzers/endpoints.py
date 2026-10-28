from __future__ import annotations

import re

from .base import FileAnalyzer

ENTRY_NAMES = {
    "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "server.js", "app.js", "main.js",
    "main.go", "main.rs", "main.cpp", "main.c", "main.rb", "main.php",
    "Program.cs", "Main.java",
}

PY_PATTERNS = [
    ("flask", re.compile(r"@(?:\w+\.)?route\(\s*(['\"])(?P<path>[^'\"]+)\1")),
    ("fastapi", re.compile(r"@\w+\.(?P<method>get|post|put|delete|patch|head|options)\s*\(\s*(['\"])(?P<path>[^'\"]+)\2")),
    ("django", re.compile(r"\b(?:path|re_path)\(\s*(['\"])(?P<path>[^'\"]+)\1")),
]
JS_PATTERNS = [
    ("express", re.compile(r"\b(?:app|router|server|api)\.(?P<method>get|post|put|delete|patch|all|use)\(\s*(['\"`])(?P<path>[^'\"`]+)\2")),
    ("nestjs", re.compile(r"@(?:Get|Post|Put|Delete|Patch|All)\(\s*(['\"])(?P<path>[^'\"]*)\1")),
]
GO_PATTERNS = [
    ("net/http", re.compile(r"http\.Handle(?:Func)?\(\s*\"(?P<path>[^\"]+)\"")),
    ("gin/echo/chi", re.compile(r"\b(?:r|e|router|g|mux)\.(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|Any)\(\s*\"(?P<path>[^\"]+)\"")),
    ("gorilla", re.compile(r"\.Methods\(\s*\"(?P<method>\w+)\"\)\.Path\(\s*\"(?P<path>[^\"]+)\"")),
]
JAVA_PATTERNS = [
    ("spring", re.compile(r"@(?P<method>Get|Post|Put|Delete|Patch|Request)Mapping\(\s*(?:value\s*=\s*)?\"(?P<path>[^\"]*)\"")),
]
RUBY_PATTERNS = [
    ("rails/sinatra", re.compile(r"^\s*(?P<method>get|post|put|patch|delete)\s+['\"](?P<path>[^'\"]+)['\"]", re.M)),
]
PHP_PATTERNS = [
    ("laravel", re.compile(r"Route::(?P<method>get|post|put|patch|delete|any|match|resource)\(\s*['\"](?P<path>[^'\"]+)['\"]")),
]
CS_PATTERNS = [
    ("aspnet", re.compile(r"\[Http(?P<method>Get|Post|Put|Delete|Patch)(?:\(\s*\"(?P<path>[^\"]*)\"\s*\))?\]")),
]
RS_PATTERNS = [
    ("axum", re.compile(r"\.route\(\s*\"(?P<path>[^\"]+)\"")),
    ("actix", re.compile(r"web::resource\(\s*\"(?P<path>[^\"]+)\"")),
]
KT_PATTERNS = [
    ("ktor", re.compile(r"\b(?P<method>get|post|put|delete|patch)\(\s*\"(?P<path>[^\"]+)\"")),
]

EXT_PATTERNS = {
    ".py": PY_PATTERNS,
    ".js": JS_PATTERNS, ".mjs": JS_PATTERNS, ".cjs": JS_PATTERNS,
    ".jsx": JS_PATTERNS, ".ts": JS_PATTERNS, ".tsx": JS_PATTERNS,
    ".go": GO_PATTERNS,
    ".java": JAVA_PATTERNS,
    ".rb": RUBY_PATTERNS,
    ".php": PHP_PATTERNS,
    ".cs": CS_PATTERNS,
    ".rs": RS_PATTERNS,
    ".kt": KT_PATTERNS, ".kts": KT_PATTERNS,
}


class EndpointsAnalyzer(FileAnalyzer):
    name = "endpoints"
    title = "Endpoints & Entry Points"
    description = "HTTP routes and program entry points."
    exts = set(EXT_PATTERNS)

    def analyze_file(self, rel, text, ctx):
        findings = []
        for framework, rx in EXT_PATTERNS.get("." + rel.rsplit(".", 1)[-1], []):
            for match in rx.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                method = match.groupdict().get("method", "")
                findings.append({
                    "file": rel,
                    "line": line,
                    "method": method.upper() if method else "ANY",
                    "path": match.group("path"),
                    "framework": framework,
                })
                if len(findings) >= 50:
                    return findings
        return findings

    def build_section(self, per_file, ctx):
        endpoints = []
        entry_points = []
        for rel, entry in per_file.items():
            findings = entry.get(self.name) or []
            endpoints.extend(findings)
            name = rel.rsplit("/", 1)[-1]
            if name in ENTRY_NAMES:
                entry_points.append(rel)
        endpoints.sort(key=lambda e: (e["file"], e["line"]))
        truncated = len(endpoints) > ctx.config.max_endpoints
        endpoints = endpoints[:ctx.config.max_endpoints]
        return {
            "endpoints": endpoints,
            "entry_points": sorted(entry_points),
            "count": len(endpoints),
            "truncated": truncated,
        }
