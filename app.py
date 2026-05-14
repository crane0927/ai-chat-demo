# ======== 第三方库：Streamlit ========

import streamlit as st
# streamlit 是用来快速写 Web 页面（特别适合 AI Demo）


# ======== 应用模块 ========

from config import (
    APP_TITLE,
    get_env_api_key,
    get_env_base_url,
    get_env_chat_model,
    get_env_context_messages,
    get_env_max_retries,
    get_env_max_tokens,
    get_env_timeout_seconds,
)
from services.llm import (
    ModelRequestOptions,
    get_answer_source,
    local_fallback_response,
    openai_stream_response,
)
from services.session import (
    create_session,
    delete_active_session,
    get_current_messages,
    get_current_system_prompt,
    init_session_state,
    sync_system_prompt,
    visible_messages as get_visible_messages,
)
from ui.components import answer_source_html, render_app_header, render_assistant_message


# ======== Streamlit 页面基础设置 ========

st.set_page_config(
    page_title=APP_TITLE,   # 浏览器标签页标题
    page_icon="💬",         # 标签页图标
    layout="wide"           # 页面宽屏显示
)

st.markdown(
    """
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

            .app-title {
                font-size: 1.9rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ======== 会话管理（多会话） ========

init_session_state(st.session_state)


# ======== 侧边栏设置区域 ========

with st.sidebar:
    # with st.sidebar 表示：下面缩进的内容都显示在侧边栏

    st.title("控制台")
    st.caption("管理会话、提示词和模型连接。")

    st.subheader("会话")

    session_names = list(st.session_state.sessions.keys())
    previous_session = st.session_state.active_session

    st.selectbox(
        "当前会话",
        session_names,
        key="active_session"
    )

    if st.session_state.active_session != previous_session:
        st.session_state.system_prompt_input = get_current_system_prompt(st.session_state)

    col_new, col_del = st.columns(2)

    with col_new:
        st.button(
            "新建",
            use_container_width=True,
            on_click=create_session,
            args=(st.session_state,),
        )

    with col_del:
        st.button(
            "删除",
            disabled=len(st.session_state.sessions) <= 1,
            use_container_width=True,
            on_click=delete_active_session,
            args=(st.session_state,),
        )

    st.caption(f"当前共有 {len(st.session_state.sessions)} 个会话。")

    st.divider()
    st.subheader("提示词")

    # 预览和编辑共用同一块区域，避免侧边栏同时出现两个提示词面板。
    preview_prompt = st.toggle(
        "预览 Markdown",
        value=True,
    )
    st.caption("系统提示词支持 Markdown，可编写角色、规则、列表和示例。")

    if not preview_prompt:
        # 系统提示词输入框（多行文本）
        system_prompt = st.text_area(
            "系统提示词",
            height=150,
            key="system_prompt_input"
        )
    else:
        system_prompt = st.session_state.system_prompt_input
        if system_prompt.strip():
            st.markdown(system_prompt)
        else:
            st.caption("暂无内容")

    st.divider()
    st.subheader("模型")

    with st.expander("普通参数", expanded=True):
        # temperature 滑块（控制模型随机性）
        temperature = st.slider(
            "温度",
            0.0,    # 最小值
            1.0,    # 最大值
            0.7,    # 默认值
            0.1,    # 步长
            help="控制模型回复的随机性，数值越高越发散。"
        )

        # 是否使用 OpenAI 接口
        use_openai = st.checkbox(
            "使用 OpenAI 接口",
            value=False,
            # help="需要配置 OPENAI_API_KEY。未启用时使用本地回显。"
        )

        api_key_input = st.text_input(
            "OpenAI API Key",
            type="password",
            value=get_env_api_key(),
            placeholder="sk-xxxxxx",
            help="可选。页面输入的 API Key 优先于环境变量 OPENAI_API_KEY。"
        )

        base_url = st.text_input(
            "Base URL",
            value=get_env_base_url(),
            placeholder="https://api.deepseek.com",
            help="可选，用于第三方兼容 OpenAI 接口，如 DeepSeek。"
        )

        model_name = st.text_input(
            "模型",
            value=get_env_chat_model(),
            help="聊天模型名称，也可通过环境变量 OPENAI_CHAT_MODEL 设置。"
        )

    with st.expander("高级参数"):
        max_tokens = st.number_input(
            "最大输出 Token",
            min_value=1,
            max_value=32000,
            value=get_env_max_tokens(),
            step=256,
            help="限制单次回复的最大输出长度。"
        )

        context_message_limit = st.number_input(
            "上下文消息数",
            min_value=1,
            max_value=200,
            value=get_env_context_messages(),
            step=2,
            help="发送给模型时保留最近多少条用户/助手消息，系统提示词会始终保留。"
        )

        timeout_seconds = st.number_input(
            "请求超时（秒）",
            min_value=1.0,
            max_value=300.0,
            value=get_env_timeout_seconds(),
            step=5.0,
            help="模型服务超过该时间未响应时中断请求。"
        )

        max_retries = st.number_input(
            "自动重试次数",
            min_value=0,
            max_value=10,
            value=get_env_max_retries(),
            step=1,
            help="网络抖动、限流等可重试错误由 OpenAI SDK 自动重试。"
        )

    st.markdown(
        """
        <div class="sidebar-note">
            未启用接口时使用本地回显。页面输入的 API Key 优先于环境变量。
        </div>
        """,
        unsafe_allow_html=True
    )


# ======== 当前会话消息 ========

messages = get_current_messages(st.session_state)


# ======== 同步 system prompt（侧边栏修改后生效） ========

sync_system_prompt(messages, system_prompt)


# ======== 顶部状态区域 ========

visible_messages = get_visible_messages(messages)
mode_label = "模型接口" if use_openai else "本地回显"
header_slot = st.empty()
# 顶部状态需要在用户发送消息后即时重绘，所以先用占位容器承载。
render_app_header(
    header_slot,
    st.session_state.active_session,
    mode_label,
    model_name,
    len(visible_messages),
)


# ======== 渲染历史消息 ========

empty_state_slot = st.empty()

if not visible_messages:
    # 空状态同样用占位容器，发送第一条消息后可以立即清掉。
    empty_state_slot.markdown(
        """
        <div class="empty-state">
            <h2>开始新的对话</h2>
            <p>输入一个问题，或者先在侧边栏调整提示词和模型配置。</p>
        </div>
        """,
        unsafe_allow_html=True
    )

for msg in visible_messages:
    # system 消息不显示在聊天窗口
    # 根据 role（user / assistant）显示不同样式
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_assistant_message(msg["content"], msg.get("source"))
        else:
            st.markdown(msg["content"])


# ======== 聊天输入框 ========

prompt = st.chat_input("请输入你的问题...")


# ======== 主聊天逻辑 ========

if prompt:
    answer_source = get_answer_source(use_openai, api_key_input, model_name)
    model_options = ModelRequestOptions(
        max_tokens=int(max_tokens),
        context_message_limit=int(context_message_limit),
        timeout_seconds=float(timeout_seconds),
        max_retries=int(max_retries),
    )
    empty_state_slot.empty()

    # 1. 记录用户消息
    messages.append(
        {"role": "user", "content": prompt}
    )

    # 2. 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. 生成 AI 回复
    with st.chat_message("assistant"):
        if use_openai:
            # 手动累积流式片段，结束后把来源标签追加到同一个消息块里。
            answer_box = st.empty()
            answer = ""
            for chunk in openai_stream_response(
                messages,
                temperature,
                api_key_input,
                model_name,
                base_url,
                model_options,
            ):
                answer += chunk
                answer_box.markdown(answer)
            answer_box.markdown(answer)
            st.markdown(answer_source_html(answer_source), unsafe_allow_html=True)
        else:
            answer = local_fallback_response(prompt)
            render_assistant_message(answer, answer_source)

    # 4. 保存 AI 回复
    messages.append(
        {"role": "assistant", "content": answer, "source": answer_source}
    )

    # 消息数在本轮脚本执行中发生变化，立即重绘顶部统计。
    render_app_header(
        header_slot,
        st.session_state.active_session,
        mode_label,
        model_name,
        len([msg for msg in messages if msg["role"] != "system"]),
    )
