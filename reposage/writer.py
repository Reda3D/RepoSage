from __future__ import annotations

import json

from . import __version__


def _kv_table(rows):
    if not rows:
        return ""
    lines = ["| Key | Value |", "|---|---|"]
    lines.extend("| %s | %s |" % (k, v) for k, v in rows)
    return "\n".join(lines) + "\n"


def _overview_section(data):
    overview = data["overview"]
    git = overview.get("git") or {}
    git_line = ""
    if git:
        parts = []
        if git.get("remote"):
            parts.append(git["remote"])
        if git.get("branch"):
            parts.append("branch " + git["branch"])
        if git.get("commit"):
            parts.append("@" + git["commit"])
        git_line = " ".join(parts)
    langs = ", ".join("%s %d%%" % (lang, round(loc / max(overview["total_loc"], 1) * 100))
                       for lang, loc, _ in overview["languages"][:6]) or "-"
    kinds = overview["file_kinds"]
    return _kv_table([
        ("Name", overview["name"]),
        ("Git", git_line or "-"),
        ("License", overview["license"]),
        ("Size", "%s LOC across %s files" % ("{:,}".format(overview["total_loc"]),
                                             "{:,}".format(overview["total_files"]))),
        ("Languages", langs),
        ("File kinds", "code %d, tests %d, config %d, docs %d" % (
            kinds["code"], kinds["test"], kinds["config"], kinds["docs"])),
    ])


def _structure_section(data):
    name = data.get("overview", {}).get("name", "root")
    return "```\n%s/\n%s\n```\n" % (name, "\n".join(data["structure"]["tree"]))


def _endpoints_section(data):
    section = data["endpoints"]
    lines = []
    if section["endpoints"]:
        lines.append("| Method | Path | File:Line |")
        lines.append("|---|---|---|")
        for ep in section["endpoints"]:
            lines.append("| %s | `%s` | %s:%d |" % (
                ep["method"], ep["path"], ep["file"], ep["line"]))
    if section["truncated"]:
        lines.append("")
        lines.append("_(%d+ more endpoints - raise `max_endpoints` in config to see all)_" % section["count"])
    if section["entry_points"]:
        lines.append("")
        lines.append("**Entry points:** " + ", ".join(section["entry_points"]))
    return "\n".join(lines) + "\n"


def _dependencies_section(data):
    section = data["dependencies"]
    lines = []
    for manifest in section["manifests"]:
        dep_keys = [k for k in ("dependencies", "devDependencies", "peerDependencies", "optional") if manifest.get(k)]
        if not dep_keys:
            continue
        lines.append("### %s" % manifest["file"])
        for key in dep_keys:
            value = manifest[key]
            if key == "optional":
                value = {group: "%d deps" % count for group, count in value.items()}
            if value:
                lines.append("**%s:**" % key)
                for name, version in list(value.items())[:40]:
                    lines.append("- %s `%s`" % (name, version))
        if manifest.get("scripts"):
            lines.append("**scripts:** " + ", ".join("`%s`" % s for s in manifest["scripts"]))
        lines.append("")
    if section["lockfiles"]:
        lines.append("**Lockfiles:** " + ", ".join(section["lockfiles"]))
    return "\n".join(lines).rstrip() + "\n"


def _todos_section(data):
    section = data["todos"]
    lines = []
    for todo in section["todos"]:
        suffix = " - %s" % todo["text"] if todo["text"] else ""
        lines.append("- [%s] %s:%d%s" % (todo["tag"], todo["file"], todo["line"], suffix))
    if section["truncated"]:
        lines.append("- _(%d+ more - raise `max_todos` in config to see all)_" % section["count"])
    return "\n".join(lines) + "\n"


