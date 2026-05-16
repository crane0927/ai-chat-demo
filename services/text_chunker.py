from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    content: str
    preview: str
    char_start: int
    char_end: int


def chunk_text(
    text: str, chunk_size: int = 800, overlap: int = 150
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0。")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须大于等于 0 且小于 chunk_size。")
    if not text.strip():
        return []

    chunks: list[TextChunk] = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        window = text[start:end]
        stripped = window.strip()

        if stripped:
            leading_whitespace = len(window) - len(window.lstrip())
            trailing_whitespace = len(window) - len(window.rstrip())
            content_start = start + leading_whitespace
            content_end = end - trailing_whitespace
            # 预览文本保持轻量，避免后续列表或引用展示时注入过长正文。
            preview = stripped[:120]
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=stripped,
                    preview=preview,
                    char_start=content_start,
                    char_end=content_end,
                )
            )
            chunk_index += 1

        if end >= len(text):
            break

        # 重叠窗口至少前进一步，避免极端参数下卡在同一位置。
        start = max(end - overlap, start + 1)

    return chunks
