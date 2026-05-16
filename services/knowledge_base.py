import json
import math
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from db.errors import execute_write, is_unique_violation
from repositories import knowledge_base_repo
from services.document_loader import load_document
from services.embeddings import EmbeddingProviderError, build_embedding_provider
from services.model_config import ModelConfig, ModelConfigInput
from services.text_chunker import chunk_text
from utils.rag_view_helpers import (
    format_rag_source_reference,
    format_rag_sources,
)


class KnowledgeBaseStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class IngestKnowledgeFileResult:
    file_id: int
    session_id: int
    filename: str
    chunk_count: int
    embedding_mode: str


@dataclass(frozen=True)
class KnowledgeSearchHit:
    file_id: int
    filename: str
    chunk_index: int
    content: str
    preview: str
    score: float


@dataclass(frozen=True)
class SessionKnowledgeFile:
    id: int
    session_id: int
    filename: str
    file_type: str
    storage_path: str
    content_hash: str
    file_size: int
    chunk_count: int
    embedding_mode: str


@dataclass(frozen=True)
class RetrievedKnowledgeContextResult:
    hits: list[KnowledgeSearchHit]
    context: str
    sources: str


def init_knowledge_base_db(database_url: str) -> None:
    knowledge_base_repo.init_knowledge_base_db(
        database_url,
        KnowledgeBaseStorageError,
    )


def register_knowledge_file(
    database_url: str,
    *,
    filename: str,
    file_type: str,
    storage_path: str,
    content_hash: str,
    file_size: int,
    chunk_count: int,
    embedding_mode: str,
    include_created: bool = False,
) -> int | tuple[int, bool]:
    existing_row = _get_ready_knowledge_file_by_hash(database_url, content_hash)
    if existing_row is not None:
        file_id = int(existing_row["id"])
        return (file_id, False) if include_created else file_id

    try:
        file_id = knowledge_base_repo.create_knowledge_file(
            database_url,
            KnowledgeBaseStorageError,
            {
                "filename": filename,
                "file_type": file_type,
                "storage_path": storage_path,
                "content_hash": content_hash,
                "file_size": file_size,
                "chunk_count": chunk_count,
                "embedding_mode": embedding_mode,
            },
        )
        return (file_id, True) if include_created else file_id
    except Exception as exc:
        if is_unique_violation(exc):
            existing_row = _get_ready_knowledge_file_by_hash(database_url, content_hash)
            if existing_row is not None:
                file_id = int(existing_row["id"])
                return (file_id, False) if include_created else file_id
            raise KnowledgeBaseStorageError("知识文件正在处理中，请稍后重试。") from exc
        if isinstance(exc, KnowledgeBaseStorageError):
            raise
        raise KnowledgeBaseStorageError("知识文件写入 PostgreSQL 失败。") from exc


def replace_knowledge_chunks(
    database_url: str,
    *,
    file_id: int,
    chunks: list[dict],
) -> None:
    def operation() -> None:
        knowledge_base_repo.replace_knowledge_chunks(
            database_url,
            KnowledgeBaseStorageError,
            file_id=file_id,
            chunks=chunks,
        )

    execute_write(
        operation=operation,
        error_cls=KnowledgeBaseStorageError,
        generic_message="知识分块写入 PostgreSQL 失败。",
    )


def update_knowledge_file_storage_path(
    database_url: str,
    *,
    file_id: int,
    storage_path: str,
) -> None:
    def operation() -> None:
        knowledge_base_repo.update_knowledge_file_storage_path(
            database_url,
            KnowledgeBaseStorageError,
            file_id=file_id,
            storage_path=storage_path,
        )

    execute_write(
        operation=operation,
        error_cls=KnowledgeBaseStorageError,
        generic_message="知识文件路径更新失败。",
    )


def delete_knowledge_file(
    database_url: str,
    *,
    file_id: int,
) -> None:
    def operation() -> None:
        knowledge_base_repo.delete_knowledge_file(
            database_url,
            KnowledgeBaseStorageError,
            file_id=file_id,
        )

    execute_write(
        operation=operation,
        error_cls=KnowledgeBaseStorageError,
        generic_message="知识文件清理失败。",
    )


