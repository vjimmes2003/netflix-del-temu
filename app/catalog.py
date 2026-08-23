from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash

from .db import get_db


catalog_bp = Blueprint("catalog", __name__)

ITEMS_PER_PAGE = 24
VALID_MEDIA_TYPES = ("movie", "series")
VALID_SORT_OPTIONS = (
    "newest",
    "oldest",
    "rating",
    "popularity",
)
DEFAULT_SORT = "popularity"
MAX_SEARCH_LENGTH = 100


def get_mature_preferences(db):
    """Obtiene el estado de la preferencia de contenido maduro."""

    row = db.execute(
        """
        SELECT
            mature_content_enabled,
            mature_content_confirmed_at
        FROM users
        WHERE id = ?
          AND is_active = 1
        """,
        (current_user.id,),
    ).fetchone()

    if row is None:
        return False, False

    enabled = bool(row["mature_content_enabled"])
    confirmed = row["mature_content_confirmed_at"] is not None

    return enabled, confirmed


def get_content_filter(mature_enabled, alias="m"):
    """Devuelve la condición SQL para controlar niveles visibles."""

    if mature_enabled:
        return f"{alias}.content_level IN ('general', 'mature')"

    return f"{alias}.content_level = 'general'"


def escape_like(value):
    """Escapa caracteres especiales usados por LIKE."""

    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def get_order_by(sort_option):
    """Devuelve una ordenación SQL permitida."""

    sort_map = {
        "newest": """
            CASE
                WHEN m.release_date IS NULL
                    OR m.release_date = ''
                THEN 2
                WHEN m.release_date > DATE('now')
                THEN 1
                ELSE 0
            END,
            CASE
                WHEN m.release_date <= DATE('now')
                THEN m.release_date
            END DESC,
            CASE
                WHEN m.release_date > DATE('now')
                THEN m.release_date
            END ASC,
            m.popularity DESC,
            m.title COLLATE NOCASE
        """,
        "oldest": """
            CASE
                WHEN m.release_date IS NULL
                    OR m.release_date = ''
                THEN 1
                ELSE 0
            END,
            m.release_date ASC,
            m.title COLLATE NOCASE
        """,
        "rating": """
            CASE
                WHEN m.tmdb_rating IS NULL
                THEN 1
                ELSE 0
            END,
            m.tmdb_rating DESC,
            m.tmdb_vote_count DESC,
            m.popularity DESC,
            m.title COLLATE NOCASE
        """,
        "popularity": """
            m.popularity DESC,
            m.title COLLATE NOCASE
        """,
    }

    return sort_map.get(
        sort_option,
        sort_map[DEFAULT_SORT],
    )


