import logging


LOGGER_NAME = "ai_chat_demo"


def get_app_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_request_started(
    *,
    session_id: int,
    model_name: str,
    mode_label: str,
    input_message_count: int,
    sent_message_count: int,
) -> None:
    trimmed_count = max(input_message_count - sent_message_count, 0)
    get_app_logger().info(
        "request_started session_id=%s mode=%s model=%s input_messages=%s sent_messages=%s trimmed_messages=%s",
        session_id,
        mode_label,
        model_name,
        input_message_count,
        sent_message_count,
        trimmed_count,
    )


def log_request_completed(
    *,
    session_id: int,
    model_name: str,
    elapsed_seconds: float,
    answer_source: str,
    input_message_count: int,
    sent_message_count: int,
) -> None:
    trimmed_count = max(input_message_count - sent_message_count, 0)
    get_app_logger().info(
        "request_completed session_id=%s model=%s elapsed_seconds=%.3f answer_source=%s input_messages=%s sent_messages=%s trimmed_messages=%s",
        session_id,
        model_name,
        elapsed_seconds,
        answer_source,
        input_message_count,
        sent_message_count,
        trimmed_count,
    )


def log_request_failed(
    *,
    session_id: int,
    model_name: str,
    elapsed_seconds: float,
    error_type: str,
    error_message: str,
    input_message_count: int,
    sent_message_count: int,
) -> None:
    trimmed_count = max(input_message_count - sent_message_count, 0)
    # 错误日志保留关键信息字段，方便后续直接在控制台按 session 或错误类型排查。
    get_app_logger().warning(
        "request_failed session_id=%s model=%s elapsed_seconds=%.3f error_type=%s error_message=%s input_messages=%s sent_messages=%s trimmed_messages=%s",
        session_id,
        model_name,
        elapsed_seconds,
        error_type,
        error_message,
        input_message_count,
        sent_message_count,
        trimmed_count,
    )
