from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import (
    get_env_base_url,
    get_env_chat_model,
    get_env_context_messages,
    get_env_max_retries,
    get_env_max_tokens,
    get_env_timeout_seconds,
)
from db.errors import execute_write
from repositories import model_config_repo


class ModelConfigStorageError(RuntimeError):
    pass


class DuplicateModelConfigName(ModelConfigStorageError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    id: int
    name: str
    provider: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float
    max_tokens: int
    context_message_limit: int
    timeout_seconds: float
    max_retries: int
    enabled: bool


@dataclass(frozen=True)
class ModelConfigInput:
    name: str
    provider: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float
    max_tokens: int
    context_message_limit: int
    timeout_seconds: float
    max_retries: int
    enabled: bool = True


def init_model_config_db(database_url: str) -> None:
    model_config_repo.init_model_config_db(database_url, ModelConfigStorageError)


def _row_to_model_config(row: Dict[str, Any]) -> ModelConfig:
    return ModelConfig(
        id=row["id"],
        name=row["name"],
        provider=row["provider"],
        api_key=row["api_key"],
        base_url=row["base_url"],
        model_name=row["model_name"],
        temperature=row["temperature"],
        max_tokens=row["max_tokens"],
        context_message_limit=row["context_message_limit"],
        timeout_seconds=row["timeout_seconds"],
        max_retries=row["max_retries"],
        enabled=bool(row["enabled"]),
    )


def ensure_default_model_config(database_url: str, api_key: str = "") -> None:
    def operation() -> None:
        count = model_config_repo.count_model_configs(database_url, ModelConfigStorageError)
        if count:
            return

        # 首次启动时把现有环境变量默认值落库，避免升级后用户还需要手动创建第一条配置。
        model_config_repo.insert_default_model_config(
            database_url,
            ModelConfigStorageError,
            {
                "name": "DeepSeek 默认",
                "provider": "DeepSeek",
                "api_key": api_key.strip(),
                "base_url": get_env_base_url(),
                "model_name": get_env_chat_model(),
                "temperature": 0.7,
                "max_tokens": get_env_max_tokens(),
                "context_message_limit": get_env_context_messages(),
                "timeout_seconds": get_env_timeout_seconds(),
                "max_retries": get_env_max_retries(),
                "enabled": True,
            },
        )

    execute_write(
        operation=operation,
        error_cls=ModelConfigStorageError,
        generic_message="模型配置写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicateModelConfigName,
        duplicate_message="配置名称已存在，请换一个名称。",
    )


def list_model_configs(database_url: str) -> List[ModelConfig]:
    rows = model_config_repo.list_model_config_rows(database_url, ModelConfigStorageError)
    return [_row_to_model_config(row) for row in rows]


def get_model_config(database_url: str, config_id: int) -> Optional[ModelConfig]:
    row = model_config_repo.get_model_config_row(database_url, ModelConfigStorageError, config_id)
    return _row_to_model_config(row) if row else None


def create_model_config(database_url: str, config: ModelConfigInput) -> int:
    def operation() -> int:
        # PostgreSQL 使用 RETURNING 获取新主键，避免依赖不同驱动的 lastrowid 行为。
        return model_config_repo.create_model_config(
            database_url,
            ModelConfigStorageError,
            {
                "name": config.name.strip(),
                "provider": config.provider.strip(),
                "api_key": config.api_key.strip(),
                "base_url": config.base_url.strip(),
                "model_name": config.model_name.strip(),
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "context_message_limit": config.context_message_limit,
                "timeout_seconds": config.timeout_seconds,
                "max_retries": config.max_retries,
                "enabled": config.enabled,
            },
        )

    return execute_write(
        operation=operation,
        error_cls=ModelConfigStorageError,
        generic_message="模型配置写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicateModelConfigName,
        duplicate_message="配置名称已存在，请换一个名称。",
    )


def update_model_config(database_url: str, config_id: int, config: ModelConfigInput) -> None:
    def operation() -> None:
        # 更新时间由数据库统一写入，便于以后做配置变更审计或按最近修改排序。
        model_config_repo.update_model_config(
            database_url,
            ModelConfigStorageError,
            config_id,
            {
                "name": config.name.strip(),
                "provider": config.provider.strip(),
                "api_key": config.api_key.strip(),
                "base_url": config.base_url.strip(),
                "model_name": config.model_name.strip(),
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "context_message_limit": config.context_message_limit,
                "timeout_seconds": config.timeout_seconds,
                "max_retries": config.max_retries,
                "enabled": config.enabled,
            },
        )

    execute_write(
        operation=operation,
        error_cls=ModelConfigStorageError,
        generic_message="模型配置写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicateModelConfigName,
        duplicate_message="配置名称已存在，请换一个名称。",
    )


def delete_model_config(database_url: str, config_id: int) -> None:
    def operation() -> None:
        model_config_repo.delete_model_config(database_url, ModelConfigStorageError, config_id)

    execute_write(
        operation=operation,
        error_cls=ModelConfigStorageError,
        generic_message="模型配置写入 PostgreSQL 失败。",
        duplicate_error_cls=DuplicateModelConfigName,
        duplicate_message="配置名称已存在，请换一个名称。",
    )
