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
                "embedding_api_key": "emb-key",
                "embedding_base_url": "https://api.deepseek.com",
                "embedding_model_name": "text-embedding-3-small",
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
        self.assertEqual(result[0].embedding_api_key, "emb-key")
        self.assertEqual(result[0].embedding_base_url, "https://api.deepseek.com")
        self.assertEqual(result[0].embedding_model_name, "text-embedding-3-small")

    def test_create_model_config_passes_embedding_fields_to_repository(self) -> None:
        payloads: list[dict] = []
        config_input = model_config.ModelConfigInput(
            name="DeepSeek 默认",
            provider="DeepSeek",
            api_key="sk-test",
            base_url="https://api.deepseek.com",
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=2048,
            context_message_limit=20,
            timeout_seconds=60.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="emb-key",
            embedding_base_url="https://emb.example.com/v1",
            embedding_model_name="text-embedding-3-small",
        )

        with mock.patch.object(
            model_config,
            "execute_write",
            side_effect=lambda operation, **_: operation(),
        ), mock.patch.object(
            model_config,
            "_encrypt_api_key_for_storage",
            side_effect=lambda value: f"encrypted::{value}",
        ), mock.patch.object(
            model_config.model_config_repo,
            "create_model_config",
            side_effect=lambda _database_url, _error_cls, payload: payloads.append(
                payload
            )
            or 99,
        ):
            result = model_config.create_model_config("postgresql://demo", config_input)

        self.assertEqual(result, 99)
        self.assertEqual(payloads[0]["embedding_api_key"], "encrypted::emb-key")
        self.assertEqual(
            payloads[0]["embedding_base_url"], "https://emb.example.com/v1"
        )
        self.assertEqual(
            payloads[0]["embedding_model_name"], "text-embedding-3-small"
        )

    def test_get_model_config_maps_embedding_fields(self) -> None:
        row = {
            "id": 9,
            "name": "OpenAI",
            "provider": "OpenAI",
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4.1",
            "temperature": 0.2,
            "max_tokens": 4096,
            "context_message_limit": 16,
            "timeout_seconds": 30.0,
            "max_retries": 1,
            "enabled": True,
            "embedding_api_key": "emb-key",
            "embedding_base_url": "https://emb.example.com/v1",
            "embedding_model_name": "text-embedding-3-small",
        }

        with mock.patch.object(
            model_config.model_config_repo,
            "get_model_config_row",
            return_value=row,
        ):
            result = model_config.get_model_config("postgresql://demo", 9)

        self.assertIsNotNone(result)
        self.assertEqual(result.embedding_api_key, "emb-key")
        self.assertEqual(result.embedding_base_url, "https://emb.example.com/v1")
        self.assertEqual(result.embedding_model_name, "text-embedding-3-small")

    def test_ensure_default_model_config_passes_empty_embedding_defaults(self) -> None:
        payloads: list[dict] = []

        with mock.patch.object(
            model_config,
            "execute_write",
            side_effect=lambda operation, **_: operation(),
        ), mock.patch.object(
            model_config.model_config_repo,
            "count_model_configs",
            return_value=0,
        ), mock.patch.object(
            model_config.model_config_repo,
            "insert_default_model_config",
            side_effect=lambda _database_url, _error_cls, payload: payloads.append(
                payload
            ),
        ):
            model_config.ensure_default_model_config("postgresql://demo")

        self.assertEqual(payloads[0]["embedding_api_key"], "")
        self.assertEqual(payloads[0]["embedding_base_url"], "")
        self.assertEqual(payloads[0]["embedding_model_name"], "")

    def test_get_model_config_tolerates_missing_embedding_fields_in_legacy_row(self) -> None:
        row = {
            "id": 10,
            "name": "Legacy",
            "provider": "DeepSeek",
            "api_key": "",
            "base_url": "https://api.deepseek.com",
            "model_name": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 2048,
            "context_message_limit": 20,
            "timeout_seconds": 60.0,
            "max_retries": 2,
            "enabled": True,
        }

        with mock.patch.object(
            model_config.model_config_repo,
            "get_model_config_row",
            return_value=row,
        ):
            result = model_config.get_model_config("postgresql://demo", 10)

        self.assertIsNotNone(result)
        self.assertEqual(result.embedding_api_key, "")
        self.assertEqual(result.embedding_base_url, "")
        self.assertEqual(result.embedding_model_name, "")

    def test_update_model_config_passes_embedding_fields_to_repository(self) -> None:
        payloads: list[dict] = []
        config_input = model_config.ModelConfigInput(
            name="DeepSeek 默认",
            provider="DeepSeek",
            api_key="sk-test",
            base_url="https://api.deepseek.com",
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=2048,
            context_message_limit=20,
            timeout_seconds=60.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="emb-key",
            embedding_base_url="https://emb.example.com/v1",
            embedding_model_name="text-embedding-3-small",
        )

        with mock.patch.object(
            model_config,
            "execute_write",
            side_effect=lambda operation, **_: operation(),
        ), mock.patch.object(
            model_config,
            "_encrypt_api_key_for_storage",
            side_effect=lambda value: f"encrypted::{value}",
        ), mock.patch.object(
            model_config.model_config_repo,
            "update_model_config",
            side_effect=lambda _database_url, _error_cls, _config_id, payload: payloads.append(
                payload
            ),
        ):
            model_config.update_model_config(
                "postgresql://demo",
                99,
                config_input,
            )

        self.assertEqual(payloads[0]["embedding_api_key"], "encrypted::emb-key")
        self.assertEqual(
            payloads[0]["embedding_base_url"], "https://emb.example.com/v1"
        )
        self.assertEqual(
            payloads[0]["embedding_model_name"], "text-embedding-3-small"
        )

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
