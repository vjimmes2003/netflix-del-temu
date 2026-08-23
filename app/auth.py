import os
import re
import sqlite3
from functools import wraps

import click
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.cli import with_appcontext
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from .db import get_db


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)

login_manager = LoginManager()

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
PASSWORD_MIN_LENGTH = 8

DEFAULT_SUPPORT_EMAIL = (
    "soporte@netflixdeltemu.test"
)


class User(UserMixin):
    """Representa al usuario autenticado."""

    def __init__(
        self,
        user_id,
        username,
        email,
        display_name,
        role,
        is_active,
    ):
        self.id = user_id
        self.username = username
        self.email = email
        self.display_name = display_name
        self.role = role
        self._is_active = bool(
            is_active
        )

    @property
    def is_active(self):
        """Indica si la cuenta puede iniciar sesión."""

        return self._is_active


def get_support_email():
    """
    Devuelve el correo de soporte.

    Puede configurarse mediante la variable:
    SUPPORT_EMAIL
    """

    return os.getenv(
        "SUPPORT_EMAIL",
        DEFAULT_SUPPORT_EMAIL,
    ).strip()


def row_to_user(row):
    """Convierte una fila SQLite en un objeto User."""

    if row is None:
        return None

    return User(
        user_id=row["id"],
        username=row["username"],
        email=row["email"],
        display_name=row["display_name"],
        role=row["role"],
        is_active=row["is_active"],
    )


@login_manager.user_loader
def load_user(user_id):
    """
    Recupera al usuario de la sesión.

    Solo devuelve cuentas activas. Si un administrador
    suspende una cuenta que estaba conectada, Flask-Login
    dejará de considerarla autenticada en la siguiente
    carga de sesión.
    """

    try:
        user_id = int(
            user_id
        )
    except (TypeError, ValueError):
        return None

    db = get_db()

    row = db.execute(
        """
        SELECT
            id,
            username,
            email,
            display_name,
            role,
            is_active
        FROM users
        WHERE id = ?
          AND is_active = 1
        """,
        (user_id,),
    ).fetchone()

    return row_to_user(
        row
    )


def admin_required(view):
    """Restringe una ruta a administradores."""

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


def get_login_identifier():
    """
    Obtiene el usuario/correo del formulario.

    Se admiten varios nombres por compatibilidad con
    versiones anteriores de la plantilla.
    """

    return (
        request.form.get(
            "identifier"
        )
        or request.form.get(
            "identity"
        )
        or request.form.get(
            "username"
        )
        or request.form.get(
            "email"
        )
        or ""
    ).strip()


@auth_bp.route(
    "/login",
    methods=("GET", "POST"),
)
def login():
    """Inicia sesión mediante usuario o correo."""

    if current_user.is_authenticated:
        if getattr(
            current_user,
            "role",
            None,
        ) == "admin":
            return redirect(
                url_for(
                    "admin.dashboard"
                )
            )

        return redirect(
            url_for(
                "catalog.catalog"
            )
        )

    if request.method == "POST":
        identifier = (
            get_login_identifier()
        )

        password = request.form.get(
            "password",
            "",
        )

        db = get_db()

        user_row = db.execute(
            """
            SELECT
                id,
                username,
                email,
                password_hash,
                display_name,
                role,
                is_active
            FROM users
            WHERE username = ?
               OR email = ?
            LIMIT 1
            """,
            (
                identifier,
                identifier,
            ),
        ).fetchone()

        credentials_are_valid = (
            user_row is not None
            and check_password_hash(
                user_row["password_hash"],
                password,
            )
        )

        if not credentials_are_valid:
            flash(
                "Usuario, correo o contraseña incorrectos.",
                "error",
            )

            return render_template(
                "auth/login.html"
            )

        if not user_row["is_active"]:
            support_email = (
                get_support_email()
            )

            flash(
                (
                    "Tu cuenta ha sido suspendida y "
                    "no puedes iniciar sesión. "
                    "Si quieres conocer más información "
                    "o solicitar una revisión, contacta "
                    f"con soporte en {support_email}."
                ),
                "error",
            )

            return render_template(
                "auth/login.html"
            )

        user = row_to_user(
            user_row
        )

        login_user(
            user
        )

        if user.role == "admin":
            return redirect(
                url_for(
                    "admin.dashboard"
                )
            )

        return redirect(
            url_for(
                "catalog.catalog"
            )
        )

    return render_template(
        "auth/login.html"
    )


