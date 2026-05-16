import streamlit as st
from html import escape

from services.knowledge_base import (
    KnowledgeBaseStorageError,
    ingest_knowledge_file,
    list_session_knowledge_files,
)
from utils.rag_view_helpers import (
    format_knowledge_source_summary,
    knowledge_file_label,
)
from ui.components import info_card_html


def render_knowledge_base_panel(
    database_url: str,
    *,
    current_session,
    selected_model_config,
    last_retrieved_knowledge_sources: str,
) -> None:
    st.subheader("知识库")
    st.caption("上传后的知识文件只绑定到当前会话，避免不同对话场景相互污染检索结果。")

    knowledge_summary = format_knowledge_source_summary(
        last_sources=last_retrieved_knowledge_sources,
        fallback_message="上传知识文件后，系统会在当前会话内优先检索这些资料；未命中时仍会按普通聊天处理。",
    )
    st.markdown(
        info_card_html("知识库说明", knowledge_summary),
        unsafe_allow_html=True,
    )

    st.caption(_embedding_mode_caption(selected_model_config))
    uploaded_files = st.file_uploader(
        "上传知识文件",
        type=["md", "txt", "pdf"],
        accept_multiple_files=True,
        help="支持 Markdown、纯文本和可提取文本的 PDF 文件。",
        key=f"knowledge_upload_{current_session.id}",
    )

    if uploaded_files and st.button(
        "导入到当前会话",
        type="primary",
        use_container_width=True,
        key=f"ingest_knowledge_files_{current_session.id}",
    ):
        imported_labels: list[str] = []
        for uploaded_file in uploaded_files:
            try:
                result = ingest_knowledge_file(
                    database_url,
                    session_id=current_session.id,
                    upload_name=uploaded_file.name,
                    raw_bytes=uploaded_file.getvalue(),
                    model_config=selected_model_config,
                )
            except KnowledgeBaseStorageError as exc:
                st.error(f"导入 {uploaded_file.name} 失败：{exc}")
                return
            imported_labels.append(
                knowledge_file_label(
                    file_name=result.filename,
                    file_type=uploaded_file.name.rsplit(".", 1)[-1],
                    chunk_count=result.chunk_count,
                )
            )

        if imported_labels:
            st.success("已导入当前会话知识文件：")
            for label in imported_labels:
                st.caption(label)
            # 上传后立即刷新页面，确保新绑定的文件列表和 file_uploader 状态同步回到最新快照。
            st.rerun()

    session_knowledge_files = list_session_knowledge_files(
        database_url,
        session_id=current_session.id,
    )
    st.markdown("**当前会话已绑定文件**")
    if not session_knowledge_files:
        st.info("当前会话还没有绑定知识文件。")
        return

    for knowledge_file in session_knowledge_files:
        st.markdown(
            f"""
            <div class="knowledge-file-item">
                <div>
                    <div class="knowledge-file-title">
                        {escape(knowledge_file_label(knowledge_file.filename, knowledge_file.file_type, knowledge_file.chunk_count))}
                    </div>
                    <div class="knowledge-file-meta">
                        <span>向量模式：{escape(_embedding_mode_label(knowledge_file.embedding_mode))}</span>
                        <span>大小：{escape(_format_file_size(knowledge_file.file_size))}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _embedding_mode_caption(selected_model_config) -> str:
    if getattr(selected_model_config, "embedding_api_key", "").strip() and getattr(
        selected_model_config, "embedding_model_name", ""
    ).strip():
        return "当前模型已配置远端 Embedding，后续上传文件会按远端向量模式入库。"
    return "当前模型未配置远端 Embedding，后续上传文件会使用本地向量模式入库。"


def _embedding_mode_label(mode: str) -> str:
    if mode == "remote":
        return "远端"
    if mode == "local":
        return "本地"
    return mode or "未知"


def _format_file_size(file_size: int) -> str:
    if file_size < 1024:
        return f"{file_size} B"
    if file_size < 1024 * 1024:
        return f"{file_size / 1024:.1f} KB"
    return f"{file_size / (1024 * 1024):.1f} MB"
