from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .db import get_db


activity_bp = Blueprint("activity", __name__)


def get_mature_preferences(db):
    """Devuelve si MATURE está activo y si el +18 ya fue confirmado."""

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


def mature_content_is_enabled(db):
    """Devuelve únicamente si el contenido maduro está activo."""

    enabled, _ = get_mature_preferences(db)
    return enabled


def get_accessible_media(db, media_id):
    """
    Obtiene un contenido si el usuario puede verlo.

    General:
        siempre permitido.

    Mature:
        requiere que el usuario lo tenga activado.

    Explicit:
        nunca permitido para clientes.
    """

    mature_enabled = mature_content_is_enabled(db)

    return db.execute(
        """
        SELECT m.*
        FROM media AS m
        WHERE m.id = ?
          AND m.is_visible = 1
          AND m.content_level <> 'explicit'
          AND (
                m.content_level = 'general'
                OR (
                    m.content_level = 'mature'
                    AND ? = 1
                )
          )
        """,
        (
            media_id,
            int(mature_enabled),
        ),
    ).fetchone()


def get_accessible_episode(db, episode_id):
    """Obtiene un episodio si pertenece a una serie accesible."""

    mature_enabled = mature_content_is_enabled(db)

    return db.execute(
        """
        SELECT
            e.id,
            e.season_id,
            s.media_id
        FROM episodes AS e
        JOIN seasons AS s
          ON s.id = e.season_id
        JOIN media AS m
          ON m.id = s.media_id
        WHERE e.id = ?
          AND e.is_visible = 1
          AND s.is_visible = 1
          AND m.is_visible = 1
          AND m.media_type = 'series'
          AND m.content_level <> 'explicit'
          AND (
                m.content_level = 'general'
                OR (
                    m.content_level = 'mature'
                    AND ? = 1
                )
          )
        """,
        (
            episode_id,
            int(mature_enabled),
        ),
    ).fetchone()


def get_return_url(
    media_id=None,
    season_id=None,
):
    """
    Construye una redirección interna conocida.

    No se aceptan URLs arbitrarias del formulario.
    """

    return_to = request.form.get(
        "return_to",
        "detail",
    )

    if return_to == "favorites":
        return url_for(
            "activity.favorites"
        )

    if return_to == "watched":
        return url_for(
            "activity.watched"
        )

    if (
        return_to == "season"
        and media_id is not None
        and season_id is not None
    ):
        return url_for(
            "catalog.season_detail",
            media_id=media_id,
            season_id=season_id,
        )

    if media_id is not None:
        return url_for(
            "catalog.media_detail",
            media_id=media_id,
        )

    return url_for(
        "catalog.catalog"
    )


@activity_bp.route(
    "/activity/favorites/<int:media_id>/toggle",
    methods=("POST",),
)
@login_required
def toggle_favorite(media_id):
    """Añade o elimina una película/serie de favoritos."""

    db = get_db()

    media = get_accessible_media(
        db,
        media_id,
    )

    if media is None:
        abort(404)

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

    if favorite is None:
        db.execute(
            """
            INSERT INTO favorites (
                user_id,
                media_id
            )
            VALUES (?, ?)
            """,
            (
                current_user.id,
                media_id,
            ),
        )

    else:
        db.execute(
            """
            DELETE FROM favorites
            WHERE user_id = ?
              AND media_id = ?
            """,
            (
                current_user.id,
                media_id,
            ),
        )

    db.commit()

    return redirect(
        get_return_url(
            media_id=media_id
        )
    )


