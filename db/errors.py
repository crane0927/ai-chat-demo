from typing import Any, Callable, Optional

from db.connection import psycopg


def is_unique_violation(exc: Exception) -> bool:
    if psycopg is None:
        return False
    return isinstance(exc, psycopg.errors.UniqueViolation)


def execute_write(
    operation: Callable[[], Any],
    error_cls: type[Exception],
    generic_message: str,
    duplicate_error_cls: Optional[type[Exception]] = None,
    duplicate_message: str = "",
) -> Any:
    try:
        return operation()
    except Exception as exc:
        if duplicate_error_cls is not None and is_unique_violation(exc):
            raise duplicate_error_cls(duplicate_message) from exc
        if isinstance(exc, error_cls):
            raise
        raise error_cls(generic_message) from exc
