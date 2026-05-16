import unittest

from services.model_config import ModelConfigInput
from services.prompt_template import PromptTemplate, PromptTemplateInput
from utils.view_helpers import (
    build_model_config_input,
    build_prompt_template_input,
    build_template_copy_name,
    model_config_label,
    prompt_template_label,
)


class ViewHelpersTestCase(unittest.TestCase):
    def test_model_config_label_marks_disabled_config(self) -> None:
        config = ModelConfigInput(
            name="DeepSeek",
            provider="DeepSeek",
            api_key="",
            base_url="https://api.deepseek.com",
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=2048,
            context_message_limit=20,
            timeout_seconds=60.0,
            max_retries=2,
            enabled=False,
        )

        self.assertEqual(model_config_label(config), "DeepSeek（已停用）")

    def test_prompt_template_label_marks_builtin_template(self) -> None:
        template = PromptTemplate(
            id=1,
            name="写作助手",
            description="desc",
            content="content",
            builtin=True,
        )

        self.assertEqual(prompt_template_label(template), "写作助手（内置）")

    def test_build_template_copy_name_avoids_collisions(self) -> None:
        templates = [
            PromptTemplate(id=1, name="模板", description="", content="", builtin=False),
            PromptTemplate(id=2, name="模板 副本", description="", content="", builtin=False),
            PromptTemplate(id=3, name="模板 副本 2", description="", content="", builtin=False),
        ]

        self.assertEqual(build_template_copy_name(templates, "模板"), "模板 副本 3")

    def test_build_model_config_input_normalizes_numeric_values(self) -> None:
        result = build_model_config_input(
            "OpenAI",
            "OpenAI",
            "sk-test",
            "https://api.openai.com/v1",
            "gpt-4.1",
            0.3,
            1024,
            12,
            45,
            1,
            True,
        )

        self.assertIsInstance(result, ModelConfigInput)
        self.assertEqual(result.max_tokens, 1024)
        self.assertEqual(result.timeout_seconds, 45.0)

    def test_build_prompt_template_input_marks_custom_template(self) -> None:
        result = build_prompt_template_input("复盘助手", "帮助复盘", "请复盘 {{主题}}")

        self.assertIsInstance(result, PromptTemplateInput)
        self.assertFalse(result.builtin)


if __name__ == "__main__":
    unittest.main()
