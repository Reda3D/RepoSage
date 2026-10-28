from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .analyzers import ALL_ANALYZERS, FILE_ANALYZERS
from .analyzers.base import FileAnalyzer
from .analyzers.security import SecurityAnalyzer
from .cache import CACHE_VERSION, load_cache, save_cache
from .config import load_config, write_default_config
from .context import Context, FileInfo
from .scanner import scan
from .writer import render_brief, render_json, render_markdown, render_prompt
from . import gitx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reposage",
        description="Generate a compressed, AI-ready context pack for any codebase.",
    )
    parser.add_argument("--version", action="version", version="reposage " + __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a .reposage.toml config file")
    p_init.add_argument("path", nargs="?", default=".")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing config")

    p_gen = sub.add_parser("generate", help="scan the repo and write the context pack")
    _add_common(p_gen)
    p_gen.add_argument("--format", choices=["md", "json", "both"], default="both",
                       help="output formats to write (default: both)")

    p_upd = sub.add_parser("update", help="incrementally refresh the context pack")
    _add_common(p_upd)
    p_upd.add_argument("--format", choices=["md", "json", "both"], default="both")
    p_upd.add_argument("--force", action="store_true", help="ignore the cache and rescan everything")

    p_brief = sub.add_parser("brief", help="print a one-page repo summary to stdout")
    _add_common(p_brief)

    p_prompt = sub.add_parser("prompt", help="print the pack wrapped in a paste-ready AI prompt")
    _add_common(p_prompt)
    p_prompt.add_argument("--out", metavar="FILE", help="also write the prompt to a file")

    p_check = sub.add_parser("check", help="security-only scan; exit 1 if secrets are found (CI mode)")
    _add_common(p_check)
    p_check.add_argument("--strict", action="store_true",
                         help="also fail on low-severity risky calls")
    return parser


def _add_common(parser):
    parser.add_argument("path", nargs="?", default=".", help="repository path (default: .)")
    parser.add_argument("--out-dir", metavar="DIR", help="override the output directory")
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress progress output")


def _load(root: Path, out_dir=None) -> tuple:
    config = load_config(root)
    if out_dir:
        config = config.with_overrides(out_dir=out_dir)
    git = gitx.repo_meta(root)
    ctx = Context(root, config, git)
    files, skipped, depth_truncated = scan(root, config)
    ctx.files = [FileInfo(rel, path, size) for rel, path, size in files]
    ctx.scan_skipped = skipped
    ctx.depth_truncated = depth_truncated
    return config, ctx


def _analyze_files(ctx: Context, changed, cache) -> dict:
    per_file = {}
    cached_files = cache.get("files", {}) if cache else {}
    for fi in ctx.files:
        if changed is not None and fi.rel not in changed and fi.rel in cached_files:
            per_file[fi.rel] = cached_files[fi.rel].get("results", {})
            continue
        entry = {}
        text = ctx.text(fi)
        for analyzer in FILE_ANALYZERS:
            if ctx.is_enabled(analyzer.name) and analyzer.matches(fi.rel):
                entry[analyzer.name] = analyzer.analyze_file(fi.rel, text, ctx)
        per_file[fi.rel] = entry
    return per_file


def _build_sections(ctx: Context, per_file: dict) -> dict:
    sections = {}
    for analyzer in ALL_ANALYZERS:
        if not ctx.is_enabled(analyzer.name):
            continue
        if isinstance(analyzer, FileAnalyzer):
            sections[analyzer.name] = analyzer.build_section(per_file, ctx)
        else:
            sections[analyzer.name] = analyzer.run(ctx)
    return sections


def _build_cache(ctx: Context, per_file: dict) -> dict:
    return {
        "version": CACHE_VERSION,
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "files": {
            fi.rel: {
                "hash": fi.hash,
                "loc": fi.loc,
                "binary": fi.binary,
                "results": per_file[fi.rel],
            }
            for fi in ctx.files
        },
    }


def _write_outputs(args, ctx: Context, sections: dict, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    written = []
    if args.format in ("md", "both"):
        path = out / "reposage.md"
        path.write_text(render_markdown(sections), encoding="utf-8")
        written.append((path, path.stat().st_size))
    if args.format in ("json", "both"):
        path = out / "reposage.json"
        path.write_text(render_json(sections), encoding="utf-8")
        written.append((path, path.stat().st_size))
    return written


def _summary(ctx: Context, written):
    parts = ["%s (%s)" % (p.name, _human(p.stat().st_size)) for p, _ in written]
    print("Scanned %d files (%s LOC) - wrote %s" % (
        len(ctx.files), "{:,}".format(ctx.loc_total()), ", ".join(parts)))
    if ctx.scan_skipped:
        print("  skipped %d file(s) (size/depth limits; see config)" % ctx.scan_skipped)
    if ctx.truncated:
        print("  warning: read budget reached - some file contents were not analyzed")


def _human(size: int) -> str:
    if size >= 1024 * 1024:
        return "%.1f MB" % (size / 1024 / 1024)
    if size >= 1024:
        return "%.1f KB" % (size / 1024)
    return "%d B" % size


def cmd_generate(args) -> int:
    root = Path(args.path).resolve()
    config, ctx = _load(root, getattr(args, "out_dir", None))
    ctx.populate()
    per_file = _analyze_files(ctx, None, None)
    sections = _build_sections(ctx, per_file)
    out = root / config.out_dir
    written = _write_outputs(args, ctx, sections, out)
    save_cache(out, _build_cache(ctx, per_file))
    if not args.quiet:
        _summary(ctx, written)
    return 0


def cmd_update(args) -> int:
    root = Path(args.path).resolve()
    config, ctx = _load(root, getattr(args, "out_dir", None))
    out = root / config.out_dir
    cache = None if getattr(args, "force", False) else load_cache(out)
    if cache is None:
        if not args.quiet:
            print("No valid cache found - performing full scan.")
        return cmd_generate(args)
    cached_files = cache.get("files", {})
    git_changed = gitx.changed_files(root) if ctx.git is not None else None
    current_rels = {fi.rel for fi in ctx.files}
    if git_changed is not None:
        changed = {rel for rel in git_changed if rel in current_rels}
        changed |= {fi.rel for fi in ctx.files if fi.rel not in cached_files}
        for fi in ctx.files:
            cached = cached_files.get(fi.rel)
            if fi.rel not in changed and cached and cached.get("hash"):
                fi.hash = cached["hash"]
                fi.loc = cached.get("loc", 0)
                fi.binary = cached.get("binary", False)
        ctx.populate(changed)
    else:
        ctx.populate()
        changed = {
            fi.rel for fi in ctx.files
            if fi.rel not in cached_files or cached_files[fi.rel].get("hash") != fi.hash
        }
    removed = set(cached_files) - current_rels
    if not changed and not removed:
        if not args.quiet:
            print("Context pack is up to date.")
        return 0
    per_file = _analyze_files(ctx, changed, cache)
    sections = _build_sections(ctx, per_file)
    written = _write_outputs(args, ctx, sections, out)
    new_files = {}
    for fi in ctx.files:
        cached = cached_files.get(fi.rel)
        if cached and fi.rel not in changed:
            new_files[fi.rel] = cached
        else:
            new_files[fi.rel] = {
                "hash": fi.hash, "loc": fi.loc, "binary": fi.binary,
                "results": per_file[fi.rel],
            }
    save_cache(out, {
        "version": CACHE_VERSION,
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "files": new_files,
    })
    if not args.quiet:
        print("Updated: %d changed, %d removed" % (len(changed), len(removed)))
        _summary(ctx, written)
    return 0


def cmd_brief(args) -> int:
    root = Path(args.path).resolve()
    config, ctx = _load(root, getattr(args, "out_dir", None))
    ctx.populate()
    per_file = _analyze_files(ctx, None, None)
    sections = _build_sections(ctx, per_file)
    if not args.quiet:
        print(render_brief(sections), end="")
    return 0


def cmd_prompt(args) -> int:
    root = Path(args.path).resolve()
    config, ctx = _load(root, getattr(args, "out_dir", None))
    ctx.populate()
    per_file = _analyze_files(ctx, None, None)
    sections = _build_sections(ctx, per_file)
    text = render_prompt(sections)
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
        if not args.quiet:
            print("Wrote %s" % args.out)
    else:
        print(text, end="")
    return 0


def cmd_check(args) -> int:
    root = Path(args.path).resolve()
    config, ctx = _load(root, getattr(args, "out_dir", None))
    ctx.populate()
    per_file = {}
    for fi in ctx.files:
        entry = {}
        if SecurityAnalyzer().matches(fi.rel):
            entry["security"] = SecurityAnalyzer().analyze_file(fi.rel, ctx.text(fi), ctx)
        per_file[fi.rel] = entry
    section = SecurityAnalyzer().build_section(per_file, ctx)
    for finding in section["secrets"]:
        print("[%s] %s:%d - %s" % (finding["severity"], finding["file"], finding["line"], finding["what"]))
    for finding in section["risky"]:
        print("[LOW] %s:%d - %s" % (finding["file"], finding["line"], finding["what"]))
    fail = section["secret_count"] > 0
    if getattr(args, "strict", False):
        fail = fail or section["risky_count"] > 0
    if not args.quiet:
        if fail:
            print("FAIL: %d secret(s), %d risky call(s) found." % (
                section["secret_count"], section["risky_count"]))
        else:
            print("OK: no secrets detected (%d low-severity findings)." % section["risky_count"])
    return 1 if fail else 0


def cmd_init(args) -> int:
    root = Path(args.path).resolve()
    created, path = write_default_config(root, force=args.force)
    if created:
        print("Wrote %s" % path)
    else:
        print("%s already exists (use --force to overwrite)" % path)
    return 0


def dispatch(args) -> int:
    commands = {
        "init": cmd_init,
        "generate": cmd_generate,
        "update": cmd_update,
        "brief": cmd_brief,
        "prompt": cmd_prompt,
        "check": cmd_check,
    }
    return commands[args.command](args)


def run(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return dispatch(args)
    except OSError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except OSError:
            pass
    sys.exit(run(argv))
