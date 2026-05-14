# ======== Python 标准库 ========

import os
# os 模块：用来读取系统环境变量，比如 OPENAI_API_KEY

from html import escape
# escape 函数：把用户输入转义后再放进 HTML，避免破坏页面结构


# ======== 类型提示（不影响运行，只是帮助理解） ========

from typing import Dict, List, Optional
# Dict[str, str]   表示字典：key 和 value 都是字符串
# List[...]        表示列表
# Optional[str]    表示：要么是 str，要么是 None


# ======== 第三方库：Streamlit ========

import streamlit as st
# streamlit 是用来快速写 Web 页面（特别适合 AI Demo）


# ======== 尝试导入 OpenAI SDK（防止没安装时报错） ========

try:
    # OpenAI：客户端对象
    # AuthenticationError：鉴权失败异常
    from openai import AuthenticationError, OpenAI
except Exception:
    # 如果 openai 库没安装，就使用本地回显模式，防止程序直接崩溃
    OpenAI = None
    AuthenticationError = None


# ======== 一些“常量配置” ========

APP_TITLE = "AI 助理"
# 页面标题

DEFAULT_SYSTEM_PROMPT = "你叫困困，是一个 AI 助理，请使用可爱活泼的语气回复用户的问题。"
# 默认系统提示词（system role）


# ======== Streamlit 页面基础设置 ========

st.set_page_config(
    page_title=APP_TITLE,   # 浏览器标签页标题
    page_icon="💬",         # 标签页图标
    layout="wide"           # 页面宽屏显示
)

