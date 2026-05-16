import os
from unittest import mock
import unittest

from services import model_config
from services.model_config import ModelConfigInput
from services.secret_crypto import decrypt_string


def build_model_input(api_key: str) -> ModelConfigInput:
    return ModelConfigInput(
        name="DeepSeek 默认",
        provider="DeepSeek",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        model_name="deepseek-chat",
        temperature=0.7,
        max_tokens=2048,
        context_message_limit=20,
        timeout_seconds=60.0,
        max_retries=2,
        enabled=True,
    )


class ModelConfigSecurityTestCase(unittest.TestCase):
    def test_create_model_config_requires_app_secret_key_for_non_empty_api_key(
        self,
    ) -> None:
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(model_config.model_config_repo, "create_model_config"),
        ):
            with self.assertRaisesRegex(
                model_config.ModelConfigStorageError,
                "APP_SECRET_KEY",
            ):
                model_config.create_model_config(
                    "postgresql://demo",
                    build_model_input("sk-test"),
                )

    def test_create_model_config_encrypts_api_key_before_write(self) -> None:
        captured_payload = {}

        def fake_create_model_config(_database_url, _error_cls, payload):
            captured_payload.update(payload)
            return 7

        with (
            mock.patch.dict(os.environ, {"APP_SECRET_KEY": "secret-key"}, clear=True),
            mock.patch.object(
                model_config.model_config_repo,
                "create_model_config",
                side_effect=fake_create_model_config,
            ),
        ):
            model_config.create_model_config(
                "postgresql://demo",
                build_model_input("sk-test"),
            )

        self.assertNotEqual(captured_payload["api_key"], "sk-test")
        self.assertEqual(
            decrypt_string(captured_payload["api_key"], "secret-key"),
            "sk-test",
        )

    def test_list_model_configs_decrypts_encrypted_api_key(self) -> None:
        encrypted_api_key = model_config.encrypt_api_key("sk-test", "secret-key")
        rows = [
            {
                "id": 1,
                "name": "DeepSeek 默认",
                "provider": "DeepSeek",
                "api_key": encrypted_api_key,
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

        with (
            mock.patch.dict(os.environ, {"APP_SECRET_KEY": "secret-key"}, clear=True),
            mock.patch.object(
                model_config.model_config_repo,
                "list_model_config_rows",
                return_value=rows,
            ),
        ):
            result = model_config.list_model_configs("postgresql://demo")

        self.assertEqual(result[0].api_key, "sk-test")

    def test_list_model_configs_keeps_legacy_plaintext_api_key(self) -> None:
        rows = [
            {
                "id": 1,
                "name": "DeepSeek 默认",
                "provider": "DeepSeek",
                "api_key": "sk-legacy",
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

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(
                model_config.model_config_repo,
                "list_model_config_rows",
                return_value=rows,
            ),
        ):
            result = model_config.list_model_configs("postgresql://demo")

        self.assertEqual(result[0].api_key, "sk-legacy")


if __name__ == "__main__":
    unittest.main()
