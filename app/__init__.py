import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template



def create_app():
    """Crea y configura la aplicación Flask."""

    load_dotenv()

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "development-secret-key",
    )

    os.makedirs(
        app.instance_path,
        exist_ok=True,
    )

    app.config["DATABASE"] = os.path.join(
        app.instance_path,
        "netflix_del_temu.sqlite3",
    )

    from . import db

    db.init_app(app)

    from .auth import auth_bp
    from .auth import init_app as init_auth

    init_auth(app)
    app.register_blueprint(auth_bp)

    from .catalog import catalog_bp

    app.register_blueprint(catalog_bp)

    from .activity import activity_bp

    app.register_blueprint(activity_bp)

    from .admin import admin_bp

    app.register_blueprint(admin_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.template_filter("tmdb_image")
    def tmdb_image(path, size="w500"):
        if not path:
            return None

        return (
            "https://image.tmdb.org/t/p/"
            f"{size}{path}"
        )

    @app.template_filter("date_es")
    def date_es(value):
        if not value:
            return "Sin fecha"

        try:
            date = datetime.strptime(
                value,
                "%Y-%m-%d",
            )

            return date.strftime(
                "%d/%m/%Y"
            )

        except ValueError:
            return value

    @app.errorhandler(401)
    def unauthorized(error):
        return render_template(
            "errors/error.html",
            error_code=401,
            error_title="Acceso no autorizado",
            error_message=(
                "Necesitas identificarte para acceder "
                "a esta sección."
            ),
        ), 401

    @app.errorhandler(403)
    def forbidden(error):
        return render_template(
            "errors/error.html",
            error_code=403,
            error_title="Acceso denegado",
            error_message=(
                "No tienes permisos para acceder "
                "a esta sección."
            ),
        ), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            "errors/error.html",
            error_code=404,
            error_title="Página no encontrada",
            error_message=(
                "La página que buscas no existe "
                "o ha cambiado de ubicación."
            ),
        ), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return render_template(
            "errors/error.html",
            error_code=405,
            error_title="Acción no permitida",
            error_message=(
                "La operación solicitada no está "
                "permitida desde esta dirección."
            ),
        ), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            "errors/error.html",
            error_code=500,
            error_title="Error interno",
            error_message=(
                "Se ha producido un error inesperado. "
                "Inténtalo de nuevo más tarde."
            ),
        ), 500

    return app