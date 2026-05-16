from db.connection import connect


def init_model_config_db(database_url: str, error_cls: type[Exception]) -> None:
    with connect(database_url, error_cls) as connection:
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


def count_model_configs(database_url: str, error_cls: type[Exception]) -> int:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM model_configs")
            return int(cursor.fetchone()["total"])


def insert_default_model_config(
    database_url: str,
    error_cls: type[Exception],
    payload: dict,
) -> None:
    with connect(database_url, error_cls) as connection:
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
                ON CONFLICT (name) DO NOTHING
                """,
                (
                    payload["name"],
                    payload["provider"],
                    payload["api_key"],
                    payload["base_url"],
                    payload["model_name"],
                    payload["temperature"],
                    payload["max_tokens"],
                    payload["context_message_limit"],
                    payload["timeout_seconds"],
                    payload["max_retries"],
                    payload["enabled"],
                ),
            )


def list_model_config_rows(database_url: str, error_cls: type[Exception]) -> list[dict]:
    with connect(database_url, error_cls) as connection:
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
            return cursor.fetchall()


def get_model_config_row(
    database_url: str,
    error_cls: type[Exception],
    config_id: int,
) -> dict | None:
    with connect(database_url, error_cls) as connection:
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
            return cursor.fetchone()


def create_model_config(
    database_url: str,
    error_cls: type[Exception],
    payload: dict,
) -> int:
    with connect(database_url, error_cls) as connection:
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
                    payload["name"],
                    payload["provider"],
                    payload["api_key"],
                    payload["base_url"],
                    payload["model_name"],
                    payload["temperature"],
                    payload["max_tokens"],
                    payload["context_message_limit"],
                    payload["timeout_seconds"],
                    payload["max_retries"],
                    payload["enabled"],
                ),
            )
            return int(cursor.fetchone()["id"])


def update_model_config(
    database_url: str,
    error_cls: type[Exception],
    config_id: int,
    payload: dict,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
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
                    payload["name"],
                    payload["provider"],
                    payload["api_key"],
                    payload["base_url"],
                    payload["model_name"],
                    payload["temperature"],
                    payload["max_tokens"],
                    payload["context_message_limit"],
                    payload["timeout_seconds"],
                    payload["max_retries"],
                    payload["enabled"],
                    config_id,
                ),
            )


def delete_model_config(
    database_url: str,
    error_cls: type[Exception],
    config_id: int,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM model_configs WHERE id = %s", (config_id,))
