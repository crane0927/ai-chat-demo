import os
from typing import Iterator

from llm.errors import format_openai_error
from llm.messages import trim_model_messages
from llm.types import Message, ModelRequestOptions


def openai_stream_response(
    history: list[Message],
    temp: float,
    api_key: str | None,
    model: str,
    base_url: str | None,
    options: ModelRequestOptions,
    *,
    openai_class,
    authentication_error,
    permission_denied_error,
    rate_limit_error,
    api_timeout_error,
    api_connection_error,
    not_found_error,
    bad_request_error,
    api_error,
) -> Iterator[str]:
    if openai_class is None:
        yield "未安装 openai 依赖，已切换为本地回显模式。"
        return

    resolved_api_key = (api_key or "").strip() or os.getenv(
        "OPENAI_API_KEY", ""
    ).strip()
    if not resolved_api_key:
        yield "未检测到 OPENAI_API_KEY，已切换为本地回显模式。"
        return

    resolved_base_url = (base_url or "").strip() or None
    client = openai_class(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
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
        # 这里把 SDK 异常映射为稳定的中文文案，避免页面层理解不同服务商的异常细节。
        yield format_openai_error(
            exc,
            authentication_error=authentication_error,
            permission_denied_error=permission_denied_error,
            rate_limit_error=rate_limit_error,
            api_timeout_error=api_timeout_error,
            api_connection_error=api_connection_error,
            not_found_error=not_found_error,
            bad_request_error=bad_request_error,
            api_error=api_error,
        )
