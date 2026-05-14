from html import escape
from typing import Optional

import streamlit as st

from config import APP_TITLE


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
) -> None:
    safe_session_name = escape(session_name)
    safe_model_name = escape(model.strip() or "未设置模型")
    safe_mode_label = escape(mode)

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
        """,
        unsafe_allow_html=True,
    )