def link_session_knowledge_file(
    database_url: str,
    *,
    session_id: int,
    file_id: int,
) -> None:
    def operation() -> None:
        knowledge_base_repo.link_session_knowledge_file(
            database_url,
            KnowledgeBaseStorageError,
            session_id=session_id,
            file_id=file_id,
        )

    execute_write(
        operation=operation,
        error_cls=KnowledgeBaseStorageError,
        generic_message="会话绑定知识文件失败。",
    )


def list_session_knowledge_files(
    database_url: str,
    *,
    session_id: int,
) -> list[SessionKnowledgeFile]:
    rows = knowledge_base_repo.list_session_knowledge_file_rows(
        database_url,
        KnowledgeBaseStorageError,
        session_id=session_id,
    )
    return [
        SessionKnowledgeFile(
            id=int(row["id"]),
            session_id=int(row["session_id"]),
            filename=str(row["filename"]),
            file_type=str(row["file_type"]),
            storage_path=str(row["storage_path"]),
            content_hash=str(row["content_hash"]),
            file_size=int(row["file_size"]),
            chunk_count=int(row["chunk_count"]),
            embedding_mode=str(row["embedding_mode"]),
        )
        for row in rows
    ]


def search_knowledge_chunks(
    database_url: str,
    *,
    session_id: int,
    query: str,
    model_config: ModelConfig | ModelConfigInput,
    top_k: int,
) -> list[KnowledgeSearchHit]:
    if top_k <= 0 or not query.strip():
        return []

    try:
        provider = build_embedding_provider(model_config)
        query_vectors = provider.embed_texts([query])
    except EmbeddingProviderError as exc:
        # 检索阶段统一收敛向量化异常，便于上层按“知识库检索失败”做一致降级。
        raise KnowledgeBaseStorageError(str(exc)) from exc
    if not query_vectors:
        return []

    query_vector = query_vectors[0]
    candidate_rows = knowledge_base_repo.list_session_knowledge_chunk_rows(
        database_url,
        KnowledgeBaseStorageError,
        session_id=session_id,
    )

    ranked_hits: list[KnowledgeSearchHit] = []
    for row in candidate_rows:
        # 只检索与当前查询向量模式一致的索引，避免本地/远端索引混用导致相似度失真。
        row_embedding_mode = str(row.get("embedding_mode", "")).strip()
        if row_embedding_mode and row_embedding_mode != provider.mode:
            continue

        chunk_vector = _deserialize_embedding_vector(row.get("embedding_vector"))
        score = _cosine_similarity(query_vector, chunk_vector)
        if score <= 0:
            continue

        ranked_hits.append(
            KnowledgeSearchHit(
                file_id=int(row["file_id"]),
                filename=str(row["filename"]),
                chunk_index=int(row["chunk_index"]),
                content=str(row["content"]),
                preview=_normalize_preview(
                    preview=str(row.get("preview", "")),
                    content=str(row["content"]),
                ),
                score=score,
            )
        )

    ranked_hits.sort(
        key=lambda hit: (-hit.score, hit.filename, hit.chunk_index, hit.file_id)
    )
    return ranked_hits[:top_k]


def build_rag_context(hits: list[KnowledgeSearchHit]) -> str:
    if not hits:
        return ""

    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        source_reference = format_rag_source_reference(hit.filename, hit.chunk_index)
        # 固定段落结构便于后续直接注入系统提示词，也便于测试保持稳定。
        blocks.append(
            "\n".join(
                [
                    f"[参考资料 {index}]",
                    f"来源：{source_reference}",
                    f"相关度：{hit.score:.4f}",
                    "内容：",
                    hit.content.strip(),
                ]
            )
        )
    return "\n\n".join(blocks)


