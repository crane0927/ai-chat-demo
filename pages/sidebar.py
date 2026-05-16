import streamlit as st

from services.session import SessionStorageError, delete_session, list_sessions
from utils.exporters import (
    build_session_export_filename,
    build_session_json,
    build_session_markdown,
)


def render_sidebar(
    database_url: str,
    sessions: list,
    sessions_by_id: dict[int, object],
    current_session,
    current_session_messages: list,
) -> None:
    with st.sidebar:
        st.title("会话")
        st.caption("选择、创建、重命名和导出对话。")

        st.selectbox(
            "当前会话",
            list(sessions_by_id.keys()),
            key="active_session_selector_id",
            format_func=lambda session_id: sessions_by_id[session_id].title,
        )

        col_new, col_rename, col_del = st.columns(3)

        with col_new:
            if st.button("新建", use_container_width=True):
                st.session_state.create_session_confirming = True
                st.rerun()

        with col_rename:
            if st.button("重命名", use_container_width=True):
                st.session_state.rename_session_confirming_id = (
                    st.session_state.active_session_id
                )
                st.rerun()

        with col_del:
            if st.button("删除", disabled=len(sessions) <= 1, use_container_width=True):
                try:
                    deleting_session_id = st.session_state.active_session_id
                    delete_session(database_url, deleting_session_id)
                    remaining_sessions = list_sessions(database_url)
                    next_session_id = (
                        remaining_sessions[0].id if remaining_sessions else None
                    )
                    st.session_state.pending_active_session_id = next_session_id
                    st.rerun()
                except SessionStorageError as exc:
                    st.error(f"删除失败：{exc}")

        session_markdown = build_session_markdown(
            current_session, current_session_messages
        )
        session_json = build_session_json(current_session, current_session_messages)

        st.download_button(
            "导出 Markdown",
            data=session_markdown,
            file_name=build_session_export_filename(current_session, "md"),
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "导出 JSON",
            data=session_json,
            file_name=build_session_export_filename(current_session, "json"),
            mime="application/json",
            use_container_width=True,
        )

        st.caption(f"当前共有 {len(sessions)} 个会话。")
