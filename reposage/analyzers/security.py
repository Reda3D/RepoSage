from __future__ import annotations

import re
from pathlib import PurePosixPath

from .base import FileAnalyzer
from ..lang import is_code
from .. import gitx

SECRET_PATTERNS = [
    ("aws-access-key", "HIGH", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS access key ID"),
    ("github-token", "HIGH", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "GitHub fine-grained token"),
    ("github-pat", "HIGH", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "GitHub personal access token"),
    ("slack-token", "HIGH", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
    ("stripe-key", "HIGH", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{10,}\b"), "Stripe API key"),
    ("openai-key", "HIGH", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI API key"),
    ("google-api", "HIGH", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    ("private-key", "HIGH", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Private key block"),
    ("jwt", "MEDIUM", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "JWT token"),
    ("basic-auth-url", "MEDIUM", re.compile(r"https?://[^/\s:@]+:[^/\s:@]+@"), "URL with embedded credentials"),
]
GENERIC_SECRET = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|client[_-]?secret|token)\b\s*[:=]\s*['\"]([^'\"]{8,64})['\"]"
)
FALSE_VALUES = re.compile(
    r"(?i)(your[_ -]|example|changeme|replace|dummy|test[_-]?value|placeholder|\$\(|\$\{|<\w+>|xxxx+|12345+|\*{3,}|password$|secret$)"
)
ENV_LOOKUPS = re.compile(r"(?i)(getenv|environ|process\.env|os\.getenv)")
RISKY_PATTERNS = [
    ("eval", re.compile(r"(?i)\beval\s*\("), "eval() call"),
    ("exec", re.compile(r"(?i)\bexec\s*\("), "exec() call"),
    ("shell-true", re.compile(r"shell\s*=\s*True"), "subprocess with shell=True"),
    ("innerhtml", re.compile(r"(?i)(?:innerHTML\s*=|dangerouslySetInnerHTML)"), "Unsafe HTML injection"),
    ("document-write", re.compile(r"(?i)document\.write\s*\("), "document.write()"),
    ("pickle", re.compile(r"(?i)\bpickle\.(?:loads?|dump)\s*\("), "Insecure deserialization (pickle)"),
    ("os-system", re.compile(r"(?i)\bos\.system\s*\("), "os.system() call"),
    ("runtime-exec", re.compile(r"Runtime\.getRuntime\(\)\.exec\s*\("), "Runtime.exec()"),
]
ENV_FILES = {".env", ".env.local", ".env.development", ".env.production", ".env.staging"}
SNIPPET_LEN = 60


def _line_snippet(text, match_start):
    line_start = text.rfind("\n", 0, match_start) + 1
    line_end = text.find("\n", match_start)
    if line_end == -1:
        line_end = len(text)
    snippet = text[line_start:line_end].strip()
    if len(snippet) > SNIPPET_LEN:
        snippet = snippet[:SNIPPET_LEN] + "..."
    return snippet


class SecurityAnalyzer(FileAnalyzer):
    name = "security"
    title = "Security Notes"
    description = "Hardcoded secrets, risky calls and untracked .env files."

    def matches(self, rel):
        name = PurePosixPath(rel).name
        return is_code(rel) or rel.endswith(".md") or name in ENV_FILES or name.endswith(".example")

    def analyze_file(self, rel, text, ctx):
        findings = []
        name = PurePosixPath(rel).name
        if name in ENV_FILES and not name.endswith((".example", ".sample")):
            ignored = gitx.is_ignored(ctx.root, rel) if ctx.git is not None else None
            severity = "INFO" if ignored is True else ("HIGH" if ignored is False else "MEDIUM")
            status = "git-ignored" if ignored is True else ("committed to git" if ignored is False else "not a git repo")
            findings.append({
                "file": rel, "line": 0, "id": "env-file", "severity": severity,
                "what": f"Environment file ({status})",
                "snippet": name,
            })
        for ident, severity, rx, what in SECRET_PATTERNS:
            for match in rx.finditer(text):
                findings.append({
                    "file": rel,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "id": ident,
                    "severity": severity,
                    "what": what,
                    "snippet": _line_snippet(text, match.start()),
                })
                if len(findings) >= 40:
                    return findings
        for match in GENERIC_SECRET.finditer(text):
            value = match.group(2)
            line = text[max(0, match.start() - 200):match.end() + 80]
            if FALSE_VALUES.search(value) or ENV_LOOKUPS.search(line):
                continue
            findings.append({
                "file": rel,
                "line": text.count("\n", 0, match.start()) + 1,
                "id": "hardcoded-secret",
                "severity": "MEDIUM",
                "what": f"Hardcoded {match.group(1)}",
                "snippet": _line_snippet(text, match.start()),
            })
            if len(findings) >= 40:
                return findings
        for ident, rx, what in RISKY_PATTERNS:
            for match in rx.finditer(text):
                findings.append({
                    "file": rel,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "id": ident,
                    "severity": "LOW",
                    "what": what,
                    "snippet": _line_snippet(text, match.start()),
                })
                if len(findings) >= 40:
                    return findings
        return findings

    def build_section(self, per_file, ctx):
        all_findings = []
        for rel, entry in per_file.items():
            all_findings.extend(entry.get(self.name) or [])
        all_findings.sort(key=lambda f: (f["file"], f["line"]))
        secrets = [f for f in all_findings if f["severity"] in ("HIGH", "MEDIUM")]
        risky = [f for f in all_findings if f["severity"] == "LOW"]
        env_files = [f for f in all_findings if f["id"] == "env-file" and f["severity"] != "INFO"]
        truncated = len(all_findings) > ctx.config.max_findings
        return {
            "secrets": secrets[:ctx.config.max_findings],
            "risky": risky[:ctx.config.max_findings],
            "env_files": env_files,
            "secret_count": len(secrets),
            "risky_count": len(risky),
            "truncated": truncated,
        }
