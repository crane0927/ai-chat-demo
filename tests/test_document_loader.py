from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import mock
import unittest

from services.document_loader import DocumentLoadError, load_document


class DocumentLoaderTestCase(unittest.TestCase):
    def test_load_document_reads_utf8_txt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.txt"
            path.write_text("第一段\n第二段", encoding="utf-8")

            result = load_document(path)

        self.assertEqual(result.file_type, "txt")
        self.assertEqual(result.content, "第一段\n第二段")

    def test_load_document_reads_utf8_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.md"
            path.write_text("# 标题\n\n这里是内容。", encoding="utf-8")

            result = load_document(path)

        self.assertEqual(result.file_type, "md")
        self.assertIn("# 标题", result.content)

    def test_load_document_extracts_text_from_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.pdf"
            path.write_bytes(b"%PDF-1.4")

            fake_reader = SimpleNamespace(
                pages=[
                    SimpleNamespace(extract_text=lambda: "第一页"),
                    SimpleNamespace(extract_text=lambda: "第二页"),
                ]
            )

            with mock.patch("services.document_loader.PdfReader", return_value=fake_reader):
                result = load_document(path)

        self.assertEqual(result.file_type, "pdf")
        self.assertEqual(result.content, "第一页\n第二页")

    def test_load_document_rejects_missing_pdf_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.pdf"
            path.write_bytes(b"%PDF-1.4")

            with mock.patch("services.document_loader.PdfReader", None):
                with self.assertRaisesRegex(
                    DocumentLoadError, "当前环境缺少 PDF 解析依赖。"
                ):
                    load_document(path)

    def test_load_document_rejects_pdf_reader_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken.pdf"
            path.write_bytes(b"%PDF-1.4")

            with mock.patch(
                "services.document_loader.PdfReader",
                side_effect=RuntimeError("reader failed"),
            ):
                with self.assertRaisesRegex(
                    DocumentLoadError, "PDF 暂无法解析文本。"
                ):
                    load_document(path)

    def test_load_document_rejects_pdf_page_extract_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken-page.pdf"
            path.write_bytes(b"%PDF-1.4")

            fake_reader = SimpleNamespace(
                pages=[SimpleNamespace(extract_text=mock.Mock(side_effect=RuntimeError))]
            )

            with mock.patch("services.document_loader.PdfReader", return_value=fake_reader):
                with self.assertRaisesRegex(
                    DocumentLoadError, "PDF 暂无法解析文本。"
                ):
                    load_document(path)

    def test_load_document_keeps_text_when_pdf_has_empty_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mixed-pages.pdf"
            path.write_bytes(b"%PDF-1.4")

            fake_reader = SimpleNamespace(
                pages=[
                    SimpleNamespace(extract_text=lambda: "   "),
                    SimpleNamespace(extract_text=lambda: "正文"),
                    SimpleNamespace(extract_text=lambda: None),
                ]
            )

            with mock.patch("services.document_loader.PdfReader", return_value=fake_reader):
                result = load_document(path)

        self.assertEqual(result.content, "正文")

    def test_load_document_rejects_unsupported_file_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.docx"
            path.write_text("not-supported", encoding="utf-8")

            with self.assertRaisesRegex(DocumentLoadError, "暂不支持"):
                load_document(path)

    def test_load_document_rejects_empty_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.txt"
            path.write_text("   \n\t", encoding="utf-8")

            with self.assertRaisesRegex(DocumentLoadError, "内容为空"):
                load_document(path)

    def test_load_document_rejects_invalid_utf8_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken.txt"
            path.write_bytes(b"\xff\xfe\xfd")

            with self.assertRaisesRegex(
                DocumentLoadError, "文档不是有效的 UTF-8 文本。"
            ):
                load_document(path)

    def test_load_document_rejects_pdf_without_extractable_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.pdf"
            path.write_bytes(b"%PDF-1.4")

            fake_reader = SimpleNamespace(
                pages=[SimpleNamespace(extract_text=lambda: "   ")]
            )

            with mock.patch("services.document_loader.PdfReader", return_value=fake_reader):
                with self.assertRaisesRegex(DocumentLoadError, "PDF 暂无法解析文本"):
                    load_document(path)


if __name__ == "__main__":
    unittest.main()
