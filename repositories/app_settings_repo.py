from db.connection import connect


def init_app_settings_db(
    database_url: str, error_cls: type[Exception], default_system_prompt: str
) -> None:
    with connect(database_url, error_cls) as connection:
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
                ("global_system_prompt", default_system_prompt),
            )


def get_setting_value(
    database_url: str,
    error_cls: type[Exception],
    key: str,
) -> str | None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT value
                FROM app_settings
                WHERE key = %s
                """,
                (key,),
            )
            row = cursor.fetchone()
    return (row or {}).get("value")


def upsert_setting_value(
    database_url: str,
    error_cls: type[Exception],
    key: str,
    value: str,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = NOW()
                """,
                (key, value),
            )