def build_catalog_filters(
    media_type,
    mature_enabled,
    search_query="",
    genre_id=None,
):
    """Construye filtros SQL de forma segura."""

    conditions = [
        "m.media_type = ?",
        "m.is_visible = 1",
        get_content_filter(mature_enabled, alias="m"),
    ]

    params = [media_type]

    if search_query:
        escaped_query = escape_like(search_query)
        pattern = f"%{escaped_query}%"

        conditions.append(
            """
            (
                m.title LIKE ?
                    ESCAPE '\\'
                    COLLATE NOCASE
                OR
                COALESCE(m.original_title, '') LIKE ?
                    ESCAPE '\\'
                    COLLATE NOCASE
            )
            """
        )

        params.extend([pattern, pattern])

    if genre_id is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM media_genres AS mg_filter
                WHERE
                    mg_filter.media_id = m.id
                    AND mg_filter.genre_id = ?
            )
            """
        )
        params.append(genre_id)

    return " AND ".join(conditions), params


def get_available_genres(
    db,
    media_type,
    mature_enabled,
):
    """Devuelve los géneros disponibles para el catálogo actual."""

    content_filter = get_content_filter(
        mature_enabled,
        alias="m",
    )

    return db.execute(
        f"""
        SELECT DISTINCT
            g.id,
            g.name
        FROM genres AS g
        JOIN media_genres AS mg
          ON mg.genre_id = g.id
        JOIN media AS m
          ON m.id = mg.media_id
        WHERE
            m.media_type = ?
            AND m.is_visible = 1
            AND {content_filter}
        ORDER BY
            g.name COLLATE NOCASE
        """,
        (media_type,),
    ).fetchall()


@catalog_bp.route("/catalog")
@login_required
def catalog():
    """Muestra el catálogo con búsqueda, género y ordenación."""

    media_type = request.args.get("type", "movie")

    if media_type not in VALID_MEDIA_TYPES:
        media_type = "movie"

    page = request.args.get("page", 1, type=int)

    if page < 1:
        page = 1

    search_query = request.args.get("q", "").strip()

    if len(search_query) > MAX_SEARCH_LENGTH:
        search_query = search_query[:MAX_SEARCH_LENGTH]

    genre_id = request.args.get("genre", type=int)

    if genre_id is not None and genre_id <= 0:
        genre_id = None

    sort_option = request.args.get("sort", DEFAULT_SORT)

    if sort_option not in VALID_SORT_OPTIONS:
        sort_option = DEFAULT_SORT

    db = get_db()

    mature_enabled, mature_confirmed = get_mature_preferences(db)

    where_sql, filter_params = build_catalog_filters(
        media_type=media_type,
        mature_enabled=mature_enabled,
        search_query=search_query,
        genre_id=genre_id,
    )

    total_items = db.execute(
        f"""
        SELECT COUNT(*)
        FROM media AS m
        WHERE {where_sql}
        """,
        filter_params,
    ).fetchone()[0]

    total_pages = max(
        1,
        (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE,
    )

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * ITEMS_PER_PAGE

    order_by = get_order_by(sort_option)

    media_items = db.execute(
        f"""
        SELECT
            m.id,
            m.title,
            m.original_title,
            m.release_date,
            m.release_year,
            m.poster_path,
            m.tmdb_rating,
            m.tmdb_vote_count,
            m.media_type,
            m.content_level,
            m.certification,
            m.certification_country
        FROM media AS m
        WHERE {where_sql}
        ORDER BY
            {order_by}
        LIMIT ?
        OFFSET ?
        """,
        (
            *filter_params,
            ITEMS_PER_PAGE,
            offset,
        ),
    ).fetchall()

    genres = get_available_genres(
        db,
        media_type,
        mature_enabled,
    )

    return render_template(
        "catalog.html",
        media_items=media_items,
        media_type=media_type,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        mature_content_enabled=mature_enabled,
        mature_content_confirmed=mature_confirmed,
        search_query=search_query,
        genre_id=genre_id,
        genres=genres,
        sort_option=sort_option,
    )


@catalog_bp.route("/catalog/<int:media_id>")
@login_required
def media_detail(media_id):
    """Muestra la ficha completa de una película o serie."""

    db = get_db()

    mature_enabled, mature_confirmed = get_mature_preferences(db)

    content_filter = get_content_filter(
        mature_enabled,
        alias="m",
    )

    media = db.execute(
        f"""
        SELECT m.*
        FROM media AS m
        WHERE
            m.id = ?
            AND m.is_visible = 1
            AND {content_filter}
        """,
        (media_id,),
    ).fetchone()

    if media is None:
        abort(404)

    genres = db.execute(
        """
        SELECT g.name
        FROM genres AS g
        JOIN media_genres AS mg
          ON mg.genre_id = g.id
        WHERE mg.media_id = ?
        ORDER BY g.name COLLATE NOCASE
        """,
        (media_id,),
    ).fetchall()

    countries = db.execute(
        """
        SELECT
            c.iso_code,
            c.name
        FROM countries AS c
        JOIN media_countries AS mc
          ON mc.country_id = c.id
        WHERE mc.media_id = ?
        ORDER BY c.name COLLATE NOCASE
        """,
        (media_id,),
    ).fetchall()

    tags = db.execute(
        """
        SELECT t.name
        FROM tags AS t
        JOIN media_tags AS mt
          ON mt.tag_id = t.id
        WHERE mt.media_id = ?
        ORDER BY t.name COLLATE NOCASE
        LIMIT 15
        """,
        (media_id,),
    ).fetchall()

    favorite = db.execute(
        """
        SELECT 1
        FROM favorites
        WHERE user_id = ?
          AND media_id = ?
        """,
        (
            current_user.id,
            media_id,
        ),
    ).fetchone()

    is_favorite = favorite is not None

    movie_watched = False

    if media["media_type"] == "movie":
        movie_watch = db.execute(
            """
            SELECT 1
            FROM movie_watches
            WHERE user_id = ?
              AND media_id = ?
            """,
            (
                current_user.id,
                media_id,
            ),
        ).fetchone()

        movie_watched = (
            movie_watch is not None
        )

    seasons = []
    series_progress = None

    if media["media_type"] == "series":
        progress_row = db.execute(
            """
            SELECT
                COUNT(DISTINCT e.id) AS total_episodes,
                COUNT(DISTINCT ew.episode_id) AS watched_episodes
            FROM seasons AS s
            LEFT JOIN episodes AS e
              ON e.season_id = s.id
             AND e.is_visible = 1
            LEFT JOIN episode_watches AS ew
              ON ew.episode_id = e.id
             AND ew.user_id = ?
            WHERE s.media_id = ?
              AND s.is_visible = 1
            """,
            (current_user.id, media_id),
        ).fetchone()

        total_episodes = progress_row["total_episodes"] if progress_row else 0
        watched_episodes = progress_row["watched_episodes"] if progress_row else 0
        progress_percent = round(watched_episodes * 100 / total_episodes) if total_episodes else 0

        series_progress = {
            "total_episodes": total_episodes,
            "watched_episodes": watched_episodes,
            "percent": progress_percent,
            "completed": total_episodes > 0 and watched_episodes == total_episodes,
        }

        seasons = db.execute(
            """
            SELECT
                s.id,
                s.season_number,
                s.name,
                s.air_date,
                s.episode_count,
                s.poster_path,
                COUNT(e.id)
                    AS imported_episode_count,
                COUNT(ew.episode_id)
                    AS watched_episode_count,
                CASE
                    WHEN COUNT(e.id) > 0
                     AND COUNT(ew.episode_id) = COUNT(e.id)
                    THEN 1
                    ELSE 0
                END AS is_completed
            FROM seasons AS s
            LEFT JOIN episodes AS e
              ON e.season_id = s.id
             AND e.is_visible = 1
            LEFT JOIN episode_watches AS ew
              ON ew.episode_id = e.id
             AND ew.user_id = ?
            WHERE s.media_id = ?
              AND s.is_visible = 1
            GROUP BY
                s.id,
                s.season_number,
                s.name,
                s.air_date,
                s.episode_count,
                s.poster_path
            ORDER BY s.season_number
            """,
            (
                current_user.id,
                media_id,
            ),
        ).fetchall()

    return render_template(
        "media_detail.html",
        media=media,
        genres=genres,
        countries=countries,
        tags=tags,
        seasons=seasons,
        mature_content_enabled=mature_enabled,
        mature_content_confirmed=mature_confirmed,
        is_favorite=is_favorite,
        movie_watched=movie_watched,
        series_progress=series_progress,
    )


@catalog_bp.route(
    "/catalog/<int:media_id>/season/<int:season_id>"
)
@login_required
def season_detail(
    media_id,
    season_id,
):
    """Muestra los episodios disponibles de una temporada."""

    db = get_db()

    mature_enabled, mature_confirmed = (
        get_mature_preferences(db)
    )

    content_filter = get_content_filter(
        mature_enabled,
        alias="m",
    )

    media = db.execute(
        f"""
        SELECT m.*
        FROM media AS m
        WHERE m.id = ?
          AND m.media_type = 'series'
          AND m.is_visible = 1
          AND {content_filter}
        """,
        (media_id,),
    ).fetchone()

    if media is None:
        abort(404)

    season = db.execute(
        """
        SELECT *
        FROM seasons
        WHERE id = ?
          AND media_id = ?
          AND is_visible = 1
        """,
        (
            season_id,
            media_id,
        ),
    ).fetchone()

    if season is None:
        abort(404)

    episodes = db.execute(
        """
        SELECT
            e.id,
            e.episode_number,
            e.name,
            e.overview,
            e.air_date,
            e.runtime_minutes,
            e.still_path,
            CASE
                WHEN ew.episode_id IS NULL
                THEN 0
                ELSE 1
            END AS is_watched,
            ew.watched_at
        FROM episodes AS e
        LEFT JOIN episode_watches AS ew
          ON ew.episode_id = e.id
         AND ew.user_id = ?
        WHERE e.season_id = ?
          AND e.is_visible = 1
        ORDER BY e.episode_number
        """,
        (
            current_user.id,
            season_id,
        ),
    ).fetchall()

    watched_count = sum(
        1
        for episode in episodes
        if episode["is_watched"]
    )

    episode_count = len(episodes)
    season_percent = round(watched_count * 100 / episode_count) if episode_count else 0
    season_completed = episode_count > 0 and watched_count == episode_count

    return render_template(
        "season_detail.html",
        media=media,
        season=season,
        episodes=episodes,
        watched_count=watched_count,
        season_percent=season_percent,
        season_completed=season_completed,
        mature_content_enabled=mature_enabled,
        mature_content_confirmed=mature_confirmed,
    )


@catalog_bp.route(
    "/settings/content",
    methods=("GET", "POST"),
)
@login_required
def content_settings():
    """Primera confirmación para habilitar contenido maduro."""

    db = get_db()

    user = db.execute(
        """
        SELECT
            id,
            password_hash,
            mature_content_enabled,
            mature_content_confirmed_at
        FROM users
        WHERE id = ?
          AND is_active = 1
        """,
        (current_user.id,),
    ).fetchone()

    if user is None:
        abort(404)

    mature_confirmed = (
        user["mature_content_confirmed_at"] is not None
    )

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "confirm":
            if mature_confirmed:
                flash(
                    "La mayoría de edad ya está confirmada.",
                    "success",
                )
                return redirect(
                    url_for("catalog.content_settings")
                )

            confirmed_adult = (
                request.form.get("confirm_adult") == "on"
            )
            password = request.form.get("password", "")

            if not confirmed_adult:
                flash(
                    "Debes confirmar que eres mayor de 18 años.",
                    "error",
                )
                return redirect(
                    url_for("catalog.content_settings")
                )

            if not password:
                flash(
                    "Debes introducir tu contraseña actual.",
                    "error",
                )
                return redirect(
                    url_for("catalog.content_settings")
                )

            if not check_password_hash(
                user["password_hash"],
                password,
            ):
                flash(
                    "La contraseña introducida no es correcta.",
                    "error",
                )
                return redirect(
                    url_for("catalog.content_settings")
                )

            db.execute(
                """
                UPDATE users
                SET
                    mature_content_enabled = 1,
                    mature_content_confirmed_at =
                        CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (current_user.id,),
            )

            db.commit()

            flash(
                "Confirmación completada. Ya puedes usar el control rápido del catálogo.",
                "success",
            )

            return redirect(
                url_for("catalog.catalog")
            )

        flash("Acción no válida.", "error")

        return redirect(
            url_for("catalog.content_settings")
        )

    return render_template(
        "content_settings.html",
        mature_content_enabled=bool(
            user["mature_content_enabled"]
        ),
        mature_content_confirmed=mature_confirmed,
        mature_content_confirmed_at=(
            user["mature_content_confirmed_at"]
        ),
    )


