try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None


def connect(database_url: str, error_cls: type[Exception]):
    if psycopg is None or dict_row is None:
        raise error_cls("未安装 PostgreSQL 驱动，请先执行：pip install -r requirements.txt")

    try:
        return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=3)
    except Exception as exc:
        raise error_cls("无法连接 PostgreSQL，请检查 APP_DATABASE_URL 或 DATABASE_URL。") from exc