def retrieve_session_knowledge_context(
    database_url: str,
    *,
    session_id: int,
    query: str,
    model_config: ModelConfig | ModelConfigInput,
    top_k: int,
) -> RetrievedKnowledgeContextResult:
    hits = search_knowledge_chunks(
        database_url,
        session_id=session_id,
        query=query,
        model_config=model_config,
        top_k=top_k,
    )
    return RetrievedKnowledgeContextResult(
        hits=hits,
        context=build_rag_context(hits),
        sources=format_rag_sources(hits),
    )


def ingest_knowledge_file(
    database_url: str,
    *,
    session_id: int,
    upload_name: str,
    raw_bytes: bytes,
    model_config: ModelConfig | ModelConfigInput,
    storage_dir: Path | None = None,
) -> IngestKnowledgeFileResult:
    normalized_filename = _normalize_upload_name(upload_name)
    content_hash = sha256(raw_bytes).hexdigest()
    existing_row = _get_ready_knowledge_file_by_hash(database_url, content_hash)
    if existing_row is not None:
        link_session_knowledge_file(
            database_url,
            session_id=session_id,
            file_id=int(existing_row["id"]),
        )
        return IngestKnowledgeFileResult(
            file_id=int(existing_row["id"]),
            session_id=session_id,
            filename=existing_row["filename"],
            chunk_count=int(existing_row["chunk_count"]),
            embedding_mode=existing_row["embedding_mode"],
        )

    staging_path: Path | None = None
    final_saved_path: Path | None = None
    file_id: int | None = None
    created_new_file = False
    storage_path_updated = False

    staging_path = _save_uploaded_file(
        filename=normalized_filename,
        raw_bytes=raw_bytes,
        storage_dir=storage_dir,
        file_id=None,
    )
    try:
        document = load_document(staging_path)
        chunks = chunk_text(document.content)
        provider = build_embedding_provider(model_config)
        vectors = provider.embed_texts([chunk.content for chunk in chunks])

        if len(vectors) != len(chunks):
            raise KnowledgeBaseStorageError("知识分块与向量数量不一致。")

        register_result = register_knowledge_file(
            database_url,
            filename=normalized_filename,
            file_type=document.file_type,
            # 未完成归档前保持空路径，避免重复上传复用到半成品记录。
            storage_path="",
            content_hash=content_hash,
            file_size=len(raw_bytes),
            chunk_count=len(chunks),
            embedding_mode=provider.mode,
            include_created=True,
        )
        if isinstance(register_result, tuple):
            file_id, created_new_file = register_result
        else:
            file_id = register_result
            created_new_file = True
        if not created_new_file:
            # 并发重复上传命中现成记录时，必须直接复用已完成文件，不能再按当前上传名覆盖路径或重写分块。
            existing_row = _get_knowledge_file_row_by_hash_after_register(
                database_url,
                content_hash,
            )
            link_session_knowledge_file(
                database_url,
                session_id=session_id,
                file_id=file_id,
            )
            _cleanup_staging_file(staging_path)
            return IngestKnowledgeFileResult(
                file_id=file_id,
                session_id=session_id,
                filename=existing_row["filename"],
                chunk_count=int(existing_row["chunk_count"]),
                embedding_mode=existing_row["embedding_mode"],
            )
        final_storage_path = _build_storage_path(
            filename=normalized_filename,
            storage_dir=storage_dir,
            file_id=file_id,
        )
        final_saved_path = _save_uploaded_file(
            filename=normalized_filename,
            raw_bytes=raw_bytes,
            storage_dir=storage_dir,
            file_id=file_id,
        )
        update_knowledge_file_storage_path(
            database_url,
            file_id=file_id,
            storage_path=str(final_storage_path),
        )
        storage_path_updated = True
        # 分块与向量一一对应保存，保证后续检索时不需要重新推导顺序关系。
        replace_knowledge_chunks(
            database_url,
            file_id=file_id,
            chunks=[
                {
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "preview": chunk.preview,
                    "embedding_vector": vector,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                }
                for chunk, vector in zip(chunks, vectors)
            ],
        )
        link_session_knowledge_file(
            database_url,
            session_id=session_id,
            file_id=file_id,
        )
    except Exception:
        # 本次新建的半成品记录必须直接删除，否则 content_hash 唯一索引会永久阻塞后续重试。
        if created_new_file and file_id is not None:
            _delete_knowledge_file_quietly(database_url, file_id)
        elif storage_path_updated and file_id is not None:
            _reset_knowledge_file_storage_path(database_url, file_id)
        _cleanup_ingest_files(staging_path=staging_path, final_saved_path=final_saved_path)
        raise

    _cleanup_staging_file(staging_path)
    return IngestKnowledgeFileResult(
        file_id=file_id,
        session_id=session_id,
        filename=normalized_filename,
        chunk_count=len(chunks),
        embedding_mode=provider.mode,
    )


