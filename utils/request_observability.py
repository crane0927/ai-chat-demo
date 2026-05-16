from dataclasses import dataclass


@dataclass(frozen=True)
class RequestTelemetry:
    elapsed_seconds: float
    answer_source: str
    input_message_count: int
    sent_message_count: int
    error_type: str = ""


@dataclass(frozen=True)
class RequestObservability:
    elapsed_label: str
    context_label: str
    trim_label: str
    outcome_label: str


def build_request_observability(
    telemetry: RequestTelemetry,
) -> RequestObservability:
    trimmed_count = max(telemetry.input_message_count - telemetry.sent_message_count, 0)
    trim_label = "未裁剪"
    if trimmed_count:
        trim_label = f"已裁剪 {trimmed_count} 条"

    outcome_label = telemetry.answer_source.strip() or "等待请求"
    if telemetry.error_type.strip():
        outcome_label = f"错误类型：{telemetry.error_type.strip()}"

    # 页面状态只展示轻量摘要，避免把完整链路细节直接暴露到主界面里。
    return RequestObservability(
        elapsed_label=f"{telemetry.elapsed_seconds:.2f} 秒",
        context_label=(
            f"{telemetry.sent_message_count} / {telemetry.input_message_count} 条上下文"
        ),
        trim_label=trim_label,
        outcome_label=outcome_label,
    )
