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

DEMO_PROFILES = (
    ("demo_cinefilo", "Clara Cinéfila", 70, 18, 3, 30, 1),
    ("demo_series", "Sergio Series", 8, 160, 12, 15, 1),
    ("demo_maraton", "Marta Maratón", 35, 230, 18, 22, 1),
    ("demo_casual", "Carlos Casual", 6, 12, 2, 4, 1),
    ("demo_equilibrado", "Elena Equilibrada", 30, 80, 8, 18, 1),
    ("demo_findesemana", "Fran Fin de Semana", 18, 55, 6, 12, 1),
    ("demo_clasicos", "Lucía Clásicos", 50, 25, 4, 20, 1),
    ("demo_favoritos", "Nora Favoritos", 14, 40, 5, 55, 1),
    ("demo_nuevo", "Pablo Nuevo", 3, 7, 1, 3, 1),
    ("demo_retirado", "Raúl Retirado", 22, 65, 7, 10, 0),
)


def get_connection():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DATABASE_PATH}")

    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def table_exists(db, table_name):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone() is not None


def clean_demo_users(db):
    rows = db.execute(
        "SELECT id FROM users WHERE username LIKE ?",
        (f"{DEMO_PREFIX}%",),
    ).fetchall()
    user_ids = [row["id"] for row in rows]

    if not user_ids:
        return 0

    marks = ",".join("?" for _ in user_ids)
    related_tables = (
        "favorites",
        "movie_watches",
        "episode_watches",
        "media_ratings",
        "season_ratings",
        "episode_ratings",
    )

    for table_name in related_tables:
        if table_exists(db, table_name):
            db.execute(
                f"DELETE FROM {table_name} WHERE user_id IN ({marks})",
                tuple(user_ids),
            )

    db.execute(f"DELETE FROM users WHERE id IN ({marks})", tuple(user_ids))
    db.commit()
    return len(user_ids)


def last_six_months():
    today = date.today()
    current = today.year * 12 + today.month - 1
    result = []

    for offset in range(5, -1, -1):
        value = current - offset
        year, zero_based_month = divmod(value, 12)
        result.append((year, zero_based_month + 1))

    return result


def random_timestamp(rng, months):
    # Ligera tendencia ascendente para que la gráfica mensual tenga forma.
    weights = (0.65, 0.80, 0.95, 1.10, 1.25, 1.45)
    year, month = rng.choices(months, weights=weights, k=1)[0]
    max_day = calendar.monthrange(year, month)[1]
    today = date.today()

    if (year, month) == (today.year, today.month):
        max_day = min(max_day, today.day)

    return datetime(
        year,
        month,
        rng.randint(1, max_day),
        rng.randint(18, 23),
        rng.randint(0, 59),
        rng.randint(0, 59),
    ).strftime("%Y-%m-%d %H:%M:%S")


def load_catalog(db):
    movies = list(db.execute(
        """
        SELECT id
        FROM media
        WHERE media_type='movie'
          AND is_visible=1
          AND content_level='general'
          AND runtime_minutes > 0
        """
    ).fetchall())

    favorite_media = list(db.execute(
        """
        SELECT id
        FROM media
        WHERE is_visible=1
          AND content_level='general'
        """
    ).fetchall())

    episodes_by_series = {}
    rows = db.execute(
        """
        SELECT e.id, s.media_id
        FROM episodes AS e
        JOIN seasons AS s ON s.id = e.season_id
        JOIN media AS m ON m.id = s.media_id
        WHERE e.is_visible=1
          AND s.is_visible=1
          AND m.is_visible=1
          AND m.media_type='series'
          AND m.content_level='general'
          AND e.runtime_minutes > 0
        ORDER BY s.media_id, e.id
        """
    ).fetchall()

    for row in rows:
        episodes_by_series.setdefault(row["media_id"], []).append(row["id"])

    return movies, favorite_media, episodes_by_series


def validate_catalog(movies, favorite_media, episodes_by_series):
    max_movies = max(profile[2] for profile in DEMO_PROFILES)
    max_episodes = max(profile[3] for profile in DEMO_PROFILES)
    max_series = max(profile[4] for profile in DEMO_PROFILES)
    max_favorites = max(profile[5] for profile in DEMO_PROFILES)

    if len(movies) < max_movies:
        raise RuntimeError(f"Faltan películas con duración: hay {len(movies)}.")
    if len(favorite_media) < max_favorites:
        raise RuntimeError("No hay suficiente contenido general para favoritos.")
    if len(episodes_by_series) < max_series:
        raise RuntimeError("No hay suficientes series con episodios importados.")
    if sum(map(len, episodes_by_series.values())) < max_episodes:
        raise RuntimeError("No hay suficientes episodios con duración conocida.")


