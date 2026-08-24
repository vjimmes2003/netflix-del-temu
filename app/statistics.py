from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .db import get_db


statistics_bp = Blueprint(
    "statistics",
    __name__,
)


def format_minutes(total_minutes):
    """Convierte minutos en una cadena legible."""

    total_minutes = int(
        total_minutes or 0
    )

    hours, minutes = divmod(
        total_minutes,
        60,
    )

    if hours and minutes:
        return f"{hours} h {minutes} min"

    if hours:
        return f"{hours} h"

    return f"{minutes} min"


def get_overview_stats(db):
    """Calcula métricas generales del usuario actual."""

    movie_stats = db.execute(
        """
        SELECT
            COUNT(*) AS watched_movies,
            COALESCE(
                SUM(
                    COALESCE(
                        m.runtime_minutes,
                        0
                    )
                ),
                0
            ) AS movie_minutes
        FROM movie_watches AS mw
        JOIN media AS m
          ON m.id = mw.media_id
        WHERE mw.user_id = ?
          AND m.media_type = 'movie'
        """,
        (current_user.id,),
    ).fetchone()

    episode_stats = db.execute(
        """
        SELECT
            COUNT(*) AS watched_episodes,
            COALESCE(
                SUM(
                    COALESCE(
                        e.runtime_minutes,
                        0
                    )
                ),
                0
            ) AS series_minutes,
            COUNT(
                DISTINCT s.media_id
            ) AS started_series
        FROM episode_watches AS ew
        JOIN episodes AS e
          ON e.id = ew.episode_id
        JOIN seasons AS s
          ON s.id = e.season_id
        WHERE ew.user_id = ?
        """,
        (current_user.id,),
    ).fetchone()

    favorite_count = db.execute(
        """
        SELECT COUNT(*)
        FROM favorites
        WHERE user_id = ?
        """,
        (current_user.id,),
    ).fetchone()[0]

    completed_series = db.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                m.id
            FROM media AS m
            JOIN seasons AS s
              ON s.media_id = m.id
             AND s.is_visible = 1
            JOIN episodes AS e
              ON e.season_id = s.id
             AND e.is_visible = 1
            LEFT JOIN episode_watches AS ew
              ON ew.episode_id = e.id
             AND ew.user_id = ?
            WHERE m.media_type = 'series'
            GROUP BY m.id
            HAVING
                COUNT(DISTINCT e.id) > 0
                AND COUNT(
                    DISTINCT ew.episode_id
                ) = COUNT(
                    DISTINCT e.id
                )
        ) AS completed
        """,
        (current_user.id,),
    ).fetchone()[0]

    movie_minutes = int(
        movie_stats["movie_minutes"]
        or 0
    )

    series_minutes = int(
        episode_stats["series_minutes"]
        or 0
    )

    total_minutes = (
        movie_minutes
        + series_minutes
    )

    if total_minutes > 0:
        movie_percent = round(
            movie_minutes * 100 / total_minutes
        )
        series_percent = 100 - movie_percent
    else:
        movie_percent = 0
        series_percent = 0

    if series_minutes > movie_minutes:
        dominant_label = "Series"
        dominant_percent = series_percent
    elif movie_minutes > series_minutes:
        dominant_label = "Películas"
        dominant_percent = movie_percent
    elif total_minutes > 0:
        dominant_label = "Películas y series"
        dominant_percent = 50
    else:
        dominant_label = "Sin tiempo registrado"
        dominant_percent = 0

    return {
        "watched_movies": int(
            movie_stats["watched_movies"]
            or 0
        ),
        "watched_episodes": int(
            episode_stats["watched_episodes"]
            or 0
        ),
        "started_series": int(
            episode_stats["started_series"]
            or 0
        ),
        "completed_series": int(
            completed_series
            or 0
        ),
        "favorites": int(
            favorite_count
            or 0
        ),
        "movie_minutes": movie_minutes,
        "series_minutes": series_minutes,
        "total_minutes": total_minutes,
        "movie_percent": movie_percent,
        "series_percent": series_percent,
        "dominant_label": dominant_label,
        "dominant_percent": dominant_percent,
        "movie_time_text": format_minutes(
            movie_minutes
        ),
        "series_time_text": format_minutes(
            series_minutes
        ),
        "total_time_text": format_minutes(
            total_minutes
        ),
    }


def get_monthly_activity(db):
    """
    Devuelve actividad de los últimos meses con registros.

    Se agrupan películas y episodios por YYYY-MM.
    """

    rows = db.execute(
        """
        SELECT
            month,
            SUM(movie_count) AS movies,
            SUM(episode_count) AS episodes
        FROM (
            SELECT
                strftime(
                    '%Y-%m',
                    watched_at
                ) AS month,
                COUNT(*) AS movie_count,
                0 AS episode_count
            FROM movie_watches
            WHERE user_id = ?
            GROUP BY month

            UNION ALL

            SELECT
                strftime(
                    '%Y-%m',
                    watched_at
                ) AS month,
                0 AS movie_count,
                COUNT(*) AS episode_count
            FROM episode_watches
            WHERE user_id = ?
            GROUP BY month
        )
        WHERE month IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
        """,
        (
            current_user.id,
            current_user.id,
        ),
    ).fetchall()

    rows = list(
        reversed(
            rows
        )
    )

    return {
        "labels": [
            row["month"]
            for row in rows
        ],
        "movies": [
            int(
                row["movies"]
                or 0
            )
            for row in rows
        ],
        "episodes": [
            int(
                row["episodes"]
                or 0
            )
            for row in rows
        ],
    }


def get_top_genres(db):
    """
    Calcula los géneros más presentes en el historial.

    Una película vista cuenta una vez.
    Una serie cuenta una vez si tiene al menos un episodio visto.
    """

    rows = db.execute(
        """
        SELECT
            genre_name,
            COUNT(*) AS total
        FROM (
            SELECT DISTINCT
                mg.genre_id,
                g.name AS genre_name,
                'movie' AS item_type,
                mw.media_id AS item_id
            FROM movie_watches AS mw
            JOIN media_genres AS mg
              ON mg.media_id = mw.media_id
            JOIN genres AS g
              ON g.id = mg.genre_id
            WHERE mw.user_id = ?

            UNION

            SELECT DISTINCT
                mg.genre_id,
                g.name AS genre_name,
                'series' AS item_type,
                s.media_id AS item_id
            FROM episode_watches AS ew
            JOIN episodes AS e
              ON e.id = ew.episode_id
            JOIN seasons AS s
              ON s.id = e.season_id
            JOIN media_genres AS mg
              ON mg.media_id = s.media_id
            JOIN genres AS g
              ON g.id = mg.genre_id
            WHERE ew.user_id = ?
        ) AS watched_genres
        GROUP BY genre_name
        ORDER BY
            total DESC,
            genre_name COLLATE NOCASE
        LIMIT 5
        """,
        (
            current_user.id,
            current_user.id,
        ),
    ).fetchall()

    return {
        "labels": [
            row["genre_name"]
            for row in rows
        ],
        "values": [
            int(
                row["total"]
                or 0
            )
            for row in rows
        ],
    }


def get_profile_initials():
    """Crea unas iniciales sencillas para el avatar del perfil."""

    source = (
        current_user.display_name
        or current_user.username
        or "U"
    ).strip()

    parts = [
        part
        for part in source.split()
        if part
    ]

    if len(parts) >= 2:
        return (
            parts[0][0]
            + parts[1][0]
        ).upper()

    return source[:2].upper()


@statistics_bp.route(
    "/profile"
)
@login_required
def user_profile():
    """Muestra el perfil personal y accesos a la actividad."""

    overview = get_overview_stats(
        get_db()
    )

    return render_template(
        "profile.html",
        overview=overview,
        profile_initials=get_profile_initials(),
    )


@statistics_bp.route(
    "/statistics"
)
@login_required
def user_statistics():
    """Muestra las estadísticas personales del usuario."""

    db = get_db()

    overview = get_overview_stats(
        db
    )

    monthly_activity = get_monthly_activity(
        db
    )

    top_genres = get_top_genres(
        db
    )

    chart_data = {
        "time": {
            "labels": [
                "Películas",
                "Series",
            ],
            "values": [
                overview[
                    "movie_minutes"
                ],
                overview[
                    "series_minutes"
                ],
            ],
        },
        "counts": {
            "labels": [
                "Películas vistas",
                "Series empezadas",
            ],
            "values": [
                overview[
                    "watched_movies"
                ],
                overview[
                    "started_series"
                ],
            ],
        },
        "monthly": monthly_activity,
        "genres": top_genres,
    }

    return render_template(
        "statistics.html",
        overview=overview,
        chart_data=chart_data,
    )
