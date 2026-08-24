import re
import sqlite3
from datetime import datetime
from functools import wraps

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
from werkzeug.security import generate_password_hash

from .db import get_db


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
DISPLAY_NAME_MAX_LENGTH = 100
PASSWORD_MIN_LENGTH = 8

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def admin_required(view):
    """Restringe una vista a usuarios administradores."""

    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if getattr(
            current_user,
            "role",
            None,
        ) != "admin":
            abort(403)

        return view(
            *args,
            **kwargs,
        )

    return wrapped_view


def normalize_user_form(form):
    """Normaliza los campos comunes del formulario."""

    return {
        "username": form.get(
            "username",
            "",
        ).strip(),
        "email": form.get(
            "email",
            "",
        ).strip().casefold(),
        "display_name": form.get(
            "display_name",
            "",
        ).strip(),
        "country_code": form.get(
            "country_code",
            "ES",
        ).strip().upper(),
        "password": form.get(
            "password",
            "",
        ),
    }


def validate_user_form(
    data,
    password_required,
):
    """Valida los datos de alta o edición."""

    errors = []

    username = data["username"]
    email = data["email"]
    display_name = data["display_name"]
    country_code = data["country_code"]
    password = data["password"]

    if not (
        USERNAME_MIN_LENGTH
        <= len(username)
        <= USERNAME_MAX_LENGTH
    ):
        errors.append(
            "El usuario debe tener entre "
            f"{USERNAME_MIN_LENGTH} y "
            f"{USERNAME_MAX_LENGTH} caracteres."
        )

    if any(
        character.isspace()
        for character in username
    ):
        errors.append(
            "El nombre de usuario no puede "
            "contener espacios."
        )

    if not EMAIL_PATTERN.fullmatch(email):
        errors.append(
            "Introduce un correo electrónico válido."
        )

    if (
        not display_name
        or len(display_name)
        > DISPLAY_NAME_MAX_LENGTH
    ):
        errors.append(
            "El nombre visible es obligatorio "
            f"y admite hasta "
            f"{DISPLAY_NAME_MAX_LENGTH} caracteres."
        )

    if not (
        len(country_code) == 2
        and country_code.isalpha()
    ):
        errors.append(
            "El país debe indicarse mediante "
            "un código de dos letras."
        )

    if password_required and not password:
        errors.append(
            "La contraseña es obligatoria."
        )

    if (
        password
        and len(password)
        < PASSWORD_MIN_LENGTH
    ):
        errors.append(
            "La contraseña debe tener al menos "
            f"{PASSWORD_MIN_LENGTH} caracteres."
        )

    return errors


def user_conflict_exists(
    db,
    username,
    email,
    exclude_user_id=None,
):
    """Comprueba usuario o correo duplicados."""

    sql = """
        SELECT id
        FROM users
        WHERE (
            username = ? COLLATE NOCASE
            OR email = ? COLLATE NOCASE
        )
    """

    params = [
        username,
        email,
    ]

    if exclude_user_id is not None:
        sql += " AND id <> ?"
        params.append(
            exclude_user_id
        )

    return (
        db.execute(
            sql,
            tuple(params),
        ).fetchone()
        is not None
    )


def get_client_or_404(
    db,
    user_id,
):
    """Obtiene únicamente una cuenta de cliente."""

    user = db.execute(
        """
        SELECT
            id,
            username,
            email,
            display_name,
            country_code,
            is_active,
            created_at,
            updated_at
        FROM users
        WHERE id = ?
          AND role = 'client'
        """,
        (user_id,),
    ).fetchone()

    if user is None:
        abort(404)

    return user


@admin_bp.route("/")
@admin_required
def dashboard():
    """Panel principal de administración."""

    db = get_db()

    client_stats = db.execute(
        """
        SELECT
            COUNT(*) AS total_clients,
            SUM(
                CASE
                    WHEN is_active = 1
                    THEN 1
                    ELSE 0
                END
            ) AS active_clients,
            SUM(
                CASE
                    WHEN is_active = 0
                    THEN 1
                    ELSE 0
                END
            ) AS inactive_clients
        FROM users
        WHERE role = 'client'
        """
    ).fetchone()

    media_stats = db.execute(
        """
        SELECT
            SUM(
                CASE
                    WHEN media_type = 'movie'
                    THEN 1
                    ELSE 0
                END
            ) AS movies,
            SUM(
                CASE
                    WHEN media_type = 'series'
                    THEN 1
                    ELSE 0
                END
            ) AS series
        FROM media
        """
    ).fetchone()

    return render_template(
        "admin/dashboard.html",
        client_stats=client_stats,
        media_stats=media_stats,
    )


