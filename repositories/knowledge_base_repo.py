import json

from db.connection import connect


def init_knowledge_base_db(database_url: str, error_cls: type[Exception]) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_files (
                    id BIGSERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    file_size BIGINT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    embedding_mode TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_files_content_hash
                ON knowledge_files (content_hash)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    file_id BIGINT NOT NULL REFERENCES knowledge_files(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    embedding_vector TEXT NOT NULL,
                    char_start INTEGER NOT NULL,
                    char_end INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_file_index
                ON knowledge_chunks (file_id, chunk_index)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_knowledge_files (
                    id BIGSERIAL PRIMARY KEY,
                    session_id BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    file_id BIGINT NOT NULL REFERENCES knowledge_files(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_session_knowledge_files_unique
                ON session_knowledge_files (session_id, file_id)
                """
            )


def get_knowledge_file_by_hash_row(
    database_url: str,
    error_cls: type[Exception],
    content_hash: str,
) -> dict | None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    filename,
                    file_type,
                    storage_path,
                    content_hash,
                    file_size,
                    chunk_count,
                    embedding_mode
                FROM knowledge_files
                WHERE content_hash = %s
                """,
                (content_hash,),
            )
            return cursor.fetchone()


def create_knowledge_file(
    database_url: str,
    error_cls: type[Exception],
    payload: dict,
) -> int:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO knowledge_files (
                    filename,
                    file_type,
                    storage_path,
                    content_hash,
                    file_size,
                    chunk_count,
                    embedding_mode
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["filename"],
                    payload["file_type"],
                    payload["storage_path"],
                    payload["content_hash"],
                    payload["file_size"],
                    payload["chunk_count"],
                    payload["embedding_mode"],
                ),
            )
            return int(cursor.fetchone()["id"])


def update_knowledge_file_storage_path(
    database_url: str,
    error_cls: type[Exception],
    *,
    file_id: int,
    storage_path: str,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE knowledge_files
                SET storage_path = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (storage_path, file_id),
            )
            if cursor.rowcount == 0:
                raise error_cls("知识文件不存在，无法更新存储路径。")


def delete_knowledge_file(
    database_url: str,
    error_cls: type[Exception],
    *,
    file_id: int,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM knowledge_files WHERE id = %s", (file_id,))


def replace_knowledge_chunks(
    database_url: str,
    error_cls: type[Exception],
    *,
    file_id: int,
    chunks: list[dict],
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM knowledge_chunks WHERE file_id = %s", (file_id,))
            for chunk in chunks:
                # 向量先按 JSON 文本存储，兼容当前阶段“不引入 pgvector”的约束。
                cursor.execute(
                    """
                    INSERT INTO knowledge_chunks (
                        file_id,
                        chunk_index,
                        content,
                        preview,
                        embedding_vector,
                        char_start,
                        char_end
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        file_id,
                        chunk["chunk_index"],
                        chunk["content"],
                        chunk["preview"],
                        json.dumps(chunk["embedding_vector"], ensure_ascii=False),
                        chunk["char_start"],
                        chunk["char_end"],
                    ),
                )


def link_session_knowledge_file(
    database_url: str,
    error_cls: type[Exception],
    *,
    session_id: int,
    file_id: int,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO session_knowledge_files (session_id, file_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (session_id, file_id),
            )


def list_session_knowledge_file_rows(
    database_url: str,
    error_cls: type[Exception],
    *,
    session_id: int,
) -> list[dict]:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    skf.session_id,
                    kf.id,
                    kf.filename,
                    kf.file_type,
                    kf.storage_path,
                    kf.content_hash,
                    kf.file_size,
                    kf.chunk_count,
                    kf.embedding_mode
                FROM session_knowledge_files AS skf
                INNER JOIN knowledge_files AS kf
                    ON kf.id = skf.file_id
                WHERE skf.session_id = %s
                ORDER BY skf.id ASC
                """,
                (session_id,),
            )
            return cursor.fetchall()


def list_session_knowledge_chunk_rows(
    database_url: str,
    error_cls: type[Exception],
    *,
    session_id: int,
) -> list[dict]:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    skf.session_id,
                    kf.id AS file_id,
                    kf.filename,
                    kf.embedding_mode,
                    kc.chunk_index,
                    kc.content,
                    kc.preview,
                    kc.embedding_vector,
                    kc.char_start,
                    kc.char_end
                FROM session_knowledge_files AS skf
                INNER JOIN knowledge_files AS kf
                    ON kf.id = skf.file_id
                INNER JOIN knowledge_chunks AS kc
                    ON kc.file_id = kf.id
                WHERE skf.session_id = %s
                ORDER BY skf.id ASC, kc.chunk_index ASC
                """,
                (session_id,),
            )
            return cursor.fetchall()
