from services.model_config import ModelConfig, ModelConfigInput
from services.model_presets import ModelPreset, resolve_model_identity
from services.prompt_template import PromptTemplate, PromptTemplateInput


def model_config_label(config: ModelConfig) -> str:
    disabled_label = "（已停用）" if not config.enabled else ""
    return f"{config.name}{disabled_label}"


def build_model_config_input(
    name: str,
    provider: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    context_message_limit: int,
    timeout_seconds: float,
    max_retries: int,
    enabled: bool,
    preset_key: str = "custom",
) -> ModelConfigInput:
    resolved_provider, resolved_base_url, resolved_model_name = resolve_model_identity(
        preset_key=preset_key,
        provider=provider,
        base_url=base_url,
        model_name=model_name,
    )
    return ModelConfigInput(
        name=name,
        provider=resolved_provider,
        api_key=api_key,
        base_url=resolved_base_url,
        model_name=resolved_model_name,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        context_message_limit=int(context_message_limit),
        timeout_seconds=float(timeout_seconds),
        max_retries=int(max_retries),
        enabled=enabled,
    )


def model_preset_label(preset: ModelPreset) -> str:
    return preset.label


def prompt_template_label(template: PromptTemplate) -> str:
    builtin_label = "（内置）" if template.builtin else ""
    return f"{template.name}{builtin_label}"


def build_prompt_template_input(
    name: str, description: str, content: str
) -> PromptTemplateInput:
    return PromptTemplateInput(
        name=name,
        description=description,
        content=content,
        builtin=False,
    )


def build_template_copy_name(
    existing_templates: list[PromptTemplate], source_name: str
) -> str:
    existing_names = {template.name for template in existing_templates}
    if f"{source_name} 副本" not in existing_names:
        return f"{source_name} 副本"

    index = 2
    while f"{source_name} 副本 {index}" in existing_names:
        index += 1
    return f"{source_name} 副本 {index}"
