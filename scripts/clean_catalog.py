from pathlib import Path
import argparse
import sqlite3
import sys

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "instance"
    / "netflix_del_temu.sqlite3"
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

load_dotenv(
    PROJECT_ROOT / ".env"
)

from app.content_policy import (
    apply_title_fallback,
    classify_content,
)
from app.tmdb_client import TMDBClient


def get_connection():
    """Abre una conexión con la base de datos."""

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def get_details(
    client,
    tmdb_id,
    media_type,
):
    """Obtiene los detalles de un contenido desde TMDB."""

    if media_type == "movie":
        return client.movie_details(
            tmdb_id,
            language="es-ES",
        )

    return client.series_details(
        tmdb_id,
        language="es-ES",
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Clasifica y sanea el catálogo "
            "importado desde TMDB."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica realmente los cambios.",
    )

    args = parser.parse_args()

    mode = (
        "APLICAR CAMBIOS"
        if args.apply
        else "SIMULACIÓN"
    )

    print("=== LIMPIEZA DEL CATÁLOGO ===")
    print(f"Modo: {mode}\n")

    client = TMDBClient()
    db = get_connection()

    contents = db.execute(
        """
        SELECT
            id,
            tmdb_id,
            media_type,
            title,
            is_visible,
            content_level
        FROM media
        WHERE source = 'tmdb'
          AND tmdb_id IS NOT NULL
        ORDER BY media_type, id
        """
    ).fetchall()

    general_count = 0
    mature_count = 0
    explicit_count = 0
    title_updates = 0
    errors = 0

    for item in contents:
        try:
            data = get_details(
                client,
                item["tmdb_id"],
                item["media_type"],
            )

            (
                content_level,
                reason,
                certification,
                certification_country,
            ) = classify_content(
                data,
                item["media_type"],
            )

            localized_data, title_source = (
                apply_title_fallback(
                    client,
                    data,
                    item["media_type"],
                )
            )

            new_title = None
            new_overview = None

            if localized_data is not None:
                if item["media_type"] == "movie":
                    new_title = localized_data.get(
                        "title"
                    )
                else:
                    new_title = localized_data.get(
                        "name"
                    )

                new_overview = localized_data.get(
                    "overview"
                )

            # Los títulos sin una alternativa legible no se consideran
            # pornográficos, pero sí se excluyen del catálogo del cliente.
            if localized_data is None:
                content_level = "explicit"
                reason = (
                    "Sin título español o inglés "
                    "legible"
                )

            if content_level == "general":
                general_count += 1

            elif content_level == "mature":
                mature_count += 1

                print(
                    f"[MATURE] "
                    f"{item['media_type']} "
                    f"#{item['tmdb_id']} "
                    f"{item['title']} "
                    f"-> {reason}"
                )

            else:
                explicit_count += 1

                print(
                    f"[EXPLICIT] "
                    f"{item['media_type']} "
                    f"#{item['tmdb_id']} "
                    f"{item['title']} "
                    f"-> {reason}"
                )

            if (
                new_title
                and new_title != item["title"]
            ):
                title_updates += 1

                print(
                    f"[TITLE] "
                    f"{item['title']} "
                    f"-> {new_title} "
                    f"({title_source})"
                )

            if args.apply:
                db.execute(
                    """
                    UPDATE media
                    SET
                        title = CASE
                            WHEN ? IS NOT NULL
                            THEN ?
                            ELSE title
                        END,

                        overview = CASE
                            WHEN ? IS NOT NULL
                                 AND ? <> ''
                            THEN ?
                            ELSE overview
                        END,

                        content_level = ?,
                        content_reason = ?,
                        certification = ?,
                        certification_country = ?,
                        updated_at = CURRENT_TIMESTAMP

                    WHERE id = ?
                    """,
                    (
                        new_title,
                        new_title,
                        new_overview,
                        new_overview,
                        new_overview,
                        content_level,
                        reason,
                        certification,
                        certification_country,
                        item["id"],
                    ),
                )

        except (
            requests.RequestException,
            sqlite3.Error,
            KeyError,
            ValueError,
        ) as error:
            errors += 1

            print(
                f"[ERROR] "
                f"{item['media_type']} "
                f"#{item['tmdb_id']}: "
                f"{error}"
            )

    if args.apply:
        db.commit()

    print("\n=== RESUMEN ===")
    print(
        f"Contenidos revisados: {len(contents)}"
    )
    print(
        f"General:              {general_count}"
    )
    print(
        f"Maduros:              {mature_count}"
    )
    print(
        f"Explícitos:           {explicit_count}"
    )
    print(
        f"Títulos actualizados: {title_updates}"
    )
    print(
        f"Errores:               {errors}"
    )

    if args.apply:
        stored_levels = db.execute(
            """
            SELECT
                content_level,
                COUNT(*) AS total
            FROM media
            GROUP BY content_level
            ORDER BY content_level
            """
        ).fetchall()

        print("\nClasificación guardada:")

        for row in stored_levels:
            print(
                f" - {row['content_level']}: "
                f"{row['total']}"
            )

    else:
        print(
            "\nNo se ha modificado "
            "la base de datos."
        )
        print(
            "Ejecuta con --apply "
            "para aplicar los cambios."
        )

    db.close()


if __name__ == "__main__":
    main()
