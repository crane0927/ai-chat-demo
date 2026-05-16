from collections.abc import Mapping, MutableMapping
from typing import Any


def ensure_base_state(
    state: MutableMapping[str, Any],
    sessions_by_id: Mapping[int, Any],
    prompt_templates_by_id: Mapping[int, Any],
    global_system_prompt: str,
) -> None:
    if "active_session_id" not in state or state["active_session_id"] not in sessions_by_id:
        # 会话删除或首次访问时，默认指向最近更新的一条会话。
        state["active_session_id"] = next(iter(sessions_by_id), None)

    if "system_prompt_session_id" not in state:
        state["system_prompt_session_id"] = state["active_session_id"]

    if "rename_session_confirming_id" not in state:
        state["rename_session_confirming_id"] = None

    pending_active_session_id = state.pop("pending_active_session_id", None)
    if pending_active_session_id in sessions_by_id:
        state["active_session_id"] = pending_active_session_id
        # 会话切换发生在下拉框实例化前时，需要同步选中项，避免旧控件状态反向覆盖。
        state["active_session_selector_id"] = pending_active_session_id

    if (
        "active_session_selector_id" not in state
        or state["active_session_selector_id"] not in sessions_by_id
    ):
        state["active_session_selector_id"] = state["active_session_id"]
    elif state["active_session_selector_id"] != state["active_session_id"]:
        state["active_session_id"] = state["active_session_selector_id"]

    if "delete_model_config_confirming_id" not in state:
        state["delete_model_config_confirming_id"] = None

    if prompt_templates_by_id and "selected_prompt_template_id" not in state:
        state["selected_prompt_template_id"] = next(iter(prompt_templates_by_id))

    if "create_session_confirming" not in state:
        state["create_session_confirming"] = False

    if "global_system_prompt_draft" not in state:
        state["global_system_prompt_draft"] = global_system_prompt


def sync_prompt_selection_state(
    state: MutableMapping[str, Any],
    prompt_templates_by_id: Mapping[int, Any],
) -> None:
    if prompt_templates_by_id and state.get("selected_prompt_template_id") not in prompt_templates_by_id:
        state["selected_prompt_template_id"] = next(iter(prompt_templates_by_id))


def sync_system_prompt_state(
    state: MutableMapping[str, Any],
    current_session: Any,
    current_preview_prompt: bool,
    previous_preview_prompt: bool,
    legacy_system_prompt_input: str,
) -> None:
    if state["system_prompt_session_id"] != current_session.id:
        # 切换会话时要切换提示词草稿，避免上一会话内容覆盖当前会话。
        state["system_prompt_draft"] = current_session.system_prompt
        state["system_prompt_session_id"] = current_session.id
        state["system_prompt_editor_nonce"] = 0
    else:
        if "system_prompt_draft" not in state:
            state["system_prompt_draft"] = legacy_system_prompt_input or current_session.system_prompt
        if not current_preview_prompt and previous_preview_prompt:
            # 从预览切回编辑时刷新编辑器 key，强制文本框以当前草稿重新初始化。
            state["system_prompt_editor_nonce"] = state.get("system_prompt_editor_nonce", 0) + 1
        elif current_preview_prompt and not previous_preview_prompt:
            active_editor_key = state.get("system_prompt_editor_active_key")
            if active_editor_key and active_editor_key in state:
                state["system_prompt_draft"] = state[active_editor_key]
        if current_preview_prompt and not state["system_prompt_draft"] and current_session.system_prompt:
            state["system_prompt_draft"] = current_session.system_prompt

    state["previous_preview_prompt"] = current_preview_prompt
