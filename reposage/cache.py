from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

CACHE_VERSION = 2


def load_cache(out_dir: Path) -> Optional[dict]:
    path = out_dir / ".cache.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
        return None
    return data


def save_cache(out_dir: Path, cache: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".cache.json").write_text(
        json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8"
    )
