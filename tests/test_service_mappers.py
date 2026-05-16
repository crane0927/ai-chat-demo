from datetime import datetime, timezone
from unittest import mock
import unittest

from services import model_config, prompt_template, session


class ServiceMapperTestCase(unittest.TestCase):
    def test_list_model_configs_maps_rows_to_dataclasses(self) -> None:
        rows = [
            {
                "id": 1,
                "name": "DeepSeek 默认",
                "provider": "DeepSeek",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "model_name": "deepseek-chat",
                "temperature": 0.7,
                "max_tokens": 2048,
                "context_message_limit": 20,
                "timeout_seconds": 60.0,
                "max_retries": 2,
                "enabled": True,
            }
        ]

        with mock.patch.object(
            model_config.model_config_repo,
            "list_model_config_rows",
            return_value=rows,
        ):
            result = model_config.list_model_configs("postgresql://demo")

        self.assertEqual(result[0].name, "DeepSeek 默认")
        self.assertTrue(result[0].enabled)

    def test_list_prompt_templates_maps_rows_to_dataclasses(self) -> None:
        rows = [
            {
                "id": 2,
                "name": "写作助手",
                "description": "desc",
                "content": "content",
                "builtin": True,
            }
        ]

        with mock.patch.object(
            prompt_template.prompt_template_repo,
            "list_prompt_template_rows",
            return_value=rows,
        ):
            result = prompt_template.list_prompt_templates("postgresql://demo")

        self.assertEqual(result[0].name, "写作助手")
        self.assertTrue(result[0].builtin)

    def test_list_session_messages_maps_rows_to_dataclasses(self) -> None:
        rows = [
            {
                "id": 3,
                "session_id": 1,
                "role": "assistant",
                "content": "你好",
                "source": "本地回显",
                "sort_order": 2,
                "created_at": datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
            }
        ]

        with mock.patch.object(
            session.session_repo,
            "list_session_message_rows",
            return_value=rows,
        ):
            result = session.list_session_messages("postgresql://demo", 1)

        self.assertEqual(result[0].content, "你好")
        self.assertEqual(result[0].source, "本地回显")


if __name__ == "__main__":
    unittest.main()
