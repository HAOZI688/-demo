"""预置 JSON 加载工具"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

from app.config import settings


@lru_cache(maxsize=64)
def load_preset(name: str) -> dict:
    """
    加载 data/preset/{name}.json
    失败返回空 dict（不抛错，保证主链路不阻塞）
    """
    path: Path = settings.PRESET_DIR / f"{name}.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
