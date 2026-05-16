from typing import Optional

from db.connection import connect


def init_session_db(database_url: str, error_cls: type[Exception]) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            # 会话和消息拆表存储，便于后续做导出、排序和多用户扩展。
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    system_prompt TEXT NOT NULL DEFAULT '',
                    model_config_id BIGINT REFERENCES model_configs(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                ALTER TABLE chat_sessions
                ADD COLUMN IF NOT EXISTS model_config_id BIGINT REFERENCES model_configs(id) ON DELETE SET NULL
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id BIGSERIAL PRIMARY KEY,
                    session_id BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT '',
                    sort_order BIGINT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_order
                ON chat_messages (session_id, sort_order, id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at
                ON chat_sessions (updated_at DESC, id DESC)
                """
            )


def build_default_session_title(existing_titles: list[str]) -> str:
    index = 1
    title_set = {title.strip() for title in existing_titles}
    while f"会话 {index}" in title_set:
        index += 1
    return f"会话 {index}"


def count_sessions(database_url: str, error_cls: type[Exception]) -> int:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM chat_sessions")
            return int(cursor.fetchone()["total"])


def create_default_session(
    database_url: str,
    error_cls: type[Exception],
    title: str,
    system_prompt: str,
    model_config_id: Optional[int],
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (title, system_prompt, model_config_id)
                VALUES (%s, %s, %s)
                """,
                (title, system_prompt, model_config_id),
            )


def list_session_rows(database_url: str, error_cls: type[Exception]) -> list[dict]:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.system_prompt,
                    s.model_config_id,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id)::INTEGER AS message_count
                FROM chat_sessions AS s
                LEFT JOIN chat_messages AS m
                    ON m.session_id = s.id
                GROUP BY s.id
                ORDER BY s.updated_at DESC, s.id DESC
                """
            )
            return cursor.fetchall()


def get_session_row(
    database_url: str, error_cls: type[Exception], session_id: int
) -> dict | None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.system_prompt,
                    s.model_config_id,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id)::INTEGER AS message_count
                FROM chat_sessions AS s
                LEFT JOIN chat_messages AS m
                    ON m.session_id = s.id
                WHERE s.id = %s
                GROUP BY s.id
                """,
                (session_id,),
            )
            return cursor.fetchone()


def list_session_titles(database_url: str, error_cls: type[Exception]) -> list[str]:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT title FROM chat_sessions")
            return [row["title"] for row in cursor.fetchall()]


def create_session(
    database_url: str,
    error_cls: type[Exception],
    title: str,
    system_prompt: str,
    model_config_id: Optional[int],
) -> int:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (title, system_prompt, model_config_id)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (title, system_prompt, model_config_id),
            )
            return int(cursor.fetchone()["id"])


def rename_session(
    database_url: str,
    error_cls: type[Exception],
    session_id: int,
    title: str,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE chat_sessions
                SET title = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (title, session_id),
            )


def update_session_system_prompt(
    database_url: str,
    error_cls: type[Exception],
    session_id: int,
    system_prompt: str,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE chat_sessions
                SET system_prompt = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (system_prompt, session_id),
            )


def update_session_model_config(
    database_url: str,
    error_cls: type[Exception],
    session_id: int,
    model_config_id: Optional[int],
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE chat_sessions
                SET model_config_id = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (model_config_id, session_id),
            )


def ensure_session_model_config(
    database_url: str,
    error_cls: type[Exception],
    fallback_model_config_id: int,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            # 历史会话升级到按会话选模型后，缺省值统一回填到当前默认模型，避免出现“无模型可用”的空状态。
            cursor.execute(
                """
                UPDATE chat_sessions
                SET model_config_id = %s
                WHERE model_config_id IS NULL
                """,
                (fallback_model_config_id,),
            )


def delete_session(
    database_url: str,
    error_cls: type[Exception],
    session_id: int,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))


def list_session_message_rows(
    database_url: str,
    error_cls: type[Exception],
    session_id: int,
) -> list[dict]:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    session_id,
                    role,
                    content,
                    source,
                    sort_order,
                    created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (session_id,),
            )
            return cursor.fetchall()


def append_session_message(
    database_url: str,
    error_cls: type[Exception],
    session_id: int,
    role: str,
    content: str,
    source: str,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            # 用会话内递增顺序保证导出和上下文裁剪时的消息顺序稳定。
            cursor.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_sort_order
                FROM chat_messages
                WHERE session_id = %s
                """,
                (session_id,),
            )
            next_sort_order = cursor.fetchone()["next_sort_order"]
            cursor.execute(
                """
                INSERT INTO chat_messages (
                    session_id,
                    role,
                    content,
                    source,
                    sort_order
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (session_id, role, content, source, next_sort_order),
            )
            cursor.execute(
                """
                UPDATE chat_sessions
                SET updated_at = NOW()
                WHERE id = %s
                """,
                (session_id,),
            )