def _normalize_upload_name(upload_name: str) -> str:
    normalized_name = Path(upload_name).name.strip()
    if normalized_name:
        return normalized_name
    return "knowledge.txt"


def _save_uploaded_file(
    *,
    filename: str,
    raw_bytes: bytes,
    storage_dir: Path | None,
    file_id: int | None,
) -> Path:
    saved_path = _build_storage_path(
        filename=filename,
        storage_dir=storage_dir,
        file_id=file_id,
    )
    target_dir = saved_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_path.write_bytes(raw_bytes)
    return saved_path


def _build_storage_path(
    *,
    filename: str,
    storage_dir: Path | None,
    file_id: int | None,
) -> Path:
    base_dir = storage_dir or Path("data/knowledge_files")
    if file_id is None:
        return base_dir / "__staging__" / filename
    return base_dir / str(file_id) / filename


def _cleanup_empty_parent_dir(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        return


def _get_ready_knowledge_file_by_hash(
    database_url: str,
    content_hash: str,
) -> dict | None:
    row = knowledge_base_repo.get_knowledge_file_by_hash_row(
        database_url,
        KnowledgeBaseStorageError,
        content_hash,
    )
    if row is None:
        return None
    if not str(row.get("storage_path", "")).strip():
        return None
    return row


def _get_knowledge_file_row_by_hash_after_register(
    database_url: str,
    content_hash: str,
) -> dict:
    row = _get_ready_knowledge_file_by_hash(database_url, content_hash)
    if row is None:
        raise KnowledgeBaseStorageError("知识文件复用失败：未找到可复用的已完成记录。")
    return row


def _cleanup_ingest_files(
    *,
    staging_path: Path | None,
    final_saved_path: Path | None,
) -> None:
    _remove_file_if_exists(final_saved_path)
    _remove_file_if_exists(staging_path)


def _cleanup_staging_file(staging_path: Path | None) -> None:
    _remove_file_if_exists(staging_path)


def _remove_file_if_exists(path: Path | None) -> None:
    if path is None or not path.exists():
        return
    try:
        path.unlink()
    except OSError:
        return
    _cleanup_empty_parent_dir(path.parent)


def _reset_knowledge_file_storage_path(database_url: str, file_id: int) -> None:
    try:
        update_knowledge_file_storage_path(
            database_url,
            file_id=file_id,
            storage_path="",
        )
    except Exception:
        return


def _delete_knowledge_file_quietly(database_url: str, file_id: int) -> None:
    try:
        delete_knowledge_file(database_url, file_id=file_id)
    except Exception:
        return


def _deserialize_embedding_vector(raw_vector: object) -> list[float]:
    if isinstance(raw_vector, list):
        return [float(value) for value in raw_vector]
    if not isinstance(raw_vector, str) or not raw_vector.strip():
        return []

    try:
        parsed = json.loads(raw_vector)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []
    return [float(value) for value in parsed]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(left_value * right_value for left_value, right_value in zip(left, right))
    if numerator <= 0:
        return 0.0

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _normalize_preview(*, preview: str, content: str) -> str:
    normalized_preview = preview.strip()
    if normalized_preview:
        return normalized_preview
    return content.strip()[:120]