st.markdown(
    """
    <style>
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

        .field-label {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            margin: 0 0 0.35rem;
            color: var(--text-main);
            font-size: 0.87rem;
            font-weight: 500;
            line-height: 1.35;
        }

        .help-dot {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 0.95rem;
            height: 0.95rem;
            border: 1px solid var(--panel-border);
            border-radius: 999px;
            color: var(--text-muted);
            font-size: 0.68rem;
            font-weight: 700;
            cursor: help;
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

if "sessions" not in st.session_state:
    st.session_state.sessions = {
        "会话 1": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
        ]
    }

if "active_session" not in st.session_state:
    st.session_state.active_session = "会话 1"

if "system_prompt_input" not in st.session_state:
    st.session_state.system_prompt_input = DEFAULT_SYSTEM_PROMPT


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
        current_system = st.session_state.sessions[st.session_state.active_session][0]["content"]
        st.session_state.system_prompt_input = current_system

    col_new, col_del = st.columns(2)

    with col_new:
        if st.button("新建", use_container_width=True):
            index = 1
            while f"会话 {index}" in st.session_state.sessions:
                index += 1
            new_name = f"会话 {index}"
            st.session_state.sessions[new_name] = [
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
            ]
            st.session_state.active_session = new_name
            st.session_state.system_prompt_input = DEFAULT_SYSTEM_PROMPT
            st.rerun()

    with col_del:
        if st.button("删除", disabled=len(st.session_state.sessions) <= 1, use_container_width=True):
            del st.session_state.sessions[st.session_state.active_session]
            st.session_state.active_session = list(st.session_state.sessions.keys())[0]
            current_system = st.session_state.sessions[st.session_state.active_session][0]["content"]
            st.session_state.system_prompt_input = current_system
            st.rerun()

    st.caption(f"当前共有 {len(st.session_state.sessions)} 个会话。")

    st.divider()
    st.subheader("提示词")

    preview_prompt = st.toggle(
        "预览 Markdown",
        value=False,
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

    # temperature 滑块（控制模型随机性）
    temperature = st.slider(
        "温度",
        0.0,    # 最小值
        1.0,    # 最大值
        0.7,    # 默认值
        0.1     # 步长
    )

    # 是否使用 OpenAI 接口
    use_openai = st.checkbox(
        "使用 OpenAI 接口",
        value=False,
        help="需要配置 OPENAI_API_KEY。未启用时使用本地回显。"
    )

    # API Key 输入框（密码形式）
    st.markdown(
        """
        <div class="field-label">
            OpenAI API Key
            <span class="help-dot" title="可选。页面输入的 API Key 优先于环境变量 OPENAI_API_KEY。">?</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        placeholder="sk-xxxxxx",
        label_visibility="collapsed"
    )

    # Base URL（支持第三方 OpenAI 兼容接口，如 DeepSeek）
    st.markdown(
        """
        <div class="field-label">
            Base URL
            <span class="help-dot" title="可选，用于第三方兼容 OpenAI 接口，如 DeepSeek。">?</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    base_url = st.text_input(
        "Base URL",
        value=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        placeholder="https://api.deepseek.com",
        label_visibility="collapsed"
    )

    # 模型名称
    st.markdown(
        """
        <div class="field-label">
            模型
            <span class="help-dot" title="也可通过环境变量 OPENAI_CHAT_MODEL 设置。">?</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    model_name = st.text_input(
        "模型",
        value=os.getenv("OPENAI_CHAT_MODEL", "deepseek-chat"),
        label_visibility="collapsed"
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

messages = st.session_state.sessions[st.session_state.active_session]


# ======== 同步 system prompt（侧边栏修改后生效） ========

if messages and messages[0].get("role") == "system":
    messages[0]["content"] = system_prompt


# ======== 消息展示与模型调用辅助函数 ========

def clean_model_messages(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    发送给模型接口前，只保留 role 和 content 字段。
    """
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if msg.get("role") in {"system", "user", "assistant"}
    ]


def get_answer_source(
    enabled_openai: bool,
    api_key: Optional[str],
    model: str,
) -> str:
    """
    根据当前配置生成回答来源标注。
    """
    if not enabled_openai:
        return "本地回显"

    if OpenAI is None:
        return "本地回显 · 未安装 openai"

    current_api_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if not current_api_key:
        return "本地回显 · 未配置密钥"

    return f"模型接口 · {model.strip() or '未设置模型'}"


def answer_source_html(source: Optional[str]) -> str:
    """
    生成助手回答来源标注。
    """
    safe_source = escape(source or "未知来源")
    return f'<div class="answer-source-row"><span class="answer-source">回答来源：{safe_source}</span></div>'


def render_assistant_message(content: str, source: Optional[str]) -> None:
    """
    将助手回答和来源合并在同一个 Markdown 块里渲染。
    """
    st.markdown(f"{content}\n\n{answer_source_html(source)}", unsafe_allow_html=True)


def render_app_header(
    container,
    session_name: str,
    mode: str,
    model: str,
    message_count: int,
) -> None:
    """
    渲染顶部状态区域。
    """
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
        unsafe_allow_html=True
    )


# ======== 顶部状态区域 ========

visible_messages = [msg for msg in messages if msg["role"] != "system"]
mode_label = "模型接口" if use_openai else "本地回显"
header_slot = st.empty()
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


# ======== 本地回显模式（未配置 API Key） ========

def local_fallback_response(user_text: str) -> str:
    """
    本地兜底响应函数
    当不使用 OpenAI 接口时调用
    """
    if "你好" in user_text:
        return "你好呀～，我是困困，一个超级可爱的AI小助手！✨ 今天有什么可以帮你的吗？"
    return (
        f"我收到了你的消息：{user_text}\n\n"
        f"当前未配置 OpenAI 密钥，所以这里是本地回显模式。"
    )


# ======== 调用 OpenAI / 兼容接口的函数 ========

def openai_response(
    history: List[Dict[str, str]],  # 聊天历史
    temp: float,                    # 温度
    api_key: Optional[str],         # API Key
    model: str,                     # 模型名
    base_url: Optional[str],        # Base URL
) -> str:

    # 如果 openai 库没安装
    if OpenAI is None:
        return "未安装 openai 依赖，已切换为本地回显模式。"

    # API Key 优先级：输入框 > 环境变量
    api_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return "未检测到 OPENAI_API_KEY，已切换为本地回显模式。"

    # Base URL 如果为空字符串，就设为 None
    base_url = (base_url or "").strip() or None

    # 创建 OpenAI 客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    try:
        # 发送聊天请求
        resp = client.chat.completions.create(
            model=model,
            messages=clean_model_messages(history),
            temperature=temp,
        )

        # 返回模型回复内容
        return resp.choices[0].message.content or ""

    except Exception as exc:
        # 鉴权失败（401）
        if AuthenticationError is not None and isinstance(exc, AuthenticationError):
            return f"鉴权失败（401）：{exc}"

        # 其他错误
        return f"请求失败：{type(exc).__name__} - {exc}"


# ======== 调用 OpenAI / 兼容接口（流式输出） ========

def openai_stream_response(
    history: List[Dict[str, str]],
    temp: float,
    api_key: Optional[str],
    model: str,
    base_url: Optional[str],
):
    """
    流式响应生成器
    每次 yield 一段增量文本
    """
    if OpenAI is None:
        yield "未安装 openai 依赖，已切换为本地回显模式。"
        return

    api_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        yield "未检测到 OPENAI_API_KEY，已切换为本地回显模式。"
        return

    base_url = (base_url or "").strip() or None

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=clean_model_messages(history),
            temperature=temp,
            stream=True,
        )
        for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        if AuthenticationError is not None and isinstance(exc, AuthenticationError):
            yield f"鉴权失败（401）：{exc}"
            return
        yield f"请求失败：{type(exc).__name__} - {exc}"


# ======== 主聊天逻辑 ========

if prompt:
    answer_source = get_answer_source(use_openai, api_key_input, model_name)
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
            answer_box = st.empty()
            answer = ""
            for chunk in openai_stream_response(
                messages,
                temperature,
                api_key_input,
                model_name,
                base_url,
            ):
                answer += chunk
                answer_box.markdown(answer)
            answer_box.markdown(
                f"{answer}\n\n{answer_source_html(answer_source)}",
                unsafe_allow_html=True
            )
        else:
            answer = local_fallback_response(prompt)
            render_assistant_message(answer, answer_source)

    # 4. 保存 AI 回复
    messages.append(
        {"role": "assistant", "content": answer, "source": answer_source}
    )

    render_app_header(
        header_slot,
        st.session_state.active_session,
        mode_label,
        model_name,
        len([msg for msg in messages if msg["role"] != "system"]),
    )
