from typing import Any, Dict, List

from config import DEFAULT_SYSTEM_PROMPT


Message = Dict[str, str]


def init_session_state(state: Any) -> None:
    if "sessions" not in state:
        state["sessions"] = {
            "会话 1": [
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
            ]
        }

    if "active_session" not in state:
        state["active_session"] = "会话 1"

    if "system_prompt_input" not in state:
        state["system_prompt_input"] = DEFAULT_SYSTEM_PROMPT


def create_session(state: Any) -> None:
    index = 1
    while f"会话 {index}" in state["sessions"]:
        index += 1

    new_name = f"会话 {index}"
    state["sessions"][new_name] = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
    ]
    state["active_session"] = new_name
    state["system_prompt_input"] = DEFAULT_SYSTEM_PROMPT


def delete_active_session(state: Any) -> None:
    if len(state["sessions"]) <= 1:
        return

    del state["sessions"][state["active_session"]]
    state["active_session"] = list(state["sessions"].keys())[0]
    state["system_prompt_input"] = get_current_system_prompt(state)


def get_current_messages(state: Any) -> List[Message]:
    return state["sessions"][state["active_session"]]


def get_current_system_prompt(state: Any) -> str:
    messages = get_current_messages(state)
    if messages and messages[0].get("role") == "system":
        return messages[0].get("content", "")
    return DEFAULT_SYSTEM_PROMPT


def sync_system_prompt(messages: List[Message], system_prompt: str) -> None:
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = system_prompt


def visible_messages(messages: List[Message]) -> List[Message]:
    return [msg for msg in messages if msg.get("role") != "system"]
