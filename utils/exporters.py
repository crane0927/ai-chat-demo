import json
import re

from services.session import ChatMessage, ChatSession


def build_session_markdown(session: ChatSession, messages: list[ChatMessage]) -> str:
    lines = [
        f"# {session.title}",
        "",
        f"- 会话 ID：{session.id}",
        f"- 创建时间：{session.created_at.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- 更新时间：{session.updated_at.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        "## 系统提示词",
        "",
        session.system_prompt.strip() or "（空）",
        "",
        "## 对话记录",
        "",
    ]

    for message in messages:
        role_label = "用户" if message.role == "user" else "助手"
        lines.append(f"### {role_label}")
        lines.append("")
        lines.append(message.content)
        if message.source:
            lines.append("")
            lines.append(f"> 回答来源：{message.source}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_session_json(session: ChatSession, messages: list[ChatMessage]) -> str:
    export_payload = {
        "session": {
            "id": session.id,
            "title": session.title,
            "system_prompt": session.system_prompt,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": session.message_count,
        },
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "source": message.source,
                "sort_order": message.sort_order,
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ],
    }
    return json.dumps(export_payload, ensure_ascii=False, indent=2)


def build_session_export_filename(session: ChatSession, suffix: str) -> str:
    # 下载文件名只保留常见安全字符，避免不同系统下出现路径或编码问题。
    safe_title = re.sub(
        r"[^\w\u4e00-\u9fff-]+", "-", session.title.strip(), flags=re.UNICODE
    )
    safe_title = safe_title.strip("-_") or f"session-{session.id}"
    return f"{safe_title}.{suffix}"
