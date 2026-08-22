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


def get_mature_preferences(db):
    """
    Obtiene el estado de la preferencia de contenido maduro.

    Devuelve:
        enabled:
            True cuando el contenido maduro está visible.

        confirmed:
            True cuando el usuario ya confirmó ser mayor de edad.
    """

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

    enabled = bool(
        row["mature_content_enabled"]
    )

    confirmed = (
        row["mature_content_confirmed_at"]
        is not None
    )

    return enabled, confirmed


def get_content_filter(mature_enabled):
    """
    Devuelve la condición SQL usada por el catálogo.

    general:
        visible para cualquier cliente.

    mature:
        visible únicamente cuando el usuario lo ha activado.

    explicit:
        nunca visible en el catálogo de clientes.
    """

    if mature_enabled:
        return """
            AND content_level IN (
                'general',
                'mature'
            )
        """

    return """
        AND content_level = 'general'
    """


@catalog_bp.route("/catalog")
@login_required
def catalog():
    """Muestra el catálogo paginado de películas o series."""

    media_type = request.args.get(
        "type",
        "movie",
    )

    if media_type not in VALID_MEDIA_TYPES:
        media_type = "movie"

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    if page < 1:
        page = 1

    db = get_db()

    (
        mature_enabled,
        mature_confirmed,
    ) = get_mature_preferences(db)

    content_filter = get_content_filter(
        mature_enabled
    )

    total_items = db.execute(
        f"""
        SELECT COUNT(*)
        FROM media
        WHERE media_type = ?
          AND is_visible = 1
          {content_filter}
        """,
        (media_type,),
    ).fetchone()[0]

    total_pages = max(
        1,
        (
            total_items
            + ITEMS_PER_PAGE
            - 1
        )
        // ITEMS_PER_PAGE,
    )

    if page > total_pages:
        page = total_pages

    offset = (
        page - 1
    ) * ITEMS_PER_PAGE

    media_items = db.execute(
        f"""
        SELECT
            id,
            title,
            release_year,
            poster_path,
            tmdb_rating,
            media_type,
            content_level,
            certification,
            certification_country
        FROM media
        WHERE media_type = ?
          AND is_visible = 1
          {content_filter}
        ORDER BY
            popularity DESC,
            title COLLATE NOCASE
        LIMIT ?
        OFFSET ?
        """,
        (
            media_type,
            ITEMS_PER_PAGE,
            offset,
        ),
    ).fetchall()

    return render_template(
        "catalog.html",
        media_items=media_items,
        media_type=media_type,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        mature_content_enabled=mature_enabled,
        mature_content_confirmed=mature_confirmed,
    )


@catalog_bp.route("/catalog/<int:media_id>")
@login_required
def media_detail(media_id):
    """Muestra la ficha completa de una película o serie."""

    db = get_db()

    (
        mature_enabled,
        mature_confirmed,
    ) = get_mature_preferences(db)

    content_filter = get_content_filter(
        mature_enabled
    )

    media = db.execute(
        f"""
        SELECT *
        FROM media
        WHERE id = ?
          AND is_visible = 1
          {content_filter}
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

    seasons = []

    if media["media_type"] == "series":
        seasons = db.execute(
            """
            SELECT
                id,
                season_number,
                name,
                air_date,
                episode_count,
                poster_path
            FROM seasons
            WHERE media_id = ?
              AND is_visible = 1
            ORDER BY season_number
            """,
            (media_id,),
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
    )


@catalog_bp.route(
    "/settings/content",
    methods=("GET", "POST"),
)
@login_required
def content_settings():
    """
    Primera confirmación para habilitar el control de contenido maduro.

    La primera activación requiere:
    - confirmar mayoría de edad;
    - introducir la contraseña actual.

    Después de esta confirmación el usuario puede utilizar el slider del
    catálogo para activar o desactivar contenido maduro sin repetir la
    contraseña.
    """

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
        user["mature_content_confirmed_at"]
        is not None
    )

    if request.method == "POST":
        action = request.form.get(
            "action",
            "",
        )

        if action == "confirm":
            if mature_confirmed:
                flash(
                    "La mayoría de edad ya está confirmada.",
                    "success",
                )

                return redirect(
                    url_for(
                        "catalog.content_settings"
                    )
                )

            confirmed_adult = (
                request.form.get(
                    "confirm_adult"
                )
                == "on"
            )

            password = request.form.get(
                "password",
                "",
            )

            if not confirmed_adult:
                flash(
                    "Debes confirmar que eres mayor de 18 años.",
                    "error",
                )

                return redirect(
                    url_for(
                        "catalog.content_settings"
                    )
                )

            if not password:
                flash(
                    "Debes introducir tu contraseña actual.",
                    "error",
                )

                return redirect(
                    url_for(
                        "catalog.content_settings"
                    )
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
                    url_for(
                        "catalog.content_settings"
                    )
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
                url_for(
                    "catalog.catalog"
                )
            )

        flash(
            "Acción no válida.",
            "error",
        )

        return redirect(
            url_for(
                "catalog.content_settings"
            )
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
    """
    Activa o desactiva rápidamente el contenido maduro.

    Solo está disponible después de que el usuario haya confirmado
    previamente su mayoría de edad.
    """

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
            url_for(
                "catalog.content_settings"
            )
        )

    enabled = (
        request.form.get("enabled")
        == "1"
    )

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

    return redirect(
        url_for(
            "catalog.catalog",
            type=media_type,
        )
    )
