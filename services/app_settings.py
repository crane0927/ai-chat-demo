from config import DEFAULT_SYSTEM_PROMPT
from repositories import app_settings_repo


class AppSettingsStorageError(RuntimeError):
    pass


def init_app_settings_db(database_url: str) -> None:
    app_settings_repo.init_app_settings_db(
        database_url,
        AppSettingsStorageError,
        DEFAULT_SYSTEM_PROMPT,
    )


def get_global_system_prompt(database_url: str) -> str:
    value = app_settings_repo.get_setting_value(
        database_url,
        AppSettingsStorageError,
        "global_system_prompt",
    )
    return value or DEFAULT_SYSTEM_PROMPT


def update_global_system_prompt(database_url: str, system_prompt: str) -> None:
    try:
        app_settings_repo.upsert_setting_value(
            database_url,
            AppSettingsStorageError,
            "global_system_prompt",
            system_prompt.strip() or DEFAULT_SYSTEM_PROMPT,
        )
    except AppSettingsStorageError:
        raise
    except Exception as exc:
        raise AppSettingsStorageError("保存全局默认提示词失败。") from exc
