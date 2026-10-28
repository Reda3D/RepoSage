from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from .base import FileAnalyzer
from ..lang import is_code

CI_FILES = {
    ".github/workflows", ".gitlab-ci.yml", ".circleci/config.yml",
    "azure-pipelines.yml", "Jenkinsfile", "bitbucket-pipelines.yml",
    ".buildkite", ".travis.yml", "appveyor.yml",
}
FORMATTER_CONFIGS = {
    ".editorconfig", ".prettierrc", ".prettierrc.json", ".prettierrc.yaml",
    ".prettierrc.js", ".prettierrc.toml", "prettier.config.js",
    ".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js", "eslint.config.mjs",
    ".stylelintrc", ".stylelintrc.json", "stylelint.config.js",
    "ruff.toml", ".ruff.toml", ".flake8", ".pylintrc", "mypy.ini",
    ".clang-format", "_clang-format", ".php-cs-fixer.php", "phpcs.xml",
    ".rubocop.yml", ".golangci.yml", ".swiftformat", "biome.json",
}
TEST_CONFIGS = {
    "conftest.py": "pytest", "pytest.ini": "pytest", "tox.ini": "pytest/tox",
    "jest.config.js": "jest", "jest.config.ts": "jest", "jest.config.json": "jest",
    "vitest.config.js": "vitest", "vitest.config.ts": "vitest",
    "mocha.opts": "mocha", ".mocharc.json": "mocha",
    "cypress.config.js": "cypress", "cypress.config.ts": "cypress",
    "playwright.config.js": "playwright", "playwright.config.ts": "playwright",
    "phpunit.xml": "phpunit", "phpunit.xml.dist": "phpunit",
    "Rakefile": "minitest/rspec", ".rspec": "rspec",
    "build.gradle": "junit", "pom.xml": "junit",
    "go.mod": "go test",
}
WORKSPACE_CONFIGS = {
    "pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json",
    "rush.json", "go.work", "workspace.json", "yarn.config.cjs",
}
PACKAGE_MANAGERS = {
    "package-lock.json": "npm", "yarn.lock": "yarn", "pnpm-lock.yaml": "pnpm", "bun.lockb": "bun",
    "poetry.lock": "poetry", "Pipfile.lock": "pipenv", "uv.lock": "uv",
    "go.sum": "go modules", "Cargo.lock": "cargo", "Gemfile.lock": "bundler",
    "composer.lock": "composer", "mix.lock": "mix",
}

TAB = "\t"
SPACE_WIDTHS = (2, 4, 8)


class ConventionsAnalyzer(FileAnalyzer):
    name = "conventions"
    title = "Conventions & Tooling"
    description = "Tests, CI, formatters, package managers and indent style."

    def matches(self, rel):
        return is_code(rel)

    def analyze_file(self, rel, text, ctx):
        tab_lines = 0
        space_widths = Counter()
        for line in text.splitlines()[:200]:
            stripped = line.lstrip(TAB)
            if len(stripped) < len(line):
                tab_lines += 1
            elif line.startswith(" ") and line.strip():
                width = len(line) - len(line.lstrip(" "))
                if width in SPACE_WIDTHS:
                    space_widths[width] += 1
        if tab_lines or space_widths:
            return {
                "tabs": tab_lines,
                "spaces": dict(space_widths),
            }
        return None

    def build_section(self, per_file, ctx):
        file_names = {PurePosixPath(fi.rel).name for fi in ctx.files}
        dir_parts = {part for fi in ctx.files for part in fi.rel.split("/")[:-1]}

        ci = sorted(p for p in CI_FILES if any(fi.rel.startswith(p) for fi in ctx.files))
        formatters = sorted(p for p in FORMATTER_CONFIGS if p in file_names)
        test_configs = sorted(p for p in TEST_CONFIGS if p in file_names)
        workspaces = sorted(p for p in WORKSPACE_CONFIGS if p in file_names)
        package_managers = sorted(PACKAGE_MANAGERS[p] for p in PACKAGE_MANAGERS if p in file_names)

        test_files = sum(
            1 for fi in ctx.files
            if any(seg in fi.rel.split("/") for seg in ("test", "tests", "spec", "__tests__"))
            or ".test." in fi.rel or fi.rel.endswith(("_test.go", "_test.py", ".spec.ts", ".spec.js"))
        )
        test_framework = self._guess_framework(test_files, test_configs, ctx)

        indent = self._indent_summary(per_file)
        return {
            "ci": ci,
            "formatters": formatters,
            "test_framework": test_framework,
            "test_files": test_files,
            "package_managers": package_managers,
            "monorepo": len(workspaces) > 0 or len(package_managers) > 1,
            "indent": indent,
        }

    def _guess_framework(self, test_files, test_configs, ctx):
        if test_configs:
            return TEST_CONFIGS.get(test_configs[0], "unknown")
        if test_files == 0:
            return "none detected"
        if any(fi.rel.endswith("_test.go") for fi in ctx.files):
            return "go test"
        if any(fi.rel.endswith("_test.py") or fi.rel.startswith("test_") for fi in ctx.files):
            return "pytest"
        if any(".test.js" in fi.rel or ".test.ts" in fi.rel or ".test.jsx" in fi.rel for fi in ctx.files):
            return "jest"
        if any(".spec.ts" in fi.rel or ".spec.js" in fi.rel for fi in ctx.files):
            return "vitest/jasmine"
        return "custom"

    def _indent_summary(self, per_file):
        results = [entry.get(self.name) for entry in per_file.values() if entry.get(self.name)]
        if not results:
            return "unknown"
        sampled = results[:20]
        tabs = sum(r["tabs"] for r in sampled)
        spaces = Counter()
        for r in sampled:
            spaces.update(r["spaces"])
        width = spaces.most_common(1)[0][0] if spaces else None
        if tabs > sum(spaces.values()):
            return "tabs"
        if width:
            return "spaces (%d)" % width
        return "mixed"
