# RAG Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为当前 Streamlit 聊天 Demo 增加支持 `Markdown / TXT / PDF` 上传、双模式向量检索、会话级知识文件绑定和引用展示的 RAG 知识库问答能力。

**Architecture:** 在现有聊天链路外新增独立的知识库服务层，负责文件落盘、文本解析、切分、向量化、索引和检索，再把召回片段以受控方式注入聊天上下文。默认使用本地轻量向量化，若模型配置补充 Embedding 配置则可切换到远端 Embedding，但两种模式共享统一的知识库仓储和 UI 入口。

**Tech Stack:** Python, Streamlit, PostgreSQL, OpenAI SDK, 本地文件存储, `pytest`, `ruff`

---

### Task 1: 扩展配置与模型配置结构

**Files:**
- Modify: `config.py`
- Modify: `services/model_config.py`
- Modify: `repositories/model_config_repo.py`
- Test: `tests/test_config.py`
- Test: `tests/test_service_mappers.py`

- [ ] **Step 1: 写失败测试，覆盖 RAG 配置默认值和模型 Embedding 字段映射**

```python
def test_get_rag_max_file_size_mb_uses_default_when_env_missing() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        self.assertEqual(config.get_rag_max_file_size_mb(), 10)


def test_list_model_configs_maps_embedding_fields(self) -> None:
    rows = [
        {
            "id": 1,
            "name": "OpenAI",
            "provider": "OpenAI",
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4.1",
            "temperature": 0.7,
            "max_tokens": 2048,
            "context_message_limit": 20,
            "timeout_seconds": 60.0,
            "max_retries": 2,
            "enabled": True,
            "embedding_api_key": "emb-key",
            "embedding_base_url": "https://api.openai.com/v1",
            "embedding_model_name": "text-embedding-3-small",
        }
    ]
    ...
    self.assertEqual(result[0].embedding_model_name, "text-embedding-3-small")
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_config.py tests/test_service_mappers.py -v`
Expected: FAIL，提示缺少 `get_rag_max_file_size_mb` 或 `embedding_*` 字段映射

- [ ] **Step 3: 以最小实现补齐配置读取与模型配置字段**

```python
DEFAULT_RAG_MAX_FILE_SIZE_MB = 10
DEFAULT_RAG_MAX_CHUNKS_PER_FILE = 200
DEFAULT_RAG_TOP_K = 4


def get_rag_max_file_size_mb() -> int:
    return _clamp_int(_get_int_env("RAG_MAX_FILE_SIZE_MB", DEFAULT_RAG_MAX_FILE_SIZE_MB), 1, 100)
```

```python
@dataclass(frozen=True)
class ModelConfig:
    ...
    embedding_api_key: str
    embedding_base_url: str
    embedding_model_name: str
```

- [ ] **Step 4: 更新仓储 schema 和读写 SQL**

```python
cursor.execute(
    """
    ALTER TABLE model_configs
    ADD COLUMN IF NOT EXISTS embedding_api_key TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS embedding_base_url TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS embedding_model_name TEXT NOT NULL DEFAULT ''
    """
)
```

- [ ] **Step 5: 重新运行测试，确认通过**

Run: `pytest tests/test_config.py tests/test_service_mappers.py -v`
Expected: PASS


### Task 2: 实现文档解析与文本切分

**Files:**
- Create: `services/document_loader.py`
- Create: `services/text_chunker.py`
- Modify: `requirements.txt`
- Test: `tests/test_document_loader.py`
- Test: `tests/test_text_chunker.py`

- [ ] **Step 1: 写失败测试，覆盖 `md/txt/pdf` 解析和重叠切分**

```python
def test_load_text_document_reads_utf8_text() -> None:
    path.write_text("第一段\\n第二段", encoding="utf-8")
    result = load_document(path)
    assert result.file_type == "txt"
    assert "第一段" in result.content


def test_chunk_text_builds_overlap_windows() -> None:
    text = "A" * 900 + "B" * 900
    chunks = chunk_text(text, chunk_size=1000, overlap=150)
    assert len(chunks) == 2
    assert chunks[0].char_end > chunks[1].char_start
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_document_loader.py tests/test_text_chunker.py -v`
Expected: FAIL，提示缺少模块或函数

- [ ] **Step 3: 增加 PDF 文本抽取依赖并实现解析器**

```python
from pypdf import PdfReader


def load_document(path: Path) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        content = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if not content:
            raise DocumentLoadError("PDF 暂无法解析文本。")
        return LoadedDocument(...)
```

- [ ] **Step 4: 实现固定窗口加重叠切分**

```python
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[TextChunk]:
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        content = text[start:end].strip()
        ...
        start = max(end - overlap, start + 1)
```

- [ ] **Step 5: 重新运行测试，确认通过**

Run: `pytest tests/test_document_loader.py tests/test_text_chunker.py -v`
Expected: PASS


### Task 3: 实现双模式向量化

**Files:**
- Create: `services/embeddings.py`
- Test: `tests/test_embeddings.py`

