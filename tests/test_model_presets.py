import unittest

from services.model_presets import (
    get_model_preset,
    resolve_model_identity,
)


class ModelPresetsTestCase(unittest.TestCase):
    def test_get_model_preset_returns_expected_provider(self) -> None:
        preset = get_model_preset("deepseek")

        self.assertIsNotNone(preset)
        self.assertEqual(preset.provider, "DeepSeek")

    def test_resolve_model_identity_uses_preset_defaults_when_fields_blank(
        self,
    ) -> None:
        result = resolve_model_identity(
            preset_key="openai",
            provider="",
            base_url="",
            model_name="",
        )

        self.assertEqual(
            result,
            ("OpenAI", "https://api.openai.com/v1", "gpt-4.1"),
        )

    def test_resolve_model_identity_keeps_manual_override(self) -> None:
        result = resolve_model_identity(
            preset_key="deepseek",
            provider="自定义服务商",
            base_url="https://proxy.example.com/v1",
            model_name="custom-model",
        )

        self.assertEqual(
            result,
            ("自定义服务商", "https://proxy.example.com/v1", "custom-model"),
        )


if __name__ == "__main__":
    unittest.main()
