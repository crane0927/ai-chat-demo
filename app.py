# ======== 第三方库：Streamlit ========

import streamlit as st
# streamlit 是用来快速写 Web 页面（特别适合 AI Demo）


# ======== 应用模块 ========

from config import (
    APP_TITLE,
    get_database_url,
    get_env_api_key,
)
from services.llm import (
    ModelRequestOptions,
    get_answer_source,
    local_fallback_response,
    openai_stream_response,
)
from services.model_config import (
    DuplicateModelConfigName,
    ModelConfig,
    ModelConfigInput,
    ModelConfigStorageError,
    create_model_config,
    delete_model_config,
    ensure_default_model_config,
    init_model_config_db,
    list_model_configs,
    update_model_config,
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


def model_config_label(config: ModelConfig) -> str:
    disabled_label = "（已停用）" if not config.enabled else ""
    return f"{config.name}{disabled_label}"


def build_model_config_input(
    name: str,
    provider: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    context_message_limit: int,
    timeout_seconds: float,
    max_retries: int,
    enabled: bool,
) -> ModelConfigInput:
    return ModelConfigInput(
        name=name,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        context_message_limit=int(context_message_limit),
        timeout_seconds=float(timeout_seconds),
        max_retries=int(max_retries),
        enabled=enabled,
    )


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


# ======== 模型配置数据库 ========

database_url = get_database_url()
try:
    init_model_config_db(database_url)
    ensure_default_model_config(database_url, get_env_api_key())
    model_configs = list_model_configs(database_url)
except ModelConfigStorageError as exc:
    # 数据库不可用时停止渲染后续聊天逻辑，避免用户误以为模型配置已经保存。
    st.error(f"模型配置数据库不可用：{exc}")
    st.info("请确认 PostgreSQL 已启动，并设置 APP_DATABASE_URL 或 DATABASE_URL。")
    st.stop()

model_configs_by_id = {config.id: config for config in model_configs}

if (
    "selected_model_config_id" not in st.session_state
    or st.session_state.selected_model_config_id not in model_configs_by_id
):
    # 当前选择可能来自上一轮页面状态；配置被删除后需要回退到第一条可用配置。
    st.session_state.selected_model_config_id = model_configs[0].id if model_configs else None

pending_model_config_id = st.session_state.pop("pending_selected_model_config_id", None)
if pending_model_config_id in model_configs_by_id:
    # 表单提交后不能在同一轮修改已实例化的小组件 key，因此把切换动作延迟到下一轮脚本执行。
    st.session_state.selected_model_config_id = pending_model_config_id

selected_model_config = model_configs_by_id[st.session_state.selected_model_config_id]


@st.dialog("设置", width="large")
def render_settings_dialog() -> None:
    prompt_tab, model_tab = st.tabs(["提示词", "模型"])

    with prompt_tab:
        st.subheader("提示词")

        # 设置页同时承载预览和编辑，避免会话侧边栏混入模型行为配置。
        preview_prompt = st.toggle(
            "预览 Markdown",
            value=st.session_state.get("preview_prompt", True),
            key="preview_prompt",
        )
        st.caption("系统提示词支持 Markdown，可编写角色、规则、列表和示例。")

        if not preview_prompt:
            st.text_area(
                "系统提示词",
                height=180,
                key="system_prompt_input",
            )
        elif st.session_state.system_prompt_input.strip():
            st.markdown(st.session_state.system_prompt_input)
        else:
            st.caption("暂无内容")

    with model_tab:
        st.subheader("模型")

        selected_model_config_id = st.selectbox(
            "当前模型配置",
            list(model_configs_by_id.keys()),
            key="selected_model_config_id",
            format_func=lambda config_id: model_config_label(model_configs_by_id[config_id]),
            help="切换后，下一次提问会使用所选模型配置。",
        )
        current_config = model_configs_by_id[selected_model_config_id]
        st.caption(
            f"服务商：{current_config.provider or '未设置'} · "
            f"Base URL：{current_config.base_url or '默认 OpenAI 地址'}"
        )

        edit_tab, new_tab = st.tabs(["编辑当前配置", "新增模型配置"])

        with edit_tab:
            with st.form("edit_model_config_form"):
                edit_name = st.text_input("配置名称", value=current_config.name)
                edit_provider = st.text_input("服务商", value=current_config.provider)
                edit_api_key = st.text_input(
                    "API Key",
                    type="password",
                    value=current_config.api_key,
                    help="当前版本会保存到 PostgreSQL；正式部署建议改为加密存储。",
                )
                edit_base_url = st.text_input(
                    "Base URL",
                    value=current_config.base_url,
                    placeholder="https://api.deepseek.com",
                )
                edit_model_name = st.text_input("模型", value=current_config.model_name)
                edit_enabled = st.checkbox("启用此配置", value=current_config.enabled)
                edit_temperature = st.slider(
                    "温度",
                    0.0,
                    1.0,
                    current_config.temperature,
                    0.1,
                    help="控制模型回复的随机性，数值越高越发散。",
                )
                edit_max_tokens = st.number_input(
                    "最大输出 Token",
                    min_value=1,
                    max_value=32000,
                    value=current_config.max_tokens,
                    step=256,
                )
                edit_context_message_limit = st.number_input(
                    "上下文消息数",
                    min_value=1,
                    max_value=200,
                    value=current_config.context_message_limit,
                    step=2,
                )
                edit_timeout_seconds = st.number_input(
                    "请求超时（秒）",
                    min_value=1.0,
                    max_value=300.0,
                    value=current_config.timeout_seconds,
                    step=5.0,
                )
                edit_max_retries = st.number_input(
                    "自动重试次数",
                    min_value=0,
                    max_value=10,
                    value=current_config.max_retries,
                    step=1,
                )
                edit_submitted = st.form_submit_button("保存当前配置", use_container_width=True)

            if edit_submitted:
                if not edit_name.strip() or not edit_model_name.strip():
                    st.error("配置名称和模型不能为空。")
                else:
                    try:
                        update_model_config(
                            database_url,
                            current_config.id,
                            build_model_config_input(
                                edit_name,
                                edit_provider,
                                edit_api_key,
                                edit_base_url,
                                edit_model_name,
                                edit_temperature,
                                edit_max_tokens,
                                edit_context_message_limit,
                                edit_timeout_seconds,
                                edit_max_retries,
                                edit_enabled,
                            ),
                        )
                        st.success("模型配置已保存。")
                        st.rerun()
                    except DuplicateModelConfigName as exc:
                        st.error(str(exc))
                    except ModelConfigStorageError as exc:
                        st.error(f"保存失败：{exc}")

            confirm_delete = st.checkbox("确认删除当前配置")
            if st.button(
                "删除当前配置",
                disabled=len(model_configs) <= 1 or not confirm_delete,
                use_container_width=True,
            ):
                try:
                    delete_model_config(database_url, current_config.id)
                    st.rerun()
                except ModelConfigStorageError as exc:
                    st.error(f"删除失败：{exc}")

        with new_tab:
            with st.form("new_model_config_form"):
                new_name = st.text_input("配置名称", placeholder="OpenAI GPT-4.1")
                new_provider = st.text_input("服务商", placeholder="OpenAI")
                new_api_key = st.text_input(
                    "API Key",
                    type="password",
                    placeholder="sk-xxxxxx",
                    help="当前版本会保存到 PostgreSQL；正式部署建议改为加密存储。",
                )
                new_base_url = st.text_input("Base URL", placeholder="https://api.openai.com/v1")
                new_model_name = st.text_input("模型", placeholder="gpt-4.1")
                new_temperature = st.slider(
                    "温度",
                    0.0,
                    1.0,
                    0.7,
                    0.1,
                    key="new_temperature",
                )
                new_max_tokens = st.number_input(
                    "最大输出 Token",
                    min_value=1,
                    max_value=32000,
                    value=2048,
                    step=256,
                    key="new_max_tokens",
                )
                new_context_message_limit = st.number_input(
                    "上下文消息数",
                    min_value=1,
                    max_value=200,
                    value=20,
                    step=2,
                    key="new_context_message_limit",
                )
                new_timeout_seconds = st.number_input(
                    "请求超时（秒）",
                    min_value=1.0,
                    max_value=300.0,
                    value=60.0,
                    step=5.0,
                    key="new_timeout_seconds",
                )
                new_max_retries = st.number_input(
                    "自动重试次数",
                    min_value=0,
                    max_value=10,
                    value=2,
                    step=1,
                    key="new_max_retries",
                )
                new_submitted = st.form_submit_button("创建模型配置", use_container_width=True)

            if new_submitted:
                if not new_name.strip() or not new_model_name.strip():
                    st.error("配置名称和模型不能为空。")
                else:
                    try:
                        new_config_id = create_model_config(
                            database_url,
                            build_model_config_input(
                                new_name,
                                new_provider,
                                new_api_key,
                                new_base_url,
                                new_model_name,
                                new_temperature,
                                new_max_tokens,
                                new_context_message_limit,
                                new_timeout_seconds,
                                new_max_retries,
                                True,
                            ),
                        )
                        st.session_state.pending_selected_model_config_id = new_config_id
                        st.success("模型配置已创建。")
                        st.rerun()
                    except DuplicateModelConfigName as exc:
                        st.error(str(exc))
                    except ModelConfigStorageError as exc:
                        st.error(f"创建失败：{exc}")

        st.caption("模型配置保存到 PostgreSQL。配置停用或未填写 API Key 时，本轮对话会使用本地回显。")


# ======== 侧边栏设置区域 ========

with st.sidebar:
    # with st.sidebar 表示：下面缩进的内容都显示在侧边栏

    st.title("会话")
    st.caption("选择、创建或删除对话。")

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


# 设置弹窗中的组件会更新 session_state；后续渲染前重新读取，确保顶部状态和请求参数一致。
selected_model_config = model_configs_by_id[st.session_state.selected_model_config_id]


# ======== 当前会话消息 ========

messages = get_current_messages(st.session_state)


# ======== 同步 system prompt（侧边栏修改后生效） ========

system_prompt = st.session_state.system_prompt_input
sync_system_prompt(messages, system_prompt)


# ======== 顶部状态区域 ========

visible_messages = get_visible_messages(messages)
use_model_api = bool(selected_model_config.enabled and selected_model_config.api_key.strip())
mode_label = "模型接口" if use_model_api else "本地回显"
_, settings_col = st.columns([0.86, 0.14])
with settings_col:
    if st.button("设置", use_container_width=True):
        render_settings_dialog()

header_slot = st.empty()
# 顶部状态需要在用户发送消息后即时重绘，所以先用占位容器承载。
render_app_header(
    header_slot,
    st.session_state.active_session,
    mode_label,
    selected_model_config.model_name,
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
            <p>输入一个问题，或者先在设置中调整提示词和模型配置。</p>
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
    answer_source = get_answer_source(
        use_model_api,
        selected_model_config.api_key,
        selected_model_config.model_name,
    )
    model_options = ModelRequestOptions(
        max_tokens=selected_model_config.max_tokens,
        context_message_limit=selected_model_config.context_message_limit,
        timeout_seconds=selected_model_config.timeout_seconds,
        max_retries=selected_model_config.max_retries,
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
        if use_model_api:
            # 手动累积流式片段，结束后把来源标签追加到同一个消息块里。
            answer_box = st.empty()
            answer = ""
            for chunk in openai_stream_response(
                messages,
                selected_model_config.temperature,
                selected_model_config.api_key,
                selected_model_config.model_name,
                selected_model_config.base_url,
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
        selected_model_config.model_name,
        len([msg for msg in messages if msg["role"] != "system"]),
    )
