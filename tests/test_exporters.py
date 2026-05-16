from datetime import datetime, timezone
import json
import unittest

from services.session import ChatMessage, ChatSession
from utils.exporters import (
    build_session_export_filename,
    build_session_json,
    build_session_markdown,
)


class ExportersTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = ChatSession(
            id=12,
            title="测试/会话 * 01",
            system_prompt="你是测试助手",
            model_config_id=3,
            created_at=datetime(2026, 5, 16, 10, 30, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 16, 11, 0, tzinfo=timezone.utc),
            message_count=2,
        )
        self.messages = [
            ChatMessage(
                id=1,
                session_id=12,
                role="user",
                content="你好",
                source="",
                sort_order=1,
                created_at=datetime(2026, 5, 16, 10, 31, tzinfo=timezone.utc),
            ),
            ChatMessage(
                id=2,
                session_id=12,
                role="assistant",
                content="你好呀",
                source="模型接口 · deepseek-chat",
                sort_order=2,
                created_at=datetime(2026, 5, 16, 10, 32, tzinfo=timezone.utc),
            ),
        ]

    def test_build_session_markdown_contains_sections_and_source(self) -> None:
        markdown = build_session_markdown(self.session, self.messages)

        self.assertIn("# 测试/会话 * 01", markdown)
        self.assertIn("## 系统提示词", markdown)
        self.assertIn("### 用户", markdown)
        self.assertIn("### 助手", markdown)
        self.assertIn("> 回答来源：模型接口 · deepseek-chat", markdown)

    def test_build_session_json_contains_serialized_payload(self) -> None:
        payload = json.loads(build_session_json(self.session, self.messages))

        self.assertEqual(payload["session"]["id"], 12)
        self.assertEqual(payload["messages"][1]["source"], "模型接口 · deepseek-chat")
        self.assertEqual(payload["messages"][0]["content"], "你好")

    def test_build_session_export_filename_sanitizes_unsafe_chars(self) -> None:
        filename = build_session_export_filename(self.session, "md")

        self.assertEqual(filename, "测试-会话-01.md")


if __name__ == "__main__":
    unittest.main()
