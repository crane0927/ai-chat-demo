import streamlit as st
# streamlit 是用来快速写 Web 页面（特别适合 AI Demo）


# ======== 应用模块 ========

from config import (
    APP_TITLE,
    get_database_url,
    get_env_api_key,
)
from pages.settings_dialog import (
    render_create_session_dialog,
    render_delete_model_config_dialog,
    render_rename_session_dialog,
    render_settings_dialog,
)
from pages.sidebar import render_sidebar
from services.app_settings import (
    AppSettingsStorageError,
    get_global_system_prompt,
    init_app_settings_db,
)
from services.llm import (
    ModelRequestOptions,
    get_answer_source,
    local_fallback_response,
    openai_stream_response,
)
from services.model_config import (
    ModelConfigStorageError,
    ensure_default_model_config,
    init_model_config_db,
    list_model_configs,
)
from services.prompt_template import (
    PromptTemplateStorageError,
    ensure_default_prompt_templates,
    init_prompt_template_db,
    list_prompt_templates,
)
from services.session import (
    SessionStorageError,
    append_session_message,
    build_model_messages,
    ensure_session_model_config,
    ensure_default_session,
    get_session,
    init_session_db,
    list_session_messages,
    list_sessions,
    update_session_model_config,
    update_session_system_prompt,
    visible_messages as get_visible_messages,
)
from state.session_state import (
    ensure_base_state,
    sync_prompt_selection_state,
    sync_system_prompt_state,
)
from ui.components import answer_source_html, render_app_header, render_assistant_message
from ui.styles import inject_app_styles


# ======== Streamlit 页面基础设置 ========

st.set_page_config(
    page_title=APP_TITLE,   # 浏览器标签页标题
    page_icon="💬",         # 标签页图标
    layout="wide"           # 页面宽屏显示
)
inject_app_styles()


# ======== PostgreSQL 数据库 ========

database_url = get_database_url()
try:
    init_model_config_db(database_url)
    ensure_default_model_config(database_url, get_env_api_key())
    model_configs = list_model_configs(database_url)
    model_configs_by_id = {config.id: config for config in model_configs}
    default_model_config = model_configs[0] if model_configs else None
    init_app_settings_db(database_url)
    global_system_prompt = get_global_system_prompt(database_url)
    init_prompt_template_db(database_url)
    ensure_default_prompt_templates(database_url)
    prompt_templates = list_prompt_templates(database_url)
    prompt_templates_by_id = {template.id: template for template in prompt_templates}
    init_session_db(database_url)
    ensure_default_session(
        database_url,
        default_model_config.id if default_model_config else None,
        global_system_prompt,
    )
    if default_model_config is not None:
        ensure_session_model_config(database_url, default_model_config.id)
    sessions = list_sessions(database_url)
except SessionStorageError as exc:
    st.error(f"聊天记录数据库不可用：{exc}")
    st.info("请确认 PostgreSQL 已启动，并设置 APP_DATABASE_URL 或 DATABASE_URL。")
    st.stop()
except AppSettingsStorageError as exc:
    st.error(f"全局设置数据库不可用：{exc}")
    st.info("请确认 PostgreSQL 已启动，并设置 APP_DATABASE_URL 或 DATABASE_URL。")
    st.stop()
except ModelConfigStorageError as exc:
    # 数据库不可用时停止渲染后续聊天逻辑，避免用户误以为模型配置已经保存。
    st.error(f"模型配置数据库不可用：{exc}")
    st.info("请确认 PostgreSQL 已启动，并设置 APP_DATABASE_URL 或 DATABASE_URL。")
    st.stop()
except PromptTemplateStorageError as exc:
    st.error(f"提示词模板数据库不可用：{exc}")
    st.info("请确认 PostgreSQL 已启动，并设置 APP_DATABASE_URL 或 DATABASE_URL。")
    st.stop()

sessions_by_id = {session.id: session for session in sessions}
ensure_base_state(
    state=st.session_state,
    sessions_by_id=sessions_by_id,
    prompt_templates_by_id=prompt_templates_by_id,
    global_system_prompt=global_system_prompt,
)

current_session = sessions_by_id.get(st.session_state.active_session_id)
current_preview_prompt = st.session_state.get("preview_prompt", True)
previous_preview_prompt = st.session_state.get("previous_preview_prompt", current_preview_prompt)
sync_prompt_selection_state(st.session_state, prompt_templates_by_id)

