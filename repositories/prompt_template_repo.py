from db.connection import connect


def init_prompt_template_db(database_url: str, error_cls: type[Exception]) -> None:
    with connect(database_url, error_cls) as connection:
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


def count_prompt_templates(database_url: str, error_cls: type[Exception]) -> int:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM prompt_templates")
            return int(cursor.fetchone()["total"])


def insert_default_prompt_templates(
    database_url: str,
    error_cls: type[Exception],
    rows: list[tuple],
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO prompt_templates (name, description, content, builtin)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
                """,
                rows,
            )


def list_prompt_template_rows(database_url: str, error_cls: type[Exception]) -> list[dict]:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, description, content, builtin
                FROM prompt_templates
                ORDER BY builtin DESC, lower(name) ASC, id ASC
                """
            )
            return cursor.fetchall()


def create_prompt_template(
    database_url: str,
    error_cls: type[Exception],
    payload: dict,
) -> int:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO prompt_templates (name, description, content, builtin)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["name"],
                    payload["description"],
                    payload["content"],
                    payload["builtin"],
                ),
            )
            return int(cursor.fetchone()["id"])


def update_prompt_template(
    database_url: str,
    error_cls: type[Exception],
    template_id: int,
    payload: dict,
) -> None:
    with connect(database_url, error_cls) as connection:
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
                    payload["name"],
                    payload["description"],
                    payload["content"],
                    payload["builtin"],
                    template_id,
                ),
            )


def delete_prompt_template(
    database_url: str,
    error_cls: type[Exception],
    template_id: int,
) -> None:
    with connect(database_url, error_cls) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM prompt_templates WHERE id = %s", (template_id,))
