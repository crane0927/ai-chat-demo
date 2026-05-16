from html import escape
from typing import Optional

import streamlit as st

from config import APP_TITLE
from utils.request_observability import RequestObservability


def answer_source_html(source: Optional[str]) -> str:
    safe_source = escape(source or "未知来源")
    return f'<div class="answer-source-row"><span class="answer-source">回答来源：{safe_source}</span></div>'


def render_assistant_message(content: str, source: Optional[str]) -> None:
    st.markdown(content)
    st.markdown(answer_source_html(source), unsafe_allow_html=True)


def render_app_header(
    container,
    session_name: str,
    mode: str,
    model: str,
    message_count: int,
    request_observability: Optional[RequestObservability] = None,
) -> None:
    safe_session_name = escape(session_name)
    safe_model_name = escape(model.strip() or "未设置模型")
    safe_mode_label = escape(mode)
    observability_html = ""
    if request_observability is not None:
        observability_html = f"""
            <div class="observability-strip">
                <span class="status-pill">耗时 {escape(request_observability.elapsed_label)}</span>
                <span class="status-pill">{escape(request_observability.context_label)}</span>
                <span class="status-pill">{escape(request_observability.trim_label)}</span>
                <span class="status-pill">{escape(request_observability.outcome_label)}</span>
            </div>
        """

    container.markdown(
        f"""
        <section class="app-hero">
            <div>
                <p class="app-kicker">AI Chat Demo</p>
                <h1 class="app-title">{APP_TITLE}</h1>
                <p class="app-subtitle">当前会话：{safe_session_name}</p>
            </div>
            <div class="status-strip">
                <span class="status-pill"><strong>{safe_mode_label}</strong></span>
                <span class="status-pill">{safe_model_name}</span>
                <span class="status-pill">{message_count} 条消息</span>
            </div>
        </section>
        {observability_html}
        """,
        unsafe_allow_html=True,
    )