@auth_bp.route(
    "/register",
    methods=("GET", "POST"),
)
def register():
    """Registra una nueva cuenta de cliente."""

    if current_user.is_authenticated:
        return redirect(
            url_for(
                "catalog.catalog"
            )
        )

    if request.method == "POST":
        username = request.form.get(
            "username",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip().casefold()

        display_name = request.form.get(
            "display_name",
            "",
        ).strip()

        country_code = request.form.get(
            "country_code",
            "ES",
        ).strip().upper()

        password = request.form.get(
            "password",
            "",
        )

        errors = []

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

        if not EMAIL_PATTERN.fullmatch(
            email
        ):
            errors.append(
                "Introduce un correo electrónico válido."
            )

        if not display_name:
            errors.append(
                "El nombre visible es obligatorio."
            )

        if not (
            len(country_code) == 2
            and country_code.isalpha()
        ):
            errors.append(
                "El país debe indicarse con "
                "un código de dos letras."
            )

        if (
            len(password)
            < PASSWORD_MIN_LENGTH
        ):
            errors.append(
                "La contraseña debe tener al menos "
                f"{PASSWORD_MIN_LENGTH} caracteres."
            )

        db = get_db()

        conflict = db.execute(
            """
            SELECT id
            FROM users
            WHERE username = ? COLLATE NOCASE
               OR email = ? COLLATE NOCASE
            LIMIT 1
            """,
            (
                username,
                email,
            ),
        ).fetchone()

        if conflict is not None:
            errors.append(
                "Ya existe una cuenta con ese "
                "usuario o correo."
            )

        if errors:
            for error in errors:
                flash(
                    error,
                    "error",
                )

            return render_template(
                "auth/register.html"
            )

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
                    username,
                    email,
                    generate_password_hash(
                        password
                    ),
                    display_name,
                    country_code,
                ),
            )

            db.commit()

        except sqlite3.IntegrityError:
            db.rollback()

            flash(
                "No se ha podido crear la cuenta "
                "porque el usuario o correo ya existe.",
                "error",
            )

            return render_template(
                "auth/register.html"
            )

        flash(
            "Cuenta creada correctamente. "
            "Ya puedes iniciar sesión.",
            "success",
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    return render_template(
        "auth/register.html"
    )


@auth_bp.route(
    "/logout",
    methods=("POST",),
)
@login_required
def logout():
    """Cierra la sesión actual."""

    logout_user()

    return redirect(
        url_for(
            "index"
        )
    )


@click.command(
    "create-admin"
)
@click.option(
    "--username",
    prompt="Usuario administrador",
)
@click.option(
    "--email",
    prompt="Correo administrador",
)
@click.option(
    "--display-name",
    prompt="Nombre visible",
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
)
@with_appcontext
def create_admin_command(
    username,
    email,
    display_name,
    password,
):
    """Crea una cuenta administrativa."""

    username = username.strip()
    email = email.strip().casefold()
    display_name = (
        display_name.strip()
    )

    if len(password) < PASSWORD_MIN_LENGTH:
        raise click.ClickException(
            "La contraseña debe tener al menos "
            f"{PASSWORD_MIN_LENGTH} caracteres."
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = ? COLLATE NOCASE
           OR email = ? COLLATE NOCASE
        LIMIT 1
        """,
        (
            username,
            email,
        ),
    ).fetchone()

    if existing is not None:
        raise click.ClickException(
            "Ya existe una cuenta con ese "
            "usuario o correo."
        )

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
            'admin', 'ES', 1
        )
        """,
        (
            username,
            email,
            generate_password_hash(
                password
            ),
            display_name,
        ),
    )

    db.commit()

    click.echo(
        "Administrador creado correctamente."
    )


def init_app(app):
    """Inicializa Flask-Login y comandos de autenticación."""

    login_manager.login_view = (
        "auth.login"
    )

    login_manager.login_message = (
        "Inicia sesión para acceder "
        "a esta sección."
    )

    login_manager.login_message_category = (
        "error"
    )

    login_manager.init_app(
        app
    )

    app.cli.add_command(
        create_admin_command
    )