@admin_bp.route("/users")
@admin_required
def users():
    """Lista todas las cuentas registradas."""

    db = get_db()

    user_rows = db.execute(
        """
        SELECT
            id,
            username,
            email,
            display_name,
            role,
            country_code,
            is_active,
            created_at
        FROM users
        ORDER BY
            CASE
                WHEN role = 'admin'
                THEN 0
                ELSE 1
            END,
            is_active DESC,
            username COLLATE NOCASE
        """
    ).fetchall()

    total_clients = sum(
        1
        for user in user_rows
        if user["role"] == "client"
    )

    active_clients = sum(
        1
        for user in user_rows
        if (
            user["role"] == "client"
            and user["is_active"]
        )
    )

    return render_template(
        "admin/users.html",
        users=user_rows,
        total_clients=total_clients,
        active_clients=active_clients,
        inactive_clients=(
            total_clients
            - active_clients
        ),
    )


@admin_bp.route(
    "/users/create",
    methods=("GET", "POST"),
)
@admin_required
def create_user():
    """Crea una nueva cuenta de cliente."""

    form_data = {
        "username": "",
        "email": "",
        "display_name": "",
        "country_code": "ES",
        "password": "",
    }

    if request.method == "POST":
        form_data = normalize_user_form(
            request.form
        )

        errors = validate_user_form(
            form_data,
            password_required=True,
        )

        db = get_db()

        if user_conflict_exists(
            db,
            form_data["username"],
            form_data["email"],
        ):
            errors.append(
                "Ya existe una cuenta con ese "
                "usuario o correo."
            )

        if not errors:
            try:
                db.execute(
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
                    VALUES (
                        ?, ?, ?, ?,
                        'client', ?, 1
                    )
                    """,
                    (
                        form_data["username"],
                        form_data["email"],
                        generate_password_hash(
                            form_data["password"]
                        ),
                        form_data["display_name"],
                        form_data["country_code"],
                    ),
                )

                db.commit()

            except sqlite3.IntegrityError:
                db.rollback()

                errors.append(
                    "No se ha podido crear la cuenta "
                    "porque el usuario o correo "
                    "ya existe."
                )

        if not errors:
            flash(
                "Cliente creado correctamente.",
                "success",
            )

            return redirect(
                url_for(
                    "admin.users"
                )
            )

        for error in errors:
            flash(
                error,
                "error",
            )

    return render_template(
        "admin/user_form.html",
        page_title="Crear cliente",
        form_mode="create",
        form_data=form_data,
        user=None,
    )


@admin_bp.route(
    "/users/<int:user_id>/edit",
    methods=("GET", "POST"),
)
@admin_required
def edit_user(user_id):
    """Edita una cuenta de cliente."""

    db = get_db()

    user = get_client_or_404(
        db,
        user_id,
    )

    if request.method == "GET":
        form_data = {
            "username": user["username"],
            "email": user["email"],
            "display_name": (
                user["display_name"]
                or ""
            ),
            "country_code": (
                user["country_code"]
                or "ES"
            ),
            "password": "",
        }

    else:
        form_data = normalize_user_form(
            request.form
        )

        errors = validate_user_form(
            form_data,
            password_required=False,
        )

        if user_conflict_exists(
            db,
            form_data["username"],
            form_data["email"],
            exclude_user_id=user_id,
        ):
            errors.append(
                "Ya existe otra cuenta con ese "
                "usuario o correo."
            )

        if not errors:
            try:
                if form_data["password"]:
                    db.execute(
                        """
                        UPDATE users
                        SET
                            username = ?,
                            email = ?,
                            display_name = ?,
                            country_code = ?,
                            password_hash = ?,
                            updated_at =
                                CURRENT_TIMESTAMP
                        WHERE id = ?
                          AND role = 'client'
                        """,
                        (
                            form_data["username"],
                            form_data["email"],
                            form_data["display_name"],
                            form_data["country_code"],
                            generate_password_hash(
                                form_data["password"]
                            ),
                            user_id,
                        ),
                    )

                else:
                    db.execute(
                        """
                        UPDATE users
                        SET
                            username = ?,
                            email = ?,
                            display_name = ?,
                            country_code = ?,
                            updated_at =
                                CURRENT_TIMESTAMP
                        WHERE id = ?
                          AND role = 'client'
                        """,
                        (
                            form_data["username"],
                            form_data["email"],
                            form_data["display_name"],
                            form_data["country_code"],
                            user_id,
                        ),
                    )

                db.commit()

            except sqlite3.IntegrityError:
                db.rollback()

                errors.append(
                    "No se han podido guardar los "
                    "cambios porque el usuario o "
                    "correo ya existe."
                )

        if not errors:
            flash(
                "Cliente actualizado correctamente.",
                "success",
            )

            return redirect(
                url_for(
                    "admin.users"
                )
            )

        for error in errors:
            flash(
                error,
                "error",
            )

    return render_template(
        "admin/user_form.html",
        page_title="Editar cliente",
        form_mode="edit",
        form_data=form_data,
        user=user,
    )


@admin_bp.route(
    "/users/<int:user_id>/toggle-active",
    methods=("POST",),
)
@admin_required
def toggle_user_active(user_id):
    """Desactiva o reactiva un cliente."""

    db = get_db()

    user = get_client_or_404(
        db,
        user_id,
    )

    new_status = (
        0
        if user["is_active"]
        else 1
    )

    db.execute(
        """
        UPDATE users
        SET
            is_active = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND role = 'client'
        """,
        (
            new_status,
            user_id,
        ),
    )

    db.commit()

    if new_status:
        message = (
            f"El cliente {user['username']} "
            "ha sido reactivado."
        )
    else:
        message = (
            f"El cliente {user['username']} "
            "ha sido desactivado."
        )

    flash(
        message,
        "success",
    )

    return redirect(
        url_for(
            "admin.users"
        )
    )


# ============================================================
# FASE 9 — CRUD ADMINISTRATIVO DEL CATÁLOGO
# ============================================================

ADMIN_MEDIA_PER_PAGE = 25

VALID_MEDIA_TYPES = (
    "movie",
    "series",
)

VALID_CONTENT_LEVELS = (
    "general",
    "mature",
    "explicit",
)

VALID_VISIBILITY_FILTERS = (
    "all",
    "visible",
    "hidden",
)

VALID_SOURCE_FILTERS = (
    "all",
    "manual",
    "tmdb",
)

VALID_CONTENT_FILTERS = (
    "all",
    "general",
    "mature",
    "explicit",
)


def parse_positive_integer(
    value,
    field_name,
    required=False,
    maximum=None,
):
    """Convierte un campo entero positivo o devuelve error."""

    raw_value = (
        value or ""
    ).strip()

    if not raw_value:
        if required:
            return (
                None,
                f"{field_name} es obligatorio.",
            )

        return None, None

    try:
        number = int(
            raw_value
        )
    except ValueError:
        return (
            None,
            f"{field_name} debe ser un número entero.",
        )

    if number <= 0:
        return (
            None,
            f"{field_name} debe ser mayor que 0.",
        )

    if (
        maximum is not None
        and number > maximum
    ):
        return (
            None,
            f"{field_name} no puede superar {maximum}.",
        )

    return number, None


def validate_iso_date(
    value,
):
    """Valida una fecha opcional YYYY-MM-DD."""

    value = (
        value or ""
    ).strip()

    if not value:
        return None, None

    try:
        datetime.strptime(
            value,
            "%Y-%m-%d",
        )
    except ValueError:
        return (
            None,
            "La fecha debe tener formato YYYY-MM-DD.",
        )

    return value, None


def normalize_media_form(
    form,
):
    """Normaliza los datos del formulario de contenido."""

    media_type = form.get(
        "media_type",
        "movie",
    ).strip()

    content_level = form.get(
        "content_level",
        "general",
    ).strip()

    return {
        "media_type": media_type,
        "title": form.get(
            "title",
            "",
        ).strip(),
        "original_title": form.get(
            "original_title",
            "",
        ).strip(),
        "overview": form.get(
            "overview",
            "",
        ).strip(),
        "release_date": form.get(
            "release_date",
            "",
        ).strip(),
        "runtime_minutes": form.get(
            "runtime_minutes",
            "",
        ).strip(),
        "original_language": form.get(
            "original_language",
            "",
        ).strip().lower(),
        "poster_path": form.get(
            "poster_path",
            "",
        ).strip(),
        "backdrop_path": form.get(
            "backdrop_path",
            "",
        ).strip(),
        "content_level": content_level,
        "content_reason": form.get(
            "content_reason",
            "",
        ).strip(),
        "certification": form.get(
            "certification",
            "",
        ).strip(),
        "certification_country": form.get(
            "certification_country",
            "",
        ).strip().upper(),
        "season_count": form.get(
            "season_count",
            "",
        ).strip(),
        "episodes_per_season": form.get(
            "episodes_per_season",
            "",
        ).strip(),
        "episode_runtime_minutes": form.get(
            "episode_runtime_minutes",
            "",
        ).strip(),
    }


def validate_media_form(
    data,
    creating=False,
):
    """Valida película o serie antes de guardarla."""

    errors = []

    if data["media_type"] not in VALID_MEDIA_TYPES:
        errors.append(
            "El tipo de contenido no es válido."
        )

    if not data["title"]:
        errors.append(
            "El título es obligatorio."
        )

    if len(
        data["title"]
    ) > 255:
        errors.append(
            "El título no puede superar 255 caracteres."
        )

    release_date, date_error = validate_iso_date(
        data["release_date"]
    )

    if date_error:
        errors.append(
            date_error
        )

    runtime = None

    if data["media_type"] == "movie":
        runtime, runtime_error = parse_positive_integer(
            data["runtime_minutes"],
            "La duración",
            required=True,
            maximum=1000,
        )

        if runtime_error:
            errors.append(
                runtime_error
            )

    if (
        data["original_language"]
        and len(
            data["original_language"]
        ) > 10
    ):
        errors.append(
            "El idioma original no puede superar 10 caracteres."
        )

    if data["content_level"] not in VALID_CONTENT_LEVELS:
        errors.append(
            "La clasificación de contenido no es válida."
        )

    if (
        data["certification_country"]
        and (
            len(
                data["certification_country"]
            ) != 2
            or not data[
                "certification_country"
            ].isalpha()
        )
    ):
        errors.append(
            "El país de certificación debe tener dos letras."
        )

    structure = {
        "season_count": None,
        "episodes_per_season": None,
        "episode_runtime_minutes": None,
    }

    if (
        creating
        and data["media_type"] == "series"
    ):
        supplied_structure = any(
            (
                data["season_count"],
                data["episodes_per_season"],
                data["episode_runtime_minutes"],
            )
        )

        if supplied_structure:
            season_count, error = parse_positive_integer(
                data["season_count"],
                "El número de temporadas",
                required=True,
                maximum=50,
            )

            if error:
                errors.append(
                    error
                )

            episodes_per_season, error = parse_positive_integer(
                data["episodes_per_season"],
                "Los episodios por temporada",
                required=True,
                maximum=100,
            )

            if error:
                errors.append(
                    error
                )

            episode_runtime, error = parse_positive_integer(
                data["episode_runtime_minutes"],
                "La duración de episodio",
                required=True,
                maximum=600,
            )

            if error:
                errors.append(
                    error
                )

            structure = {
                "season_count": season_count,
                "episodes_per_season": episodes_per_season,
                "episode_runtime_minutes": episode_runtime,
            }

    return (
        errors,
        release_date,
        runtime,
        structure,
    )


def extract_release_year(
    release_date,
):
    """Obtiene el año de una fecha ISO."""

    if not release_date:
        return None

    return int(
        release_date[:4]
    )


def get_genres(
    db,
):
    """Devuelve los géneros disponibles para administración."""

    return db.execute(
        """
        SELECT
            id,
            name
        FROM genres
        ORDER BY name COLLATE NOCASE
        """
    ).fetchall()


def get_selected_genre_ids(
    form,
):
    """Convierte los géneros enviados a IDs enteros."""

    genre_ids = []

    for value in form.getlist(
        "genre_ids"
    ):
        try:
            genre_id = int(
                value
            )
        except ValueError:
            continue

        if genre_id > 0:
            genre_ids.append(
                genre_id
            )

    return sorted(
        set(
            genre_ids
        )
    )


def validate_genre_ids(
    db,
    genre_ids,
):
    """Garantiza que todos los géneros seleccionados existen."""

    if not genre_ids:
        return True

    placeholders = ",".join(
        "?"
        for _ in genre_ids
    )

    found = db.execute(
        f"""
        SELECT COUNT(*)
        FROM genres
        WHERE id IN ({placeholders})
        """,
        tuple(
            genre_ids
        ),
    ).fetchone()[0]

    return found == len(
        genre_ids
    )


def sync_media_genres_admin(
    db,
    media_id,
    genre_ids,
):
    """Sincroniza géneros asignados a una película o serie."""

    db.execute(
        """
        DELETE FROM media_genres
        WHERE media_id = ?
        """,
        (media_id,),
    )

    for genre_id in genre_ids:
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
                genre_id,
            ),
        )


def create_manual_series_structure(
    db,
    media_id,
    structure,
):
    """
    Crea temporadas y episodios genéricos para una serie manual.

    Solo se ejecuta durante la creación inicial.
    """

    season_count = structure[
        "season_count"
    ]

    episodes_per_season = structure[
        "episodes_per_season"
    ]

    runtime = structure[
        "episode_runtime_minutes"
    ]

    if not (
        season_count
        and episodes_per_season
        and runtime
    ):
        return

    for season_number in range(
        1,
        season_count + 1,
    ):
        cursor = db.execute(
            """
            INSERT INTO seasons (
                media_id,
                season_number,
                name,
                episode_count,
                is_visible
            )
            VALUES (?, ?, ?, ?, 1)
            """,
            (
                media_id,
                season_number,
                f"Temporada {season_number}",
                episodes_per_season,
            ),
        )

        season_id = (
            cursor.lastrowid
        )

        for episode_number in range(
            1,
            episodes_per_season + 1,
        ):
            db.execute(
                """
                INSERT INTO episodes (
                    season_id,
                    episode_number,
                    name,
                    runtime_minutes,
                    is_visible
                )
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    season_id,
                    episode_number,
                    f"Episodio {episode_number}",
                    runtime,
                ),
            )


