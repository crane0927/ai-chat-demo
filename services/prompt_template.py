import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List
from db.errors import execute_write
from repositories import prompt_template_repo


class PromptTemplateStorageError(RuntimeError):
    pass


class DuplicatePromptTemplateName(PromptTemplateStorageError):
    pass


@dataclass(frozen=True)
class PromptTemplate:
    id: int
    name: str
    description: str
    content: str
    builtin: bool


@dataclass(frozen=True)
class PromptTemplateInput:
    name: str
    description: str
    content: str
    builtin: bool = False


PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\-\u4e00-\u9fff]+)\s*\}\}")


DEFAULT_PROMPT_TEMPLATES: List[PromptTemplateInput] = [
    PromptTemplateInput(
        name="写作助手",
        description="适合公众号、邮件、方案说明等通用写作场景。",
        content=(
            "你是一名资深写作助手。\n"
            "请围绕主题“{{主题}}”输出一份{{文体}}。\n"
            "目标读者：{{目标读者}}\n"
            "写作目标：{{写作目标}}\n"
            "风格要求：{{风格要求}}\n"
            "请先给出结构，再输出正文，并确保语言准确、自然、可直接使用。"
        ),
        builtin=True,
    ),
    PromptTemplateInput(
        name="代码审查",
        description="关注正确性、风险、测试缺口和可维护性。",
        content=(
            "你是一名严格但务实的代码审查助手。\n"
            "请审查以下改动：{{改动说明}}\n"
            "重点关注：{{关注点}}\n"
            "输出时请按严重级别排序，优先指出 bug、回归风险、边界条件和缺失测试，"
            "并给出简洁的修复建议。"
        ),
        builtin=True,
    ),
    PromptTemplateInput(
        name="SQL 助手",
        description="用于生成、优化和解释 SQL。",
        content=(
            "你是一名 SQL 助手。\n"
            "数据库类型：{{数据库类型}}\n"
            "业务目标：{{业务目标}}\n"
            "相关表结构：{{表结构}}\n"
            "请输出可执行 SQL，并解释关键查询思路、索引建议和潜在风险。"
        ),
        builtin=True,
    ),
    PromptTemplateInput(
        name="客服助手",
        description="适合用户咨询、售后答复和工单回复。",
        content=(
            "你是一名专业客服助手。\n"
            "产品/服务：{{产品或服务}}\n"
            "用户问题：{{用户问题}}\n"
            "处理原则：{{处理原则}}\n"
            "请给出礼貌、清晰、可执行的回复，并在必要时补充下一步操作建议。"
        ),
        builtin=True,
    ),
    PromptTemplateInput(
        name="学习教练",
        description="适合拆解学习计划、讲解难点和跟进练习。",
        content=(
            "你是一名学习教练。\n"
            "学习主题：{{学习主题}}\n"
            "当前水平：{{当前水平}}\n"
            "学习目标：{{学习目标}}\n"
            "可投入时间：{{可投入时间}}\n"
            "请制定循序渐进的学习方案，并给出每日或每周行动建议。"
        ),
        builtin=True,
    ),
]


def init_prompt_template_db(database_url: str) -> None:
    prompt_template_repo.init_prompt_template_db(
        database_url, PromptTemplateStorageError
    )


def ensure_default_prompt_templates(database_url: str) -> None:
    def operation() -> None:
        total = prompt_template_repo.count_prompt_templates(
            database_url,
            PromptTemplateStorageError,
        )
        if total:
            return

        # 首次初始化时注入常用模板，保证模板库开箱即可体验。
        prompt_template_repo.insert_default_prompt_templates(
            database_url,
            PromptTemplateStorageError,
            [
                (
                    template.name,
                    template.description,
                    template.content,
                    template.builtin,
                )
                for template in DEFAULT_PROMPT_TEMPLATES
            ],
        )

    execute_write(
        operation=operation,
        error_cls=PromptTemplateStorageError,
        generic_message="提示词模板写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicatePromptTemplateName,
        duplicate_message="模板名称已存在，请换一个名称。",
    )


def _row_to_prompt_template(row: Dict[str, Any]) -> PromptTemplate:
    return PromptTemplate(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        content=row["content"],
        builtin=bool(row["builtin"]),
    )


def list_prompt_templates(database_url: str) -> List[PromptTemplate]:
    rows = prompt_template_repo.list_prompt_template_rows(
        database_url,
        PromptTemplateStorageError,
    )
    return [_row_to_prompt_template(row) for row in rows]


def create_prompt_template(database_url: str, template: PromptTemplateInput) -> int:
    def operation() -> int:
        return prompt_template_repo.create_prompt_template(
            database_url,
            PromptTemplateStorageError,
            {
                "name": template.name.strip(),
                "description": template.description.strip(),
                "content": template.content.strip(),
                "builtin": template.builtin,
            },
        )

    return execute_write(
        operation=operation,
        error_cls=PromptTemplateStorageError,
        generic_message="提示词模板写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicatePromptTemplateName,
        duplicate_message="模板名称已存在，请换一个名称。",
    )


def update_prompt_template(
    database_url: str,
    template_id: int,
    template: PromptTemplateInput,
) -> None:
    def operation() -> None:
        prompt_template_repo.update_prompt_template(
            database_url,
            PromptTemplateStorageError,
            template_id,
            {
                "name": template.name.strip(),
                "description": template.description.strip(),
                "content": template.content.strip(),
                "builtin": template.builtin,
            },
        )

    execute_write(
        operation=operation,
        error_cls=PromptTemplateStorageError,
        generic_message="提示词模板写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicatePromptTemplateName,
        duplicate_message="模板名称已存在，请换一个名称。",
    )


def delete_prompt_template(database_url: str, template_id: int) -> None:
    def operation() -> None:
        prompt_template_repo.delete_prompt_template(
            database_url,
            PromptTemplateStorageError,
            template_id,
        )

    execute_write(
        operation=operation,
        error_cls=PromptTemplateStorageError,
        generic_message="提示词模板写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicatePromptTemplateName,
        duplicate_message="模板名称已存在，请换一个名称。",
    )


def extract_template_variables(content: str) -> List[str]:
    seen = set()
    ordered_names: List[str] = []
    for matched_name in PLACEHOLDER_PATTERN.findall(content or ""):
        if matched_name in seen:
            continue
        seen.add(matched_name)
        ordered_names.append(matched_name)
    return ordered_names


def render_prompt_template(content: str, variables: Dict[str, str]) -> str:
    # 模板渲染只替换声明过的占位符，未提供值时保留原占位符，方便用户继续补全。
    def replace_placeholder(match: re.Match[str]) -> str:
        variable_name = match.group(1)
        value = variables.get(variable_name, "")
        return value if value.strip() else match.group(0)

    return PLACEHOLDER_PATTERN.sub(replace_placeholder, content or "")


def build_template_variables_json(content: str) -> str:
    variable_names = extract_template_variables(content)
    return json.dumps(variable_names, ensure_ascii=False, indent=2)
