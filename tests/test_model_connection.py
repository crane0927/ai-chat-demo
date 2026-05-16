from unittest import mock
import unittest

from services.model_config import ModelConfigInput
from services.model_connection import (
    ModelConnectionTestError,
    test_model_connection,
)


def build_model_input(api_key: str) -> ModelConfigInput:
    return ModelConfigInput(
        name="OpenAI GPT-4.1",
        provider="OpenAI",
        api_key=api_key,
        base_url="https://api.openai.com/v1",
        model_name="gpt-4.1",
        temperature=0.7,
        max_tokens=2048,
        context_message_limit=20,
        timeout_seconds=60.0,
        max_retries=2,
        enabled=True,
    )


class ModelConnectionTestCase(unittest.TestCase):
    def test_test_model_connection_requires_api_key(self) -> None:
        with self.assertRaisesRegex(ModelConnectionTestError, "API Key"):
            test_model_connection(build_model_input(""))

    def test_test_model_connection_returns_success_message(self) -> None:
        fake_client = mock.Mock()
        fake_client.chat.completions.create.return_value = object()

        with mock.patch(
            "services.model_connection.OpenAI",
            return_value=fake_client,
        ):
            result = test_model_connection(build_model_input("sk-test"))

        self.assertIn("连接成功", result)
        fake_client.chat.completions.create.assert_called_once()

    def test_test_model_connection_formats_provider_error(self) -> None:
        fake_client = mock.Mock()
        fake_client.chat.completions.create.side_effect = RuntimeError("boom")

        with (
            mock.patch(
                "services.model_connection.OpenAI",
                return_value=fake_client,
            ),
            mock.patch(
                "services.model_connection.format_openai_error",
                return_value="连接失败：boom",
            ),
        ):
            with self.assertRaisesRegex(ModelConnectionTestError, "连接失败：boom"):
                test_model_connection(build_model_input("sk-test"))


if __name__ == "__main__":
    unittest.main()
