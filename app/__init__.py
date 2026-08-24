import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template


ERROR_PAGES = {
    401: (
        "Acceso no autorizado",
        "Necesitas identificarte para acceder a esta sección.",
    ),
    403: (
        "Acceso denegado",
        "No tienes permisos para acceder a esta sección.",
    ),
    404: (
        "Página no encontrada",
        "La página que buscas no existe o ha cambiado de ubicación.",
    ),
    405: (
        "Acción no permitida",
        "La operación solicitada no está permitida desde esta dirección.",
    ),
    500: (
        "Error interno",
        "Se ha producido un error inesperado. Inténtalo de nuevo más tarde.",
    ),
}


def create_app():
    """Crea y configura la aplicación Flask."""

    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "development-secret-key",
    )

    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE"] = os.path.join(
        app.instance_path,
        "netflix_del_temu.sqlite3",
    )

    from . import db

    db.init_app(app)

    from .auth import auth_bp
    from .auth import init_app as init_auth

    init_auth(app)

    from .activity import activity_bp
    from .admin import admin_bp
    from .catalog import catalog_bp
    from .statistics import statistics_bp

    for blueprint in (
        auth_bp,
        catalog_bp,
        activity_bp,
        statistics_bp,
        admin_bp,
    ):
        app.register_blueprint(blueprint)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.template_filter("tmdb_image")
    def tmdb_image(path, size="w500"):
        if not path:
            return None

        return f"https://image.tmdb.org/t/p/{size}{path}"

    @app.template_filter("date_es")
    def date_es(value):
        if not value:
            return "Sin fecha"

        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value

    def render_app_error(error):
        code = error.code
        title, message = ERROR_PAGES[code]

        return (
            render_template(
                "errors/error.html",
                error_code=code,
                error_title=title,
                error_message=message,
            ),
            code,
        )

    for code in ERROR_PAGES:
        app.register_error_handler(code, render_app_error)

    return app
