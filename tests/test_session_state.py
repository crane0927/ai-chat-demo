from types import SimpleNamespace
import unittest

from state.session_state import (
    ensure_base_state,
    sync_prompt_selection_state,
    sync_system_prompt_state,
)


class SessionStateTestCase(unittest.TestCase):
    def test_ensure_base_state_applies_pending_active_session(self) -> None:
        state = {"pending_active_session_id": 2}
        sessions_by_id = {1: object(), 2: object()}

        ensure_base_state(
            state=state,
            sessions_by_id=sessions_by_id,
            prompt_templates_by_id={10: object()},
            global_system_prompt="默认提示词",
        )

        self.assertEqual(state["active_session_id"], 2)
        self.assertEqual(state["active_session_selector_id"], 2)
        self.assertEqual(state["selected_prompt_template_id"], 10)
        self.assertEqual(state["global_system_prompt_draft"], "默认提示词")

    def test_sync_prompt_selection_state_falls_back_to_first_template(self) -> None:
        state = {"selected_prompt_template_id": 99}

        sync_prompt_selection_state(state, {11: object(), 12: object()})

        self.assertEqual(state["selected_prompt_template_id"], 11)

    def test_sync_system_prompt_state_updates_for_session_switch(self) -> None:
        state = {"system_prompt_session_id": 1}
        current_session = SimpleNamespace(id=2, system_prompt="新的提示词")

        sync_system_prompt_state(
            state=state,
            current_session=current_session,
            current_preview_prompt=True,
            previous_preview_prompt=True,
            legacy_system_prompt_input="",
        )

        self.assertEqual(state["system_prompt_draft"], "新的提示词")
        self.assertEqual(state["system_prompt_session_id"], 2)
        self.assertEqual(state["system_prompt_editor_nonce"], 0)

    def test_sync_system_prompt_state_reads_editor_value_when_switching_to_preview(self) -> None:
        state = {
            "system_prompt_session_id": 3,
            "system_prompt_draft": "旧草稿",
            "system_prompt_editor_active_key": "editor-key",
            "editor-key": "编辑器中的值",
        }
        current_session = SimpleNamespace(id=3, system_prompt="数据库中的值")

        sync_system_prompt_state(
            state=state,
            current_session=current_session,
            current_preview_prompt=True,
            previous_preview_prompt=False,
            legacy_system_prompt_input="",
        )

        self.assertEqual(state["system_prompt_draft"], "编辑器中的值")
        self.assertTrue(state["previous_preview_prompt"])


if __name__ == "__main__":
    unittest.main()