def _security_section(data):
    section = data["security"]
    lines = []
    for finding in section["secrets"]:
        lines.append("- **[%s]** %s:%d - %s  `%s`" % (
            finding["severity"], finding["file"], finding["line"], finding["what"], finding["snippet"]))
    for finding in section["risky"][:15]:
        lines.append("- [LOW] %s:%d - %s" % (finding["file"], finding["line"], finding["what"]))
    if section["risky_count"] > 15:
        lines.append("- _(%d more low-severity findings)_" % (section["risky_count"] - 15))
    if section["truncated"]:
        lines.append("- _(more findings - raise `max_findings` in config)_")
    if not section["secrets"] and not section["risky"]:
        lines.append("- No obvious secrets or risky calls detected.")
    return "\n".join(lines) + "\n"


def _conventions_section(data):
    section = data["conventions"]
    rows = [
        ("Tests", "%s (%d test files)" % (section["test_framework"], section["test_files"])),
        ("CI", ", ".join(section["ci"]) or "-"),
        ("Formatters", ", ".join(section["formatters"]) or "-"),
        ("Package managers", ", ".join(section["package_managers"]) or "-"),
        ("Monorepo", "yes" if section["monorepo"] else "no"),
        ("Indent style", section["indent"]),
    ]
    return _kv_table(rows)


SECTION_RENDERERS = {
    "overview": _overview_section,
    "structure": _structure_section,
    "endpoints": _endpoints_section,
    "dependencies": _dependencies_section,
    "todos": _todos_section,
    "security": _security_section,
    "conventions": _conventions_section,
}


def render_markdown(sections):
    overview = sections.get("overview", {})
    name = overview.get("name", "unknown")
    lines = [
        "# RepoSage Context Pack - %s" % name,
        "",
        "> Generated %s with RepoSage v%s. AI-ready repository context." % (
            overview.get("generated", ""), __version__),
        "",
    ]
    for key, renderer in SECTION_RENDERERS.items():
        if key not in sections:
            continue
        lines.append("## %s" % key.replace("-", " ").title())
        lines.append("")
        lines.append(renderer(sections))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(sections):
    return json.dumps(sections, indent=2, ensure_ascii=False) + "\n"


def render_prompt(sections):
    md = render_markdown(sections)
    return (
        "You are a senior software engineer working in the repository summarized below.\n"
        "Use this context to ground your answers and cite file paths when referencing code.\n"
        "If the answer is not in the context, say so instead of guessing.\n\n"
        "<repository_context>\n" + md + "\n</repository_context>\n"
    )


def render_brief(sections):
    overview = sections.get("overview", {})
    git = overview.get("git") or {}
    lines = [
        "%s" % overview.get("name", ""),
        "  %s files, %s LOC | %s" % (
            "{:,}".format(overview.get("total_files", 0)),
            "{:,}".format(overview.get("total_loc", 0)),
            git.get("remote") or "no git remote"),
    ]
    langs = ", ".join("%s %d%%" % (l, round(loc / max(overview.get("total_loc", 1), 1) * 100))
                      for l, loc, _ in overview.get("languages", [])[:5])
    if langs:
        lines.append("  Languages: " + langs)
    tree = sections.get("structure", {}).get("tree", [])
    if tree:
        lines.append("  Structure:")
        lines.extend("  " + line for line in tree[:20])
        if len(tree) > 20:
            lines.append("  ...")
    endpoints = sections.get("endpoints", {})
    if endpoints.get("endpoints"):
        lines.append("  Endpoints (%d):" % endpoints["count"])
        for ep in endpoints["endpoints"][:10]:
            lines.append("    %s %s  (%s:%d)" % (ep["method"], ep["path"], ep["file"], ep["line"]))
    todos = sections.get("todos", {})
    if todos.get("todos"):
        lines.append("  TODOs (%d), first 5:" % todos["count"])
        for todo in todos["todos"][:5]:
            lines.append("    %s:%d %s" % (todo["file"], todo["line"], todo["text"] or todo["tag"]))
    security = sections.get("security", {})
    lines.append("  Security: %d secret(s), %d risky call(s)" % (
        security.get("secret_count", 0), security.get("risky_count", 0)))
    return "\n".join(lines) + "\n"
