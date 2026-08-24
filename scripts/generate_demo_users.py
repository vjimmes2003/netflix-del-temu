from pathlib import Path
import argparse
import calendar
import random
import sqlite3
from datetime import date, datetime

from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "instance" / "netflix_del_temu.sqlite3"

DEMO_PREFIX = "demo_"
DEMO_PASSWORD = "Demo1234!"
DEFAULT_SEED = 42
DEFAULT_COUNT = 100

# nombre, películas mín/max, episodios mín/max,
# series mín/max, favoritos mín/max, probabilidad de activo.
ARCHETYPES = (
    ("Cinéfilo", 45, 85, 8, 35, 2, 5, 18, 40, 0.97),
    ("Seriéfilo", 4, 18, 110, 210, 8, 16, 8, 24, 0.97),
    ("Maratoniano", 20, 50, 180, 280, 12, 20, 12, 32, 0.96),
    ("Casual", 2, 12, 5, 28, 1, 4, 2, 10, 0.94),
    ("Equilibrado", 20, 45, 55, 115, 5, 10, 10, 26, 0.97),
    ("Fin de semana", 12, 30, 35, 80, 4, 8, 7, 20, 0.96),
    ("Clásicos", 35, 70, 12, 45, 2, 6, 16, 34, 0.95),
    ("Favoritos", 8, 25, 25, 65, 3, 7, 35, 65, 0.97),
    ("Nuevo", 1, 7, 2, 16, 1, 3, 1, 7, 0.99),
    ("Intensivo", 50, 95, 120, 240, 10, 18, 20, 45, 0.95),
)


def get_connection():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"No existe la base de datos: {DATABASE_PATH}"
        )

    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def table_exists(db, table_name):
    return (
        db.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,),
        ).fetchone()
        is not None
    )


def clean_demo_users(db):
    rows = db.execute(
        "SELECT id FROM users WHERE username LIKE ?",
        (f"{DEMO_PREFIX}%",),
    ).fetchall()

    user_ids = [row["id"] for row in rows]

    if not user_ids:
        return 0

    marks = ",".join("?" for _ in user_ids)

    for table_name in (
        "favorites",
        "movie_watches",
        "episode_watches",
        "media_ratings",
        "season_ratings",
        "episode_ratings",
    ):
        if table_exists(db, table_name):
            db.execute(
                f"DELETE FROM {table_name} "
                f"WHERE user_id IN ({marks})",
                tuple(user_ids),
            )

    db.execute(
        f"DELETE FROM users WHERE id IN ({marks})",
        tuple(user_ids),
    )
    db.commit()
    return len(user_ids)


def last_six_months():
    today = date.today()
    current = today.year * 12 + today.month - 1
    months = []

    for offset in range(5, -1, -1):
        value = current - offset
        year, zero_based_month = divmod(value, 12)
        months.append((year, zero_based_month + 1))

    return months


def random_timestamp(rng, months):
    weights = (0.65, 0.80, 0.95, 1.10, 1.25, 1.45)
    year, month = rng.choices(
        months,
        weights=weights,
        k=1,
    )[0]

    max_day = calendar.monthrange(year, month)[1]
    today = date.today()

    if (year, month) == (today.year, today.month):
        max_day = min(max_day, today.day)

    return datetime(
        year,
        month,
        rng.randint(1, max_day),
        rng.randint(17, 23),
        rng.randint(0, 59),
        rng.randint(0, 59),
    ).strftime("%Y-%m-%d %H:%M:%S")