def get_admin_media_or_404(
    db,
    media_id,
):
    """Obtiene un contenido sin aplicar filtros de cliente."""

    media = db.execute(
        """
        SELECT *
        FROM media
        WHERE id = ?
        """,
        (media_id,),
    ).fetchone()

    if media is None:
        abort(404)

    return media


@admin_bp.route(
    "/catalog"
)
@admin_required
def media_catalog():
    """Lista administrativa de películas y series."""

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    if page < 1:
        page = 1

    search_query = request.args.get(
        "q",
        "",
    ).strip()[:100]

    media_type = request.args.get(
        "type",
        "all",
    ).strip()

    visibility = request.args.get(
        "visibility",
        "all",
    ).strip()

    source = request.args.get(
        "source",
        "all",
    ).strip()

    content_level = request.args.get(
        "content_level",
        "all",
    ).strip()

    if media_type not in (
        "all",
        *VALID_MEDIA_TYPES,
    ):
        media_type = "all"

    if visibility not in VALID_VISIBILITY_FILTERS:
        visibility = "all"

    if source not in VALID_SOURCE_FILTERS:
        source = "all"

    if content_level not in VALID_CONTENT_FILTERS:
        content_level = "all"

    conditions = [
        "1 = 1"
    ]

    params = []

    if search_query:
        escaped = (
            search_query
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

        conditions.append(
            """
            (
                m.title LIKE ? ESCAPE '\\'
                OR m.original_title LIKE ? ESCAPE '\\'
            )
            """
        )

        like_value = (
            f"%{escaped}%"
        )

        params.extend(
            (
                like_value,
                like_value,
            )
        )

    if media_type != "all":
        conditions.append(
            "m.media_type = ?"
        )
        params.append(
            media_type
        )

    if visibility == "visible":
        conditions.append(
            "m.is_visible = 1"
        )
    elif visibility == "hidden":
        conditions.append(
            "m.is_visible = 0"
        )

    if source != "all":
        conditions.append(
            "m.source = ?"
        )
        params.append(
            source
        )

    if content_level != "all":
        conditions.append(
            "m.content_level = ?"
        )
        params.append(
            content_level
        )

    where_clause = " AND ".join(
        conditions
    )

    db = get_db()

    total_items = db.execute(
        f"""
        SELECT COUNT(*)
        FROM media AS m
        WHERE {where_clause}
        """,
        tuple(
            params
        ),
    ).fetchone()[0]

    total_pages = max(
        1,
        (
            total_items
            + ADMIN_MEDIA_PER_PAGE
            - 1
        )
        // ADMIN_MEDIA_PER_PAGE,
    )

    if page > total_pages:
        page = total_pages

    offset = (
        page - 1
    ) * ADMIN_MEDIA_PER_PAGE

    items = db.execute(
        f"""
        SELECT
            m.id,
            m.title,
            m.original_title,
            m.media_type,
            m.release_year,
            m.runtime_minutes,
            m.poster_path,
            m.source,
            m.is_visible,
            m.content_level,
            m.tmdb_id,
            GROUP_CONCAT(
                DISTINCT g.name
            ) AS genres
        FROM media AS m
        LEFT JOIN media_genres AS mg
          ON mg.media_id = m.id
        LEFT JOIN genres AS g
          ON g.id = mg.genre_id
        WHERE {where_clause}
        GROUP BY m.id
        ORDER BY
            m.is_visible DESC,
            m.title COLLATE NOCASE
        LIMIT ?
        OFFSET ?
        """,
        (
            *params,
            ADMIN_MEDIA_PER_PAGE,
            offset,
        ),
    ).fetchall()

    stats = db.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN media_type = 'movie'
                    THEN 1
                    ELSE 0
                END
            ) AS movies,
            SUM(
                CASE
                    WHEN media_type = 'series'
                    THEN 1
                    ELSE 0
                END
            ) AS series,
            SUM(
                CASE
                    WHEN is_visible = 0
                    THEN 1
                    ELSE 0
                END
            ) AS hidden
        FROM media
        """
    ).fetchone()

    return render_template(
        "admin/media_list.html",
        items=items,
        stats=stats,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        search_query=search_query,
        media_type=media_type,
        visibility=visibility,
        source=source,
        content_level=content_level,
    )


@admin_bp.route(
    "/catalog/create",
    methods=("GET", "POST"),
)
@admin_required
def create_media():
    """Crea manualmente una película o serie."""

    db = get_db()

    genres = get_genres(
        db
    )

    form_data = {
        "media_type": "movie",
        "title": "",
        "original_title": "",
        "overview": "",
        "release_date": "",
        "runtime_minutes": "",
        "original_language": "es",
        "poster_path": "",
        "backdrop_path": "",
        "content_level": "general",
        "content_reason": "",
        "certification": "",
        "certification_country": "ES",
        "season_count": "",
        "episodes_per_season": "",
        "episode_runtime_minutes": "",
    }

    selected_genres = []

    if request.method == "POST":
        form_data = normalize_media_form(
            request.form
        )

        selected_genres = get_selected_genre_ids(
            request.form
        )

        (
            errors,
            release_date,
            runtime,
            structure,
        ) = validate_media_form(
            form_data,
            creating=True,
        )

        if not validate_genre_ids(
            db,
            selected_genres,
        ):
            errors.append(
                "Uno de los géneros seleccionados no existe."
            )

        if not selected_genres:
            errors.append(
                "Selecciona al menos un género."
            )

        if not errors:
            try:
                cursor = db.execute(
                    """
                    INSERT INTO media (
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
                        source,
                        is_visible,
                        content_level,
                        content_reason,
                        certification,
                        certification_country,
                        updated_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        'manual', 1, ?, ?, ?, ?,
                        CURRENT_TIMESTAMP
                    )
                    """,
                    (
                        form_data["media_type"],
                        form_data["title"],
                        (
                            form_data["original_title"]
                            or None
                        ),
                        (
                            form_data["overview"]
                            or None
                        ),
                        release_date,
                        extract_release_year(
                            release_date
                        ),
                        (
                            runtime
                            if form_data["media_type"]
                            == "movie"
                            else None
                        ),
                        (
                            form_data["original_language"]
                            or None
                        ),
                        (
                            form_data["poster_path"]
                            or None
                        ),
                        (
                            form_data["backdrop_path"]
                            or None
                        ),
                        form_data["content_level"],
                        (
                            form_data["content_reason"]
                            or None
                        ),
                        (
                            form_data["certification"]
                            or None
                        ),
                        (
                            form_data[
                                "certification_country"
                            ]
                            or None
                        ),
                    ),
                )

                media_id = (
                    cursor.lastrowid
                )

                sync_media_genres_admin(
                    db,
                    media_id,
                    selected_genres,
                )

                if (
                    form_data["media_type"]
                    == "series"
                ):
                    create_manual_series_structure(
                        db,
                        media_id,
                        structure,
                    )

                db.commit()

            except sqlite3.IntegrityError:
                db.rollback()

                errors.append(
                    "No se ha podido crear el contenido "
                    "por una restricción de la base de datos."
                )

        if not errors:
            flash(
                "Contenido creado correctamente.",
                "success",
            )

            return redirect(
                url_for(
                    "admin.media_catalog"
                )
            )

        for error in errors:
            flash(
                error,
                "error",
            )

    return render_template(
        "admin/media_form.html",
        page_title="Crear contenido",
        form_mode="create",
        form_data=form_data,
        genres=genres,
        selected_genres=selected_genres,
        media=None,
        series_stats=None,
    )


@admin_bp.route(
    "/catalog/<int:media_id>/edit",
    methods=("GET", "POST"),
)
@admin_required
def edit_media(media_id):
    """Edita una película o serie existente."""

    db = get_db()

    media = get_admin_media_or_404(
        db,
        media_id,
    )

    genres = get_genres(
        db
    )

    current_genres = db.execute(
        """
        SELECT genre_id
        FROM media_genres
        WHERE media_id = ?
        """,
        (media_id,),
    ).fetchall()

    selected_genres = [
        row["genre_id"]
        for row in current_genres
    ]

    series_stats = None

    if media["media_type"] == "series":
        series_stats = db.execute(
            """
            SELECT
                COUNT(DISTINCT s.id)
                    AS seasons,
                COUNT(DISTINCT e.id)
                    AS episodes,
                ROUND(
                    AVG(e.runtime_minutes)
                )
                    AS average_runtime
            FROM seasons AS s
            LEFT JOIN episodes AS e
              ON e.season_id = s.id
            WHERE s.media_id = ?
            """,
            (media_id,),
        ).fetchone()

    if request.method == "GET":
        form_data = {
            "media_type": media["media_type"],
            "title": media["title"] or "",
            "original_title": (
                media["original_title"]
                or ""
            ),
            "overview": (
                media["overview"]
                or ""
            ),
            "release_date": (
                media["release_date"]
                or ""
            ),
            "runtime_minutes": (
                media["runtime_minutes"]
                or ""
            ),
            "original_language": (
                media["original_language"]
                or ""
            ),
            "poster_path": (
                media["poster_path"]
                or ""
            ),
            "backdrop_path": (
                media["backdrop_path"]
                or ""
            ),
            "content_level": (
                media["content_level"]
                or "general"
            ),
            "content_reason": (
                media["content_reason"]
                or ""
            ),
            "certification": (
                media["certification"]
                or ""
            ),
            "certification_country": (
                media["certification_country"]
                or ""
            ),
            "season_count": "",
            "episodes_per_season": "",
            "episode_runtime_minutes": "",
        }

    else:
        form_data = normalize_media_form(
            request.form
        )

        # Para no romper relaciones temporadas/episodios,
        # un contenido existente conserva su tipo.
        form_data["media_type"] = (
            media["media_type"]
        )

        selected_genres = get_selected_genre_ids(
            request.form
        )

        (
            errors,
            release_date,
            runtime,
            _,
        ) = validate_media_form(
            form_data,
            creating=False,
        )

        if not validate_genre_ids(
            db,
            selected_genres,
        ):
            errors.append(
                "Uno de los géneros seleccionados no existe."
            )

        if not selected_genres:
            errors.append(
                "Selecciona al menos un género."
            )

        if not errors:
            try:
                db.execute(
                    """
                    UPDATE media
                    SET
                        title = ?,
                        original_title = ?,
                        overview = ?,
                        release_date = ?,
                        release_year = ?,
                        runtime_minutes = ?,
                        original_language = ?,
                        poster_path = ?,
                        backdrop_path = ?,
                        content_level = ?,
                        content_reason = ?,
                        certification = ?,
                        certification_country = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        form_data["title"],
                        (
                            form_data["original_title"]
                            or None
                        ),
                        (
                            form_data["overview"]
                            or None
                        ),
                        release_date,
                        extract_release_year(
                            release_date
                        ),
                        (
                            runtime
                            if media["media_type"]
                            == "movie"
                            else None
                        ),
                        (
                            form_data["original_language"]
                            or None
                        ),
                        (
                            form_data["poster_path"]
                            or None
                        ),
                        (
                            form_data["backdrop_path"]
                            or None
                        ),
                        form_data["content_level"],
                        (
                            form_data["content_reason"]
                            or None
                        ),
                        (
                            form_data["certification"]
                            or None
                        ),
                        (
                            form_data[
                                "certification_country"
                            ]
                            or None
                        ),
                        media_id,
                    ),
                )

                sync_media_genres_admin(
                    db,
                    media_id,
                    selected_genres,
                )

                db.commit()

            except sqlite3.IntegrityError:
                db.rollback()

                errors.append(
                    "No se han podido guardar los cambios."
                )

        if not errors:
            flash(
                "Contenido actualizado correctamente.",
                "success",
            )

            return redirect(
                url_for(
                    "admin.media_catalog"
                )
            )

        for error in errors:
            flash(
                error,
                "error",
            )

    return render_template(
        "admin/media_form.html",
        page_title="Editar contenido",
        form_mode="edit",
        form_data=form_data,
        genres=genres,
        selected_genres=selected_genres,
        media=media,
        series_stats=series_stats,
    )


