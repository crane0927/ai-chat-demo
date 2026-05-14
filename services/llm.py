import os
from typing import Dict, Iterator, List, Optional


try:
    from openai import AuthenticationError, OpenAI
except Exception:
    OpenAI = None
    AuthenticationError = None


Message = Dict[str, str]


def clean_model_messages(history: List[Message]) -> List[Message]:
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if msg.get("role") in {"system", "user", "assistant"}
    ]


def get_answer_source(
    enabled_openai: bool,
    api_key: Optional[str],
    model: str,
) -> str:
    if not enabled_openai:
        return "本地回显"

    if OpenAI is None:
        return "本地回显 · 未安装 openai"

    current_api_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
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


def openai_stream_response(
    history: List[Message],
    temp: float,
    api_key: Optional[str],
    model: str,
    base_url: Optional[str],
) -> Iterator[str]:
    if OpenAI is None:
        yield "未安装 openai 依赖，已切换为本地回显模式。"
        return

    api_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        yield "未检测到 OPENAI_API_KEY，已切换为本地回显模式。"
        return

    base_url = (base_url or "").strip() or None

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=clean_model_messages(history),
            temperature=temp,
            stream=True,
        )
        for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        if AuthenticationError is not None and isinstance(exc, AuthenticationError):
            yield f"鉴权失败（401）：{exc}"
            return
        yield f"请求失败：{type(exc).__name__} - {exc}"
