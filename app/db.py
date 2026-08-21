import sqlite3
from pathlib import Path

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    """Devuelve la conexión SQLite asociada a la petición actual."""

    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"]
        )

        g.db.row_factory = sqlite3.Row

        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(exception=None):
    """Cierra la conexión al finalizar la petición."""

    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    """Crea las tablas definidas en database/schema.sql."""

    db = get_db()

    project_root = Path(current_app.root_path).parent
    schema_path = project_root / "database" / "schema.sql"

    with schema_path.open("r", encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())

    db.commit()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Inicializa la base de datos."""

    init_db()

    click.echo("Base de datos inicializada correctamente.")


def init_app(app):
    """Registra las funciones de base de datos en Flask."""

    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)