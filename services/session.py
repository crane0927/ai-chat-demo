from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import DEFAULT_SYSTEM_PROMPT


try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None


Message = Dict[str, str]


class SessionStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatSession:
    id: int
    title: str
    system_prompt: str
    created_at: datetime
    updated_at: datetime
    message_count: int


@dataclass(frozen=True)
class ChatMessage:
    id: int
    session_id: int
    role: str
    content: str
    source: str
    sort_order: int
    created_at: datetime


def _connect(database_url: str):
    if psycopg is None or dict_row is None:
        raise SessionStorageError(
            "未安装 PostgreSQL 驱动，请先执行：pip install -r requirements.txt"
        )

    try:
        return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=3)
    except Exception as exc:
        raise SessionStorageError(
            "无法连接 PostgreSQL，请检查 APP_DATABASE_URL 或 DATABASE_URL。"
        ) from exc


def init_session_db(database_url: str) -> None:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            # 会话和消息拆表存储，便于后续做导出、排序和多用户扩展。
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    system_prompt TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
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


def _row_to_chat_session(row: Dict[str, Any]) -> ChatSession:
    return ChatSession(
        id=row["id"],
        title=row["title"],
        system_prompt=row["system_prompt"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        message_count=row["message_count"],
    )


def _row_to_chat_message(row: Dict[str, Any]) -> ChatMessage:
    return ChatMessage(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        source=row["source"],
        sort_order=row["sort_order"],
        created_at=row["created_at"],
    )


def _build_default_session_title(existing_titles: List[str]) -> str:
    index = 1
    title_set = {title.strip() for title in existing_titles}
    while f"会话 {index}" in title_set:
        index += 1
    return f"会话 {index}"


def ensure_default_session(database_url: str) -> None:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM chat_sessions")
            total = cursor.fetchone()["total"]
            if total:
                return

            # 首次启动至少准备一个会话，避免页面出现“无可选会话”的空洞状态。
            cursor.execute(
                """
                INSERT INTO chat_sessions (title, system_prompt)
                VALUES (%s, %s)
                """,
                ("会话 1", DEFAULT_SYSTEM_PROMPT),
            )


def list_sessions(database_url: str) -> List[ChatSession]:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.system_prompt,
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
            rows = cursor.fetchall()
    return [_row_to_chat_session(row) for row in rows]


def get_session(database_url: str, session_id: int) -> Optional[ChatSession]:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.system_prompt,
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
            row = cursor.fetchone()
    return _row_to_chat_session(row) if row else None


def create_session(
    database_url: str,
    title: Optional[str] = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> int:
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                resolved_title = (title or "").strip()
                if not resolved_title:
                    cursor.execute("SELECT title FROM chat_sessions")
                    existing_titles = [row["title"] for row in cursor.fetchall()]
                    resolved_title = _build_default_session_title(existing_titles)

                cursor.execute(
                    """
                    INSERT INTO chat_sessions (title, system_prompt)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (resolved_title, system_prompt.strip() or DEFAULT_SYSTEM_PROMPT),
                )
                return cursor.fetchone()["id"]
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("创建会话失败。") from exc


def rename_session(database_url: str, session_id: int, title: str) -> None:
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET title = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (title.strip(), session_id),
                )
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("重命名会话失败。") from exc


def update_session_system_prompt(
    database_url: str,
    session_id: int,
    system_prompt: str,
) -> None:
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET system_prompt = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (system_prompt.strip() or DEFAULT_SYSTEM_PROMPT, session_id),
                )
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("保存系统提示词失败。") from exc


def delete_session(database_url: str, session_id: int) -> None:
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("删除会话失败。") from exc


def list_session_messages(database_url: str, session_id: int) -> List[ChatMessage]:
    with _connect(database_url) as connection:
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
            rows = cursor.fetchall()
    return [_row_to_chat_message(row) for row in rows]


def append_session_message(
    database_url: str,
    session_id: int,
    role: str,
    content: str,
    source: str = "",
) -> None:
    try:
        with _connect(database_url) as connection:
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
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("保存聊天消息失败。") from exc


def build_model_messages(system_prompt: str, messages: List[ChatMessage]) -> List[Message]:
    model_messages: List[Message] = [
        {"role": "system", "content": system_prompt.strip() or DEFAULT_SYSTEM_PROMPT}
    ]
    for message in messages:
        model_messages.append({"role": message.role, "content": message.content})
    return model_messages


def visible_messages(messages: List[ChatMessage]) -> List[ChatMessage]:
    return [message for message in messages if message.role != "system"]
