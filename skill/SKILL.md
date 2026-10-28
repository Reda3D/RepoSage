---
name: reposage
description: Generate an AI-ready context pack of the current repository (architecture, HTTP endpoints, dependencies, TODOs, security findings, conventions) using the RepoSage CLI. Use when asked to summarize, explain, or explore an unfamiliar codebase, when answering "where is X implemented" style questions across files, or when a repo map would help ground answers with file:line citations.
when_to_use: Repo overview questions, codebase exploration, "how does this project work", security/secret quick-scan requests.
argument-hint: "[brief | generate | prompt | update | check]"
---

# RepoSage

RepoSage distills a repository into a token-efficient context pack with file:line
citations. Prefer it over reading many files when the question spans the codebase.

## Workflow

1. Determine what the user needs:
   - Quick question or orientation -> run `brief`
   - Full deep-dive, or the pack should be saved/reused -> run `generate`
   - User wants text to paste into another AI tool -> run `prompt`
2. Run the command in the repo root:
   - `python -m reposage brief` - one-page summary (name, git, size, languages, tree, top endpoints, TODO count, security counts)
   - `python -m reposage generate` - writes `reposage-out/reposage.md` and `reposage.json`; then read `reposage-out/reposage.md`
   - `python -m reposage prompt` - same content wrapped in a paste-ready AI prompt (stdout)
   - `python -m reposage update` - incremental refresh; run this instead of generate when the pack already exists and only a few files changed
   - `python -m reposage check` - security-only scan; non-zero exit = secrets found
3. Answer the user's question from the pack output, citing `file:line` from it.
   If the pack lacks detail needed for the question, read the specific files directly.

## Rules

- Run `update` instead of `generate` when `reposage-out/reposage.md` already exists
  and looks recent; it re-analyzes only changed files.
- The pack is regex-based and may miss dynamically-built routes or obfuscated
  secrets; verify anything security-critical by reading the actual file.
- If `python -m reposage` fails with ModuleNotFoundError, tell the user to install
  it first: `pip install .` from the reposage repo, or `pip install reposage`.
- If the current directory is not inside the target repo, pass the path:
  `python -m reposage brief /path/to/repo`.

## Output locations

- `reposage-out/reposage.md` - human/AI-readable context pack
- `reposage-out/reposage.json` - machine-readable version
- `.reposage.toml` - optional config (create with `reposage init`)
