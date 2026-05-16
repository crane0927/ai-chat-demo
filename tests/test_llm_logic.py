from types import SimpleNamespace
from unittest import mock
import unittest

from services import llm


class LlmLogicTestCase(unittest.TestCase):
    def test_clean_model_messages_filters_unknown_roles(self) -> None:
        history = [
            {"role": "system", "content": "s"},
            {"role": "tool", "content": "x"},
            {"role": "user", "content": "u"},
        ]

        result = llm.clean_model_messages(history)

        self.assertEqual(
            result,
            [
                {"role": "system", "content": "s"},
                {"role": "user", "content": "u"},
            ],
        )

    def test_trim_model_messages_keeps_first_system_and_recent_dialog(self) -> None:
        history = [
            {"role": "system", "content": "s1"},
            {"role": "system", "content": "s2"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]

        result = llm.trim_model_messages(history, 2)

        self.assertEqual(
            result,
            [
                {"role": "system", "content": "s1"},
                {"role": "assistant", "content": "a1"},
                {"role": "user", "content": "u2"},
            ],
        )

    def test_get_answer_source_returns_local_when_disabled(self) -> None:
        self.assertEqual(llm.get_answer_source(False, "sk", "gpt-4.1"), "本地回显")

    def test_get_answer_source_returns_model_label_when_enabled(self) -> None:
        with mock.patch.object(llm, "OpenAI", object()):
            self.assertEqual(
                llm.get_answer_source(True, "sk-test", "gpt-4.1"),
                "模型接口 · gpt-4.1",
            )

    def test_local_fallback_response_has_greeting_variant(self) -> None:
        result = llm.local_fallback_response("你好，介绍一下自己")

        self.assertIn("你好呀", result)

    def test_format_openai_error_prefers_specific_message(self) -> None:
        fake_auth_error = type("FakeAuthError", (Exception,), {})
        with mock.patch.multiple(
            llm,
            AuthenticationError=fake_auth_error,
            PermissionDeniedError=None,
            RateLimitError=None,
            APITimeoutError=None,
            APIConnectionError=None,
            NotFoundError=None,
            BadRequestError=None,
            APIError=None,
        ):
            result = llm.format_openai_error(fake_auth_error("bad"))

        self.assertIn("鉴权失败", result)

    def test_openai_stream_response_returns_missing_key_message(self) -> None:
        options = llm.ModelRequestOptions(
            max_tokens=100,
            context_message_limit=10,
            timeout_seconds=30.0,
            max_retries=1,
        )
        with mock.patch.object(llm, "OpenAI", object()), mock.patch.dict("os.environ", {}, clear=True):
            result = list(
                llm.openai_stream_response(
                    history=[{"role": "user", "content": "hi"}],
                    temp=0.7,
                    api_key="",
                    model="gpt-4.1",
                    base_url=None,
                    options=options,
                )
            )

        self.assertEqual(result, ["未检测到 OPENAI_API_KEY，已切换为本地回显模式。"])


if __name__ == "__main__":
    unittest.main()
