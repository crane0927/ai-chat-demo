from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import DEFAULT_SYSTEM_PROMPT
from repositories import session_repo


Message = Dict[str, str]


class SessionStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatSession:
    id: int
    title: str
    system_prompt: str
    model_config_id: Optional[int]
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


def init_session_db(database_url: str) -> None:
    session_repo.init_session_db(database_url, SessionStorageError)


def _row_to_chat_session(row: Dict[str, Any]) -> ChatSession:
    return ChatSession(
        id=row["id"],
        title=row["title"],
        system_prompt=row["system_prompt"],
        model_config_id=row.get("model_config_id"),
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
    return session_repo.build_default_session_title(existing_titles)


def ensure_default_session(
    database_url: str,
    model_config_id: Optional[int],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> None:
    total = session_repo.count_sessions(database_url, SessionStorageError)
    if total:
        return

    # 首次启动至少准备一个会话，避免页面出现“无可选会话”的空洞状态。
    session_repo.create_default_session(
        database_url,
        SessionStorageError,
        "会话 1",
        system_prompt.strip() or DEFAULT_SYSTEM_PROMPT,
        model_config_id,
    )


def list_sessions(database_url: str) -> List[ChatSession]:
    rows = session_repo.list_session_rows(database_url, SessionStorageError)
    return [_row_to_chat_session(row) for row in rows]


def get_session(database_url: str, session_id: int) -> Optional[ChatSession]:
    row = session_repo.get_session_row(database_url, SessionStorageError, session_id)
    return _row_to_chat_session(row) if row else None


def create_session(
    database_url: str,
    title: Optional[str] = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    model_config_id: Optional[int] = None,
) -> int:
    try:
        resolved_title = (title or "").strip()
        if not resolved_title:
            existing_titles = session_repo.list_session_titles(
                database_url, SessionStorageError
            )
            resolved_title = _build_default_session_title(existing_titles)

        return session_repo.create_session(
            database_url,
            SessionStorageError,
            resolved_title,
            system_prompt.strip() or DEFAULT_SYSTEM_PROMPT,
            model_config_id,
        )
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("创建会话失败。") from exc


def rename_session(database_url: str, session_id: int, title: str) -> None:
    try:
        session_repo.rename_session(
            database_url,
            SessionStorageError,
            session_id,
            title.strip(),
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
        session_repo.update_session_system_prompt(
            database_url,
            SessionStorageError,
            session_id,
            system_prompt.strip() or DEFAULT_SYSTEM_PROMPT,
        )
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("保存系统提示词失败。") from exc


def update_session_model_config(
    database_url: str,
    session_id: int,
    model_config_id: Optional[int],
) -> None:
    try:
        session_repo.update_session_model_config(
            database_url,
            SessionStorageError,
            session_id,
            model_config_id,
        )
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("保存会话模型失败。") from exc


def ensure_session_model_config(
    database_url: str, fallback_model_config_id: int
) -> None:
    try:
        session_repo.ensure_session_model_config(
            database_url,
            SessionStorageError,
            fallback_model_config_id,
        )
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("初始化会话模型失败。") from exc


def delete_session(database_url: str, session_id: int) -> None:
    try:
        session_repo.delete_session(database_url, SessionStorageError, session_id)
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("删除会话失败。") from exc


def list_session_messages(database_url: str, session_id: int) -> List[ChatMessage]:
    rows = session_repo.list_session_message_rows(
        database_url, SessionStorageError, session_id
    )
    return [_row_to_chat_message(row) for row in rows]


def append_session_message(
    database_url: str,
    session_id: int,
    role: str,
    content: str,
    source: str = "",
) -> None:
    try:
        session_repo.append_session_message(
            database_url,
            SessionStorageError,
            session_id,
            role,
            content,
            source,
        )
    except SessionStorageError:
        raise
    except Exception as exc:
        raise SessionStorageError("保存聊天消息失败。") from exc


def build_model_messages(
    system_prompt: str,
    messages: List[ChatMessage],
    rag_context: str = "",
) -> List[Message]:
    prompt = system_prompt.strip() or DEFAULT_SYSTEM_PROMPT
    normalized_rag_context = rag_context.strip()
    if normalized_rag_context:
        # RAG 资料放进 system prompt，可以让模型把召回片段当作“回答约束”而不是普通对话，
        # 从而降低它把资料块误解为用户新问题、或在多轮里丢失参考边界的概率。
        prompt = f"{prompt}\n\n## 参考资料\n{normalized_rag_context}"
    # 没有命中时必须保持原始 prompt 不变，避免一次空检索把普通聊天行为偷偷改掉。
    model_messages: List[Message] = [{"role": "system", "content": prompt}]
    for message in messages:
        model_messages.append({"role": message.role, "content": message.content})
    return model_messages


def merge_answer_sources(base_source: str, rag_sources: str) -> str:
    normalized_base_source = base_source.strip()
    normalized_rag_sources = rag_sources.strip()
    if not normalized_rag_sources:
        return normalized_base_source

    # 回答来源最终会进入单行展示区，这里先把多行 RAG 来源压平，保证页面和历史消息里都可读。
    flattened_rag_sources = " / ".join(
        line.strip() for line in normalized_rag_sources.splitlines() if line.strip()
    )
    rag_label = f"参考资料：{flattened_rag_sources}"
    if not normalized_base_source:
        return rag_label
    return f"{normalized_base_source}；{rag_label}"


def visible_messages(messages: List[ChatMessage]) -> List[ChatMessage]:
    return [message for message in messages if message.role != "system"]
