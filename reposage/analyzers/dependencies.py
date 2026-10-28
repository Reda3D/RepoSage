from __future__ import annotations

import ast
import json
import re
from pathlib import PurePosixPath

from .base import FileAnalyzer
from ..lang import LOCKFILES

REQ_NAMES = {
    "requirements.txt", "requirements-dev.txt", "dev-requirements.txt",
    "requirements-test.txt", "requirements-prod.txt",
}
REQ_LINE = re.compile(r"^([A-Za-z0-9_.\-\[\]]+)\s*(.*)$")
GOMOD_LINE = re.compile(r"^([\w./\-]+)\s+(v[\w.+\-]+)")
CARGO_LINE = re.compile(r"^([A-Za-z0-9_.\-]+)\s*=\s*(?:[\"']([^\"']+)[\"']|\{[^}]*version\s*=\s*[\"']([^\"']+)[\"'])")
GEM_LINE = re.compile(r"^\s*gem\s+[\"']([^\"']+)[\"'](?:,\s*[\"']([^\"']*)[\"'])?")


def _naive_toml(text):
    root = {}
    current = root
    pending_list = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if pending_list is not None:
            if line.endswith("]"):
                item = line[:-1].strip().rstrip(",")
                if item:
                    pending_list.append(_scalar(item))
                pending_list = None
            else:
                item = line.rstrip(",").strip()
                if item:
                    pending_list.append(_scalar(item))
            continue
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            keys = [k.strip().strip("\"'") for k in line[1:-1].split(".")]
            current = root
            for key in keys:
                current = current.setdefault(key, {})
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value == "[":
                current[key] = []
                pending_list = current[key]
            else:
                current[key] = _scalar(value)
    return root


def _scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value
    try:
        return int(value)
    except ValueError:
        return value


def parse_requirements(text):
    deps = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        match = REQ_LINE.match(line)
        if match:
            deps[match.group(1)] = match.group(2).strip() or "any"
    return {"dependencies": deps}


def parse_package_json(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return {
        "dependencies": data.get("dependencies", {}) or {},
        "devDependencies": data.get("devDependencies", {}) or {},
        "peerDependencies": data.get("peerDependencies", {}) or {},
        "scripts": data.get("scripts", {}) or {},
    }


def parse_pyproject(text):
    try:
        import tomllib  # Python 3.11+
        data = tomllib.loads(text)
    except (ImportError, ValueError):
        data = _naive_toml(text)
    result = {"dependencies": {}, "optional": {}, "scripts": {}}
    project = data.get("project", {}) if isinstance(data.get("project"), dict) else {}
    for dep in project.get("dependencies", []) or []:
        name, _, spec = dep.partition("==") if "==" in dep else dep.partition(">=")
        name = re.split(r"[<>=!~\s]", dep, 1)[0].strip() if not name else name.strip()
        if name:
            result["dependencies"][name] = spec.strip() if spec else "any"
    optional = project.get("optional-dependencies", {}) or {}
    if isinstance(optional, dict):
        for group, deps in optional.items():
            result["optional"][group] = len(deps) if isinstance(deps, list) else 0
    scripts = project.get("scripts", {}) or {}
    if isinstance(scripts, dict):
        result["scripts"] = dict(scripts)
    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool", {}), dict) else {}
    if isinstance(poetry, dict):
        for name, spec in poetry.get("dependencies", {}).items():
            if name == "python":
                continue
            version = spec.get("version", "any") if isinstance(spec, dict) else str(spec)
            result["dependencies"][name] = version
    return result


def parse_gomod(text):
    deps = {}
    in_block = False
    for line in text.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        if line.startswith("require") and line.endswith("("):
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        candidate = line[7:].strip() if line.startswith("require ") else line
        match = GOMOD_LINE.match(candidate)
        if match and (in_block or line.startswith("require ")):
            deps[match.group(1)] = match.group(2)
    return deps


def parse_cargo(text):
    deps = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            current = stripped.strip("[]").strip()
            continue
        if current in ("dependencies", "dev-dependencies", "build-dependencies"):
            match = CARGO_LINE.match(stripped)
            if match:
                deps[match.group(1)] = match.group(2) or match.group(3) or "any"
    return deps


def parse_gemfile(text):
    deps = {}
    for line in text.splitlines():
        match = GEM_LINE.match(line)
        if match:
            deps[match.group(1)] = match.group(2) or "any"
    return deps


def parse_composer(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return {
        "dependencies": data.get("require", {}) or {},
        "devDependencies": data.get("require-dev", {}) or {},
    }


def parse_pom(text):
    deps = {}
    pattern = re.compile(
        r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*(?:<version>([^<]+)</version>)?",
        re.S,
    )
    for match in pattern.finditer(text):
        deps[f"{match.group(1)}:{match.group(2)}"] = match.group(3) or "any"
    return deps


PARSERS = {
    "requirements.txt": parse_requirements,
    "requirements-dev.txt": parse_requirements,
    "dev-requirements.txt": parse_requirements,
    "requirements-test.txt": parse_requirements,
    "requirements-prod.txt": parse_requirements,
    "package.json": parse_package_json,
    "pyproject.toml": parse_pyproject,
    "go.mod": parse_gomod,
    "Cargo.toml": parse_cargo,
    "Gemfile": parse_gemfile,
    "composer.json": parse_composer,
    "pom.xml": parse_pom,
}


class DependenciesAnalyzer(FileAnalyzer):
    name = "dependencies"
    title = "Dependencies"
    description = "Third-party dependencies and build scripts."
    names = set(PARSERS)

    def matches(self, rel):
        return PurePosixPath(rel).name in self.names

    def analyze_file(self, rel, text, ctx):
        parser = PARSERS[PurePosixPath(rel).name]
        return parser(text)

    def build_section(self, per_file, ctx):
        manifests = []
        lockfiles = []
        for rel, entry in per_file.items():
            data = entry.get(self.name)
            if data is not None:
                manifests.append({"file": rel, **data})
            if PurePosixPath(rel).name in LOCKFILES:
                lockfiles.append(rel)
        for rel, entry in per_file.items():
            if PurePosixPath(rel).name in LOCKFILES and rel not in lockfiles:
                lockfiles.append(rel)
        return {
            "manifests": sorted(manifests, key=lambda m: m["file"]),
            "lockfiles": sorted(set(lockfiles)),
            "manifest_count": len(manifests),
        }
