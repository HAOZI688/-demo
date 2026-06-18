"""配置管理 — pydantic Settings + dotenv"""
import os
from pathlib import Path
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).parent.parent
# 优先读 .env.runtime（部署时生成），fallback 到 .env
load_dotenv(_BASE_DIR / ".env.runtime", override=False)
load_dotenv(_BASE_DIR / ".env", override=False)


def _bool(val: str) -> bool:
    return str(val).lower() in ("1", "true", "yes", "on")


class Settings:
    # === 第一轮最小配置 ===
    # 模式开关
    USE_LLM: bool = _bool(os.getenv("USE_LLM", "0"))  # 默认 mock

    # LLM 凭据（仅 USE_LLM=1 时使用；当前第一轮安全 fallback mock）
    TOKEN_API_BASE: str = os.getenv("TOKEN_API_BASE", "")
    TOKEN_API_KEY: str = os.getenv("TOKEN_API_KEY", "")
    TOKEN_MODEL_NAME: str = os.getenv("TOKEN_MODEL_NAME", "")

    # 路径
    BASE_DIR: Path = _BASE_DIR
    DATA_DIR: Path = _BASE_DIR / "data"
    PRESET_DIR: Path = _BASE_DIR / "data" / "preset"
    DATABASE_URL: str = f"sqlite:///{_BASE_DIR}/data/manju.db"

    # 业务
    SESSION_EXPIRE_HOURS: int = 24
    MIN_SCRIPT_CHARS: int = 50
    APP_VERSION: str = "0.1.0"

    # 占位版本信息（第二轮 CI 注入真实 commit/build_time）
    PLACEHOLDER_COMMIT: str = "local-dev"
    PLACEHOLDER_BUILD_TIME: str = "local-dev"


settings = Settings()
