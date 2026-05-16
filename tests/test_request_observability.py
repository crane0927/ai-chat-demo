import unittest

from utils.request_observability import (
    RequestObservability,
    RequestTelemetry,
    build_request_observability,
)


class RequestObservabilityTestCase(unittest.TestCase):
    def test_build_request_observability_marks_trimmed_request(self) -> None:
        telemetry = RequestTelemetry(
            elapsed_seconds=1.25,
            answer_source="模型接口 · deepseek-chat",
            input_message_count=9,
            sent_message_count=5,
            error_type="",
        )

        result = build_request_observability(telemetry)

        self.assertEqual(
            result,
            RequestObservability(
                elapsed_label="1.25 秒",
                context_label="5 / 9 条上下文",
                trim_label="已裁剪 4 条",
                outcome_label="模型接口 · deepseek-chat",
            ),
        )

    def test_build_request_observability_marks_untrimmed_error_request(self) -> None:
        telemetry = RequestTelemetry(
            elapsed_seconds=0.4,
            answer_source="",
            input_message_count=3,
            sent_message_count=3,
            error_type="AuthenticationError",
        )

        result = build_request_observability(telemetry)

        self.assertEqual(result.trim_label, "未裁剪")
        self.assertEqual(result.outcome_label, "错误类型：AuthenticationError")
        self.assertEqual(result.context_label, "3 / 3 条上下文")


if __name__ == "__main__":
    unittest.main()
