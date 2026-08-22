from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "instance"
    / "netflix_del_temu.sqlite3"
)


def get_columns(connection, table):
    """Devuelve los nombres de las columnas existentes en una tabla."""

    rows = connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


def main():
    connection = sqlite3.connect(DATABASE_PATH)

    user_columns = get_columns(
        connection,
        "users",
    )

    media_columns = get_columns(
        connection,
        "media",
    )

    if "mature_content_enabled" not in user_columns:
        connection.execute(
            """
            ALTER TABLE users
            ADD COLUMN mature_content_enabled INTEGER
            NOT NULL DEFAULT 0
            CHECK (
                mature_content_enabled IN (0, 1)
            )
            """
        )

    if "mature_content_confirmed_at" not in user_columns:
        connection.execute(
            """
            ALTER TABLE users
            ADD COLUMN mature_content_confirmed_at TEXT
            """
        )

    if "content_level" not in media_columns:
        connection.execute(
            """
            ALTER TABLE media
            ADD COLUMN content_level TEXT
            NOT NULL DEFAULT 'general'
            CHECK (
                content_level IN (
                    'general',
                    'mature',
                    'explicit'
                )
            )
            """
        )

    if "content_reason" not in media_columns:
        connection.execute(
            """
            ALTER TABLE media
            ADD COLUMN content_reason TEXT
            """
        )

    if "certification" not in media_columns:
        connection.execute(
            """
            ALTER TABLE media
            ADD COLUMN certification TEXT
            """
        )

    if "certification_country" not in media_columns:
        connection.execute(
            """
            ALTER TABLE media
            ADD COLUMN certification_country TEXT
            """
        )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_media_content_visibility
        ON media(
            media_type,
            is_visible,
            content_level
        )
        """
    )

    connection.commit()
    connection.close()

    print(
        "Migración de niveles de contenido completada."
    )


if __name__ == "__main__":
    main()
