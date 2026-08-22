from pathlib import Path
import argparse
import sqlite3
import sys

from dotenv import load_dotenv
import requests


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

load_dotenv(PROJECT_ROOT / ".env")

from app.tmdb_client import TMDBClient

EXPLICIT_KEYWORDS = {
    "hentai",
    "ecchi",
    "pornography",
    "pornographic",
    "softcore",
    "hardcore",
    "sexploitation",
    "adult animation",
}

def is_explicit_content(data, media_type):
    """Detecta contenido claramente explícito."""

    if data.get("adult") is True:
        return True

    keywords = extract_keywords(
        data,
        media_type,
    )

    keyword_names = {
        keyword.get("name", "")
        .strip()
        .casefold()
        for keyword in keywords
    }

    return any(
        blocked in keyword_names
        for blocked in EXPLICIT_KEYWORDS
    )

def apply_title_fallback(
    client,
    data,
    media_type,
):
    """Busca un título inglés si TMDB no tiene traducción española."""

    if media_type == "movie":
        title_key = "title"
        original_key = "original_title"
    else:
        title_key = "name"
        original_key = "original_name"

    title = data.get(title_key)
    original_title = data.get(original_key)
    original_language = data.get(
        "original_language"
    )

    # Español o inglés: no hace falta fallback.
    if original_language in ("es", "en"):
        return data

    # TMDB ya nos ha devuelto una traducción española.
    if title and title != original_title:
        return data

    if media_type == "movie":
        english_data = client.movie_details(
            data["id"],
            language="en-US",
        )
    else:
        english_data = client.series_details(
            data["id"],
            language="en-US",
        )

    english_title = english_data.get(
        title_key
    )

    if (
        english_title
        and english_title
        != english_data.get(original_key)
    ):
        data[title_key] = english_title

        if not data.get("overview"):
            data["overview"] = (
                english_data.get("overview")
            )

        return data

    return None


def get_connection():
    """Abre una conexión con la base de datos."""

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def extract_year(date):
    """Extrae el año de una fecha ISO."""

    if not date:
        return None

    try:
        return int(date[:4])
    except (TypeError, ValueError):
        return None

def positive_integer_or_none(value):
    """Convierte valores no positivos en NULL."""

    if value is None:
        return None

    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    return value if value > 0 else None

def get_media_id(db, tmdb_id, media_type):
    """Obtiene el ID local de un contenido."""

    row = db.execute(
        """
        SELECT id
        FROM media
        WHERE tmdb_id = ?
          AND media_type = ?
        """,
        (tmdb_id, media_type),
    ).fetchone()

    return row["id"]


def upsert_media(db, data, media_type):
    """Inserta o actualiza una película o serie."""

    if media_type == "movie":
        title = data["title"]
        original_title = data.get("original_title")
        release_date = data.get("release_date")
        runtime = positive_integer_or_none(
                    data.get("runtime")
                    )

    else:
        title = data["name"]
        original_title = data.get("original_name")
        release_date = data.get("first_air_date")
        runtime = None

    db.execute(
        """
        INSERT INTO media (
            tmdb_id,
            media_type,
            title,
            original_title,
            overview,
            release_date,
            release_year,
            runtime_minutes,
            original_language,
            poster_path,
            backdrop_path,
            tmdb_rating,
            tmdb_vote_count,
            popularity,
            source,
            last_synced_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, 'tmdb', CURRENT_TIMESTAMP
        )

        ON CONFLICT (tmdb_id, media_type)
        DO UPDATE SET
            title = excluded.title,
            original_title = excluded.original_title,
            overview = excluded.overview,
            release_date = excluded.release_date,
            release_year = excluded.release_year,
            runtime_minutes = excluded.runtime_minutes,
            original_language = excluded.original_language,
            poster_path = excluded.poster_path,
            backdrop_path = excluded.backdrop_path,
            tmdb_rating = excluded.tmdb_rating,
            tmdb_vote_count = excluded.tmdb_vote_count,
            popularity = excluded.popularity,
            source = 'tmdb',
            updated_at = CURRENT_TIMESTAMP,
            last_synced_at = CURRENT_TIMESTAMP
        """,
        (
            data["id"],
            media_type,
            title,
            original_title,
            data.get("overview"),
            release_date,
            extract_year(release_date),
            runtime,
            data.get("original_language"),
            data.get("poster_path"),
            data.get("backdrop_path"),
            data.get("vote_average"),
            data.get("vote_count"),
            data.get("popularity"),
        ),
    )

    return get_media_id(
        db,
        data["id"],
        media_type,
    )


