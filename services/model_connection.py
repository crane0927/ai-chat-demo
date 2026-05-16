try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from services.llm import format_openai_error
from services.model_config import ModelConfigInput


class ModelConnectionTestError(RuntimeError):
    pass


def test_model_connection(config: ModelConfigInput) -> str:
    if OpenAI is None:
        raise ModelConnectionTestError("未安装 openai 依赖，无法执行连接测试。")

    if not config.api_key.strip():
        raise ModelConnectionTestError("请先填写 API Key，再执行连接测试。")

    try:
        client = OpenAI(
            api_key=config.api_key.strip(),
            base_url=config.base_url.strip() or None,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        # 连接测试只验证当前配置是否可完成一次最小请求，不在这里引入真实业务上下文。
        client.chat.completions.create(
            model=config.model_name.strip(),
            messages=[{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=1,
            stream=False,
        )
    except Exception as exc:
        raise ModelConnectionTestError(format_openai_error(exc)) from exc

    provider_label = config.provider.strip() or "模型接口"
    return f"连接成功：{provider_label} / {config.model_name.strip()}"


test_model_connection.__test__ = False
