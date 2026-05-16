import os

from llm.client import openai_stream_response as stream_openai_response
from llm.errors import format_openai_error as format_sdk_error
from llm.fallback import get_answer_source as resolve_answer_source
from llm.fallback import local_fallback_response
from llm.messages import clean_model_messages, trim_model_messages
from llm.types import Message, ModelRequestOptions


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


def get_answer_source(
    enabled_openai: bool,
    api_key: str | None,
    model: str,
) -> str:
    return resolve_answer_source(
        enabled_openai=enabled_openai,
        api_key=api_key,
        model=model,
        openai_available=OpenAI is not None,
        env_api_key=os.getenv("OPENAI_API_KEY", ""),
    )


def format_openai_error(exc: Exception) -> str:
    return format_sdk_error(
        exc,
        authentication_error=AuthenticationError,
        permission_denied_error=PermissionDeniedError,
        rate_limit_error=RateLimitError,
        api_timeout_error=APITimeoutError,
        api_connection_error=APIConnectionError,
        not_found_error=NotFoundError,
        bad_request_error=BadRequestError,
        api_error=APIError,
    )


def openai_stream_response(
    history: list[Message],
    temp: float,
    api_key: str | None,
    model: str,
    base_url: str | None,
    options: ModelRequestOptions,
    error_handler=None,
):
    return stream_openai_response(
        history=history,
        temp=temp,
        api_key=api_key,
        model=model,
        base_url=base_url,
        options=options,
        openai_class=OpenAI,
        authentication_error=AuthenticationError,
        permission_denied_error=PermissionDeniedError,
        rate_limit_error=RateLimitError,
        api_timeout_error=APITimeoutError,
        api_connection_error=APIConnectionError,
        not_found_error=NotFoundError,
        bad_request_error=BadRequestError,
        api_error=APIError,
        error_handler=error_handler,
    )


__all__ = [
    "Message",
    "ModelRequestOptions",
    "OpenAI",
    "AuthenticationError",
    "PermissionDeniedError",
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "NotFoundError",
    "BadRequestError",
    "APIError",
    "clean_model_messages",
    "trim_model_messages",
    "get_answer_source",
    "local_fallback_response",
    "format_openai_error",
    "openai_stream_response",
]
