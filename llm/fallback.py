def get_answer_source(
    enabled_openai: bool,
    api_key: str | None,
    model: str,
    openai_available: bool,
    env_api_key: str,
) -> str:
    if not enabled_openai:
        return "本地回显"

    if not openai_available:
        return "本地回显 · 未安装 openai"

    current_api_key = (api_key or "").strip() or env_api_key.strip()
    if not current_api_key:
        return "本地回显 · 未配置密钥"

    return f"模型接口 · {model.strip() or '未设置模型'}"


def local_fallback_response(user_text: str) -> str:
    if "你好" in user_text:
        return "你好呀～，我是困困，一个超级可爱的AI小助手！✨ 今天有什么可以帮你的吗？"
    return (
        f"我收到了你的消息：{user_text}\n\n"
        f"当前未配置 OpenAI 密钥，所以这里是本地回显模式。"
    )
