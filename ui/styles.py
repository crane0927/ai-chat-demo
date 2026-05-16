import streamlit as st


APP_STYLES = """
<style>
    /* 使用 Streamlit 主题变量，保证浅色和深色模式下都能保持可读。 */
    :root {
        --app-bg: var(--background-color);
        --panel-bg: var(--secondary-background-color);
        --panel-border: rgba(128, 128, 128, 0.26);
        --text-main: var(--text-color);
        --text-muted: color-mix(in srgb, var(--text-color) 62%, transparent);
        --accent: var(--primary-color);
        --accent-soft: color-mix(in srgb, var(--primary-color) 16%, transparent);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, var(--accent-soft), transparent 28rem),
            linear-gradient(180deg, var(--app-bg) 0%, var(--panel-bg) 100%);
        color: var(--text-main);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        max-width: 1040px;
        padding-top: 2rem;
        padding-bottom: 6rem;
    }

    section[data-testid="stSidebar"] > div {
        background: var(--panel-bg);
        border-right: 1px solid var(--panel-border);
        padding-top: 1.6rem;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: var(--text-main);
        letter-spacing: 0;
    }

    .app-hero {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: end;
        gap: 1.25rem;
        margin-bottom: 1.4rem;
        padding-bottom: 1.2rem;
        border-bottom: 1px solid var(--panel-border);
    }

    .app-kicker {
        color: var(--accent);
        font-size: 0.82rem;
        font-weight: 700;
        margin: 0 0 0.35rem;
    }

    .app-title {
        color: var(--text-main);
        font-size: 2.3rem;
        line-height: 1.12;
        font-weight: 760;
        margin: 0;
        letter-spacing: 0;
    }

    .app-subtitle {
        color: var(--text-muted);
        font-size: 0.98rem;
        margin: 0.55rem 0 0;
    }

    .status-strip {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 0.5rem;
        min-width: 18rem;
    }

    .observability-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: -0.4rem;
        margin-bottom: 1.2rem;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.42rem 0.7rem;
        border-radius: 999px;
        border: 1px solid var(--panel-border);
        background: color-mix(in srgb, var(--panel-bg) 92%, transparent);
        color: var(--text-muted);
        font-size: 0.82rem;
        font-weight: 650;
        white-space: nowrap;
    }

    .status-pill strong {
        color: var(--text-main);
        font-weight: 760;
    }

    .empty-state {
        max-width: 560px;
        margin: 1.4rem auto 0;
        padding: 1.15rem 1.25rem;
        border: 1px solid var(--panel-border);
        border-radius: 8px;
        background: color-mix(in srgb, var(--panel-bg) 90%, transparent);
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
    }

    .empty-state h2 {
        margin: 0 0 0.4rem;
        color: var(--text-main);
        font-size: 1.05rem;
        letter-spacing: 0;
    }

    .empty-state p {
        margin: 0;
        color: var(--text-muted);
        font-size: 0.86rem;
    }

    [data-testid="stChatMessage"] {
        border: 1px solid var(--panel-border);
        border-radius: 8px;
        background: color-mix(in srgb, var(--panel-bg) 92%, transparent);
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
        padding: calc(0.85rem + 10px) 1rem;
        margin-bottom: 0.85rem;
        overflow: hidden;
    }

    [data-testid="stChatMessage"] p {
        line-height: 1.72;
    }

    div[data-testid="stChatInput"] {
        border-top: 1px solid var(--panel-border);
        background: color-mix(in srgb, var(--app-bg) 88%, transparent);
        backdrop-filter: blur(10px);
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        border-radius: 8px;
    }

    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 650;
    }

    .answer-source-row {
        display: flex;
        width: 100%;
        min-width: 0;
        margin-top: 0.55rem;
        box-sizing: border-box;
    }

    /* 来源标签需要被限制在聊天卡片内部，避免长模型名撑破容器。 */
    .answer-source {
        display: inline-flex;
        align-items: center;
        max-width: 100%;
        padding: 0.28rem 0.55rem;
        border-radius: 999px;
        border: 1px solid var(--panel-border);
        background: color-mix(in srgb, var(--panel-bg) 92%, transparent);
        color: var(--text-muted);
        font-size: 0.76rem;
        font-weight: 650;
        line-height: 1.4;
        overflow-wrap: anywhere;
        white-space: normal;
        box-sizing: border-box;
    }

    .sidebar-note {
        color: var(--text-muted);
        font-size: 0.82rem;
        line-height: 1.55;
        padding: 0.7rem 0.8rem;
        border-radius: 8px;
        background: color-mix(in srgb, var(--panel-bg) 92%, transparent);
        border: 1px solid var(--panel-border);
    }

    div[data-testid="stCheckbox"] {
        position: relative;
    }

    div[data-testid="stCheckbox"] [id$="__anchor"] {
        position: absolute;
        top: 0.12rem;
        right: 0;
    }

    @media (max-width: 760px) {
        .block-container {
            padding-top: 1.2rem;
        }

        .app-hero {
            grid-template-columns: 1fr;
            align-items: start;
        }

        .status-strip {
            justify-content: flex-start;
            min-width: 0;
        }

        .observability-strip {
            margin-top: -0.1rem;
        }

        .app-title {
            font-size: 1.9rem;
        }
    }
</style>
"""


def inject_app_styles() -> None:
    st.markdown(APP_STYLES, unsafe_allow_html=True)
