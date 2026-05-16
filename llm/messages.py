from llm.types import Message


def clean_model_messages(history: list[Message]) -> list[Message]:
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if msg.get("role") in {"system", "user", "assistant"}
    ]


def trim_model_messages(
    history: list[Message],
    context_message_limit: int,
) -> list[Message]:
    cleaned_messages = clean_model_messages(history)
    if context_message_limit <= 0:
        return cleaned_messages

    system_messages = [msg for msg in cleaned_messages if msg["role"] == "system"]
    dialog_messages = [msg for msg in cleaned_messages if msg["role"] != "system"]

    # 系统提示词只保留第一条，避免重复注入；普通对话则按最近消息裁剪。
    trimmed_dialog = dialog_messages[-context_message_limit:]
    if system_messages:
        return [system_messages[0], *trimmed_dialog]
    return trimmed_dialog
