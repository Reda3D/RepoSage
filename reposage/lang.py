from __future__ import annotations

from pathlib import Path

EXT_LANG = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript (JSX)",
    ".ts": "TypeScript", ".tsx": "TypeScript (TSX)",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".go": "Go", ".rs": "Rust",
    ".c": "C", ".h": "C/C++ Header", ".cpp": "C++", ".cc": "C++", ".hpp": "C++",
    ".cs": "C#", ".fs": "F#", ".vb": "Visual Basic",
    ".rb": "Ruby", ".php": "PHP", ".pl": "Perl", ".lua": "Lua",
    ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C++",
    ".dart": "Dart", ".r": "R", ".jl": "Julia", ".ex": "Elixir", ".exs": "Elixir",
    ".clj": "Clojure", ".erl": "Erlang", ".hs": "Haskell", ".ml": "OCaml",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell",
    ".ps1": "PowerShell", ".bat": "Batch", ".cmd": "Batch",
    ".sql": "SQL",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "Sass",
    ".less": "Less", ".vue": "Vue", ".svelte": "Svelte",
    ".md": "Markdown", ".markdown": "Markdown", ".rst": "reStructuredText",
    ".txt": "Text",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
    ".xml": "XML", ".ini": "INI", ".cfg": "Config", ".conf": "Config",
    ".csv": "CSV", ".tsv": "TSV",
    ".proto": "Protobuf", ".graphql": "GraphQL", ".gql": "GraphQL",
    ".tf": "Terraform", ".hcl": "HCL",
    ".mod": "Go", ".sum": "Go",
    ".dockerfile": "Dockerfile", ".mk": "Makefile", ".cmake": "CMake",
    ".ipynb": "Jupyter Notebook",
    ".gradle": "Gradle", ".groovy": "Groovy",
    ".sol": "Solidity", ".nim": "Nim", ".zig": "Zig", ".v": "V",
}

DATA_EXTS = {".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".tsv", ".lock"}
DOC_EXTS = {".md", ".markdown", ".rst", ".txt", ".adoc", ".org"}
LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock",
    "poetry.lock", "Pipfile.lock", "uv.lock", "requirements.lock",
    "go.sum", "Cargo.lock", "Gemfile.lock", "composer.lock", "mix.lock",
    "gradle.lockfile", "pubspec.lock", "packages.lock.json", "Podfile.lock",
}


def classify(path: str) -> str:
    name = path.lower()
    if name.endswith("dockerfile"):
        return "Dockerfile"
    if name == "makefile":
        return "Makefile"
    if name.endswith("gemfile"):
        return "Ruby"
    return EXT_LANG.get(Path(name).suffix, "")


def is_code(path: str) -> bool:
    lang = classify(path)
    if not lang:
        return False
    ext = Path(path).suffix.lower()
    return ext not in DATA_EXTS and ext not in DOC_EXTS


def count_loc(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())
