# RepoSage Context Pack - e40bcc4b

> Generated 2026-10-28T18:21+00:00 with RepoSage v1.0.0. AI-ready repository context.

## Overview

| Key | Value |
|---|---|
| Name | e40bcc4b |
| Git | - |
| License | MIT |
| Size | 2,299 LOC across 29 files |
| Languages | Python 91%, Markdown 5%, TOML 1%, Other 1%, YAML 1% |
| File kinds | code 19, tests 5, config 2, docs 1 |


## Structure

```
e40bcc4b/
|-- .gitignore
|-- LICENSE
|-- pyproject.toml
|-- README.md
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- reposage/  (19 files)
|   |-- __init__.py
|   |-- __main__.py
|   |-- cache.py
|   |-- cli.py
|   |-- config.py
|   |-- context.py
|   |-- gitx.py
|   |-- lang.py
|   |-- scanner.py
|   |-- writer.py
|   `-- analyzers/  (9 files)
|       |-- __init__.py
|       |-- base.py
|       |-- conventions.py
|       |-- dependencies.py
|       |-- endpoints.py
|       |-- overview.py
|       |-- security.py
|       |-- structure.py
|       `-- todos.py
`-- tests/  (5 files)
    |-- __init__.py
    |-- test_analyzers.py
    |-- test_cli.py
    |-- test_lang.py
    `-- test_scanner.py
```


## Endpoints

| Method | Path | File:Line |
|---|---|---|
| ANY | `/api/users` | tests/test_analyzers.py:27 |
| ANY | `/api/users/<int:uid>` | tests/test_analyzers.py:31 |
| GET | `/items` | tests/test_analyzers.py:40 |
| POST | `/items` | tests/test_analyzers.py:41 |
| ANY | `/api/hello` | tests/test_cli.py:13 |
| ANY | `/api/goodbye` | tests/test_cli.py:47 |


## Dependencies




## Todos

- [TODO] README.md:137 - items are riskiest?"*
- [HACK] reposage/analyzers/todos.py:15 - markers with file and line."
- [TODO] reposage/writer.py:94 - in section["todos"]:
- [TODO] reposage/writer.py:205 - in todos["todos"][:5]:
- [TODO] tests/test_analyzers.py:219 - implement this\n\n# FIXME broken\n"
- [TODO] tests/test_cli.py:13 - add docs\n',


## Security

- **[HIGH]** tests/test_analyzers.py:185 - AWS access key ID  `findings = self._findings("config.py", 'key = "AKIAIOSFODNN7...`
- **[MEDIUM]** tests/test_analyzers.py:200 - Hardcoded password  `findings = self._findings("config.py", 'password = "SuperSec...`
- **[HIGH]** tests/test_cli.py:63 - AWS access key ID  `(root / "config.py").write_text('aws_key = "AKIAIOSFODNN7EXA...`
- [LOW] README.md:15 - subprocess with shell=True
- [LOW] README.md:109 - subprocess with shell=True
- [LOW] reposage/analyzers/security.py:30 - eval() call
- [LOW] reposage/analyzers/security.py:31 - exec() call
- [LOW] reposage/analyzers/security.py:32 - subprocess with shell=True
- [LOW] reposage/analyzers/security.py:33 - Unsafe HTML injection
- [LOW] reposage/analyzers/security.py:34 - document.write()
- [LOW] reposage/analyzers/security.py:36 - os.system() call
- [LOW] reposage/analyzers/security.py:37 - exec() call
- [LOW] tests/test_analyzers.py:205 - subprocess with shell=True


## Conventions

| Key | Value |
|---|---|
| Tests | custom (5 test files) |
| CI | .github/workflows |
| Formatters | - |
| Package managers | - |
| Monorepo | no |
| Indent style | spaces (4) |
