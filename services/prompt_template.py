import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List


try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None


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


def _connect(database_url: str):
    if psycopg is None or dict_row is None:
        raise PromptTemplateStorageError(
            "未安装 PostgreSQL 驱动，请先执行：pip install -r requirements.txt"
        )

    try:
        return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=3)
    except Exception as exc:
        raise PromptTemplateStorageError(
            "无法连接 PostgreSQL，请检查 APP_DATABASE_URL 或 DATABASE_URL。"
        ) from exc


def _is_unique_violation(exc: Exception) -> bool:
    if psycopg is None:
        return False
    return isinstance(exc, psycopg.errors.UniqueViolation)


def _execute_write(operation) -> Any:
    try:
        return operation()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise DuplicatePromptTemplateName("模板名称已存在，请换一个名称。") from exc
        if isinstance(exc, PromptTemplateStorageError):
            raise
        raise PromptTemplateStorageError("提示词模板写入 PostgreSQL 失败。") from exc


def init_prompt_template_db(database_url: str) -> None:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS prompt_templates (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    builtin BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


def ensure_default_prompt_templates(database_url: str) -> None:
    def operation() -> None:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM prompt_templates")
                total = cursor.fetchone()["total"]
                if total:
                    return

                # 首次初始化时注入常用模板，保证模板库开箱即可体验。
                cursor.executemany(
                    """
                    INSERT INTO prompt_templates (name, description, content, builtin)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                    """,
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

    _execute_write(operation)


def _row_to_prompt_template(row: Dict[str, Any]) -> PromptTemplate:
    return PromptTemplate(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        content=row["content"],
        builtin=bool(row["builtin"]),
    )


def list_prompt_templates(database_url: str) -> List[PromptTemplate]:
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, description, content, builtin
                FROM prompt_templates
                ORDER BY builtin DESC, lower(name) ASC, id ASC
                """
            )
            rows = cursor.fetchall()
    return [_row_to_prompt_template(row) for row in rows]


def create_prompt_template(database_url: str, template: PromptTemplateInput) -> int:
    def operation() -> int:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO prompt_templates (name, description, content, builtin)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        template.name.strip(),
                        template.description.strip(),
                        template.content.strip(),
                        template.builtin,
                    ),
                )
                return int(cursor.fetchone()["id"])

    return _execute_write(operation)


def update_prompt_template(
    database_url: str,
    template_id: int,
    template: PromptTemplateInput,
) -> None:
    def operation() -> None:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE prompt_templates
                    SET
                        name = %s,
                        description = %s,
                        content = %s,
                        builtin = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        template.name.strip(),
                        template.description.strip(),
                        template.content.strip(),
                        template.builtin,
                        template_id,
                    ),
                )

    _execute_write(operation)


def delete_prompt_template(database_url: str, template_id: int) -> None:
    def operation() -> None:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM prompt_templates WHERE id = %s", (template_id,))

    _execute_write(operation)


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