def sync_genres(db, media_id, genres):
    """Sincroniza los géneros asociados al contenido."""

    db.execute(
        "DELETE FROM media_genres WHERE media_id = ?",
        (media_id,),
    )

    for genre in genres:
        db.execute(
            """
            INSERT INTO genres (name)
            VALUES (?)
            ON CONFLICT (name) DO NOTHING
            """,
            (genre["name"],),
        )

        genre_row = db.execute(
            """
            SELECT id
            FROM genres
            WHERE name = ?
            """,
            (genre["name"],),
        ).fetchone()

        db.execute(
            """
            INSERT OR IGNORE INTO media_genres (
                media_id,
                genre_id
            )
            VALUES (?, ?)
            """,
            (
                media_id,
                genre_row["id"],
            ),
        )


def sync_countries(db, media_id, countries):
    """Sincroniza países de producción."""

    db.execute(
        "DELETE FROM media_countries WHERE media_id = ?",
        (media_id,),
    )

    for country in countries:
        iso_code = country.get("iso_3166_1")
        name = country.get("name")

        if not iso_code or not name:
            continue

        db.execute(
            """
            INSERT INTO countries (
                iso_code,
                name
            )
            VALUES (?, ?)
            ON CONFLICT (iso_code)
            DO UPDATE SET
                name = excluded.name
            """,
            (
                iso_code,
                name,
            ),
        )

        country_row = db.execute(
            """
            SELECT id
            FROM countries
            WHERE iso_code = ?
            """,
            (iso_code,),
        ).fetchone()

        db.execute(
            """
            INSERT OR IGNORE INTO media_countries (
                media_id,
                country_id
            )
            VALUES (?, ?)
            """,
            (
                media_id,
                country_row["id"],
            ),
        )


def extract_keywords(data, media_type):
    """Obtiene las palabras clave devueltas por TMDB."""

    keywords_data = data.get("keywords") or {}

    if media_type == "movie":
        return keywords_data.get("keywords", [])

    return keywords_data.get("results", [])


def sync_tags(db, media_id, tags):
    """Sincroniza las etiquetas del contenido."""

    db.execute(
        "DELETE FROM media_tags WHERE media_id = ?",
        (media_id,),
    )

    for tag in tags:
        name = tag.get("name", "").strip()

        if not name:
            continue

        db.execute(
            """
            INSERT INTO tags (name)
            VALUES (?)
            ON CONFLICT (name) DO NOTHING
            """,
            (name,),
        )

        tag_row = db.execute(
            """
            SELECT id
            FROM tags
            WHERE name = ?
            """,
            (name,),
        ).fetchone()

        db.execute(
            """
            INSERT OR IGNORE INTO media_tags (
                media_id,
                tag_id
            )
            VALUES (?, ?)
            """,
            (
                media_id,
                tag_row["id"],
            ),
        )


def upsert_season(db, media_id, season):
    """Inserta o actualiza una temporada."""

    db.execute(
        """
        INSERT INTO seasons (
            tmdb_id,
            media_id,
            season_number,
            name,
            overview,
            poster_path,
            air_date,
            episode_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT (media_id, season_number)
        DO UPDATE SET
            tmdb_id = excluded.tmdb_id,
            name = excluded.name,
            overview = excluded.overview,
            poster_path = excluded.poster_path,
            air_date = excluded.air_date,
            episode_count = excluded.episode_count
        """,
        (
            season.get("id"),
            media_id,
            season["season_number"],
            season.get("name") or (
                f"Temporada {season['season_number']}"
            ),
            season.get("overview"),
            season.get("poster_path"),
            season.get("air_date"),
            season.get("episode_count"),
        ),
    )

    row = db.execute(
        """
        SELECT id
        FROM seasons
        WHERE media_id = ?
          AND season_number = ?
        """,
        (
            media_id,
            season["season_number"],
        ),
    ).fetchone()

    return row["id"]


def upsert_episode(db, season_id, episode):
    """Inserta o actualiza un episodio."""

    db.execute(
        """
        INSERT INTO episodes (
            tmdb_id,
            season_id,
            episode_number,
            name,
            overview,
            air_date,
            runtime_minutes,
            still_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT (season_id, episode_number)
        DO UPDATE SET
            tmdb_id = excluded.tmdb_id,
            name = excluded.name,
            overview = excluded.overview,
            air_date = excluded.air_date,
            runtime_minutes = excluded.runtime_minutes,
            still_path = excluded.still_path
        """,
        (
            episode.get("id"),
            season_id,
            episode["episode_number"],
            episode.get("name") or (
                f"Episodio {episode['episode_number']}"
            ),
            episode.get("overview"),
            episode.get("air_date"),
            positive_integer_or_none(episode.get("runtime")),
            episode.get("still_path"),
        ),
    )


