from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "instance"
    / "netflix_del_temu.sqlite3"
)


TABLES = (
    "media",
    "seasons",
    "episodes",
    "genres",
    "media_genres",
    "countries",
    "media_countries",
    "tags",
    "media_tags",
)


def main():
    connection = sqlite3.connect(DATABASE_PATH)

    print("=== ESTADO DEL CATÁLOGO ===\n")

    for table in TABLES:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(
            f"{table:<20} {count}"
        )

    movies = connection.execute(
        """
        SELECT COUNT(*)
        FROM media
        WHERE media_type = 'movie'
        """
    ).fetchone()[0]

    series = connection.execute(
        """
        SELECT COUNT(*)
        FROM media
        WHERE media_type = 'series'
        """
    ).fetchone()[0]

    print()
    print(f"Películas: {movies}")
    print(f"Series:    {series}")

    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    print(f"Integridad: {integrity}")

    connection.close()


if __name__ == "__main__":
    main()