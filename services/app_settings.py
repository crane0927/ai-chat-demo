from typing import Any

from config import DEFAULT_SYSTEM_PROMPT


try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None


class AppSettingsStorageError(RuntimeError):
    pass


def _connect(database_url: str):
    if psycopg is None or dict_row is None:
        raise AppSettingsStorageError(
            "未安装 PostgreSQL 驱动，请先执行：pip install -r requirements.txt"
        )

    try:
        return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=3)
    except Exception as exc:
        raise AppSettingsStorageError(
            "无法连接 PostgreSQL，请检查 APP_DATABASE_URL 或 DATABASE_URL。"
        ) from exc


def init_app_settings_db(database_url: str) -> None:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            # 全局应用设置集中存表，便于后续继续扩展默认提示词、主题或其他站点级配置。
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
                """,
                ("global_system_prompt", DEFAULT_SYSTEM_PROMPT),
            )


def get_global_system_prompt(database_url: str) -> str:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT value
                FROM app_settings
                WHERE key = %s
                """,
                ("global_system_prompt",),
            )
            row = cursor.fetchone()
    return (row or {}).get("value", DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT


def update_global_system_prompt(database_url: str, system_prompt: str) -> None:
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    ("global_system_prompt", system_prompt.strip() or DEFAULT_SYSTEM_PROMPT),
                )
    except AppSettingsStorageError:
        raise
    except Exception as exc:
        raise AppSettingsStorageError("保存全局默认提示词失败。") from exc
