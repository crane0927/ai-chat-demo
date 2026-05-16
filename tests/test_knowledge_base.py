from dataclasses import dataclass
from pathlib import Path
import tempfile
from unittest import mock
import unittest

from repositories import knowledge_base_repo
from services.knowledge_base import (
    build_rag_context,
    IngestKnowledgeFileResult,
    KnowledgeSearchHit,
    delete_knowledge_file,
    KnowledgeBaseStorageError,
    ingest_knowledge_file,
    init_knowledge_base_db,
    link_session_knowledge_file,
    register_knowledge_file,
    retrieve_session_knowledge_context,
    search_knowledge_chunks,
    update_knowledge_file_storage_path,
)
from services.embeddings import EmbeddingProviderError
from services.model_config import ModelConfigInput
from services.text_chunker import TextChunk


class _FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None, rowcount: int = 1) -> None:
        self.executed: list[tuple[str, tuple | None]] = []
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.rowcount = rowcount

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params=None) -> None:
        self.executed.append((sql, params))

    def fetchone(self):
        if self._fetchone_results:
            return self._fetchone_results.pop(0)
        return None

    def fetchall(self):
        if self._fetchall_results:
            return self._fetchall_results.pop(0)
        return []


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cursor


class _KnowledgeBaseStatefulCursor(_FakeCursor):
    def __init__(self, state: dict) -> None:
        super().__init__()
        self._state = state
        self._fetchall_result: list[dict] = []

    def execute(self, sql: str, params=None) -> None:
        super().execute(sql, params)
        normalized_sql = " ".join(sql.split())
        if normalized_sql.startswith(
            "INSERT INTO session_knowledge_files (session_id, file_id)"
        ):
            session_id, file_id = params
            mapping = {"session_id": session_id, "file_id": file_id}
            if mapping not in self._state["links"]:
                self._state["links"].append(mapping)
            return

        if "FROM session_knowledge_files AS skf" in normalized_sql:
            session_id = params[0]
            self._fetchall_result = []
            for link in self._state["links"]:
                if link["session_id"] != session_id:
                    continue
                file_row = self._state["files"][link["file_id"]]
                self._fetchall_result.append(
                    {
                        "session_id": session_id,
                        "id": file_row["id"],
                        "filename": file_row["filename"],
                        "file_type": file_row["file_type"],
                        "storage_path": file_row["storage_path"],
                        "content_hash": file_row["content_hash"],
                        "file_size": file_row["file_size"],
                        "chunk_count": file_row["chunk_count"],
                        "embedding_mode": file_row["embedding_mode"],
                    }
                )

    def fetchall(self):
        return list(self._fetchall_result)


class _FakeProvider:
    mode = "local"

    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return self._vectors


@dataclass(frozen=True)
class _FakeLoadedDocument:
    file_type: str
    content: str