def load_catalog(db):
    movies = list(
        db.execute(
            """
            SELECT id
            FROM media
            WHERE media_type = 'movie'
              AND is_visible = 1
              AND content_level = 'general'
              AND runtime_minutes > 0
            """
        ).fetchall()
    )

    favorite_media = list(
        db.execute(
            """
            SELECT id
            FROM media
            WHERE is_visible = 1
              AND content_level = 'general'
            """
        ).fetchall()
    )

    episodes_by_series = {}
    rows = db.execute(
        """
        SELECT
            e.id,
            s.media_id
        FROM episodes AS e
        JOIN seasons AS s
          ON s.id = e.season_id
        JOIN media AS m
          ON m.id = s.media_id
        WHERE e.is_visible = 1
          AND s.is_visible = 1
          AND m.is_visible = 1
          AND m.media_type = 'series'
          AND m.content_level = 'general'
          AND e.runtime_minutes > 0
        ORDER BY
            s.media_id,
            e.id
        """
    ).fetchall()

    for row in rows:
        episodes_by_series.setdefault(
            row["media_id"],
            [],
        ).append(row["id"])

    return movies, favorite_media, episodes_by_series


def validate_catalog(movies, favorite_media, episodes_by_series):
    max_movies = max(profile[2] for profile in ARCHETYPES)
    max_episodes = max(profile[4] for profile in ARCHETYPES)
    max_series = max(profile[6] for profile in ARCHETYPES)
    max_favorites = max(profile[8] for profile in ARCHETYPES)

    if len(movies) < max_movies:
        raise RuntimeError(
            f"Faltan películas con duración: hay {len(movies)}."
        )

    if len(favorite_media) < max_favorites:
        raise RuntimeError(
            "No hay suficiente contenido general para favoritos."
        )

    if len(episodes_by_series) < max_series:
        raise RuntimeError(
            "No hay suficientes series con episodios importados."
        )

    if sum(map(len, episodes_by_series.values())) < max_episodes:
        raise RuntimeError(
            "No hay suficientes episodios con duración conocida."
        )


def choose_episodes(rng, episodes_by_series, total, series_target):
    available = list(episodes_by_series)
    selected_series = rng.sample(available, series_target)

    pools = {
        media_id: list(episodes_by_series[media_id])
        for media_id in selected_series
    }

    for pool in pools.values():
        rng.shuffle(pool)

    chosen = []

    while len(chosen) < total:
        added = False

        for media_id in selected_series:
            if pools[media_id]:
                chosen.append(pools[media_id].pop())
                added = True

                if len(chosen) == total:
                    break

        if added:
            continue

        remaining = [
            media_id
            for media_id in available
            if media_id not in selected_series
        ]

        if not remaining:
            break

        media_id = rng.choice(remaining)
        selected_series.append(media_id)
        pools[media_id] = list(
            episodes_by_series[media_id]
        )
        rng.shuffle(pools[media_id])

    if len(chosen) < total:
        raise RuntimeError(
            "No se pudieron seleccionar suficientes episodios."
        )

    return chosen


def build_profiles(rng, count):
    profiles = []

    for number in range(1, count + 1):
        archetype = ARCHETYPES[
            (number - 1) % len(ARCHETYPES)
        ]

        (
            label,
            movie_min,
            movie_max,
            episode_min,
            episode_max,
            series_min,
            series_max,
            favorite_min,
            favorite_max,
            active_probability,
        ) = archetype

        profiles.append(
            {
                "username": f"{DEMO_PREFIX}{number:03d}",
                "display_name": f"{label} {number:03d}",
                "movies": rng.randint(
                    movie_min,
                    movie_max,
                ),
                "episodes": rng.randint(
                    episode_min,
                    episode_max,
                ),
                "series": rng.randint(
                    series_min,
                    series_max,
                ),
                "favorites": rng.randint(
                    favorite_min,
                    favorite_max,
                ),
                "active": (
                    1
                    if rng.random() < active_probability
                    else 0
                ),
            }
        )

    return profiles


def create_user(db, profile, password_hash):
    cursor = db.execute(
        """
        INSERT INTO users (
            username,
            email,
            password_hash,
            display_name,
            role,
            country_code,
            is_active
        )
        VALUES (?, ?, ?, ?, 'client', 'ES', ?)
        """,
        (
            profile["username"],
            f"{profile['username']}@netflixdeltemu.test",
            password_hash,
            profile["display_name"],
            profile["active"],
        ),
    )

    return cursor.lastrowid