def import_movie(client, db, tmdb_id):
    """Importa una película completa."""

    data = client.movie_details(tmdb_id)
    
    if is_explicit_content(
        data,
        "movie",
    ):
        print(
            f"[SKIP] Película {tmdb_id}: "
            "contenido explícito"
        )
        return


    data = apply_title_fallback(
        client,
        data,
        "movie",
    )

    if data is None:
        print(
            f"[SKIP] Película {tmdb_id}: "
            "sin título español o inglés"
        )
        return

    media_id = upsert_media(
        db,
        data,
        "movie",
    )

    sync_genres(
        db,
        media_id,
        data.get("genres", []),
    )

    sync_countries(
        db,
        media_id,
        data.get("production_countries", []),
    )

    sync_tags(
        db,
        media_id,
        extract_keywords(data, "movie"),
    )

    db.commit()

    print(
        f"[OK] Película: {data['title']}"
    )


def import_series(
    client,
    db,
    tmdb_id,
    include_episodes,
):
    """Importa una serie y opcionalmente sus episodios."""

    data = client.series_details(tmdb_id)
    
    if is_explicit_content(
        data,
        "series",
    ):
        print(
            f"[SKIP] Serie {tmdb_id}: "
            "contenido explícito"
        )
        return


    data = apply_title_fallback(
        client,
        data,
        "series",
    )

    if data is None:
        print(
            f"[SKIP] Serie {tmdb_id}: "
            "sin título español o inglés"
        )
        return

    media_id = upsert_media(
        db,
        data,
        "series",
    )

    sync_genres(
        db,
        media_id,
        data.get("genres", []),
    )

    sync_countries(
        db,
        media_id,
        data.get("production_countries", []),
    )

    sync_tags(
        db,
        media_id,
        extract_keywords(data, "series"),
    )

    for season in data.get("seasons", []):
        season_id = upsert_season(
            db,
            media_id,
            season,
        )

        if not include_episodes:
            continue

        season_data = client.season_details(
            tmdb_id,
            season["season_number"],
        )

        for episode in season_data.get(
            "episodes",
            [],
        ):
            upsert_episode(
                db,
                season_id,
                episode,
            )

    db.commit()

    print(
        f"[OK] Serie: {data['name']}"
    )


def discover_ids(
    client,
    media_type,
    limit,
):
    """Obtiene IDs únicos desde Discover."""

    ids = []
    seen_ids = set()
    page = 1

    while len(ids) < limit:
        if media_type == "movie":
            response = client.discover_movies(page)
        else:
            response = client.discover_series(page)

        results = response.get("results", [])

        if not results:
            break

        for item in results:
            tmdb_id = item.get("id")

            if not tmdb_id:
                continue

            if tmdb_id in seen_ids:
                continue

            seen_ids.add(tmdb_id)
            ids.append(tmdb_id)

            if len(ids) >= limit:
                break

        total_pages = response.get(
            "total_pages",
            page,
        )

        if page >= total_pages:
            break

        page += 1

    return ids


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Importa películas y series "
            "desde TMDB a SQLite."
        )
    )

    parser.add_argument(
        "--movies",
        type=int,
        default=10,
        help="Número de películas a importar.",
    )

    parser.add_argument(
        "--series",
        type=int,
        default=5,
        help="Número de series a importar.",
    )

    parser.add_argument(
        "--episodes",
        action="store_true",
        help=(
            "Importa también los episodios "
            "de cada serie."
        ),
    )

    args = parser.parse_args()

    if args.movies < 0 or args.series < 0:
        parser.error(
            "Las cantidades no pueden ser negativas."
        )

    print("=== IMPORTACIÓN TMDB ===")
    print(f"Películas: {args.movies}")
    print(f"Series: {args.series}")
    print(
        "Episodios: "
        f"{'Sí' if args.episodes else 'No'}"
    )
    print()

    client = TMDBClient()
    db = get_connection()

    movie_ids = discover_ids(
        client,
        "movie",
        args.movies,
    )

    series_ids = discover_ids(
        client,
        "series",
        args.series,
    )

    for tmdb_id in movie_ids:
        try:
            import_movie(
                client,
                db,
                tmdb_id,
            )

        except (
            requests.RequestException,
            sqlite3.Error,
            KeyError,
        ) as error:
            db.rollback()

            print(
                f"[ERROR] Película {tmdb_id}: "
                f"{error}"
            )

    for tmdb_id in series_ids:
        try:
            import_series(
                client,
                db,
                tmdb_id,
                args.episodes,
            )

        except (
            requests.RequestException,
            sqlite3.Error,
            KeyError,
        ) as error:
            db.rollback()

            print(
                f"[ERROR] Serie {tmdb_id}: "
                f"{error}"
            )

    db.close()

    print("\nImportación finalizada.")


if __name__ == "__main__":
    main()