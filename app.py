# ======== Python 标准库 ========

import os
# os 模块：用来读取系统环境变量，比如 OPENAI_API_KEY


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
    layout="centered"       # 页面居中
)

st.title(APP_TITLE)
# 页面主标题


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

    st.header("会话")

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
        if st.button("新建会话"):
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
        if st.button("删除会话", disabled=len(st.session_state.sessions) <= 1):
            del st.session_state.sessions[st.session_state.active_session]
            st.session_state.active_session = list(st.session_state.sessions.keys())[0]
            current_system = st.session_state.sessions[st.session_state.active_session][0]["content"]
            st.session_state.system_prompt_input = current_system
            st.rerun()

    st.header("设置")

    # 系统提示词输入框（多行文本）
    system_prompt = st.text_area(
        "系统提示词",
        height=120,
        key="system_prompt_input"
    )

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
        "使用 OpenAI 接口（需要 OPENAI_API_KEY）",
        value=False
    )

    # API Key 输入框（密码形式）
    api_key_input = st.text_input(
        "OpenAI API Key（可选，优先于环境变量）",
        type="password",
        value=os.getenv("OPENAI_API_KEY", "sk-xxxxxx"),
        placeholder="sk-xxxxxx"
    )

    # Base URL（支持第三方 OpenAI 兼容接口，如 DeepSeek）
    base_url = st.text_input(
        "Base URL（可选，用于第三方兼容 OpenAI 接口）",
        value=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        placeholder="https://api.deepseek.com"
    )

    # 模型名称
    model_name = st.text_input(
        "模型",
        value=os.getenv("OPENAI_CHAT_MODEL", "deepseek-chat"),
        help="也可通过环境变量 OPENAI_CHAT_MODEL 设置"
    )

    st.caption("未配置密钥时将使用本地回显模式。")


# ======== 当前会话消息 ========

messages = st.session_state.sessions[st.session_state.active_session]


# ======== 同步 system prompt（侧边栏修改后生效） ========

if messages and messages[0].get("role") == "system":
    messages[0]["content"] = system_prompt


# ======== 渲染历史消息 ========

for msg in messages:
    # system 消息不显示在聊天窗口
    if msg["role"] == "system":
        continue

    # 根据 role（user / assistant）显示不同样式
    with st.chat_message(msg["role"]):
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
            messages=history,
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
            messages=history,
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
            answer_chunks = st.write_stream(
                openai_stream_response(
                    messages,
                    temperature,
                    api_key_input,
                    model_name,
                    base_url,
                )
            )
            answer = "".join(answer_chunks) if isinstance(answer_chunks, list) else str(answer_chunks)
        else:
            answer = local_fallback_response(prompt)
            st.markdown(answer)

    # 4. 保存 AI 回复
    messages.append(
        {"role": "assistant", "content": answer}
    )
