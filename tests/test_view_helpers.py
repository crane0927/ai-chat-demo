import unittest

from services.model_config import ModelConfigInput
from services.knowledge_base import KnowledgeSearchHit
from services.prompt_template import PromptTemplate, PromptTemplateInput
from utils.rag_view_helpers import (
    format_knowledge_source_summary,
    format_rag_sources,
    knowledge_file_label,
)
from utils.view_helpers import (
    build_model_config_input,
    build_prompt_template_input,
    build_template_copy_name,
    model_config_label,
    prompt_template_label,
)


class ViewHelpersTestCase(unittest.TestCase):
    def test_model_config_label_marks_disabled_config(self) -> None:
        config = ModelConfigInput(
            name="DeepSeek",
            provider="DeepSeek",
            api_key="",
            base_url="https://api.deepseek.com",
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=2048,
            context_message_limit=20,
            timeout_seconds=60.0,
            max_retries=2,
            enabled=False,
        )

        self.assertEqual(model_config_label(config), "DeepSeek（已停用）")

    def test_prompt_template_label_marks_builtin_template(self) -> None:
        template = PromptTemplate(
            id=1,
            name="写作助手",
            description="desc",
            content="content",
            builtin=True,
        )

        self.assertEqual(prompt_template_label(template), "写作助手（内置）")

    def test_build_template_copy_name_avoids_collisions(self) -> None:
        templates = [
            PromptTemplate(
                id=1, name="模板", description="", content="", builtin=False
            ),
            PromptTemplate(
                id=2, name="模板 副本", description="", content="", builtin=False
            ),
            PromptTemplate(
                id=3, name="模板 副本 2", description="", content="", builtin=False
            ),
        ]

        self.assertEqual(build_template_copy_name(templates, "模板"), "模板 副本 3")

    def test_build_model_config_input_normalizes_numeric_values(self) -> None:
        result = build_model_config_input(
            "OpenAI",
            "OpenAI",
            "sk-test",
            "https://api.openai.com/v1",
            "gpt-4.1",
            0.3,
            1024,
            12,
            45,
            1,
            True,
        )

        self.assertIsInstance(result, ModelConfigInput)
        self.assertEqual(result.max_tokens, 1024)
        self.assertEqual(result.timeout_seconds, 45.0)

    def test_build_model_config_input_preserves_embedding_fields(self) -> None:
        result = build_model_config_input(
            "OpenAI",
            "OpenAI",
            "sk-test",
            "https://api.openai.com/v1",
            "gpt-4.1",
            0.3,
            1024,
            12,
            45,
            1,
            True,
            embedding_api_key="emb-key",
            embedding_base_url="https://emb.example.com/v1",
            embedding_model_name="text-embedding-3-small",
        )

        self.assertEqual(result.embedding_api_key, "emb-key")
        self.assertEqual(result.embedding_base_url, "https://emb.example.com/v1")
        self.assertEqual(result.embedding_model_name, "text-embedding-3-small")

    def test_build_prompt_template_input_marks_custom_template(self) -> None:
        result = build_prompt_template_input("复盘助手", "帮助复盘", "请复盘 {{主题}}")

        self.assertIsInstance(result, PromptTemplateInput)
        self.assertFalse(result.builtin)

    def test_format_rag_sources_builds_multiline_label(self) -> None:
        label = format_rag_sources(
            [
                KnowledgeSearchHit(
                    file_id=10,
                    filename="manual.md",
                    chunk_index=1,
                    content="部署资料",
                    preview="部署摘要",
                    score=0.91,
                ),
                KnowledgeSearchHit(
                    file_id=11,
                    filename="faq.txt",
                    chunk_index=0,
                    content="排查资料",
                    preview="排查摘要",
                    score=0.67,
                ),
            ]
        )

        self.assertEqual(
            label,
            "\n".join(
                [
                    "1. manual.md#1",
                    "摘要：部署摘要",
                    "2. faq.txt#0",
                    "摘要：排查摘要",
                ]
            ),
        )

    def test_format_rag_sources_returns_empty_string_when_no_hits(self) -> None:
        self.assertEqual(format_rag_sources([]), "")

    def test_knowledge_file_label_includes_chunk_count(self) -> None:
        label = knowledge_file_label(
            file_name="manual.pdf",
            file_type="pdf",
            chunk_count=12,
        )

        self.assertEqual(label, "manual.pdf · PDF · 12 片段")

    def test_format_knowledge_source_summary_prefers_latest_rag_sources(self) -> None:
        summary = format_knowledge_source_summary(
            last_sources="1. manual.pdf#1\n摘要：部署摘要",
            fallback_message="上传知识文件后，系统会在当前会话内优先检索这些资料。",
        )

        self.assertEqual(summary, "最近一次检索：1. manual.pdf#1 / 摘要：部署摘要")

    def test_format_knowledge_source_summary_falls_back_to_explanation(self) -> None:
        summary = format_knowledge_source_summary(
            last_sources="",
            fallback_message="上传知识文件后，系统会在当前会话内优先检索这些资料。",
        )

        self.assertEqual(
            summary,
            "上传知识文件后，系统会在当前会话内优先检索这些资料。",
        )


if __name__ == "__main__":
    unittest.main()