@admin_bp.route(
    "/catalog/<int:media_id>/toggle-visible",
    methods=("POST",),
)
@admin_required
def toggle_media_visible(media_id):
    """
    Elimina lógicamente o restaura contenido.

    No borra actividad, temporadas ni relaciones.
    """

    db = get_db()

    media = get_admin_media_or_404(
        db,
        media_id,
    )

    new_visibility = (
        0
        if media["is_visible"]
        else 1
    )

    db.execute(
        """
        UPDATE media
        SET
            is_visible = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            new_visibility,
            media_id,
        ),
    )

    db.commit()

    if new_visibility:
        message = (
            f"{media['title']} se ha restaurado "
            "en el catálogo."
        )
    else:
        message = (
            f"{media['title']} se ha eliminado "
            "del catálogo visible."
        )

    flash(
        message,
        "success",
    )

    return redirect(
        url_for(
            "admin.media_catalog"
        )
    )

# ============================================================
# FASE 11 — ESTADÍSTICAS ADMINISTRATIVAS
# ============================================================

ADMIN_STATS_STATUS_FILTERS = (
    "all",
    "active",
    "inactive",
)

ADMIN_STATS_SORTS = (
    "time",
    "records",
    "favorites",
    "username",
)


def format_admin_minutes(total_minutes):
    """Convierte minutos en una duración legible."""

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


def get_admin_client_statistics(
    db,
    search_query="",
    status="all",
    sort="time",
):
    """Obtiene métricas comparables de las cuentas cliente."""

    where_clauses = [
        "u.role = 'client'",
    ]

    params = []

    if search_query:
        search_value = (
            f"%{search_query}%"
        )

        where_clauses.append(
            """
            (
                u.username LIKE ? COLLATE NOCASE
                OR COALESCE(
                    u.display_name,
                    ''
                ) LIKE ? COLLATE NOCASE
                OR u.email LIKE ? COLLATE NOCASE
            )
            """
        )

        params.extend(
            [
                search_value,
                search_value,
                search_value,
            ]
        )

    if status == "active":
        where_clauses.append(
            "u.is_active = 1"
        )
    elif status == "inactive":
        where_clauses.append(
            "u.is_active = 0"
        )

    order_by = {
        "time": (
            "total_minutes DESC, "
            "total_records DESC, "
            "u.username COLLATE NOCASE"
        ),
        "records": (
            "total_records DESC, "
            "total_minutes DESC, "
            "u.username COLLATE NOCASE"
        ),
        "favorites": (
            "favorites DESC, "
            "total_minutes DESC, "
            "u.username COLLATE NOCASE"
        ),
        "username": (
            "u.username COLLATE NOCASE ASC"
        ),
    }[sort]

    where_sql = " AND ".join(
        where_clauses
    )

    rows = db.execute(
        f"""
        WITH movie_activity AS (
            SELECT
                mw.user_id,
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
            WHERE m.media_type = 'movie'
            GROUP BY mw.user_id
        ),
        episode_activity AS (
            SELECT
                ew.user_id,
                COUNT(*) AS watched_episodes,
                COUNT(
                    DISTINCT s.media_id
                ) AS started_series,
                COALESCE(
                    SUM(
                        COALESCE(
                            e.runtime_minutes,
                            0
                        )
                    ),
                    0
                ) AS series_minutes
            FROM episode_watches AS ew
            JOIN episodes AS e
              ON e.id = ew.episode_id
            JOIN seasons AS s
              ON s.id = e.season_id
            GROUP BY ew.user_id
        ),
        favorite_activity AS (
            SELECT
                user_id,
                COUNT(*) AS favorites
            FROM favorites
            GROUP BY user_id
        )
        SELECT
            u.id,
            u.username,
            u.email,
            u.display_name,
            u.is_active,
            COALESCE(
                ma.watched_movies,
                0
            ) AS watched_movies,
            COALESCE(
                ea.started_series,
                0
            ) AS started_series,
            COALESCE(
                ea.watched_episodes,
                0
            ) AS watched_episodes,
            COALESCE(
                fa.favorites,
                0
            ) AS favorites,
            COALESCE(
                ma.movie_minutes,
                0
            ) AS movie_minutes,
            COALESCE(
                ea.series_minutes,
                0
            ) AS series_minutes,
            (
                COALESCE(
                    ma.watched_movies,
                    0
                )
                + COALESCE(
                    ea.watched_episodes,
                    0
                )
            ) AS total_records,
            (
                COALESCE(
                    ma.movie_minutes,
                    0
                )
                + COALESCE(
                    ea.series_minutes,
                    0
                )
            ) AS total_minutes
        FROM users AS u
        LEFT JOIN movie_activity AS ma
          ON ma.user_id = u.id
        LEFT JOIN episode_activity AS ea
          ON ea.user_id = u.id
        LEFT JOIN favorite_activity AS fa
          ON fa.user_id = u.id
        WHERE {where_sql}
        ORDER BY {order_by}
        """,
        tuple(params),
    ).fetchall()

    return rows


def get_admin_monthly_activity(db):
    """Agrupa la actividad global de clientes por mes."""

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
                    mw.watched_at
                ) AS month,
                COUNT(*) AS movie_count,
                0 AS episode_count
            FROM movie_watches AS mw
            JOIN users AS u
              ON u.id = mw.user_id
            WHERE u.role = 'client'
            GROUP BY month

            UNION ALL

            SELECT
                strftime(
                    '%Y-%m',
                    ew.watched_at
                ) AS month,
                0 AS movie_count,
                COUNT(*) AS episode_count
            FROM episode_watches AS ew
            JOIN users AS u
              ON u.id = ew.user_id
            WHERE u.role = 'client'
            GROUP BY month
        ) AS activity
        WHERE month IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
        """
    ).fetchall()

    return list(
        reversed(
            rows
        )
    )


