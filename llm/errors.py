def format_openai_error(
    exc: Exception,
    *,
    authentication_error,
    permission_denied_error,
    rate_limit_error,
    api_timeout_error,
    api_connection_error,
    not_found_error,
    bad_request_error,
    api_error,
) -> str:
    if authentication_error is not None and isinstance(exc, authentication_error):
        return "鉴权失败：API Key 无效、已过期，或当前服务商不接受该密钥。"

    if permission_denied_error is not None and isinstance(exc, permission_denied_error):
        return "权限不足：当前 API Key 没有访问该模型或接口的权限。"

    if rate_limit_error is not None and isinstance(exc, rate_limit_error):
        return "请求受限：触发了频率限制或额度不足，请稍后重试或检查账户额度。"

    if api_timeout_error is not None and isinstance(exc, api_timeout_error):
        return "请求超时：模型服务响应时间过长，请调大超时时间或稍后重试。"

    if api_connection_error is not None and isinstance(exc, api_connection_error):
        return "连接失败：无法连接到模型服务，请检查 Base URL、网络或代理配置。"

    if not_found_error is not None and isinstance(exc, not_found_error):
        return "资源不存在：请检查模型名称、Base URL 或接口路径是否正确。"

    if bad_request_error is not None and isinstance(exc, bad_request_error):
        return f"请求参数无效：{exc}"

    if api_error is not None and isinstance(exc, api_error):
        return f"模型服务异常：{exc}"

    return f"请求失败：{type(exc).__name__} - {exc}"
