import os


APP_TITLE = "AI 助理"
DEFAULT_SYSTEM_PROMPT = "你叫困困，是一个 AI 助理，请使用可爱活泼的语气回复用户的问题。"
DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_chat_demo"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_CHAT_MODEL = "deepseek-chat"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_CONTEXT_MESSAGES = 20
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 2


def get_env_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


def get_database_url() -> str:
    return os.getenv("APP_DATABASE_URL") or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


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
    return _clamp_int(_get_int_env("OPENAI_CONTEXT_MESSAGES", DEFAULT_CONTEXT_MESSAGES), 1, 200)


def get_env_timeout_seconds() -> float:
    return _clamp_float(
        _get_float_env("OPENAI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        1.0,
        300.0,
    )


def get_env_max_retries() -> int:
    return _clamp_int(_get_int_env("OPENAI_MAX_RETRIES", DEFAULT_MAX_RETRIES), 0, 10)