def build_admin_statistics_summary(rows):
    """Resume las métricas globales de todos los clientes."""

    total_clients = len(
        rows
    )

    active_clients = sum(
        1
        for row in rows
        if row["is_active"]
    )

    clients_with_activity = sum(
        1
        for row in rows
        if row["total_records"] > 0
    )

    total_records = sum(
        int(
            row["total_records"]
            or 0
        )
        for row in rows
    )

    total_minutes = sum(
        int(
            row["total_minutes"]
            or 0
        )
        for row in rows
    )

    movie_minutes = sum(
        int(
            row["movie_minutes"]
            or 0
        )
        for row in rows
    )

    series_minutes = sum(
        int(
            row["series_minutes"]
            or 0
        )
        for row in rows
    )

    top_client = (
        max(
            rows,
            key=lambda row: row["total_minutes"],
        )
        if rows
        else None
    )

    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "clients_with_activity": clients_with_activity,
        "total_records": total_records,
        "total_minutes": total_minutes,
        "total_time_text": format_admin_minutes(
            total_minutes
        ),
        "movie_minutes": movie_minutes,
        "series_minutes": series_minutes,
        "movie_time_text": format_admin_minutes(
            movie_minutes
        ),
        "series_time_text": format_admin_minutes(
            series_minutes
        ),
        "top_client": top_client,
    }


