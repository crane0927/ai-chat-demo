from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPreset:
    key: str
    label: str
    provider: str
    base_url: str
    model_name: str


MODEL_PRESETS = {
    "custom": ModelPreset(
        key="custom",
        label="手动填写",
        provider="",
        base_url="",
        model_name="",
    ),
    "deepseek": ModelPreset(
        key="deepseek",
        label="DeepSeek 兼容接口",
        provider="DeepSeek",
        base_url="https://api.deepseek.com",
        model_name="deepseek-chat",
    ),
    "openai": ModelPreset(
        key="openai",
        label="OpenAI 官方接口",
        provider="OpenAI",
        base_url="https://api.openai.com/v1",
        model_name="gpt-4.1",
    ),
    "qwen-compatible": ModelPreset(
        key="qwen-compatible",
        label="通义千问兼容接口",
        provider="通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model_name="qwen-plus",
    ),
}


def list_model_presets() -> list[ModelPreset]:
    return list(MODEL_PRESETS.values())


def get_model_preset(preset_key: str) -> ModelPreset | None:
    return MODEL_PRESETS.get(preset_key)


def resolve_model_identity(
    *,
    preset_key: str,
    provider: str,
    base_url: str,
    model_name: str,
) -> tuple[str, str, str]:
    preset = get_model_preset(preset_key)
    resolved_provider = provider.strip()
    resolved_base_url = base_url.strip()
    resolved_model_name = model_name.strip()

    if preset is not None:
        resolved_provider = resolved_provider or preset.provider
        resolved_base_url = resolved_base_url or preset.base_url
        resolved_model_name = resolved_model_name or preset.model_name

    return resolved_provider, resolved_base_url, resolved_model_name