- [ ] **Step 1: 写失败测试，覆盖本地向量化、远端 Embedding 和模式选择**

```python
def test_local_embedder_returns_repeatable_vectors() -> None:
    embedder = LocalEmbeddingProvider()
    result = embedder.embed_texts(["alpha beta", "alpha gamma"])
    assert len(result) == 2
    assert len(result[0]) == len(result[1])


def test_build_embedding_provider_prefers_remote_when_config_complete() -> None:
    config = ModelConfigInput(..., embedding_api_key="emb-key", embedding_base_url="https://api.openai.com/v1", embedding_model_name="text-embedding-3-small")
    provider = build_embedding_provider(config)
    assert provider.mode == "remote"
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_embeddings.py -v`
Expected: FAIL，提示缺少 provider 实现

- [ ] **Step 3: 实现本地轻量向量提供器**

```python
class LocalEmbeddingProvider:
    mode = "local"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vocabulary = sorted({token for text in texts for token in tokenize(text)})
        return [build_tf_vector(text, vocabulary) for text in texts]
```

- [ ] **Step 4: 实现远端 Embedding 提供器和选择逻辑**

```python
def build_embedding_provider(config: ModelConfig | ModelConfigInput):
    if config.embedding_api_key.strip() and config.embedding_model_name.strip():
        return RemoteEmbeddingProvider(...)
    return LocalEmbeddingProvider()
```

- [ ] **Step 5: 重新运行测试，确认通过**

Run: `pytest tests/test_embeddings.py -v`
Expected: PASS


### Task 4: 实现知识库仓储与表初始化

**Files:**
- Create: `repositories/knowledge_base_repo.py`
- Create: `services/knowledge_base.py`
- Test: `tests/test_knowledge_base.py`

- [ ] **Step 1: 写失败测试，覆盖表初始化、文件去重和会话绑定**

```python
def test_register_knowledge_file_reuses_same_hash(...) -> None:
    first_id = register_knowledge_file(...)
    second_id = register_knowledge_file(...)
    assert first_id == second_id


def test_link_session_knowledge_file_creates_mapping(...) -> None:
    link_session_knowledge_file("postgresql://demo", session_id=1, file_id=2)
    rows = ...
    assert rows[0]["session_id"] == 1
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_knowledge_base.py -v`
Expected: FAIL，提示缺少仓储或初始化逻辑

- [ ] **Step 3: 新增知识库表初始化与基础仓储函数**

```python
CREATE TABLE IF NOT EXISTS knowledge_files (...);
CREATE TABLE IF NOT EXISTS knowledge_chunks (...);
CREATE TABLE IF NOT EXISTS session_knowledge_files (...);
```

```python
def create_knowledge_file(...): ...
def insert_knowledge_chunks(...): ...
def link_session_knowledge_file(...): ...
def list_session_knowledge_files(...): ...
```

- [ ] **Step 4: 在服务层封装文件注册、切块保存和会话绑定**

```python
def ingest_knowledge_file(database_url: str, session_id: int, upload_name: str, raw_bytes: bytes, ...):
    saved_path = save_uploaded_file(...)
    document = load_document(saved_path)
    chunks = chunk_text(document.content, ...)
    vectors = provider.embed_texts([chunk.content for chunk in chunks])
    ...
```

- [ ] **Step 5: 重新运行测试，确认通过**

Run: `pytest tests/test_knowledge_base.py -v`
Expected: PASS


### Task 5: 实现检索与引用来源组装

**Files:**
- Modify: `services/knowledge_base.py`
- Create: `utils/rag_view_helpers.py`
- Test: `tests/test_knowledge_base.py`
- Test: `tests/test_view_helpers.py`

- [ ] **Step 1: 写失败测试，覆盖 top-k 检索、无命中回退和引用格式化**

```python
def test_search_knowledge_chunks_returns_top_matches(...) -> None:
    result = search_knowledge_chunks(...)
    assert result[0].file_name == "manual.md"
    assert result[0].chunk_index == 1


def test_format_rag_sources_builds_multiline_label() -> None:
    label = format_rag_sources([...])
    assert "manual.md#1" in label
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_knowledge_base.py tests/test_view_helpers.py -v`
Expected: FAIL，提示缺少检索或格式化逻辑

- [ ] **Step 3: 实现向量相似度检索**

```python
def cosine_similarity(left: list[float], right: list[float]) -> float:
    ...


def search_knowledge_chunks(..., top_k: int) -> list[KnowledgeSearchHit]:
    query_vector = provider.embed_texts([query])[0]
    ranked_hits = sorted(candidates, key=lambda item: item.score, reverse=True)
    return [hit for hit in ranked_hits if hit.score > 0][:top_k]
```

- [ ] **Step 4: 实现引用来源与 RAG 上下文组装**

```python
def build_rag_context(hits: list[KnowledgeSearchHit]) -> str:
    return "\n\n".join(
        f"[资料 {index}] 文件：{hit.file_name}，片段：{hit.chunk_index}\n{hit.content}"
        for index, hit in enumerate(hits, start=1)
    )
```

