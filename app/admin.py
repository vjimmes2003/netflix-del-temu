import re
import sqlite3
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
