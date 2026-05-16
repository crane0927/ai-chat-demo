import streamlit as st

from services.app_settings import AppSettingsStorageError, update_global_system_prompt
from services.model_connection import (
    ModelConnectionTestError,
    test_model_connection,
)
from services.model_config import (
    DuplicateModelConfigName,
    ModelConfigStorageError,
    create_model_config,
    delete_model_config,
    update_model_config,
)
from services.model_presets import list_model_presets
from services.prompt_template import (
    DuplicatePromptTemplateName,
    PromptTemplateInput,
    PromptTemplateStorageError,
    create_prompt_template,
    delete_prompt_template,
    extract_template_variables,
    render_prompt_template,
    update_prompt_template,
)
from services.session import (
    SessionStorageError,
    create_session,
    get_session,
    rename_session,
    update_session_model_config,
    update_session_system_prompt,
)
from utils.view_helpers import (
    build_model_config_input,
    model_preset_label,
    build_prompt_template_input,
    build_template_copy_name,
    model_config_label,
    prompt_template_label,
)


@st.dialog("确认删除模型配置", width="small")
def render_delete_model_config_dialog(
    database_url: str,
    config_id: int,
    model_configs_by_id: dict[int, object],
) -> None:
    current_config = model_configs_by_id.get(config_id)
    if current_config is None:
        st.session_state.delete_model_config_confirming_id = None
        st.rerun()

    st.write(f"确认删除模型配置“{current_config.name}”吗？删除后无法恢复。")
    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button(
            "确认删除",
            type="primary",
            use_container_width=True,
            key=f"delete_model_config_confirm_{config_id}",
        ):
            try:
                delete_model_config(database_url, config_id)
                st.session_state.delete_model_config_confirming_id = None
                st.rerun()
            except ModelConfigStorageError as exc:
                st.error(f"删除失败：{exc}")

    with cancel_col:
        if st.button(
            "取消",
            use_container_width=True,
            key=f"delete_model_config_cancel_{config_id}",
        ):
            st.session_state.delete_model_config_confirming_id = None
            st.rerun()


@st.dialog("重命名会话", width="small")
def render_rename_session_dialog(database_url: str, session_id: int) -> None:
    session = get_session(database_url, session_id)
    if session is None:
        st.session_state.rename_session_confirming_id = None
        st.rerun()

    with st.form(f"rename_session_form_{session_id}"):
        new_title = st.text_input("会话名称", value=session.title)
        submitted = st.form_submit_button("保存名称", use_container_width=True)

    if submitted:
        if not new_title.strip():
            st.error("会话名称不能为空。")
        else:
            try:
                rename_session(database_url, session_id, new_title)
                st.session_state.rename_session_confirming_id = None
                st.rerun()
            except SessionStorageError as exc:
                st.error(f"重命名失败：{exc}")

    if st.button(
        "取消", key=f"cancel_rename_session_{session_id}", use_container_width=True
    ):
        st.session_state.rename_session_confirming_id = None
        st.rerun()


@st.dialog("新建会话", width="small")
def render_create_session_dialog(
    database_url: str,
    model_configs_by_id: dict[int, object],
    global_system_prompt_draft: str,
) -> None:
    with st.form("create_session_form"):
        new_session_title = st.text_input("会话名称", placeholder="留空则自动生成")
        new_session_model_config_id = st.selectbox(
            "选择模型",
            list(model_configs_by_id.keys()),
            format_func=lambda config_id: model_config_label(
                model_configs_by_id[config_id]
            ),
        )
        st.caption("新会话会默认使用全局默认提示词，创建后仍可按会话单独修改。")
        submitted = st.form_submit_button("创建会话", use_container_width=True)

    if submitted:
        try:
            new_session_id = create_session(
                database_url,
                title=new_session_title,
                system_prompt=global_system_prompt_draft,
                model_config_id=new_session_model_config_id,
            )
            st.session_state.pending_active_session_id = new_session_id
            st.session_state.create_session_confirming = False
            st.rerun()
        except SessionStorageError as exc:
            st.error(f"创建失败：{exc}")

    if st.button("取消", key="cancel_create_session", use_container_width=True):
        st.session_state.create_session_confirming = False
        st.rerun()


