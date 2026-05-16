from dataclasses import dataclass
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - 依赖缺失时由运行环境或调用方处理
    PdfReader = None


class DocumentLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadedDocument:
    file_type: str
    content: str


def _load_utf8_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentLoadError("文档不是有效的 UTF-8 文本。") from exc


def _load_pdf_text(path: Path) -> str:
    if PdfReader is None:
        raise DocumentLoadError("当前环境缺少 PDF 解析依赖。")

    try:
        reader = PdfReader(str(path))
        page_texts: list[str] = []
        for page in reader.pages:
            # 统一收敛底层 PDF 解析异常，避免把库内部报错暴露给上层调用方。
            extracted_text = page.extract_text() or ""
            normalized_text = extracted_text.strip()
            if normalized_text:
                page_texts.append(normalized_text)
        return "\n".join(page_texts)
    except DocumentLoadError:
        raise
    except Exception as exc:
        raise DocumentLoadError("PDF 暂无法解析文本。") from exc


def load_document(path: Path) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        file_type = "txt"
        content = _load_utf8_text(path)
    elif suffix == ".md":
        file_type = "md"
        content = _load_utf8_text(path)
    elif suffix == ".pdf":
        file_type = "pdf"
        content = _load_pdf_text(path)
    else:
        raise DocumentLoadError(f"暂不支持该文件类型：{suffix or 'unknown'}")

    if not content.strip():
        if file_type == "pdf":
            raise DocumentLoadError("PDF 暂无法解析文本。")
        raise DocumentLoadError("文档内容为空。")

    return LoadedDocument(file_type=file_type, content=content.strip())