class KnowledgeBaseRepositoryTestCase(unittest.TestCase):
    def test_init_knowledge_base_db_creates_required_tables(self) -> None:
        cursor = _FakeCursor()
        connection = _FakeConnection(cursor)

        with mock.patch(
            "repositories.knowledge_base_repo.connect",
            return_value=connection,
        ):
            knowledge_base_repo.init_knowledge_base_db(
                "postgresql://demo",
                RuntimeError,
            )

        executed_sql = "\n".join(sql for sql, _ in cursor.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS knowledge_files", executed_sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS knowledge_chunks", executed_sql)
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS session_knowledge_files", executed_sql
        )
        self.assertIn(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_files_content_hash",
            executed_sql,
        )

    def test_link_session_knowledge_file_mapping_can_be_queried_back(self) -> None:
        state = {
            "files": {
                7: {
                    "id": 7,
                    "filename": "manual.md",
                    "file_type": "md",
                    "storage_path": "/tmp/7/manual.md",
                    "content_hash": "hash-7",
                    "file_size": 128,
                    "chunk_count": 2,
                    "embedding_mode": "local",
                }
            },
            "links": [],
        }
        cursor = _KnowledgeBaseStatefulCursor(state)
        connection = _FakeConnection(cursor)

        with mock.patch(
            "repositories.knowledge_base_repo.connect",
            return_value=connection,
        ):
            knowledge_base_repo.link_session_knowledge_file(
                "postgresql://demo",
                RuntimeError,
                session_id=3,
                file_id=7,
            )
            rows = knowledge_base_repo.list_session_knowledge_file_rows(
                "postgresql://demo",
                RuntimeError,
                session_id=3,
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_id"], 3)
        self.assertEqual(rows[0]["id"], 7)
        self.assertEqual(rows[0]["filename"], "manual.md")

    def test_update_knowledge_file_storage_path_raises_when_row_not_found(self) -> None:
        cursor = _FakeCursor(rowcount=0)
        connection = _FakeConnection(cursor)

        with mock.patch(
            "repositories.knowledge_base_repo.connect",
            return_value=connection,
        ):
            with self.assertRaisesRegex(RuntimeError, "知识文件不存在"):
                knowledge_base_repo.update_knowledge_file_storage_path(
                    "postgresql://demo",
                    RuntimeError,
                    file_id=999,
                    storage_path="/tmp/999/manual.md",
                )

    def test_delete_knowledge_file_executes_delete_sql(self) -> None:
        cursor = _FakeCursor()
        connection = _FakeConnection(cursor)

        with mock.patch(
            "repositories.knowledge_base_repo.connect",
            return_value=connection,
        ):
            knowledge_base_repo.delete_knowledge_file(
                "postgresql://demo",
                RuntimeError,
                file_id=23,
            )

        self.assertIn("DELETE FROM knowledge_files WHERE id = %s", cursor.executed[0][0])
        self.assertEqual(cursor.executed[0][1], (23,))


class KnowledgeBaseServiceTestCase(unittest.TestCase):
    def test_search_knowledge_chunks_returns_top_matches(self) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        provider = _FakeProvider([[1.0, 0.0]])

        with mock.patch(
            "services.knowledge_base.build_embedding_provider",
            return_value=provider,
        ):
            with mock.patch.object(
                knowledge_base_repo,
                "list_session_knowledge_chunk_rows",
                return_value=[
                    {
                        "file_id": 10,
                        "filename": "manual.md",
                        "chunk_index": 1,
                        "content": "与部署相关的操作说明",
                        "preview": "部署说明",
                        "embedding_vector": "[0.95, 0.05]",
                    },
                    {
                        "file_id": 11,
                        "filename": "faq.txt",
                        "chunk_index": 0,
                        "content": "常见错误排查",
                        "preview": "错误排查",
                        "embedding_vector": "[0.4, 0.3]",
                    },
                    {
                        "file_id": 12,
                        "filename": "noise.txt",
                        "chunk_index": 3,
                        "content": "无关资料",
                        "preview": "无关资料",
                        "embedding_vector": "[-1.0, 0.0]",
                    },
                ],
            ):
                result = search_knowledge_chunks(
                    "postgresql://demo",
                    session_id=5,
                    query="怎么部署",
                    model_config=config,
                    top_k=2,
                )

        self.assertEqual(provider.calls, [["怎么部署"]])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].file_id, 10)
        self.assertEqual(result[0].filename, "manual.md")
        self.assertEqual(result[0].chunk_index, 1)
        self.assertGreater(result[0].score, result[1].score)
        self.assertNotIn("noise.txt", [hit.filename for hit in result])

    def test_search_knowledge_chunks_returns_empty_when_no_positive_hit(self) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )

        with mock.patch(
            "services.knowledge_base.build_embedding_provider",
            return_value=_FakeProvider([[1.0, 0.0]]),
        ):
            with mock.patch.object(
                knowledge_base_repo,
                "list_session_knowledge_chunk_rows",
                return_value=[
                    {
                        "file_id": 10,
                        "filename": "manual.md",
                        "chunk_index": 1,
                        "content": "与部署相关的操作说明",
                        "preview": "部署说明",
                        "embedding_vector": "[0.0, 1.0]",
                    },
                    {
                        "file_id": 11,
                        "filename": "faq.txt",
                        "chunk_index": 0,
                        "content": "常见错误排查",
                        "preview": "错误排查",
                        "embedding_vector": "[-1.0, 0.0]",
                    },
                ],
            ):
                result = search_knowledge_chunks(
                    "postgresql://demo",
                    session_id=5,
                    query="怎么部署",
                    model_config=config,
                    top_k=4,
                )

        self.assertEqual(result, [])

    def test_search_knowledge_chunks_wraps_embedding_error_as_storage_error(self) -> None:
        config = ModelConfigInput(
            name="Remote",
            provider="OpenAI",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="emb-key",
            embedding_base_url="https://emb.example.com/v1",
            embedding_model_name="text-embedding-3-small",
        )

        with mock.patch(
            "services.knowledge_base.build_embedding_provider",
            side_effect=EmbeddingProviderError("Embedding 服务调用失败，请稍后重试或检查配置。"),
        ):
            with self.assertRaisesRegex(
                KnowledgeBaseStorageError,
                "Embedding 服务调用失败，请稍后重试或检查配置。",
            ):
                search_knowledge_chunks(
                    "postgresql://demo",
                    session_id=5,
                    query="怎么部署",
                    model_config=config,
                    top_k=4,
                )

    def test_build_rag_context_outputs_stable_multiblock_text(self) -> None:
        result = build_rag_context(
            [
                KnowledgeSearchHit(
                    file_id=10,
                    filename="manual.md",
                    chunk_index=1,
                    content="第一段资料",
                    preview="第一段",
                    score=0.91,
                ),
                KnowledgeSearchHit(
                    file_id=11,
                    filename="faq.txt",
                    chunk_index=0,
                    content="第二段资料",
                    preview="第二段",
                    score=0.67,
                ),
            ]
        )

        self.assertEqual(
            result,
            "\n\n".join(
                [
                    "[参考资料 1]\n来源：manual.md#1\n相关度：0.9100\n内容：\n第一段资料",
                    "[参考资料 2]\n来源：faq.txt#0\n相关度：0.6700\n内容：\n第二段资料",
                ]
            ),
        )

    def test_retrieve_session_knowledge_context_builds_context_and_sources(self) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )

        with mock.patch(
            "services.knowledge_base.search_knowledge_chunks",
            return_value=[
                KnowledgeSearchHit(
                    file_id=10,
                    filename="manual.md",
                    chunk_index=1,
                    content="第一段资料",
                    preview="第一段",
                    score=0.91,
                )
            ],
        ):
            result = retrieve_session_knowledge_context(
                "postgresql://demo",
                session_id=5,
                query="怎么部署",
                model_config=config,
                top_k=4,
            )

        self.assertEqual(result.hits[0].filename, "manual.md")
        self.assertIn("manual.md#1", result.context)
        self.assertIn("manual.md#1", result.sources)

    def test_register_knowledge_file_reuses_same_hash(self) -> None:
        with mock.patch.object(
            knowledge_base_repo,
            "get_knowledge_file_by_hash_row",
            side_effect=[
                None,
                {
                    "id": 11,
                    "content_hash": "same-hash",
                    "storage_path": "/tmp/11/demo.txt",
                },
            ],
        ) as get_by_hash_mock:
            with mock.patch.object(
                knowledge_base_repo,
                "create_knowledge_file",
                return_value=11,
            ) as create_mock:
                first_id = register_knowledge_file(
                    "postgresql://demo",
                    filename="demo.txt",
                    file_type="txt",
                    storage_path="/tmp/demo.txt",
                    content_hash="same-hash",
                    file_size=8,
                    chunk_count=2,
                    embedding_mode="local",
                )
                second_id = register_knowledge_file(
                    "postgresql://demo",
                    filename="demo.txt",
                    file_type="txt",
                    storage_path="/tmp/demo.txt",
                    content_hash="same-hash",
                    file_size=8,
                    chunk_count=2,
                    embedding_mode="local",
                )

        self.assertEqual(first_id, 11)
        self.assertEqual(second_id, 11)
        self.assertEqual(get_by_hash_mock.call_count, 2)
        create_mock.assert_called_once()

    def test_register_knowledge_file_returns_existing_id_after_unique_conflict(self) -> None:
        class FakeUniqueViolation(Exception):
            pass

        with mock.patch.object(
            knowledge_base_repo,
            "get_knowledge_file_by_hash_row",
            side_effect=[
                None,
                {
                    "id": 29,
                    "filename": "demo.txt",
                    "storage_path": "/tmp/29/demo.txt",
                    "chunk_count": 2,
                    "embedding_mode": "local",
                },
            ],
        ):
            with mock.patch.object(
                knowledge_base_repo,
                "create_knowledge_file",
                side_effect=FakeUniqueViolation("dup"),
            ):
                with mock.patch("db.errors.psycopg") as fake_psycopg:
                    fake_psycopg.errors.UniqueViolation = FakeUniqueViolation
                    file_id = register_knowledge_file(
                        "postgresql://demo",
                        filename="demo.txt",
                        file_type="txt",
                        storage_path="/tmp/29/demo.txt",
                        content_hash="same-hash",
                        file_size=8,
                        chunk_count=2,
                        embedding_mode="local",
                    )

        self.assertEqual(file_id, 29)

    def test_link_session_knowledge_file_creates_mapping(self) -> None:
        with mock.patch.object(
            knowledge_base_repo,
            "link_session_knowledge_file",
        ) as repo_link_mock:
            link_session_knowledge_file("postgresql://demo", session_id=3, file_id=7)

        repo_link_mock.assert_called_once_with(
            "postgresql://demo",
            KnowledgeBaseStorageError,
            session_id=3,
            file_id=7,
        )

    def test_ingest_knowledge_file_orchestrates_parse_chunk_embed_store_and_link(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        loaded_document = _FakeLoadedDocument(file_type="md", content="第一段\n第二段")
        chunks = [
            TextChunk(
                chunk_index=0,
                content="第一段",
                preview="第一段",
                char_start=0,
                char_end=3,
            ),
            TextChunk(
                chunk_index=1,
                content="第二段",
                preview="第二段",
                char_start=4,
                char_end=7,
            ),
        ]
        provider = _FakeProvider([[0.1, 0.2], [0.3, 0.4]])

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            with mock.patch(
                "services.knowledge_base.load_document",
                return_value=loaded_document,
            ):
                with mock.patch(
                    "services.knowledge_base.chunk_text",
                    return_value=chunks,
                ) as chunk_mock:
                    with mock.patch(
                        "services.knowledge_base.build_embedding_provider",
                        return_value=provider,
                    ) as provider_builder_mock:
                        with mock.patch.object(
                            knowledge_base_repo,
                            "get_knowledge_file_by_hash_row",
                            return_value=None,
                        ):
                            with mock.patch(
                                "services.knowledge_base.register_knowledge_file",
                                return_value=23,
                            ) as register_mock:
                                with mock.patch(
                                    "services.knowledge_base.update_knowledge_file_storage_path"
                                ) as update_path_mock:
                                    with mock.patch(
                                        "services.knowledge_base.replace_knowledge_chunks",
                                    ) as replace_chunks_mock:
                                        with mock.patch(
                                            "services.knowledge_base.link_session_knowledge_file",
                                        ) as link_mock:
                                            result = ingest_knowledge_file(
                                                "postgresql://demo",
                                                session_id=5,
                                                upload_name="guide.md",
                                                raw_bytes="你好，知识库".encode("utf-8"),
                                                model_config=config,
                                                storage_dir=storage_dir,
                                            )
                                            saved_path = storage_dir / "23" / "guide.md"
                                            staging_path = storage_dir / "__staging__" / "guide.md"
                                            self.assertTrue(saved_path.exists())
                                            self.assertFalse(staging_path.exists())
                                            self.assertEqual(
                                                saved_path.read_bytes(),
                                                "你好，知识库".encode("utf-8"),
                                            )

        self.assertEqual(
            result,
            IngestKnowledgeFileResult(
                file_id=23,
                session_id=5,
                filename="guide.md",
                chunk_count=2,
                embedding_mode="local",
            ),
        )
        chunk_mock.assert_called_once_with("第一段\n第二段")
        provider_builder_mock.assert_called_once_with(config)
        self.assertEqual(provider.calls, [["第一段", "第二段"]])
        register_payload = register_mock.call_args.kwargs
        self.assertEqual(register_payload["filename"], "guide.md")
        self.assertEqual(register_payload["file_type"], "md")
        self.assertEqual(register_payload["chunk_count"], 2)
        self.assertEqual(register_payload["embedding_mode"], "local")
        self.assertEqual(len(register_payload["content_hash"]), 64)
        update_path_mock.assert_called_once_with(
            "postgresql://demo",
            file_id=23,
            storage_path=str(storage_dir / "23" / "guide.md"),
        )
        replace_chunks_mock.assert_called_once()
        stored_chunks = replace_chunks_mock.call_args.kwargs["chunks"]
        self.assertEqual(stored_chunks[0]["embedding_vector"], [0.1, 0.2])
        self.assertEqual(stored_chunks[1]["chunk_index"], 1)
        link_mock.assert_called_once_with("postgresql://demo", session_id=5, file_id=23)

    def test_ingest_knowledge_file_does_not_overwrite_same_name_different_content(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        provider = _FakeProvider([[0.1, 0.2]])

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            with mock.patch(
                "services.knowledge_base.load_document",
                return_value=_FakeLoadedDocument(file_type="txt", content="第一版"),
            ):
                with mock.patch(
                    "services.knowledge_base.chunk_text",
                    return_value=[
                        TextChunk(
                            chunk_index=0,
                            content="第一版",
                            preview="第一版",
                            char_start=0,
                            char_end=3,
                        )
                    ],
                ):
                    with mock.patch(
                        "services.knowledge_base.build_embedding_provider",
                        return_value=provider,
                    ):
                        with mock.patch.object(
                            knowledge_base_repo,
                            "get_knowledge_file_by_hash_row",
                            side_effect=[None, None],
                        ):
                            with mock.patch(
                                "services.knowledge_base.register_knowledge_file",
                                side_effect=[23, 24],
                            ):
                                with mock.patch(
                                    "services.knowledge_base.update_knowledge_file_storage_path"
                                ):
                                    with mock.patch(
                                        "services.knowledge_base.replace_knowledge_chunks"
                                    ):
                                        with mock.patch(
                                            "services.knowledge_base.link_session_knowledge_file"
                                        ):
                                            ingest_knowledge_file(
                                                "postgresql://demo",
                                                session_id=5,
                                                upload_name="guide.txt",
                                                raw_bytes="第一版".encode("utf-8"),
                                                model_config=config,
                                                storage_dir=storage_dir,
                                            )
                                            ingest_knowledge_file(
                                                "postgresql://demo",
                                                session_id=5,
                                                upload_name="guide.txt",
                                                raw_bytes="第二版".encode("utf-8"),
                                                model_config=config,
                                                storage_dir=storage_dir,
                                            )
                                            self.assertEqual(
                                                (storage_dir / "23" / "guide.txt").read_bytes(),
                                                "第一版".encode("utf-8"),
                                            )
                                            self.assertEqual(
                                                (storage_dir / "24" / "guide.txt").read_bytes(),
                                                "第二版".encode("utf-8"),
                                            )

    def test_ingest_knowledge_file_reuses_ready_file_without_rewriting_or_reembedding(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        existing_row = {
            "id": 41,
            "filename": "guide.md",
            "storage_path": "/tmp/41/guide.md",
            "chunk_count": 2,
            "embedding_mode": "local",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            with mock.patch.object(
                knowledge_base_repo,
                "get_knowledge_file_by_hash_row",
                return_value=existing_row,
            ):
                with mock.patch(
                    "services.knowledge_base.load_document",
                    side_effect=AssertionError("should not load document"),
                ):
                    with mock.patch(
                        "services.knowledge_base.chunk_text",
                        side_effect=AssertionError("should not chunk"),
                    ):
                        with mock.patch(
                            "services.knowledge_base.build_embedding_provider",
                            side_effect=AssertionError("should not build provider"),
                        ):
                            with mock.patch(
                                "services.knowledge_base.link_session_knowledge_file"
                            ) as link_mock:
                                result = ingest_knowledge_file(
                                    "postgresql://demo",
                                    session_id=5,
                                    upload_name="guide.md",
                                    raw_bytes="你好，知识库".encode("utf-8"),
                                    model_config=config,
                                    storage_dir=storage_dir,
                                )

        self.assertEqual(result.file_id, 41)
        self.assertFalse((storage_dir / "__staging__" / "guide.md").exists())
        link_mock.assert_called_once_with("postgresql://demo", session_id=5, file_id=41)

    def test_ingest_knowledge_file_cleans_staging_and_final_file_when_update_storage_path_fails(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        provider = _FakeProvider([[0.1, 0.2]])

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            with mock.patch(
                "services.knowledge_base.load_document",
                return_value=_FakeLoadedDocument(file_type="txt", content="正文"),
            ):
                with mock.patch(
                    "services.knowledge_base.chunk_text",
                    return_value=[
                        TextChunk(
                            chunk_index=0,
                            content="正文",
                            preview="正文",
                            char_start=0,
                            char_end=2,
                        )
                    ],
                ):
                    with mock.patch(
                        "services.knowledge_base.build_embedding_provider",
                        return_value=provider,
                    ):
                        with mock.patch.object(
                            knowledge_base_repo,
                            "get_knowledge_file_by_hash_row",
                            return_value=None,
                        ):
                            with mock.patch(
                                "services.knowledge_base.register_knowledge_file",
                                return_value=23,
                            ):
                                with mock.patch(
                                    "services.knowledge_base.update_knowledge_file_storage_path",
                                    side_effect=KnowledgeBaseStorageError("路径更新失败"),
                                ):
                                    with self.assertRaisesRegex(
                                        KnowledgeBaseStorageError, "路径更新失败"
                                    ):
                                        ingest_knowledge_file(
                                            "postgresql://demo",
                                            session_id=5,
                                            upload_name="guide.txt",
                                            raw_bytes="正文".encode("utf-8"),
                                            model_config=config,
                                            storage_dir=storage_dir,
                                        )

            self.assertFalse((storage_dir / "__staging__" / "guide.txt").exists())
            self.assertFalse((storage_dir / "23" / "guide.txt").exists())

    def test_ingest_knowledge_file_cleans_final_file_when_replace_chunks_fails(self) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        provider = _FakeProvider([[0.1, 0.2]])

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            with mock.patch(
                "services.knowledge_base.load_document",
                return_value=_FakeLoadedDocument(file_type="txt", content="正文"),
            ):
                with mock.patch(
                    "services.knowledge_base.chunk_text",
                    return_value=[
                        TextChunk(
                            chunk_index=0,
                            content="正文",
                            preview="正文",
                            char_start=0,
                            char_end=2,
                        )
                    ],
                ):
                    with mock.patch(
                        "services.knowledge_base.build_embedding_provider",
                        return_value=provider,
                    ):
                        with mock.patch.object(
                            knowledge_base_repo,
                            "get_knowledge_file_by_hash_row",
                            return_value=None,
                        ):
                            with mock.patch(
                                "services.knowledge_base.register_knowledge_file",
                                return_value=23,
                            ):
                                with mock.patch(
                                    "services.knowledge_base.update_knowledge_file_storage_path"
                                ):
                                    with mock.patch(
                                        "services.knowledge_base.replace_knowledge_chunks",
                                        side_effect=KnowledgeBaseStorageError("分块失败"),
                                    ):
                                        with self.assertRaisesRegex(
                                            KnowledgeBaseStorageError, "分块失败"
                                        ):
                                            ingest_knowledge_file(
                                                "postgresql://demo",
                                                session_id=5,
                                                upload_name="guide.txt",
                                                raw_bytes="正文".encode("utf-8"),
                                                model_config=config,
                                                storage_dir=storage_dir,
                                            )

            self.assertFalse((storage_dir / "__staging__" / "guide.txt").exists())
            self.assertFalse((storage_dir / "23" / "guide.txt").exists())

    def test_update_knowledge_file_storage_path_delegates_to_repository(self) -> None:
        with mock.patch.object(
            knowledge_base_repo, "update_knowledge_file_storage_path"
        ) as update_mock:
            update_knowledge_file_storage_path(
                "postgresql://demo",
                file_id=23,
                storage_path="/tmp/23/guide.txt",
            )

        update_mock.assert_called_once_with(
            "postgresql://demo",
            KnowledgeBaseStorageError,
            file_id=23,
            storage_path="/tmp/23/guide.txt",
        )

    def test_delete_knowledge_file_delegates_to_repository(self) -> None:
        with mock.patch.object(knowledge_base_repo, "delete_knowledge_file") as delete_mock:
            delete_knowledge_file("postgresql://demo", file_id=23)

        delete_mock.assert_called_once_with(
            "postgresql://demo",
            KnowledgeBaseStorageError,
            file_id=23,
        )

    def test_ingest_knowledge_file_retry_succeeds_after_registered_file_is_cleaned_up(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        provider = _FakeProvider([[0.1, 0.2]])

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            with mock.patch(
                "services.knowledge_base.load_document",
                return_value=_FakeLoadedDocument(file_type="txt", content="正文"),
            ):
                with mock.patch(
                    "services.knowledge_base.chunk_text",
                    return_value=[
                        TextChunk(
                            chunk_index=0,
                            content="正文",
                            preview="正文",
                            char_start=0,
                            char_end=2,
                        )
                    ],
                ):
                    with mock.patch(
                        "services.knowledge_base.build_embedding_provider",
                        return_value=provider,
                    ):
                        with mock.patch.object(
                            knowledge_base_repo,
                            "get_knowledge_file_by_hash_row",
                            return_value=None,
                        ):
                            with mock.patch(
                                "services.knowledge_base.register_knowledge_file",
                                side_effect=[23, 24],
                            ):
                                with mock.patch(
                                    "services.knowledge_base.update_knowledge_file_storage_path",
                                    side_effect=[
                                        KnowledgeBaseStorageError("路径更新失败"),
                                        None,
                                    ],
                                ):
                                    with mock.patch(
                                        "services.knowledge_base.delete_knowledge_file"
                                    ) as delete_mock:
                                        with mock.patch(
                                            "services.knowledge_base.replace_knowledge_chunks"
                                        ) as replace_mock:
                                            with mock.patch(
                                                "services.knowledge_base.link_session_knowledge_file"
                                            ) as link_mock:
                                                with self.assertRaisesRegex(
                                                    KnowledgeBaseStorageError, "路径更新失败"
                                                ):
                                                    ingest_knowledge_file(
                                                        "postgresql://demo",
                                                        session_id=5,
                                                        upload_name="guide.txt",
                                                        raw_bytes="正文".encode("utf-8"),
                                                        model_config=config,
                                                        storage_dir=storage_dir,
                                                    )

                                                result = ingest_knowledge_file(
                                                    "postgresql://demo",
                                                    session_id=5,
                                                    upload_name="guide.txt",
                                                    raw_bytes="正文".encode("utf-8"),
                                                    model_config=config,
                                                    storage_dir=storage_dir,
                                                )

        delete_mock.assert_called_once_with("postgresql://demo", file_id=23)
        replace_mock.assert_called_once()
        link_mock.assert_called_once_with("postgresql://demo", session_id=5, file_id=24)
        self.assertEqual(result.file_id, 24)

    def test_ingest_knowledge_file_reuses_existing_registered_file_without_rewriting_artifacts(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )
        loaded_document = _FakeLoadedDocument(file_type="txt", content="正文")
        chunks = [
            TextChunk(
                chunk_index=0,
                content="正文",
                preview="正文",
                char_start=0,
                char_end=2,
            )
        ]
        provider = _FakeProvider([[0.1, 0.2]])
        existing_row = {
            "id": 41,
            "filename": "a.txt",
            "file_type": "txt",
            "storage_path": "/tmp/41/a.txt",
            "content_hash": "same-hash",
            "file_size": 6,
            "chunk_count": 1,
            "embedding_mode": "local",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            with mock.patch(
                "services.knowledge_base.load_document",
                return_value=loaded_document,
            ):
                with mock.patch(
                    "services.knowledge_base.chunk_text",
                    return_value=chunks,
                ):
                    with mock.patch(
                        "services.knowledge_base.build_embedding_provider",
                        return_value=provider,
                    ):
                        with mock.patch.object(
                            knowledge_base_repo,
                            "get_knowledge_file_by_hash_row",
                            return_value=None,
                        ):
                            with mock.patch(
                                "services.knowledge_base.register_knowledge_file",
                                return_value=(41, False),
                            ) as register_mock:
                                with mock.patch(
                                    "services.knowledge_base.update_knowledge_file_storage_path"
                                ) as update_path_mock:
                                    with mock.patch(
                                        "services.knowledge_base.replace_knowledge_chunks"
                                    ) as replace_mock:
                                        with mock.patch(
                                            "services.knowledge_base.link_session_knowledge_file"
                                        ) as link_mock:
                                            with mock.patch(
                                                "services.knowledge_base._get_knowledge_file_row_by_hash_after_register",
                                                return_value=existing_row,
                                            ):
                                                result = ingest_knowledge_file(
                                                    "postgresql://demo",
                                                    session_id=5,
                                                    upload_name="b.txt",
                                                    raw_bytes="正文".encode("utf-8"),
                                                    model_config=config,
                                                    storage_dir=storage_dir,
                                                )

        register_mock.assert_called_once()
        update_path_mock.assert_not_called()
        replace_mock.assert_not_called()
        link_mock.assert_called_once_with("postgresql://demo", session_id=5, file_id=41)
        self.assertEqual(result.file_id, 41)
        self.assertEqual(result.filename, "a.txt")
        self.assertEqual(result.chunk_count, 1)
        self.assertEqual(result.embedding_mode, "local")

    def test_init_knowledge_base_db_delegates_to_repository(self) -> None:
        with mock.patch.object(knowledge_base_repo, "init_knowledge_base_db") as init_mock:
            init_knowledge_base_db("postgresql://demo")

        init_mock.assert_called_once_with("postgresql://demo", KnowledgeBaseStorageError)


if __name__ == "__main__":
    unittest.main()