@st.dialog("设置", width="large")
def render_settings_dialog(
    database_url: str,
    current_session,
    model_configs: list,
    model_configs_by_id: dict[int, object],
    prompt_templates: list,
    prompt_templates_by_id: dict[int, object],
    global_system_prompt: str,
) -> None:
    prompt_tab, model_tab = st.tabs(["提示词", "模型"])

    with prompt_tab:
        st.subheader("提示词")
        current_prompt_tab, global_prompt_tab, template_library_tab = st.tabs(
            ["当前会话", "全局默认", "模板库"]
        )

        with current_prompt_tab:
            preview_prompt = st.toggle(
                "预览 Markdown",
                value=st.session_state.get("preview_prompt", True),
                key="preview_prompt",
            )
            st.caption("当前会话的系统提示词可单独修改，不影响其他会话。")

            if not preview_prompt:
                editor_key = (
                    f"system_prompt_editor_{current_session.id}_"
                    f"{st.session_state.get('system_prompt_editor_nonce', 0)}"
                )
                editor_value = st.text_area(
                    "系统提示词",
                    height=180,
                    value=st.session_state.system_prompt_draft,
                    key=editor_key,
                )
                st.session_state.system_prompt_editor_active_key = editor_key
                st.session_state.system_prompt_draft = editor_value
            elif st.session_state.system_prompt_draft.strip():
                st.markdown(st.session_state.system_prompt_draft)
            else:
                st.caption("暂无内容")

        with global_prompt_tab:
            st.caption("新建会话会默认使用这里的系统提示词，后续每个会话仍可单独修改。")
            with st.form("global_system_prompt_form"):
                global_prompt_value = st.text_area(
                    "全局默认系统提示词",
                    height=180,
                    value=st.session_state.global_system_prompt_draft,
                )
                global_prompt_submitted = st.form_submit_button(
                    "保存全局默认提示词", use_container_width=True
                )

            if global_prompt_submitted:
                try:
                    update_global_system_prompt(database_url, global_prompt_value)
                    st.session_state.global_system_prompt_draft = (
                        global_prompt_value.strip() or global_system_prompt
                    )
                    st.success("全局默认提示词已保存。")
                    st.rerun()
                except AppSettingsStorageError as exc:
                    st.error(f"保存失败：{exc}")

        with template_library_tab:
            st.caption("支持保存、编辑、复制和应用模板；占位符使用 `{{变量名}}` 格式。")

            template_use_tab, template_new_tab = st.tabs(["使用模板", "新增模板"])

            with template_use_tab:
                if not prompt_templates:
                    st.info("当前还没有可用模板，请先新增模板。")
                else:
                    selected_template_id = st.selectbox(
                        "选择模板",
                        list(prompt_templates_by_id.keys()),
                        key="selected_prompt_template_id",
                        format_func=lambda template_id: prompt_template_label(
                            prompt_templates_by_id[template_id]
                        ),
                    )
                    selected_template = prompt_templates_by_id[selected_template_id]
                    template_variables = extract_template_variables(
                        selected_template.content
                    )

                    if selected_template.description.strip():
                        st.caption(selected_template.description)

                    variable_values = {}
                    if template_variables:
                        st.markdown("**变量填写**")
                        # 变量输入框按模板 ID 隔离，避免切换模板时把不同含义的值串在一起。
                        for variable_name in template_variables:
                            variable_values[variable_name] = st.text_input(
                                variable_name,
                                key=f"prompt_template_var_{selected_template.id}_{variable_name}",
                            )
                    else:
                        st.caption("该模板没有变量占位符，可直接应用。")

                    rendered_template_content = render_prompt_template(
                        selected_template.content,
                        variable_values,
                    )
                    missing_variables = [
                        variable_name
                        for variable_name in template_variables
                        if not variable_values.get(variable_name, "").strip()
                    ]

                    st.text_area(
                        "渲染预览",
                        value=rendered_template_content,
                        height=220,
                        disabled=True,
                    )
                    if missing_variables:
                        st.caption(
                            "以下变量尚未填写，预览中会保留原占位符："
                            + "、".join(missing_variables)
                        )

                    apply_current_col, apply_global_col, duplicate_col = st.columns(3)

                    with apply_current_col:
                        if st.button(
                            "应用到当前会话",
                            use_container_width=True,
                            key=f"apply_template_current_{selected_template.id}",
                        ):
                            try:
                                # 应用模板时同时更新数据库和编辑草稿，保证页面状态与持久化一致。
                                update_session_system_prompt(
                                    database_url,
                                    current_session.id,
                                    rendered_template_content,
                                )
                                st.session_state.system_prompt_draft = (
                                    rendered_template_content
                                )
                                st.session_state.preview_prompt = False
                                st.success("已应用到当前会话。")
                                st.rerun()
                            except SessionStorageError as exc:
                                st.error(f"应用失败：{exc}")

                    with apply_global_col:
                        if st.button(
                            "设为全局默认",
                            use_container_width=True,
                            key=f"apply_template_global_{selected_template.id}",
                        ):
                            try:
                                update_global_system_prompt(
                                    database_url, rendered_template_content
                                )
                                st.session_state.global_system_prompt_draft = (
                                    rendered_template_content
                                )
                                st.success("已更新全局默认提示词。")
                                st.rerun()
                            except AppSettingsStorageError as exc:
                                st.error(f"应用失败：{exc}")

                    with duplicate_col:
                        if st.button(
                            "复制为新模板",
                            use_container_width=True,
                            key=f"duplicate_template_{selected_template.id}",
                        ):
                            try:
                                create_prompt_template(
                                    database_url,
                                    PromptTemplateInput(
                                        name=build_template_copy_name(
                                            prompt_templates, selected_template.name
                                        ),
                                        description=selected_template.description,
                                        content=selected_template.content,
                                        builtin=False,
                                    ),
                                )
                                st.success("模板已复制。")
                                st.rerun()
                            except DuplicatePromptTemplateName as exc:
                                st.error(str(exc))
                            except PromptTemplateStorageError as exc:
                                st.error(f"复制失败：{exc}")

                    st.divider()
                    st.markdown("**编辑当前模板**")
                    with st.form(f"edit_prompt_template_form_{selected_template.id}"):
                        edit_template_name = st.text_input(
                            "模板名称", value=selected_template.name
                        )
                        edit_template_description = st.text_input(
                            "模板说明",
                            value=selected_template.description,
                        )
                        edit_template_content = st.text_area(
                            "模板内容",
                            value=selected_template.content,
                            height=220,
                        )
                        edit_template_submitted = st.form_submit_button(
                            "保存模板",
                            use_container_width=True,
                        )

                    if edit_template_submitted:
                        if (
                            not edit_template_name.strip()
                            or not edit_template_content.strip()
                        ):
                            st.error("模板名称和模板内容不能为空。")
                        else:
                            try:
                                update_prompt_template(
                                    database_url,
                                    selected_template.id,
                                    PromptTemplateInput(
                                        name=edit_template_name,
                                        description=edit_template_description,
                                        content=edit_template_content,
                                        builtin=selected_template.builtin,
                                    ),
                                )
                                st.success("模板已保存。")
                                st.rerun()
                            except DuplicatePromptTemplateName as exc:
                                st.error(str(exc))
                            except PromptTemplateStorageError as exc:
                                st.error(f"保存失败：{exc}")

                    if st.button(
                        "删除当前模板",
                        use_container_width=True,
                        key=f"delete_prompt_template_{selected_template.id}",
                    ):
                        try:
                            delete_prompt_template(database_url, selected_template.id)
                            st.success("模板已删除。")
                            st.rerun()
                        except PromptTemplateStorageError as exc:
                            st.error(f"删除失败：{exc}")

            with template_new_tab:
                with st.form("new_prompt_template_form"):
                    new_template_name = st.text_input(
                        "模板名称", placeholder="例如：产品需求分析"
                    )
                    new_template_description = st.text_input(
                        "模板说明",
                        placeholder="描述适用场景，便于后续选择。",
                    )
                    new_template_content = st.text_area(
                        "模板内容",
                        height=220,
                        placeholder=(
                            "你是一名产品分析助手。\n"
                            "请围绕“{{产品名称}}”分析目标用户、核心痛点和改进建议。"
                        ),
                    )
                    new_template_submitted = st.form_submit_button(
                        "创建模板",
                        use_container_width=True,
                    )

                if new_template_submitted:
                    if (
                        not new_template_name.strip()
                        or not new_template_content.strip()
                    ):
                        st.error("模板名称和模板内容不能为空。")
                    else:
                        try:
                            create_prompt_template(
                                database_url,
                                build_prompt_template_input(
                                    new_template_name,
                                    new_template_description,
                                    new_template_content,
                                ),
                            )
                            st.success("模板已创建。")
                            st.rerun()
                        except DuplicatePromptTemplateName as exc:
                            st.error(str(exc))
                        except PromptTemplateStorageError as exc:
                            st.error(f"创建失败：{exc}")

    with model_tab:
        st.subheader("模型")
        model_presets = list_model_presets()
        model_presets_by_key = {preset.key: preset for preset in model_presets}

        session_model_selector_key = f"session_model_selector_{current_session.id}"
        selected_model_config_id = st.selectbox(
            "当前会话使用的模型",
            list(model_configs_by_id.keys()),
            index=list(model_configs_by_id.keys()).index(
                current_session.model_config_id
            ),
            key=session_model_selector_key,
            format_func=lambda config_id: model_config_label(
                model_configs_by_id[config_id]
            ),
            help="每个会话会单独记住自己的模型配置。",
        )
        if selected_model_config_id != current_session.model_config_id:
            try:
                update_session_model_config(
                    database_url, current_session.id, selected_model_config_id
                )
                st.rerun()
            except SessionStorageError as exc:
                st.error(f"切换模型失败：{exc}")

        current_config = model_configs_by_id[selected_model_config_id]
        st.caption(
            f"服务商：{current_config.provider or '未设置'} · "
            f"Base URL：{current_config.base_url or '默认 OpenAI 地址'}"
        )

        edit_tab, new_tab = st.tabs(["编辑当前配置", "新增模型配置"])

        with edit_tab:
            with st.form("edit_model_config_form"):
                edit_preset_key = st.selectbox(
                    "服务商预设",
                    list(model_presets_by_key.keys()),
                    key=f"edit_model_preset_{current_config.id}",
                    format_func=lambda preset_key: model_preset_label(
                        model_presets_by_key[preset_key]
                    ),
                    help="未填写的服务商、Base URL 和模型会自动套用预设默认值。",
                )
                selected_edit_preset = model_presets_by_key[edit_preset_key]
                if edit_preset_key != "custom":
                    st.caption(
                        "预设默认值："
                        f"{selected_edit_preset.provider} / "
                        f"{selected_edit_preset.base_url} / "
                        f"{selected_edit_preset.model_name}"
                    )
                edit_name = st.text_input("配置名称", value=current_config.name)
                edit_provider = st.text_input("服务商", value=current_config.provider)
                edit_api_key = st.text_input(
                    "API Key",
                    type="password",
                    value=current_config.api_key,
                    help="保存非空 API Key 前请先配置 APP_SECRET_KEY，数据库中会以密文形式持久化。",
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
                edit_test_col, edit_save_col = st.columns(2)
                with edit_test_col:
                    edit_test_submitted = st.form_submit_button(
                        "测试连接", use_container_width=True
                    )
                with edit_save_col:
                    edit_submitted = st.form_submit_button(
                        "保存当前配置", use_container_width=True
                    )

            edit_model_input = build_model_config_input(
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
                preset_key=edit_preset_key,
            )

            if edit_test_submitted:
                if not edit_model_input.model_name.strip():
                    st.error("连接测试前请先填写模型，或选择带默认模型的服务商预设。")
                else:
                    try:
                        st.success(test_model_connection(edit_model_input))
                    except ModelConnectionTestError as exc:
                        st.error(str(exc))

            if edit_submitted:
                if not edit_model_input.name.strip() or not edit_model_input.model_name.strip():
                    st.error("配置名称和模型不能为空。")
                else:
                    try:
                        update_model_config(
                            database_url,
                            current_config.id,
                            edit_model_input,
                        )
                        st.success("模型配置已保存。")
                        st.rerun()
                    except DuplicateModelConfigName as exc:
                        st.error(str(exc))
                    except ModelConfigStorageError as exc:
                        st.error(f"保存失败：{exc}")

            if st.button(
                "删除当前配置",
                disabled=len(model_configs) <= 1,
                use_container_width=True,
                key=f"delete_model_config_trigger_{current_config.id}",
            ):
                st.session_state.delete_model_config_confirming_id = current_config.id
                st.rerun()

        with new_tab:
            with st.form("new_model_config_form"):
                new_preset_key = st.selectbox(
                    "服务商预设",
                    list(model_presets_by_key.keys()),
                    key="new_model_preset",
                    format_func=lambda preset_key: model_preset_label(
                        model_presets_by_key[preset_key]
                    ),
                    help="未填写的服务商、Base URL 和模型会自动套用预设默认值。",
                )
                selected_new_preset = model_presets_by_key[new_preset_key]
                if new_preset_key != "custom":
                    st.caption(
                        "预设默认值："
                        f"{selected_new_preset.provider} / "
                        f"{selected_new_preset.base_url} / "
                        f"{selected_new_preset.model_name}"
                    )
                new_name = st.text_input("配置名称", placeholder="OpenAI GPT-4.1")
                new_provider = st.text_input("服务商", placeholder="OpenAI")
                new_api_key = st.text_input(
                    "API Key",
                    type="password",
                    placeholder="sk-xxxxxx",
                    help="保存非空 API Key 前请先配置 APP_SECRET_KEY，数据库中会以密文形式持久化。",
                )
                new_base_url = st.text_input(
                    "Base URL", placeholder="https://api.openai.com/v1"
                )
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
                new_test_col, new_create_col = st.columns(2)
                with new_test_col:
                    new_test_submitted = st.form_submit_button(
                        "测试连接", use_container_width=True
                    )
                with new_create_col:
                    new_submitted = st.form_submit_button(
                        "创建模型配置", use_container_width=True
                    )

            new_model_input = build_model_config_input(
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
                preset_key=new_preset_key,
            )

            if new_test_submitted:
                if not new_model_input.model_name.strip():
                    st.error("连接测试前请先填写模型，或选择带默认模型的服务商预设。")
                else:
                    try:
                        st.success(test_model_connection(new_model_input))
                    except ModelConnectionTestError as exc:
                        st.error(str(exc))

            if new_submitted:
                if not new_model_input.name.strip() or not new_model_input.model_name.strip():
                    st.error("配置名称和模型不能为空。")
                else:
                    try:
                        new_config_id = create_model_config(
                            database_url,
                            new_model_input,
                        )
                        update_session_model_config(
                            database_url, current_session.id, new_config_id
                        )
                        st.success("模型配置已创建。")
                        st.rerun()
                    except DuplicateModelConfigName as exc:
                        st.error(str(exc))
                    except ModelConfigStorageError as exc:
                        st.error(f"创建失败：{exc}")

        st.caption(
            "模型配置保存到 PostgreSQL。配置停用或未填写 API Key 时，本轮对话会使用本地回显。保存非空 API Key 前请先配置 APP_SECRET_KEY。"
        )
