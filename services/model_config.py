from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import (
    get_env_base_url,
    get_env_chat_model,
    get_env_context_messages,
    get_env_max_retries,
    get_env_max_tokens,
    get_env_timeout_seconds,
)


try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None


class ModelConfigStorageError(RuntimeError):
    pass


class DuplicateModelConfigName(ModelConfigStorageError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    id: int
    name: str
    provider: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float
    max_tokens: int
    context_message_limit: int
    timeout_seconds: float
    max_retries: int
    enabled: bool


@dataclass(frozen=True)
class ModelConfigInput:
    name: str
    provider: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float
    max_tokens: int
    context_message_limit: int
    timeout_seconds: float
    max_retries: int
    enabled: bool = True


def _connect(database_url: str):
    if psycopg is None or dict_row is None:
        raise ModelConfigStorageError(
            "未安装 PostgreSQL 驱动，请先执行：pip install -r requirements.txt"
        )

    try:
        return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=3)
    except Exception as exc:
        raise ModelConfigStorageError(
            "无法连接 PostgreSQL，请检查 APP_DATABASE_URL 或 DATABASE_URL。"
        ) from exc


def _execute_write(operation) -> Any:
    try:
        return operation()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise DuplicateModelConfigName("配置名称已存在，请换一个名称。") from exc
        if isinstance(exc, ModelConfigStorageError):
            raise
        raise ModelConfigStorageError("模型配置写入 PostgreSQL 失败。") from exc


def _is_unique_violation(exc: Exception) -> bool:
    if psycopg is None:
        return False
    return isinstance(exc, psycopg.errors.UniqueViolation)


def init_model_config_db(database_url: str) -> None:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            # PostgreSQL 负责保存模型配置；API Key 当前仍为 Demo 级明文存储，正式部署应改为加密或密钥管理服务。
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS model_configs (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    provider TEXT NOT NULL DEFAULT '',
                    api_key TEXT NOT NULL DEFAULT '',
                    base_url TEXT NOT NULL DEFAULT '',
                    model_name TEXT NOT NULL,
                    temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,
                    max_tokens INTEGER NOT NULL,
                    context_message_limit INTEGER NOT NULL,
                    timeout_seconds DOUBLE PRECISION NOT NULL,
                    max_retries INTEGER NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


def _row_to_model_config(row: Dict[str, Any]) -> ModelConfig:
    return ModelConfig(
        id=row["id"],
        name=row["name"],
        provider=row["provider"],
        api_key=row["api_key"],
        base_url=row["base_url"],
        model_name=row["model_name"],
        temperature=row["temperature"],
        max_tokens=row["max_tokens"],
        context_message_limit=row["context_message_limit"],
        timeout_seconds=row["timeout_seconds"],
        max_retries=row["max_retries"],
        enabled=bool(row["enabled"]),
    )


def ensure_default_model_config(database_url: str, api_key: str = "") -> None:
    def operation() -> None:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM model_configs")
                count = cursor.fetchone()["total"]
                if count:
                    return

                # 首次启动时把现有环境变量默认值落库，避免升级后用户还需要手动创建第一条配置。
                cursor.execute(
                    """
                    INSERT INTO model_configs (
                        name,
                        provider,
                        api_key,
                        base_url,
                        model_name,
                        temperature,
                        max_tokens,
                        context_message_limit,
                        timeout_seconds,
                        max_retries,
                        enabled
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (
                        "DeepSeek 默认",
                        "DeepSeek",
                        api_key.strip(),
                        get_env_base_url(),
                        get_env_chat_model(),
                        0.7,
                        get_env_max_tokens(),
                        get_env_context_messages(),
                        get_env_timeout_seconds(),
                        get_env_max_retries(),
                        True,
                    ),
                )

    _execute_write(operation)


def list_model_configs(database_url: str) -> List[ModelConfig]:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    provider,
                    api_key,
                    base_url,
                    model_name,
                    temperature,
                    max_tokens,
                    context_message_limit,
                    timeout_seconds,
                    max_retries,
                    enabled
                FROM model_configs
                ORDER BY lower(name) ASC, id ASC
                """
            )
            rows = cursor.fetchall()
    return [_row_to_model_config(row) for row in rows]


def get_model_config(database_url: str, config_id: int) -> Optional[ModelConfig]:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    provider,
                    api_key,
                    base_url,
                    model_name,
                    temperature,
                    max_tokens,
                    context_message_limit,
                    timeout_seconds,
                    max_retries,
                    enabled
                FROM model_configs
                WHERE id = %s
                """,
                (config_id,),
            )
            row = cursor.fetchone()
    return _row_to_model_config(row) if row else None


def create_model_config(database_url: str, config: ModelConfigInput) -> int:
    def operation() -> int:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO model_configs (
                        name,
                        provider,
                        api_key,
                        base_url,
                        model_name,
                        temperature,
                        max_tokens,
                        context_message_limit,
                        timeout_seconds,
                        max_retries,
                        enabled
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        config.name.strip(),
                        config.provider.strip(),
                        config.api_key.strip(),
                        config.base_url.strip(),
                        config.model_name.strip(),
                        config.temperature,
                        config.max_tokens,
                        config.context_message_limit,
                        config.timeout_seconds,
                        config.max_retries,
                        config.enabled,
                    ),
                )
                # PostgreSQL 使用 RETURNING 获取新主键，避免依赖不同驱动的 lastrowid 行为。
                return int(cursor.fetchone()["id"])

    return _execute_write(operation)


def update_model_config(database_url: str, config_id: int, config: ModelConfigInput) -> None:
    def operation() -> None:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                # 更新时间由数据库统一写入，便于以后做配置变更审计或按最近修改排序。
                cursor.execute(
                    """
                    UPDATE model_configs
                    SET
                        name = %s,
                        provider = %s,
                        api_key = %s,
                        base_url = %s,
                        model_name = %s,
                        temperature = %s,
                        max_tokens = %s,
                        context_message_limit = %s,
                        timeout_seconds = %s,
                        max_retries = %s,
                        enabled = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        config.name.strip(),
                        config.provider.strip(),
                        config.api_key.strip(),
                        config.base_url.strip(),
                        config.model_name.strip(),
                        config.temperature,
                        config.max_tokens,
                        config.context_message_limit,
                        config.timeout_seconds,
                        config.max_retries,
                        config.enabled,
                        config_id,
                    ),
                )

    _execute_write(operation)


def delete_model_config(database_url: str, config_id: int) -> None:
    def operation() -> None:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM model_configs WHERE id = %s", (config_id,))

    _execute_write(operation)