if current_session is None:
    st.error("未找到当前会话，请刷新页面重试。")
    st.stop()

if current_session.model_config_id not in model_configs_by_id:
    default_model_config = model_configs[0] if model_configs else None
    if default_model_config is None:
        st.error("未找到可用模型配置，请先在设置中创建模型。")
        st.stop()
    try:
        update_session_model_config(database_url, current_session.id, default_model_config.id)
        current_session = get_session(database_url, current_session.id) or current_session
    except SessionStorageError as exc:
        st.error(f"初始化会话模型失败：{exc}")
        st.stop()

selected_model_config = model_configs_by_id[current_session.model_config_id]

legacy_system_prompt_input = st.session_state.pop("system_prompt_input", "")
sync_system_prompt_state(
    state=st.session_state,
    current_session=current_session,
    current_preview_prompt=current_preview_prompt,
    previous_preview_prompt=previous_preview_prompt,
    legacy_system_prompt_input=legacy_system_prompt_input,
)

current_session_messages = list_session_messages(database_url, current_session.id)
if st.session_state.delete_model_config_confirming_id in model_configs_by_id:
    render_delete_model_config_dialog(
        database_url=database_url,
        config_id=st.session_state.delete_model_config_confirming_id,
        model_configs_by_id=model_configs_by_id,
    )


if st.session_state.rename_session_confirming_id in sessions_by_id:
    render_rename_session_dialog(
        database_url=database_url,
        session_id=st.session_state.rename_session_confirming_id,
    )


if st.session_state.create_session_confirming:
    render_create_session_dialog(
        database_url=database_url,
        model_configs_by_id=model_configs_by_id,
        global_system_prompt_draft=st.session_state.global_system_prompt_draft,
    )


# ======== 侧边栏设置区域 ========

render_sidebar(
    database_url=database_url,
    sessions=sessions,
    sessions_by_id=sessions_by_id,
    current_session=current_session,
    current_session_messages=current_session_messages,
)

# ======== 当前会话消息 ========

messages = current_session_messages
system_prompt = st.session_state.system_prompt_draft.strip() or current_session.system_prompt
if system_prompt != current_session.system_prompt:
    try:
        update_session_system_prompt(database_url, current_session.id, system_prompt)
        current_session = get_session(database_url, current_session.id) or current_session
    except SessionStorageError as exc:
        st.error(f"保存提示词失败：{exc}")
        st.stop()


# ======== 顶部状态区域 ========

visible_messages = get_visible_messages(messages)
use_model_api = bool(selected_model_config.enabled and selected_model_config.api_key.strip())
mode_label = "模型接口" if use_model_api else "本地回显"
_, settings_col = st.columns([0.86, 0.14])
with settings_col:
    if st.button("设置", use_container_width=True):
        render_settings_dialog(
            database_url=database_url,
            current_session=current_session,
            model_configs=model_configs,
            model_configs_by_id=model_configs_by_id,
            prompt_templates=prompt_templates,
            prompt_templates_by_id=prompt_templates_by_id,
            global_system_prompt=global_system_prompt,
        )

header_slot = st.empty()
# 顶部状态需要在用户发送消息后即时重绘，所以先用占位容器承载。
render_app_header(
    header_slot,
    current_session.title,
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
    with st.chat_message(msg.role):
        if msg.role == "assistant":
            render_assistant_message(msg.content, msg.source)
        else:
            st.markdown(msg.content)


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

    conversation_messages = build_model_messages(system_prompt, messages)

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
                conversation_messages + [{"role": "user", "content": prompt}],
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

    try:
        # 先保存用户消息，再保存助手回复，保证数据库中的顺序和页面展示一致。
        append_session_message(database_url, current_session.id, "user", prompt)
        append_session_message(database_url, current_session.id, "assistant", answer, answer_source)
    except SessionStorageError as exc:
        st.error(f"保存聊天记录失败：{exc}")
        st.stop()

    # 消息数在本轮脚本执行中发生变化，立即重绘顶部统计。
    render_app_header(
        header_slot,
        current_session.title,
        mode_label,
        selected_model_config.model_name,
        len(messages) + 2,
    )
