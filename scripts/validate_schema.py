from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


def expect_integrity_error(name, operation):
    try:
        operation()
        print(f"[ERROR] {name}")
        return False

    except sqlite3.IntegrityError:
        print(f"[OK]    {name}")
        return True


def main():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")

    with SCHEMA_PATH.open("r", encoding="utf-8") as file:
        connection.executescript(file.read())

    cursor = connection.cursor()

    print("\n=== VALIDACIÓN DEL ESQUEMA ===\n")

    # -----------------------------------------------------
    # Usuarios válidos
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO users (
            username,
            email,
            password_hash,
            display_name,
            role
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "victor",
            "victor@example.com",
            "hash",
            "Víctor",
            "client",
        ),
    )

    user_1 = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO users (
            username,
            email,
            password_hash,
            display_name,
            role
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "ana",
            "ana@example.com",
            "hash",
            "Ana",
            "client",
        ),
    )

    user_2 = cursor.lastrowid

    print("[OK]    Inserción de usuarios válidos")

    # -----------------------------------------------------
    # Restricciones de usuarios
    # -----------------------------------------------------

    expect_integrity_error(
        "Username duplicado bloqueado",
        lambda: cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                password_hash,
                display_name
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "VICTOR",
                "otro@example.com",
                "hash",
                "Otro",
            ),
        ),
    )

    expect_integrity_error(
        "Rol inválido bloqueado",
        lambda: cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                password_hash,
                display_name,
                role
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "test",
                "test@example.com",
                "hash",
                "Test",
                "superadmin",
            ),
        ),
    )

    # -----------------------------------------------------
    # Contenidos
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO media (
            tmdb_id,
            media_type,
            title,
            runtime_minutes
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            157336,
            "movie",
            "Interstellar",
            169,
        ),
    )

    movie_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO media (
            tmdb_id,
            media_type,
            title
        )
        VALUES (?, ?, ?)
        """,
        (
            70523,
            "series",
            "Dark",
        ),
    )

    series_id = cursor.lastrowid

    print("[OK]    Película y serie insertadas")

    # -----------------------------------------------------
    # Relación N:M favoritos
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO favorites (user_id, media_id)
        VALUES (?, ?)
        """,
        (user_1, movie_id),
    )

    cursor.execute(
        """
        INSERT INTO favorites (user_id, media_id)
        VALUES (?, ?)
        """,
        (user_1, series_id),
    )

    cursor.execute(
        """
        INSERT INTO favorites (user_id, media_id)
        VALUES (?, ?)
        """,
        (user_2, movie_id),
    )

    favorites_count = cursor.execute(
        "SELECT COUNT(*) FROM favorites"
    ).fetchone()[0]

    if favorites_count == 3:
        print("[OK]    Relación N:M User <-> Media")
    else:
        print("[ERROR] Relación N:M User <-> Media")

    expect_integrity_error(
        "Favorito duplicado bloqueado",
        lambda: cursor.execute(
            """
            INSERT INTO favorites (user_id, media_id)
            VALUES (?, ?)
            """,
            (user_1, movie_id),
        ),
    )

    # -----------------------------------------------------
    # Foreign Keys
    # -----------------------------------------------------

    expect_integrity_error(
        "Foreign Key inválida bloqueada",
        lambda: cursor.execute(
            """
            INSERT INTO favorites (user_id, media_id)
            VALUES (?, ?)
            """,
            (user_1, 999999),
        ),
    )

    # -----------------------------------------------------
    # Series -> Temporadas -> Episodios
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO seasons (
            media_id,
            season_number,
            name,
            episode_count
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            series_id,
            1,
            "Temporada 1",
            10,
        ),
    )

    season_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO episodes (
            season_id,
            episode_number,
            name,
            runtime_minutes
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            season_id,
            1,
            "Episodio 1",
            50,
        ),
    )

    episode_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO episode_watches (
            user_id,
            episode_id
        )
        VALUES (?, ?)
        """,
        (
            user_1,
            episode_id,
        ),
    )

    print("[OK]    Serie -> Temporada -> Episodio")
    print("[OK]    Registro de episodio visto")

    # -----------------------------------------------------
    # Valoraciones
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO media_ratings (
            user_id,
            media_id,
            rating
        )
        VALUES (?, ?, ?)
        """,
        (
            user_1,
            movie_id,
            9,
        ),
    )

    print("[OK]    Valoración válida 9/10")

    expect_integrity_error(
        "Valoración superior a 10 bloqueada",
        lambda: cursor.execute(
            """
            INSERT INTO media_ratings (
                user_id,
                media_id,
                rating
            )
            VALUES (?, ?, ?)
            """,
            (
                user_2,
                movie_id,
                11,
            ),
        ),
    )

    # -----------------------------------------------------
    # Integridad final
    # -----------------------------------------------------

    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    print(f"\nIntegridad final: {integrity}")

    connection.close()


if __name__ == "__main__":
    main()