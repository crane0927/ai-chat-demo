import os
from pathlib import Path


APP_TITLE = "AI 助理"
DEFAULT_SYSTEM_PROMPT = "你叫困困，是一个 AI 助理，请使用可爱活泼的语气回复用户的问题。"
DEFAULT_DATABASE_URL = "postgresql://admin:PK3uK7pUIwUTi1@localhost:5432/ai_chat_demo"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_CHAT_MODEL = "deepseek-chat"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_CONTEXT_MESSAGES = 20
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RAG_MAX_FILE_SIZE_MB = 10
DEFAULT_RAG_MAX_CHUNKS_PER_FILE = 200
DEFAULT_RAG_TOP_K = 4


def get_app_secret_key() -> str:
    return os.getenv("APP_SECRET_KEY", "")


def load_dotenv_file(path: str | Path = ".env") -> bool:
    env_path = Path(path)
    if not env_path.exists() or not env_path.is_file():
        return False

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key or normalized_key in os.environ:
            continue

        normalized_value = value.strip().strip('"').strip("'")
        # 本地 .env 只补齐缺省值，避免覆盖 shell 或部署环境中显式传入的配置。
        os.environ[normalized_key] = normalized_value

    return True


load_dotenv_file()


def get_env_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


def get_database_url() -> str:
    return os.getenv("APP_DATABASE_URL") or os.getenv(
        "DATABASE_URL", DEFAULT_DATABASE_URL
    )


def get_env_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)


def get_env_chat_model() -> str:
    return os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)


def _clamp_int(value: int, min_value: int, max_value: int) -> int:
    return min(max(value, min_value), max_value)


def _clamp_float(value: float, min_value: float, max_value: float) -> float:
    return min(max(value, min_value), max_value)


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_env_max_tokens() -> int:
    return _clamp_int(_get_int_env("OPENAI_MAX_TOKENS", DEFAULT_MAX_TOKENS), 1, 32000)


def get_env_context_messages() -> int:
    return _clamp_int(
        _get_int_env("OPENAI_CONTEXT_MESSAGES", DEFAULT_CONTEXT_MESSAGES), 1, 200
    )


def get_env_timeout_seconds() -> float:
    return _clamp_float(
        _get_float_env("OPENAI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        1.0,
        300.0,
    )


def get_env_max_retries() -> int:
    return _clamp_int(_get_int_env("OPENAI_MAX_RETRIES", DEFAULT_MAX_RETRIES), 0, 10)


def get_rag_max_file_size_mb() -> int:
    # 文件体积限制需要保留合理上限，避免超大文件在本地 Demo 中拖垮解析流程。
    return _clamp_int(
        _get_int_env("RAG_MAX_FILE_SIZE_MB", DEFAULT_RAG_MAX_FILE_SIZE_MB), 1, 100
    )


def get_rag_max_chunks_per_file() -> int:
    # 分块数量限制用于兜住异常长文本，避免单文件生成过多片段影响性能。
    return _clamp_int(
        _get_int_env(
            "RAG_MAX_CHUNKS_PER_FILE",
            DEFAULT_RAG_MAX_CHUNKS_PER_FILE,
        ),
        1,
        1000,
    )


def get_rag_top_k() -> int:
    # 检索条数过大会显著放大上下文注入量，这里统一做边界收敛。
    return _clamp_int(_get_int_env("RAG_TOP_K", DEFAULT_RAG_TOP_K), 1, 20)