@activity_bp.route(
    "/activity/movies/<int:media_id>/toggle-watched",
    methods=("POST",),
)
@login_required
def toggle_movie_watched(media_id):
    """Marca o desmarca una película como vista."""

    db = get_db()

    media = get_accessible_media(
        db,
        media_id,
    )

    if (
        media is None
        or media["media_type"] != "movie"
    ):
        abort(404)

    watch = db.execute(
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

    if watch is None:
        db.execute(
            """
            INSERT INTO movie_watches (
                user_id,
                media_id
            )
            VALUES (?, ?)
            """,
            (
                current_user.id,
                media_id,
            ),
        )

    else:
        db.execute(
            """
            DELETE FROM movie_watches
            WHERE user_id = ?
              AND media_id = ?
            """,
            (
                current_user.id,
                media_id,
            ),
        )

    db.commit()

    return redirect(
        get_return_url(
            media_id=media_id
        )
    )


def get_accessible_season(db, season_id):
    """Obtiene una temporada si pertenece a una serie accesible."""

    mature_enabled = mature_content_is_enabled(db)

    return db.execute(
        """
        SELECT
            s.id,
            s.media_id
        FROM seasons AS s
        JOIN media AS m
          ON m.id = s.media_id
        WHERE s.id = ?
          AND s.is_visible = 1
          AND m.is_visible = 1
          AND m.media_type = 'series'
          AND m.content_level <> 'explicit'
          AND (
                m.content_level = 'general'
                OR (
                    m.content_level = 'mature'
                    AND ? = 1
                )
          )
        """,
        (season_id, int(mature_enabled)),
    ).fetchone()


@activity_bp.route(
    "/activity/seasons/<int:season_id>/toggle-watched",
    methods=("POST",),
)
@login_required
def toggle_season_watched(season_id):
    """Marca o desmarca todos los episodios visibles de una temporada."""

    db = get_db()
    season = get_accessible_season(db, season_id)

    if season is None:
        abort(404)

    total_episodes = db.execute(
        """
        SELECT COUNT(*)
        FROM episodes
        WHERE season_id = ?
          AND is_visible = 1
        """,
        (season_id,),
    ).fetchone()[0]

    if total_episodes == 0:
        return redirect(
            get_return_url(
                media_id=season["media_id"],
                season_id=season_id,
            )
        )

    watched_count = db.execute(
        """
        SELECT COUNT(*)
        FROM episode_watches AS ew
        JOIN episodes AS e
          ON e.id = ew.episode_id
        WHERE ew.user_id = ?
          AND e.season_id = ?
          AND e.is_visible = 1
        """,
        (current_user.id, season_id),
    ).fetchone()[0]

    if watched_count == total_episodes:
        db.execute(
            """
            DELETE FROM episode_watches
            WHERE user_id = ?
              AND episode_id IN (
                    SELECT id
                    FROM episodes
                    WHERE season_id = ?
                      AND is_visible = 1
              )
            """,
            (current_user.id, season_id),
        )
    else:
        db.execute(
            """
            INSERT OR IGNORE INTO episode_watches (
                user_id,
                episode_id
            )
            SELECT ?, id
            FROM episodes
            WHERE season_id = ?
              AND is_visible = 1
            """,
            (current_user.id, season_id),
        )

    db.commit()

    return redirect(
        get_return_url(
            media_id=season["media_id"],
            season_id=season_id,
        )
    )


@activity_bp.route(
    "/activity/episodes/<int:episode_id>/toggle-watched",
    methods=("POST",),
)
@login_required
def toggle_episode_watched(episode_id):
    """Marca o desmarca un episodio como visto."""

    db = get_db()

    episode = get_accessible_episode(
        db,
        episode_id,
    )

    if episode is None:
        abort(404)

    watch = db.execute(
        """
        SELECT 1
        FROM episode_watches
        WHERE user_id = ?
          AND episode_id = ?
        """,
        (
            current_user.id,
            episode_id,
        ),
    ).fetchone()

    if watch is None:
        db.execute(
            """
            INSERT INTO episode_watches (
                user_id,
                episode_id
            )
            VALUES (?, ?)
            """,
            (
                current_user.id,
                episode_id,
            ),
        )

    else:
        db.execute(
            """
            DELETE FROM episode_watches
            WHERE user_id = ?
              AND episode_id = ?
            """,
            (
                current_user.id,
                episode_id,
            ),
        )

    db.commit()

    return redirect(
        get_return_url(
            media_id=episode["media_id"],
            season_id=episode["season_id"],
        )
    )


@activity_bp.route("/favorites")
@login_required
def favorites():
    """Muestra los favoritos del usuario autenticado."""

    db = get_db()

    (
        mature_enabled,
        mature_confirmed,
    ) = get_mature_preferences(db)

    items = db.execute(
        """
        SELECT
            m.id,
            m.title,
            m.release_year,
            m.poster_path,
            m.tmdb_rating,
            m.media_type,
            m.content_level,
            m.certification,
            f.created_at AS favorite_since
        FROM favorites AS f
        JOIN media AS m
          ON m.id = f.media_id
        WHERE f.user_id = ?
          AND m.is_visible = 1
          AND m.content_level <> 'explicit'
          AND (
                m.content_level = 'general'
                OR (
                    m.content_level = 'mature'
                    AND ? = 1
                )
          )
        ORDER BY
            f.created_at DESC,
            m.title COLLATE NOCASE
        """,
        (
            current_user.id,
            int(mature_enabled),
        ),
    ).fetchall()

    return render_template(
        "favorites.html",
        items=items,
        mature_content_enabled=mature_enabled,
        mature_content_confirmed=mature_confirmed,
    )


@activity_bp.route("/watched")
@login_required
def watched():
    """
    Muestra películas vistas y series con episodios vistos.
    """

    db = get_db()

    (
        mature_enabled,
        mature_confirmed,
    ) = get_mature_preferences(db)

    movies = db.execute(
        """
        SELECT
            m.id,
            m.title,
            m.release_year,
            m.poster_path,
            m.tmdb_rating,
            m.content_level,
            m.certification,
            mw.watched_at
        FROM movie_watches AS mw
        JOIN media AS m
          ON m.id = mw.media_id
        WHERE mw.user_id = ?
          AND m.media_type = 'movie'
          AND m.is_visible = 1
          AND m.content_level <> 'explicit'
          AND (
                m.content_level = 'general'
                OR (
                    m.content_level = 'mature'
                    AND ? = 1
                )
          )
        ORDER BY
            mw.watched_at DESC,
            m.title COLLATE NOCASE
        """,
        (
            current_user.id,
            int(mature_enabled),
        ),
    ).fetchall()

    series = db.execute(
        """
        SELECT
            m.id,
            m.title,
            m.release_year,
            m.poster_path,
            m.tmdb_rating,
            m.content_level,
            m.certification,
            COUNT(DISTINCT ew.episode_id)
                AS watched_episodes,
            COUNT(DISTINCT e_all.id)
                AS available_episodes,
            MAX(ew.watched_at)
                AS last_watched_at
        FROM episode_watches AS ew
        JOIN episodes AS e
          ON e.id = ew.episode_id
        JOIN seasons AS s
          ON s.id = e.season_id
        JOIN media AS m
          ON m.id = s.media_id
        LEFT JOIN seasons AS s_all
          ON s_all.media_id = m.id
         AND s_all.is_visible = 1
        LEFT JOIN episodes AS e_all
          ON e_all.season_id = s_all.id
         AND e_all.is_visible = 1
        WHERE ew.user_id = ?
          AND e.is_visible = 1
          AND s.is_visible = 1
          AND m.media_type = 'series'
          AND m.is_visible = 1
          AND m.content_level <> 'explicit'
          AND (
                m.content_level = 'general'
                OR (
                    m.content_level = 'mature'
                    AND ? = 1
                )
          )
        GROUP BY
            m.id,
            m.title,
            m.release_year,
            m.poster_path,
            m.tmdb_rating,
            m.content_level,
            m.certification
        ORDER BY
            last_watched_at DESC,
            m.title COLLATE NOCASE
        """,
        (
            current_user.id,
            int(mature_enabled),
        ),
    ).fetchall()

    return render_template(
        "watched.html",
        movies=movies,
        series=series,
        mature_content_enabled=mature_enabled,
        mature_content_confirmed=mature_confirmed,
    )
