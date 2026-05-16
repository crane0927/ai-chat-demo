from typing import TYPE_CHECKING, Sequence


if TYPE_CHECKING:
    from services.knowledge_base import KnowledgeSearchHit


def format_rag_source_reference(filename: str, chunk_index: int) -> str:
    return f"{filename}#{chunk_index}"


def format_rag_sources(hits: Sequence["KnowledgeSearchHit"]) -> str:
    if not hits:
        return ""

    lines: list[str] = []
    for index, hit in enumerate(hits, start=1):
        lines.append(
            f"{index}. {format_rag_source_reference(hit.filename, hit.chunk_index)}"
        )
        preview = hit.preview.strip()
        if preview:
            lines.append(f"摘要：{preview}")
    return "\n".join(lines)


def knowledge_file_label(file_name: str, file_type: str, chunk_count: int) -> str:
    normalized_type = (file_type or "").strip().upper() or "未知类型"
    return f"{file_name} · {normalized_type} · {int(chunk_count)} 片段"


def format_knowledge_source_summary(
    last_sources: str,
    fallback_message: str,
) -> str:
    normalized_sources = " / ".join(
        line.strip() for line in last_sources.splitlines() if line.strip()
    )
    if normalized_sources:
        return f"最近一次检索：{normalized_sources}"
    return fallback_message.strip()