@catalog_bp.route(
    "/settings/content/toggle",
    methods=("POST",),
)
@login_required
def toggle_mature_content():
    """Activa o desactiva rápidamente el contenido maduro."""

    db = get_db()

    user = db.execute(
        """
        SELECT
            mature_content_enabled,
            mature_content_confirmed_at
        FROM users
        WHERE id = ?
          AND is_active = 1
        """,
        (current_user.id,),
    ).fetchone()

    if user is None:
        abort(404)

    if user["mature_content_confirmed_at"] is None:
        flash(
            "Primero debes confirmar que eres mayor de 18 años.",
            "error",
        )
        return redirect(
            url_for("catalog.content_settings")
        )

    enabled = request.form.get("enabled") == "1"

    db.execute(
        """
        UPDATE users
        SET
            mature_content_enabled = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            int(enabled),
            current_user.id,
        ),
    )

    db.commit()

    media_type = request.form.get(
        "media_type",
        "movie",
    )

    if media_type not in VALID_MEDIA_TYPES:
        media_type = "movie"

    search_query = request.form.get(
        "q",
        "",
    ).strip()

    genre_id = request.form.get(
        "genre",
        type=int,
    )

    sort_option = request.form.get(
        "sort",
        DEFAULT_SORT,
    )

    if sort_option not in VALID_SORT_OPTIONS:
        sort_option = DEFAULT_SORT

    return_to = request.form.get(
        "return_to",
        "catalog",
    )

    if return_to == "favorites":
        return redirect(
            url_for(
                "activity.favorites"
            )
        )

    if return_to == "watched":
        return redirect(
            url_for(
                "activity.watched"
            )
        )

    redirect_args = {
        "type": media_type,
        "sort": sort_option,
    }

    if search_query:
        redirect_args["q"] = (
            search_query[:MAX_SEARCH_LENGTH]
        )

    if genre_id is not None and genre_id > 0:
        redirect_args["genre"] = genre_id

    return redirect(
        url_for(
            "catalog.catalog",
            **redirect_args,
        )
    )
