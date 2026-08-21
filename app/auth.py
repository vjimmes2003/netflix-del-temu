import sqlite3

import click
from flask import (
    Blueprint,
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
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db


auth_bp = Blueprint("auth", __name__)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Debes iniciar sesión para acceder."
login_manager.login_message_category = "info"


class User(UserMixin):
    """Representa al usuario autenticado de la aplicación."""

    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.email = row["email"]
        self.display_name = row["display_name"]
        self.role = row["role"]
        self._is_active = bool(row["is_active"])

    @property
    def is_active(self):
        return self._is_active


@login_manager.user_loader
def load_user(user_id):
    row = get_db().execute(
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

    if row is None:
        return None

    return User(row)


@auth_bp.route("/register", methods=("GET", "POST"))
def register():
    if current_user.is_authenticated:
        return redirect(url_for("catalog.catalog"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_confirmation = request.form.get(
            "password_confirmation",
            "",
        )

        error = None

        if len(username) < 3:
            error = "El nombre de usuario debe tener al menos 3 caracteres."

        elif not email or "@" not in email:
            error = "Introduce un correo electrónico válido."

        elif len(password) < 8:
            error = "La contraseña debe tener al menos 8 caracteres."

        elif password != password_confirmation:
            error = "Las contraseñas no coinciden."

        if not display_name:
            display_name = username

        db = get_db()

        if error is None:
            existing_user = db.execute(
                """
                SELECT id
                FROM users
                WHERE username = ?
                   OR email = ?
                """,
                (username, email),
            ).fetchone()

            if existing_user is not None:
                error = "El usuario o correo electrónico ya está registrado."

        if error is None:
            try:
                cursor = db.execute(
                    """
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        display_name,
                        role
                    )
                    VALUES (?, ?, ?, ?, 'client')
                    """,
                    (
                        username,
                        email,
                        generate_password_hash(password),
                        display_name,
                    ),
                )

                db.commit()

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
                    """,
                    (cursor.lastrowid,),
                ).fetchone()

                login_user(User(row))

                flash("Cuenta creada correctamente.", "success")

                return redirect(url_for("catalog.catalog"))

            except sqlite3.IntegrityError:
                db.rollback()
                error = "No se ha podido crear la cuenta."

        flash(error, "error")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user.is_authenticated:
        return redirect(url_for("catalog.catalog"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        row = get_db().execute(
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
            WHERE (username = ? OR email = ?)
              AND is_active = 1
            """,
            (identifier, identifier),
        ).fetchone()

        if row is None or not check_password_hash(
            row["password_hash"],
            password,
        ):
            flash("Usuario, correo o contraseña incorrectos.", "error")
            return render_template("auth/login.html")

        login_user(User(row))

        flash("Sesión iniciada correctamente.", "success")

        return redirect(url_for("catalog.catalog"))

    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("Sesión cerrada.", "info")

    return redirect(url_for("index"))


@click.command("create-admin")
@click.option("--username", prompt="Usuario")
@click.option("--email", prompt="Correo electrónico")
@click.option("--display-name", prompt="Nombre visible")
@click.option(
    "--password",
    prompt="Contraseña",
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
    """Crea una cuenta con permisos de administrador."""

    if len(password) < 8:
        raise click.ClickException(
            "La contraseña debe tener al menos 8 caracteres."
        )

    db = get_db()

    existing_user = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
           OR email = ?
        """,
        (username, email),
    ).fetchone()

    if existing_user is not None:
        raise click.ClickException(
            "El usuario o correo ya existe."
        )

    db.execute(
        """
        INSERT INTO users (
            username,
            email,
            password_hash,
            display_name,
            role
        )
        VALUES (?, ?, ?, ?, 'admin')
        """,
        (
            username,
            email.lower(),
            generate_password_hash(password),
            display_name,
        ),
    )

    db.commit()

    click.echo("Administrador creado correctamente.")


def init_app(app):
    login_manager.init_app(app)
    app.cli.add_command(create_admin_command)