def fill_activity(
    db,
    rng,
    user_id,
    profile,
    movies,
    favorite_media,
    episodes_by_series,
    months,
):
    movie_ids = [
        row["id"]
        for row in rng.sample(
            movies,
            profile["movies"],
        )
    ]

    episode_ids = choose_episodes(
        rng,
        episodes_by_series,
        profile["episodes"],
        profile["series"],
    )

    favorite_ids = [
        row["id"]
        for row in rng.sample(
            favorite_media,
            profile["favorites"],
        )
    ]

    db.executemany(
        """
        INSERT OR IGNORE INTO movie_watches (
            user_id,
            media_id,
            watched_at
        )
        VALUES (?, ?, ?)
        """,
        [
            (
                user_id,
                media_id,
                random_timestamp(rng, months),
            )
            for media_id in movie_ids
        ],
    )

    db.executemany(
        """
        INSERT OR IGNORE INTO episode_watches (
            user_id,
            episode_id,
            watched_at
        )
        VALUES (?, ?, ?)
        """,
        [
            (
                user_id,
                episode_id,
                random_timestamp(rng, months),
            )
            for episode_id in episode_ids
        ],
    )

    db.executemany(
        """
        INSERT OR IGNORE INTO favorites (
            user_id,
            media_id
        )
        VALUES (?, ?)
        """,
        [
            (user_id, media_id)
            for media_id in favorite_ids
        ],
    )


def generate_demo(seed, count):
    if count < 1 or count > 500:
        raise ValueError(
            "El número de usuarios debe estar entre 1 y 500."
        )

    rng = random.Random(seed)
    db = get_connection()

    try:
        removed = clean_demo_users(db)
        movies, favorite_media, episodes_by_series = load_catalog(db)

        validate_catalog(
            movies,
            favorite_media,
            episodes_by_series,
        )

        months = last_six_months()
        profiles = build_profiles(rng, count)

        # Todos comparten contraseña: el hash se calcula una sola vez.
        password_hash = generate_password_hash(
            DEMO_PASSWORD
        )

        for profile in profiles:
            user_id = create_user(
                db,
                profile,
                password_hash,
            )

            fill_activity(
                db,
                rng,
                user_id,
                profile,
                movies,
                favorite_media,
                episodes_by_series,
                months,
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    active = sum(
        profile["active"]
        for profile in profiles
    )

    print(
        f"Usuarios demo eliminados previamente: {removed}"
    )
    print(
        f"Usuarios demo generados: {len(profiles)}"
    )
    print(
        f"Activos: {active} | "
        f"Inactivos: {len(profiles) - active}"
    )
    print(
        "Actividad distribuida en los últimos 6 meses."
    )
    print(
        f"Semilla utilizada: {seed}"
    )
    print(
        f"Contraseña común: {DEMO_PASSWORD}"
    )
    print(
        "Abre /admin/statistics para ver el resultado."
    )


def clean_only():
    db = get_connection()

    try:
        removed = clean_demo_users(db)
    finally:
        db.close()

    print(
        f"Usuarios demo eliminados: {removed}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Genera usuarios y actividad demo "
            "para las estadísticas administrativas."
        )
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Elimina únicamente usuarios demo_ "
            "y su actividad."
        ),
    )

    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=(
            "Número de usuarios demo. "
            f"Por defecto: {DEFAULT_COUNT}."
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=(
            "Semilla reproducible. "
            f"Por defecto: {DEFAULT_SEED}."
        ),
    )

    args = parser.parse_args()

    if args.clean:
        clean_only()
    else:
        generate_demo(
            args.seed,
            args.count,
        )


if __name__ == "__main__":
    main()