def choose_episodes(rng, episodes_by_series, total, series_target):
    available = list(episodes_by_series)
    selected_series = rng.sample(available, series_target)
    pools = {}

    for media_id in selected_series:
        pools[media_id] = list(episodes_by_series[media_id])
        rng.shuffle(pools[media_id])

    chosen = []

    while len(chosen) < total:
        added = False

        for media_id in selected_series:
            if pools[media_id]:
                chosen.append(pools[media_id].pop())
                added = True
                if len(chosen) == total:
                    break

        if not added:
            remaining = [m for m in available if m not in selected_series]
            if not remaining:
                break
            media_id = rng.choice(remaining)
            selected_series.append(media_id)
            pools[media_id] = list(episodes_by_series[media_id])
            rng.shuffle(pools[media_id])

    if len(chosen) < total:
        raise RuntimeError("No se pudieron seleccionar suficientes episodios.")

    return chosen


def create_user(db, username, display_name, active):
    cursor = db.execute(
        """
        INSERT INTO users (
            username, email, password_hash, display_name,
            role, country_code, is_active
        )
        VALUES (?, ?, ?, ?, 'client', 'ES', ?)
        """,
        (
            username,
            f"{username}@netflixdeltemu.test",
            generate_password_hash(DEMO_PASSWORD),
            display_name,
            active,
        ),
    )
    return cursor.lastrowid


def fill_activity(
    db,
    rng,
    user_id,
    movies_count,
    episodes_count,
    series_count,
    favorites_count,
    movies,
    favorite_media,
    episodes_by_series,
    months,
):
    movie_ids = [row["id"] for row in rng.sample(movies, movies_count)]
    episode_ids = choose_episodes(
        rng, episodes_by_series, episodes_count, series_count
    )
    favorite_ids = [row["id"] for row in rng.sample(
        favorite_media, favorites_count
    )]

    db.executemany(
        "INSERT OR IGNORE INTO movie_watches "
        "(user_id, media_id, watched_at) VALUES (?, ?, ?)",
        [(user_id, media_id, random_timestamp(rng, months)) for media_id in movie_ids],
    )
    db.executemany(
        "INSERT OR IGNORE INTO episode_watches "
        "(user_id, episode_id, watched_at) VALUES (?, ?, ?)",
        [(user_id, episode_id, random_timestamp(rng, months)) for episode_id in episode_ids],
    )
    db.executemany(
        "INSERT OR IGNORE INTO favorites (user_id, media_id) VALUES (?, ?)",
        [(user_id, media_id) for media_id in favorite_ids],
    )


def generate_demo(seed):
    rng = random.Random(seed)
    db = get_connection()

    try:
        removed = clean_demo_users(db)
        movies, favorite_media, episodes_by_series = load_catalog(db)
        validate_catalog(movies, favorite_media, episodes_by_series)
        months = last_six_months()

        for profile in DEMO_PROFILES:
            username, name, movies_n, episodes_n, series_n, favorites_n, active = profile
            user_id = create_user(db, username, name, active)
            fill_activity(
                db, rng, user_id,
                movies_n, episodes_n, series_n, favorites_n,
                movies, favorite_media, episodes_by_series, months,
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Usuarios demo eliminados previamente: {removed}")
    print(f"Usuarios demo generados: {len(DEMO_PROFILES)}")
    print("Actividad distribuida en los últimos 6 meses.")
    print(f"Contraseña común: {DEMO_PASSWORD}")
    print("Abre /admin/statistics para ver el resultado.")


def clean_only():
    db = get_connection()
    try:
        removed = clean_demo_users(db)
    finally:
        db.close()
    print(f"Usuarios demo eliminados: {removed}")


def main():
    parser = argparse.ArgumentParser(
        description="Genera actividad demo para las estadísticas administrativas."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Elimina únicamente usuarios demo_ y su actividad.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    if args.clean:
        clean_only()
    else:
        generate_demo(args.seed)


if __name__ == "__main__":
    main()