@admin_bp.route(
    "/statistics"
)
@admin_required
def statistics():
    """Compara la actividad audiovisual de los clientes."""

    search_query = request.args.get(
        "q",
        "",
    ).strip()[:100]

    status = request.args.get(
        "status",
        "all",
    ).strip()

    sort = request.args.get(
        "sort",
        "time",
    ).strip()

    if status not in ADMIN_STATS_STATUS_FILTERS:
        status = "all"

    if sort not in ADMIN_STATS_SORTS:
        sort = "time"

    db = get_db()

    all_clients = get_admin_client_statistics(
        db,
        status="all",
        sort="time",
    )

    client_rows = get_admin_client_statistics(
        db,
        search_query=search_query,
        status=status,
        sort=sort,
    )

    summary = build_admin_statistics_summary(
        all_clients
    )

    comparison_rows = sorted(
        client_rows,
        key=lambda row: (
            row["total_minutes"],
            row["total_records"],
        ),
        reverse=True,
    )[:10]

    monthly_rows = get_admin_monthly_activity(
        db
    )

    chart_data = {
        "clients": {
            "labels": [
                row["username"]
                for row in comparison_rows
            ],
            "movies": [
                round(
                    row["movie_minutes"] / 60,
                    2,
                )
                for row in comparison_rows
            ],
            "series": [
                round(
                    row["series_minutes"] / 60,
                    2,
                )
                for row in comparison_rows
            ],
        },
        "monthly": {
            "labels": [
                row["month"]
                for row in monthly_rows
            ],
            "movies": [
                int(
                    row["movies"]
                    or 0
                )
                for row in monthly_rows
            ],
            "episodes": [
                int(
                    row["episodes"]
                    or 0
                )
                for row in monthly_rows
            ],
        },
    }

    return render_template(
        "admin/statistics.html",
        summary=summary,
        clients=client_rows,
        chart_data=chart_data,
        search_query=search_query,
        status=status,
        sort=sort,
        format_minutes=format_admin_minutes,
    )

