import os

from flask import Flask, render_template
from dotenv import load_dotenv


def create_app():
    """
    Crea y configura la aplicación Flask.
    """

    load_dotenv()

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "development-secret-key"
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    return app