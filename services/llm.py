import os
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional


try:
    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        NotFoundError,
        OpenAI,
        PermissionDeniedError,
        RateLimitError,
    )
except Exception:
    OpenAI = None
    APIConnectionError = None
    APIError = None
    APITimeoutError = None
    AuthenticationError = None
    BadRequestError = None
    NotFoundError = None
    PermissionDeniedError = None
    RateLimitError = None


Message = Dict[str, str]


@dataclass(frozen=True)
class ModelRequestOptions:
    max_tokens: int
    context_message_limit: int
    timeout_seconds: float
    max_retries: int


def clean_model_messages(history: List[Message]) -> List[Message]:
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if msg.get("role") in {"system", "user", "assistant"}
    ]


def trim_model_messages(
    history: List[Message],
    context_message_limit: int,
) -> List[Message]:
    cleaned_messages = clean_model_messages(history)
    if context_message_limit <= 0:
        return cleaned_messages

    system_messages = [msg for msg in cleaned_messages if msg["role"] == "system"]
    dialog_messages = [msg for msg in cleaned_messages if msg["role"] != "system"]

    trimmed_dialog = dialog_messages[-context_message_limit:]
    if system_messages:
        return [system_messages[0], *trimmed_dialog]
    return trimmed_dialog


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


def format_openai_error(exc: Exception) -> str:
    if AuthenticationError is not None and isinstance(exc, AuthenticationError):
        return "鉴权失败：API Key 无效、已过期，或当前服务商不接受该密钥。"

    if PermissionDeniedError is not None and isinstance(exc, PermissionDeniedError):
        return "权限不足：当前 API Key 没有访问该模型或接口的权限。"

    if RateLimitError is not None and isinstance(exc, RateLimitError):
        return "请求受限：触发了频率限制或额度不足，请稍后重试或检查账户额度。"

    if APITimeoutError is not None and isinstance(exc, APITimeoutError):
        return "请求超时：模型服务响应时间过长，请调大超时时间或稍后重试。"

    if APIConnectionError is not None and isinstance(exc, APIConnectionError):
        return "连接失败：无法连接到模型服务，请检查 Base URL、网络或代理配置。"

    if NotFoundError is not None and isinstance(exc, NotFoundError):
        return "资源不存在：请检查模型名称、Base URL 或接口路径是否正确。"

    if BadRequestError is not None and isinstance(exc, BadRequestError):
        return f"请求参数无效：{exc}"

    if APIError is not None and isinstance(exc, APIError):
        return f"模型服务异常：{exc}"

    return f"请求失败：{type(exc).__name__} - {exc}"


def openai_stream_response(
    history: List[Message],
    temp: float,
    api_key: Optional[str],
    model: str,
    base_url: Optional[str],
    options: ModelRequestOptions,
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
        timeout=options.timeout_seconds,
        max_retries=options.max_retries,
    )

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=trim_model_messages(history, options.context_message_limit),
            temperature=temp,
            max_tokens=options.max_tokens,
            stream=True,
        )
        for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        yield format_openai_error(exc)