- [ ] **Step 5: 重新运行测试，确认通过**

Run: `pytest tests/test_knowledge_base.py tests/test_view_helpers.py -v`
Expected: PASS


### Task 6: 把 RAG 集成进聊天主链路

**Files:**
- Modify: `services/session.py`
- Modify: `app.py`
- Modify: `state/session_state.py`
- Test: `tests/test_llm_logic.py`
- Test: `tests/test_session_state.py`
- Test: `tests/test_knowledge_base.py`

- [ ] **Step 1: 写失败测试，覆盖“有命中时注入知识上下文”和“无命中时回退普通聊天”**

```python
def test_build_model_messages_appends_rag_context_when_hits_exist() -> None:
    messages = build_model_messages("系统提示", history, rag_context="资料块")
    assert "资料块" in messages[0]["content"]


def test_build_model_messages_keeps_plain_prompt_when_no_rag_context() -> None:
    messages = build_model_messages("系统提示", history, rag_context="")
    assert messages[0]["content"] == "系统提示"
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_llm_logic.py tests/test_knowledge_base.py tests/test_session_state.py -v`
Expected: FAIL，提示现有消息构造不支持 RAG 上下文

- [ ] **Step 3: 扩展会话状态与消息组装逻辑**

```python
def build_model_messages(system_prompt: str, messages: list[ChatMessage], rag_context: str = "") -> list[Message]:
    prompt = system_prompt.strip() or DEFAULT_SYSTEM_PROMPT
    if rag_context.strip():
        prompt = f"{prompt}\n\n## 参考资料\n{rag_context}"
    return [{"role": "system", "content": prompt}, ...]
```

- [ ] **Step 4: 在 `app.py` 中接入检索、日志和引用来源**

```python
rag_result = retrieve_session_knowledge_context(...)
conversation_messages = build_model_messages(system_prompt, messages, rag_result.context)
answer_source = format_answer_source(base_source=answer_source, rag_sources=rag_result.sources)
```

- [ ] **Step 5: 重新运行测试，确认通过**

Run: `pytest tests/test_llm_logic.py tests/test_knowledge_base.py tests/test_session_state.py -v`
Expected: PASS


### Task 7: 增加知识库管理 UI

**Files:**
- Modify: `pages/settings_dialog.py`
- Modify: `ui/components.py`
- Modify: `ui/styles.py`
- Possibly Create: `pages/knowledge_base_panel.py`
- Test: `tests/test_view_helpers.py`

- [ ] **Step 1: 写失败测试，覆盖文件标签、引用展示和模式说明**

```python
def test_knowledge_file_label_includes_chunk_count() -> None:
    label = knowledge_file_label(file_name="manual.pdf", file_type="pdf", chunk_count=12)
    assert label == "manual.pdf · PDF · 12 片段"
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_view_helpers.py -v`
Expected: FAIL，提示缺少知识库视图辅助函数

- [ ] **Step 3: 在设置弹窗增加知识库 tab 和上传/绑定入口**

```python
knowledge_tab, prompt_tab, model_tab = st.tabs(["知识库", "提示词", "模型"])

uploaded_files = st.file_uploader(
    "上传知识文件",
    type=["md", "txt", "pdf"],
    accept_multiple_files=True,
)
enable_rag = st.checkbox("本会话启用知识库问答", value=...)
embedding_mode = st.radio("向量模式", ["本地", "远端"], ...)
```

- [ ] **Step 4: 增加当前会话文件列表和引用展示样式**

```python
for file in session_knowledge_files:
    st.caption(knowledge_file_label(...))
    if st.button("移除", key=f"unlink_knowledge_{file.id}"):
        unlink_session_knowledge_file(...)
```

- [ ] **Step 5: 重新运行测试，确认通过**

Run: `pytest tests/test_view_helpers.py -v`
Expected: PASS


### Task 8: 完整回归与文档更新

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/remaining-optimizations.md`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写失败测试或断言，覆盖新增 RAG 环境变量默认值**

```python
def test_get_rag_top_k_clamps_to_default_for_invalid_value() -> None:
    with mock.patch.dict(os.environ, {"RAG_TOP_K": "oops"}, clear=True):
        assert config.get_rag_top_k() == config.DEFAULT_RAG_TOP_K
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL，提示缺少 RAG 配置读取

- [ ] **Step 3: 更新示例环境变量、README 和剩余清单**

```text
RAG_MAX_FILE_SIZE_MB=10
RAG_MAX_CHUNKS_PER_FILE=200
RAG_TOP_K=4
```

- [ ] **Step 4: 运行全量验证**

Run: `pytest`
Expected: PASS，全量测试通过

Run: `ruff check .`
Expected: PASS，无 lint 错误

- [ ] **Step 5: 手动验证主要链路**

Run: `streamlit run app.py`
Expected: 页面可上传 `md/txt/pdf`，能绑定到当前会话，提问后能看到引用来源；无命中时正常回退普通聊天
