from __future__ import annotations

import argparse
import compileall
import contextlib
import importlib.util
import io
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATABASE = (
    PROJECT_ROOT
    / "instance"
    / "netflix_del_temu.sqlite3"
)

TEST_PASSWORD = "Phase13Test123!"
TEST_PREFIX = "phase13_"

EXPECTED_TABLES = {
    "users",
    "media",
    "seasons",
    "episodes",
    "genres",
    "media_genres",
    "countries",
    "media_countries",
    "tags",
    "media_tags",
    "favorites",
    "movie_watches",
    "episode_watches",
    "media_ratings",
    "season_ratings",
    "episode_ratings",
}


class SkipTest(Exception):
    pass


@dataclass
class Result:
    name: str
    status: str
    detail: str
    seconds: float


class Runner:
    def __init__(self):
        self.results: list[Result] = []
        self.notes: list[str] = []

    def note(self, text: str):
        self.notes.append(text)
        print(f"    INFO  {text}")

    def run(self, name, function):
        started = time.perf_counter()

        try:
            function()
        except SkipTest as error:
            seconds = time.perf_counter() - started
            self.results.append(
                Result(name, "SKIP", str(error), seconds)
            )
            print(
                f"[SKIP] {name} "
                f"({seconds:.2f}s) — {error}"
            )
        except Exception as error:
            seconds = time.perf_counter() - started
            detail = (
                f"{type(error).__name__}: {error}"
            )
            self.results.append(
                Result(name, "FAIL", detail, seconds)
            )
            print(
                f"[FAIL] {name} "
                f"({seconds:.2f}s) — {detail}"
            )
        else:
            seconds = time.perf_counter() - started
            self.results.append(
                Result(name, "PASS", "", seconds)
            )
            print(
                f"[PASS] {name} "
                f"({seconds:.2f}s)"
            )

    @property
    def failures(self):
        return [
            result
            for result in self.results
            if result.status == "FAIL"
        ]

    @property
    def passes(self):
        return [
            result
            for result in self.results
            if result.status == "PASS"
        ]

    @property
    def skips(self):
        return [
            result
            for result in self.results
            if result.status == "SKIP"
        ]

    def report_text(self):
        width = 72
        lines = [
            "=" * width,
            "NETFLIX DEL TEMU — FASE 13 — RESULTADOS AUTOMÁTICOS",
            "=" * width,
            "",
        ]

        for result in self.results:
            suffix = (
                f" — {result.detail}"
                if result.detail
                else ""
            )
            lines.append(
                f"[{result.status}] "
                f"{result.name} "
                f"({result.seconds:.2f}s)"
                f"{suffix}"
            )

        lines.extend(
            [
                "",
                "-" * width,
                (
                    f"PASS: {len(self.passes)} | "
                    f"FAIL: {len(self.failures)} | "
                    f"SKIP: {len(self.skips)}"
                ),
            ]
        )

        if self.notes:
            lines.append("")
            lines.append("Notas:")
            lines.extend(
                f"- {note}"
                for note in self.notes
            )

        lines.append("=" * width)
        return "\n".join(lines)


class Context:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.database = (
            temp_dir
            / "phase13.sqlite3"
        )
        self.app = None
        self.client = None
        self.names = {}
        self.ids = {}
        self.catalog = {}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def db_connect(path: Path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def scalar(ctx, sql, params=()):
    with db_connect(ctx.database) as db:
        row = db.execute(
            sql,
            params,
        ).fetchone()

    if row is None:
        return None

    return row[0]


def row(ctx, sql, params=()):
    with db_connect(ctx.database) as db:
        return db.execute(
            sql,
            params,
        ).fetchone()


def create_database_backup(ctx):
    require(
        SOURCE_DATABASE.exists(),
        (
            "No existe la base de datos real en "
            f"{SOURCE_DATABASE}"
        ),
    )

    source = sqlite3.connect(
        SOURCE_DATABASE
    )
    target = sqlite3.connect(
        ctx.database
    )

    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def create_test_users(ctx):
    stamp = str(
        int(time.time() * 1000)
    )[-8:]

    ctx.names = {
        "client": (
            f"{TEST_PREFIX}client_{stamp}"
        ),
        "inactive": (
            f"{TEST_PREFIX}inactive_{stamp}"
        ),
        "admin": (
            f"{TEST_PREFIX}admin_{stamp}"
        ),
        "register": (
            f"{TEST_PREFIX}register_{stamp}"
        ),
        "admin_created": (
            f"{TEST_PREFIX}created_{stamp}"
        ),
    }

    password_hash = (
        generate_password_hash(
            TEST_PASSWORD
        )
    )

    with db_connect(ctx.database) as db:
        for key, role, active in (
            ("client", "client", 1),
            ("inactive", "client", 0),
            ("admin", "admin", 1),
        ):
            username = ctx.names[key]

            cursor = db.execute(
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
                VALUES (?, ?, ?, ?, ?, 'ES', ?)
                """,
                (
                    username,
                    f"{username}@phase13.test",
                    password_hash,
                    f"Phase13 {key}",
                    role,
                    active,
                ),
            )

            ctx.ids[key] = (
                cursor.lastrowid
            )

        db.commit()


def discover_catalog(ctx):
    with db_connect(ctx.database) as db:
        movie = db.execute(
            """
            SELECT id, title, runtime_minutes
            FROM media
            WHERE media_type = 'movie'
              AND is_visible = 1
              AND content_level = 'general'
              AND runtime_minutes > 0
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

        series = db.execute(
            """
            SELECT
                m.id AS media_id,
                s.id AS season_id,
                e.id AS episode_id
            FROM media AS m
            JOIN seasons AS s
              ON s.media_id = m.id
             AND s.is_visible = 1
            JOIN episodes AS e
              ON e.season_id = s.id
             AND e.is_visible = 1
            WHERE m.media_type = 'series'
              AND m.is_visible = 1
              AND m.content_level = 'general'
            ORDER BY
                m.id,
                s.season_number,
                e.episode_number
            LIMIT 1
            """
        ).fetchone()

        mature = db.execute(
            """
            SELECT id, media_type
            FROM media
            WHERE is_visible = 1
              AND content_level = 'mature'
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

        explicit = db.execute(
            """
            SELECT id, media_type
            FROM media
            WHERE is_visible = 1
              AND content_level = 'explicit'
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

        genre = db.execute(
            """
            SELECT id
            FROM genres
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

    require(
        movie is not None,
        "No existe ninguna película general usable.",
    )
    require(
        series is not None,
        (
            "No existe ninguna serie general "
            "con episodios visibles."
        ),
    )
    require(
        genre is not None,
        "No existe ningún género.",
    )

    ctx.catalog = {
        "movie_id": movie["id"],
        "movie_title": movie["title"],
        "movie_runtime": (
            movie["runtime_minutes"]
        ),
        "series_id": series["media_id"],
        "season_id": series["season_id"],
        "episode_id": series["episode_id"],
        "mature_id": (
            mature["id"]
            if mature
            else None
        ),
        "explicit_id": (
            explicit["id"]
            if explicit
            else None
        ),
        "genre_id": genre["id"],
    }


def create_app(ctx):
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

    from app import create_app as factory

    app = factory()
    app.config.update(
        TESTING=True,
        SECRET_KEY="phase13-test-secret",
        DATABASE=str(ctx.database),
    )

    ctx.app = app
    ctx.client = app.test_client()


def logout(ctx):
    ctx.client.post(
        "/auth/logout",
        follow_redirects=False,
    )


def login(ctx, username):
    return ctx.client.post(
        "/auth/login",
        data={
            "identifier": username,
            "password": TEST_PASSWORD,
        },
        follow_redirects=False,
    )


def response_text(response):
    return response.get_data(
        as_text=True
    )


def assert_status(response, expected):
    require(
        response.status_code == expected,
        (
            f"HTTP {response.status_code}; "
            f"se esperaba {expected}. "
            f"Location={response.headers.get('Location')}"
        ),
    )


def assert_redirect_contains(
    response,
    fragment,
):
    assert_status(response, 302)

    location = (
        response.headers.get("Location")
        or ""
    )

    require(
        fragment in location,
        (
            f"Redirección inesperada: "
            f"{location!r}; "
            f"se esperaba {fragment!r}."
        ),
    )


def test_python_compilation():
    ok_app = compileall.compile_dir(
        PROJECT_ROOT / "app",
        quiet=1,
    )
    ok_scripts = compileall.compile_dir(
        PROJECT_ROOT / "scripts",
        quiet=1,
    )

    require(
        ok_app and ok_scripts,
        "Hay archivos Python que no compilan.",
    )


def test_database_integrity(ctx):
    with db_connect(ctx.database) as db:
        integrity = db.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        fk_errors = db.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    require(
        integrity == "ok",
        (
            "PRAGMA integrity_check "
            f"devolvió {integrity!r}."
        ),
    )
    require(
        not fk_errors,
        (
            "Hay errores de claves foráneas: "
            f"{len(fk_errors)}."
        ),
    )


def test_database_schema(ctx):
    with db_connect(ctx.database) as db:
        tables = {
            item["name"]
            for item in db.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }

    missing = EXPECTED_TABLES - tables

    require(
        not missing,
        (
            "Faltan tablas obligatorias: "
            + ", ".join(sorted(missing))
        ),
    )


def test_jinja_templates(ctx):
    templates = [
        name
        for name in (
            ctx.app
            .jinja_env
            .list_templates()
        )
        if name.endswith(".html")
    ]

    require(
        templates,
        "Jinja no ha encontrado plantillas.",
    )

    for template in templates:
        ctx.app.jinja_env.get_template(
            template
        )


def test_static_assets(ctx):
    for path in (
        "/static/css/app.css",
        "/static/js/app.js",
    ):
        response = ctx.client.get(path)
        assert_status(response, 200)

        require(
            len(response.data) > 100,
            f"{path} parece vacío.",
        )


def test_route_map(ctx):
    rules = {
        rule.rule
        for rule in ctx.app.url_map.iter_rules()
    }

    expected = {
        "/",
        "/auth/login",
        "/auth/register",
        "/auth/logout",
        "/catalog",
        "/favorites",
        "/watched",
        "/profile",
        "/statistics",
        "/settings/content",
        "/settings/content/toggle",
        "/admin/",
        "/admin/users",
        "/admin/catalog",
        "/admin/statistics",
    }

    missing = expected - rules

    require(
        not missing,
        (
            "Faltan rutas esperadas: "
            + ", ".join(sorted(missing))
        ),
    )


def test_public_routes(ctx):
    for path in (
        "/",
        "/auth/login",
        "/auth/register",
    ):
        assert_status(
            ctx.client.get(path),
            200,
        )

    assert_status(
        ctx.client.get(
            "/ruta-que-no-existe-phase13"
        ),
        404,
    )


def test_protected_routes(ctx):
    logout(ctx)

    for path in (
        "/catalog",
        "/favorites",
        "/watched",
        "/profile",
        "/statistics",
        "/settings/content",
        "/admin/",
        "/admin/users",
        "/admin/catalog",
        "/admin/statistics",
    ):
        response = ctx.client.get(
            path,
            follow_redirects=False,
        )

        require(
            response.status_code == 302,
            (
                f"{path} debería redirigir "
                "al no estar autenticado."
            ),
        )
        require(
            "/auth/login" in (
                response.headers.get(
                    "Location"
                )
                or ""
            ),
            (
                f"{path} no redirige "
                "hacia login."
            ),
        )


def test_register_validation(ctx):
    logout(ctx)

    response = ctx.client.post(
        "/auth/register",
        data={
            "username": "x",
            "email": "correo-invalido",
            "display_name": "",
            "country_code": "ESP",
            "password": "123",
            "password_confirmation": "456",
        },
    )

    assert_status(response, 200)
    body = response_text(response)

    for expected in (
        "entre 3 y 50",
        "correo electrónico válido",
        "nombre visible es obligatorio",
        "código de dos letras",
        "al menos 8",
        "no coinciden",
    ):
        require(
            expected.lower()
            in body.lower(),
            (
                "No apareció el error "
                f"esperado: {expected}"
            ),
        )


def test_register_and_duplicate(ctx):
    username = ctx.names["register"]

    response = ctx.client.post(
        "/auth/register",
        data={
            "username": username,
            "email": (
                f"{username}@phase13.test"
            ),
            "display_name": (
                "Phase13 Registro"
            ),
            "country_code": "es",
            "password": TEST_PASSWORD,
            "password_confirmation": (
                TEST_PASSWORD
            ),
        },
        follow_redirects=False,
    )

    assert_redirect_contains(
        response,
        "/auth/login",
    )

    created = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM users
        WHERE username = ?
          AND role = 'client'
          AND is_active = 1
        """,
        (username,),
    )

    require(
        created == 1,
        "El registro válido no creó la cuenta.",
    )

    duplicate = ctx.client.post(
        "/auth/register",
        data={
            "username": username,
            "email": (
                f"{username}@phase13.test"
            ),
            "display_name": "Duplicado",
            "country_code": "ES",
            "password": TEST_PASSWORD,
            "password_confirmation": (
                TEST_PASSWORD
            ),
        },
    )

    assert_status(duplicate, 200)
    require(
        "ya existe una cuenta"
        in response_text(
            duplicate
        ).lower(),
        "No se detectó el registro duplicado.",
    )


def test_login_behaviour(ctx):
    logout(ctx)

    invalid = ctx.client.post(
        "/auth/login",
        data={
            "identifier": ctx.names["client"],
            "password": "incorrecta",
        },
    )

    assert_status(invalid, 200)

    require(
        "incorrectos"
        in response_text(invalid).lower(),
        "Login incorrecto sin mensaje esperado.",
    )

    inactive = ctx.client.post(
        "/auth/login",
        data={
            "identifier": (
                ctx.names["inactive"]
            ),
            "password": TEST_PASSWORD,
        },
    )

    assert_status(inactive, 200)

    require(
        "suspendida"
        in response_text(inactive).lower(),
        "La cuenta inactiva pudo iniciar sesión.",
    )

    client_login = login(
        ctx,
        ctx.names["client"],
    )

    assert_redirect_contains(
        client_login,
        "/catalog",
    )

    logout(ctx)

    admin_login = login(
        ctx,
        ctx.names["admin"],
    )

    assert_redirect_contains(
        admin_login,
        "/admin/",
    )

    logout(ctx)


def test_logout_method(ctx):
    login(
        ctx,
        ctx.names["client"],
    )

    assert_status(
        ctx.client.get("/auth/logout"),
        405,
    )

    response = ctx.client.post(
        "/auth/logout",
        follow_redirects=False,
    )

    assert_redirect_contains(
        response,
        "/",
    )


def test_role_permissions(ctx):
    login(
        ctx,
        ctx.names["client"],
    )

    for path in (
        "/admin/",
        "/admin/users",
        "/admin/catalog",
        "/admin/statistics",
    ):
        assert_status(
            ctx.client.get(path),
            403,
        )

    logout(ctx)

    login(
        ctx,
        ctx.names["admin"],
    )

    for path in (
        "/admin/",
        "/admin/users",
        "/admin/catalog",
        "/admin/statistics",
    ):
        assert_status(
            ctx.client.get(path),
            200,
        )

    protected_admin = ctx.client.get(
        (
            "/admin/users/"
            f"{ctx.ids['admin']}/edit"
        )
    )

    assert_status(
        protected_admin,
        404,
    )

    logout(ctx)


def test_catalog_filters(ctx):
    login(
        ctx,
        ctx.names["client"],
    )

    queries = (
        "/catalog?type=movie",
        "/catalog?type=series",
        "/catalog?type=movie&per_page=10",
        "/catalog?type=movie&per_page=30",
        "/catalog?type=movie&per_page=50",
        "/catalog?type=movie&per_page=100",
        "/catalog?type=movie&per_page=999",
        "/catalog?type=no-valido",
        "/catalog?type=movie&sort=newest",
        "/catalog?type=movie&sort=oldest",
        "/catalog?type=movie&sort=rating",
        "/catalog?type=movie&sort=popularity",
        (
            "/catalog?type=movie&q="
            + "a" * 120
        ),
        (
            "/catalog?type=movie&q="
            "%27%20OR%201%3D1%20--"
        ),
        (
            "/catalog?type=movie&q="
            "%3Cscript%3Ealert(1)%3C%2Fscript%3E"
        ),
    )

    for path in queries:
        response = ctx.client.get(path)
        assert_status(response, 200)

    xss = ctx.client.get(
        (
            "/catalog?type=movie&q="
            "%3Cscript%3Ealert(1)%3C%2Fscript%3E"
        )
    )

    require(
        "<script>alert(1)</script>"
        not in response_text(xss),
        (
            "La búsqueda se refleja sin escape "
            "HTML."
        ),
    )

    logout(ctx)


def test_media_details(ctx):
    login(
        ctx,
        ctx.names["client"],
    )

    assert_status(
        ctx.client.get(
            f"/catalog/{ctx.catalog['movie_id']}"
        ),
        200,
    )

    assert_status(
        ctx.client.get(
            f"/catalog/{ctx.catalog['series_id']}"
        ),
        200,
    )

    assert_status(
        ctx.client.get(
            "/catalog/999999999"
        ),
        404,
    )

    assert_status(
        ctx.client.get(
            (
                f"/catalog/"
                f"{ctx.catalog['series_id']}"
                "/season/"
                f"{ctx.catalog['season_id']}"
            )
        ),
        200,
    )

    logout(ctx)


def test_content_policy(ctx):
    mature_id = ctx.catalog[
        "mature_id"
    ]
    explicit_id = ctx.catalog[
        "explicit_id"
    ]

    if mature_id is None:
        raise SkipTest(
            "No hay contenido mature "
            "en la copia de la BD."
        )

    login(
        ctx,
        ctx.names["client"],
    )

    # Antes de confirmar +18 debe estar oculto.
    assert_status(
        ctx.client.get(
            f"/catalog/{mature_id}"
        ),
        404,
    )

    wrong = ctx.client.post(
        "/settings/content",
        data={
            "action": "confirm",
            "confirm_adult": "on",
            "password": "incorrecta",
        },
        follow_redirects=False,
    )

    assert_status(wrong, 302)

    confirmed_before = scalar(
        ctx,
        """
        SELECT mature_content_confirmed_at
        FROM users
        WHERE id = ?
        """,
        (ctx.ids["client"],),
    )

    require(
        confirmed_before is None,
        (
            "Una contraseña incorrecta "
            "confirmó mature."
        ),
    )

    correct = ctx.client.post(
        "/settings/content",
        data={
            "action": "confirm",
            "confirm_adult": "on",
            "password": TEST_PASSWORD,
        },
        follow_redirects=False,
    )

    assert_redirect_contains(
        correct,
        "/catalog",
    )

    flags = row(
        ctx,
        """
        SELECT
            mature_content_enabled,
            mature_content_confirmed_at
        FROM users
        WHERE id = ?
        """,
        (ctx.ids["client"],),
    )

    require(
        flags["mature_content_enabled"] == 1,
        "Mature no quedó activado.",
    )
    require(
        flags[
            "mature_content_confirmed_at"
        ]
        is not None,
        "No se guardó la confirmación +18.",
    )

    assert_status(
        ctx.client.get(
            f"/catalog/{mature_id}"
        ),
        200,
    )

    disabled = ctx.client.post(
        "/settings/content/toggle",
        data={
            "enabled": "0",
            "return_to": "catalog",
            "media_type": "movie",
            "q": "",
            "genre": "",
            "sort": "popularity",
            "per_page": "30",
        },
        follow_redirects=False,
    )

    assert_status(disabled, 302)

    require(
        scalar(
            ctx,
            """
            SELECT mature_content_enabled
            FROM users
            WHERE id = ?
            """,
            (ctx.ids["client"],),
        )
        == 0,
        "El toggle no desactivó mature.",
    )

    assert_status(
        ctx.client.get(
            f"/catalog/{mature_id}"
        ),
        404,
    )

    # Lo reactivamos para comprobar que explicit
    # continúa bloqueado incluso con +18.
    ctx.client.post(
        "/settings/content/toggle",
        data={
            "enabled": "1",
            "return_to": "catalog",
            "media_type": "movie",
            "q": "",
            "genre": "",
            "sort": "popularity",
            "per_page": "30",
        },
    )

    if explicit_id is not None:
        assert_status(
            ctx.client.get(
                f"/catalog/{explicit_id}"
            ),
            404,
        )

    logout(ctx)


def test_favorites_and_movie_watch(ctx):
    user_id = ctx.ids["client"]
    movie_id = ctx.catalog["movie_id"]

    with db_connect(ctx.database) as db:
        db.execute(
            """
            DELETE FROM favorites
            WHERE user_id = ?
              AND media_id = ?
            """,
            (user_id, movie_id),
        )
        db.execute(
            """
            DELETE FROM movie_watches
            WHERE user_id = ?
              AND media_id = ?
            """,
            (user_id, movie_id),
        )
        db.commit()

    login(
        ctx,
        ctx.names["client"],
    )

    favorite_url = (
        "/activity/favorites/"
        f"{movie_id}/toggle"
    )

    watched_url = (
        "/activity/movies/"
        f"{movie_id}/toggle-watched"
    )

    assert_status(
        ctx.client.get(favorite_url),
        405,
    )

    ctx.client.post(
        favorite_url,
        data={"return_to": "detail"},
    )

    require(
        scalar(
            ctx,
            """
            SELECT COUNT(*)
            FROM favorites
            WHERE user_id = ?
              AND media_id = ?
            """,
            (user_id, movie_id),
        )
        == 1,
        "No se añadió el favorito.",
    )

    ctx.client.post(
        favorite_url,
        data={"return_to": "detail"},
    )

    require(
        scalar(
            ctx,
            """
            SELECT COUNT(*)
            FROM favorites
            WHERE user_id = ?
              AND media_id = ?
            """,
            (user_id, movie_id),
        )
        == 0,
        "No se eliminó el favorito.",
    )

    # Dejamos un favorito para probar la biblioteca.
    ctx.client.post(
        favorite_url,
        data={"return_to": "favorites"},
    )

    ctx.client.post(
        watched_url,
        data={"return_to": "detail"},
    )

    require(
        scalar(
            ctx,
            """
            SELECT COUNT(*)
            FROM movie_watches
            WHERE user_id = ?
              AND media_id = ?
            """,
            (user_id, movie_id),
        )
        == 1,
        "No se marcó la película como vista.",
    )

    ctx.client.post(
        watched_url,
        data={"return_to": "detail"},
    )

    require(
        scalar(
            ctx,
            """
            SELECT COUNT(*)
            FROM movie_watches
            WHERE user_id = ?
              AND media_id = ?
            """,
            (user_id, movie_id),
        )
        == 0,
        "No se desmarcó la película.",
    )

    # La dejamos vista para estadísticas.
    ctx.client.post(
        watched_url,
        data={"return_to": "watched"},
    )

    assert_status(
        ctx.client.get("/favorites"),
        200,
    )
    assert_status(
        ctx.client.get("/watched"),
        200,
    )

    logout(ctx)


def test_series_tracking(ctx):
    user_id = ctx.ids["client"]
    season_id = ctx.catalog["season_id"]
    episode_id = ctx.catalog["episode_id"]

    with db_connect(ctx.database) as db:
        db.execute(
            """
            DELETE FROM episode_watches
            WHERE user_id = ?
              AND episode_id IN (
                    SELECT id
                    FROM episodes
                    WHERE season_id = ?
              )
            """,
            (
                user_id,
                season_id,
            ),
        )
        db.commit()

    login(
        ctx,
        ctx.names["client"],
    )

    episode_url = (
        "/activity/episodes/"
        f"{episode_id}/toggle-watched"
    )

    ctx.client.post(
        episode_url,
        data={"return_to": "season"},
    )

    require(
        scalar(
            ctx,
            """
            SELECT COUNT(*)
            FROM episode_watches
            WHERE user_id = ?
              AND episode_id = ?
            """,
            (
                user_id,
                episode_id,
            ),
        )
        == 1,
        "No se marcó el episodio.",
    )

    ctx.client.post(
        episode_url,
        data={"return_to": "season"},
    )

    require(
        scalar(
            ctx,
            """
            SELECT COUNT(*)
            FROM episode_watches
            WHERE user_id = ?
              AND episode_id = ?
            """,
            (
                user_id,
                episode_id,
            ),
        )
        == 0,
        "No se desmarcó el episodio.",
    )

    season_url = (
        "/activity/seasons/"
        f"{season_id}/toggle-watched"
    )

    ctx.client.post(
        season_url,
        data={
            "return_to": "season",
            "media_id": (
                str(ctx.catalog["series_id"])
            ),
        },
    )

    total = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM episodes
        WHERE season_id = ?
          AND is_visible = 1
        """,
        (season_id,),
    )

    watched = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM episode_watches AS ew
        JOIN episodes AS e
          ON e.id = ew.episode_id
        WHERE ew.user_id = ?
          AND e.season_id = ?
          AND e.is_visible = 1
        """,
        (
            user_id,
            season_id,
        ),
    )

    require(
        watched == total,
        (
            "Marcar temporada completa "
            f"produjo {watched}/{total}."
        ),
    )

    ctx.client.post(
        season_url,
        data={
            "return_to": "season",
            "media_id": (
                str(ctx.catalog["series_id"])
            ),
        },
    )

    watched_after = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM episode_watches AS ew
        JOIN episodes AS e
          ON e.id = ew.episode_id
        WHERE ew.user_id = ?
          AND e.season_id = ?
        """,
        (
            user_id,
            season_id,
        ),
    )

    require(
        watched_after == 0,
        (
            "Desmarcar temporada dejó "
            f"{watched_after} episodios."
        ),
    )

    # Dejamos un episodio para estadísticas.
    ctx.client.post(
        episode_url,
        data={"return_to": "season"},
    )

    logout(ctx)


def test_profile_statistics(ctx):
    login(
        ctx,
        ctx.names["client"],
    )

    profile = ctx.client.get(
        "/profile"
    )
    statistics = ctx.client.get(
        "/statistics"
    )

    assert_status(profile, 200)
    assert_status(statistics, 200)

    body = response_text(statistics)

    require(
        "window.statisticsData"
        in body,
        (
            "La página no contiene los "
            "datos para Chart.js."
        ),
    )

    movie_records = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM movie_watches
        WHERE user_id = ?
        """,
        (ctx.ids["client"],),
    )

    episode_records = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM episode_watches
        WHERE user_id = ?
        """,
        (ctx.ids["client"],),
    )

    require(
        movie_records >= 1,
        (
            "No hay actividad de películas "
            "para validar estadísticas."
        ),
    )
    require(
        episode_records >= 1,
        (
            "No hay actividad de episodios "
            "para validar estadísticas."
        ),
    )

    logout(ctx)


def test_admin_user_crud(ctx):
    login(
        ctx,
        ctx.names["admin"],
    )

    username = (
        ctx.names["admin_created"]
    )

    response = ctx.client.post(
        "/admin/users/create",
        data={
            "username": username,
            "email": (
                f"{username}@phase13.test"
            ),
            "display_name": (
                "Cliente creado Phase13"
            ),
            "country_code": "ES",
            "password": TEST_PASSWORD,
        },
        follow_redirects=False,
    )

    assert_redirect_contains(
        response,
        "/admin/users",
    )

    created = row(
        ctx,
        """
        SELECT id, is_active
        FROM users
        WHERE username = ?
          AND role = 'client'
        """,
        (username,),
    )

    require(
        created is not None,
        "Admin no creó el cliente.",
    )

    user_id = created["id"]

    edited_name = (
        "Cliente editado Phase13"
    )

    response = ctx.client.post(
        (
            f"/admin/users/"
            f"{user_id}/edit"
        ),
        data={
            "username": username,
            "email": (
                f"{username}@phase13.test"
            ),
            "display_name": edited_name,
            "country_code": "ES",
            "password": "",
        },
        follow_redirects=False,
    )

    assert_redirect_contains(
        response,
        "/admin/users",
    )

    require(
        scalar(
            ctx,
            """
            SELECT display_name
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        == edited_name,
        "Admin no editó el cliente.",
    )

    toggle_url = (
        f"/admin/users/"
        f"{user_id}/toggle-active"
    )

    ctx.client.post(toggle_url)

    require(
        scalar(
            ctx,
            """
            SELECT is_active
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        == 0,
        "No se desactivó el cliente.",
    )

    ctx.client.post(toggle_url)

    require(
        scalar(
            ctx,
            """
            SELECT is_active
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        == 1,
        "No se reactivó el cliente.",
    )

    logout(ctx)


def test_admin_movie_crud(ctx):
    login(
        ctx,
        ctx.names["admin"],
    )

    genre_id = ctx.catalog["genre_id"]
    title = "PHASE13 Película automática"

    create_data = {
        "media_type": "movie",
        "title": title,
        "original_title": title,
        "overview": (
            "Contenido temporal de prueba."
        ),
        "release_date": "2026-08-24",
        "runtime_minutes": "123",
        "original_language": "es",
        "poster_path": "",
        "backdrop_path": "",
        "content_level": "general",
        "content_reason": "",
        "certification": "12",
        "certification_country": "ES",
        "season_count": "",
        "episodes_per_season": "",
        "episode_runtime_minutes": "",
        "genre_ids": str(genre_id),
    }

    response = ctx.client.post(
        "/admin/catalog/create",
        data=create_data,
        follow_redirects=False,
    )

    assert_redirect_contains(
        response,
        "/admin/catalog",
    )

    media = row(
        ctx,
        """
        SELECT id, source, is_visible
        FROM media
        WHERE title = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (title,),
    )

    require(
        media is not None,
        "No se creó la película manual.",
    )
    require(
        media["source"] == "manual",
        "La película no quedó como manual.",
    )

    media_id = media["id"]
    new_title = (
        "PHASE13 Película editada"
    )

    edit_data = dict(create_data)
    edit_data["title"] = new_title

    response = ctx.client.post(
        (
            f"/admin/catalog/"
            f"{media_id}/edit"
        ),
        data=edit_data,
        follow_redirects=False,
    )

    assert_redirect_contains(
        response,
        "/admin/catalog",
    )

    require(
        scalar(
            ctx,
            """
            SELECT title
            FROM media
            WHERE id = ?
            """,
            (media_id,),
        )
        == new_title,
        "No se editó la película.",
    )

    toggle_url = (
        f"/admin/catalog/"
        f"{media_id}/toggle-visible"
    )

    ctx.client.post(toggle_url)

    require(
        scalar(
            ctx,
            """
            SELECT is_visible
            FROM media
            WHERE id = ?
            """,
            (media_id,),
        )
        == 0,
        (
            "La eliminación lógica "
            "no ocultó la película."
        ),
    )

    assert_status(
        ctx.client.get(
            f"/catalog/{media_id}"
        ),
        404,
    )

    ctx.client.post(toggle_url)

    require(
        scalar(
            ctx,
            """
            SELECT is_visible
            FROM media
            WHERE id = ?
            """,
            (media_id,),
        )
        == 1,
        "La restauración no funcionó.",
    )

    assert_status(
        ctx.client.get(
            f"/catalog/{media_id}"
        ),
        200,
    )

    logout(ctx)


def test_admin_series_creation(ctx):
    login(
        ctx,
        ctx.names["admin"],
    )

    genre_id = ctx.catalog["genre_id"]
    title = "PHASE13 Serie automática"

    response = ctx.client.post(
        "/admin/catalog/create",
        data={
            "media_type": "series",
            "title": title,
            "original_title": title,
            "overview": (
                "Serie temporal de prueba."
            ),
            "release_date": "2026-08-24",
            "runtime_minutes": "",
            "original_language": "es",
            "poster_path": "",
            "backdrop_path": "",
            "content_level": "general",
            "content_reason": "",
            "certification": "12",
            "certification_country": "ES",
            "season_count": "2",
            "episodes_per_season": "3",
            "episode_runtime_minutes": "45",
            "genre_ids": str(genre_id),
        },
        follow_redirects=False,
    )

    assert_redirect_contains(
        response,
        "/admin/catalog",
    )

    media_id = scalar(
        ctx,
        """
        SELECT id
        FROM media
        WHERE title = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (title,),
    )

    require(
        media_id is not None,
        "No se creó la serie manual.",
    )

    seasons = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM seasons
        WHERE media_id = ?
        """,
        (media_id,),
    )

    episodes = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM episodes AS e
        JOIN seasons AS s
          ON s.id = e.season_id
        WHERE s.media_id = ?
        """,
        (media_id,),
    )

    require(
        seasons == 2,
        (
            "Se esperaban 2 temporadas; "
            f"hay {seasons}."
        ),
    )

    require(
        episodes == 6,
        (
            "Se esperaban 6 episodios; "
            f"hay {episodes}."
        ),
    )

    logout(ctx)


def test_admin_filters_statistics(ctx):
    login(
        ctx,
        ctx.names["admin"],
    )

    paths = (
        (
            "/admin/catalog"
            "?q=%27%20OR%201%3D1%20--"
            "&type=movie"
            "&visibility=all"
            "&source=all"
            "&content_level=all"
        ),
        (
            "/admin/statistics"
            "?status=active"
            "&sort=records"
            "&q=phase13"
        ),
        (
            "/admin/statistics"
            "?status=inactive"
            "&sort=username"
        ),
    )

    for path in paths:
        assert_status(
            ctx.client.get(path),
            200,
        )

    stats = ctx.client.get(
        "/admin/statistics"
    )

    require(
        "window.adminStatisticsData"
        in response_text(stats),
        (
            "No aparecen los datos "
            "Chart.js de administración."
        ),
    )

    logout(ctx)


def test_demo100_on_temporary_db(
    ctx,
    runner,
):
    generator_path = (
        PROJECT_ROOT
        / "scripts"
        / "generate_demo_users.py"
    )

    require(
        generator_path.exists(),
        (
            "No existe "
            "scripts/generate_demo_users.py."
        ),
    )

    spec = (
        importlib.util
        .spec_from_file_location(
            "phase13_demo_generator",
            generator_path,
        )
    )

    require(
        spec is not None
        and spec.loader is not None,
        "No se pudo cargar el generador demo.",
    )

    module = (
        importlib.util
        .module_from_spec(spec)
    )
    spec.loader.exec_module(module)

    require(
        hasattr(module, "generate_demo"),
        (
            "El generador no expone "
            "generate_demo()."
        ),
    )

    module.DATABASE_PATH = ctx.database

    output = io.StringIO()

    started = time.perf_counter()

    with contextlib.redirect_stdout(output):
        module.generate_demo(
            42,
            100,
        )

    elapsed = (
        time.perf_counter()
        - started
    )

    total_demo = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM users
        WHERE username LIKE 'demo_%'
        """,
    )

    demo_movies = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM movie_watches AS mw
        JOIN users AS u
          ON u.id = mw.user_id
        WHERE u.username LIKE 'demo_%'
        """,
    )

    demo_episodes = scalar(
        ctx,
        """
        SELECT COUNT(*)
        FROM episode_watches AS ew
        JOIN users AS u
          ON u.id = ew.user_id
        WHERE u.username LIKE 'demo_%'
        """,
    )

    require(
        total_demo == 100,
        (
            "El generador creó "
            f"{total_demo}/100 usuarios."
        ),
    )

    require(
        demo_movies > 0,
        (
            "Los usuarios demo "
            "no tienen películas vistas."
        ),
    )

    require(
        demo_episodes > 0,
        (
            "Los usuarios demo "
            "no tienen episodios vistos."
        ),
    )

    runner.note(
        (
            "Generador 100 usuarios: "
            f"{elapsed:.2f}s, "
            f"{demo_movies} registros de películas, "
            f"{demo_episodes} episodios."
        )
    )

    login(
        ctx,
        ctx.names["admin"],
    )

    page_started = time.perf_counter()
    response = ctx.client.get(
        "/admin/statistics"
    )
    page_elapsed = (
        time.perf_counter()
        - page_started
    )

    assert_status(response, 200)

    runner.note(
        (
            "/admin/statistics con 100 demo: "
            f"{page_elapsed:.2f}s."
        )
    )

    logout(ctx)


def test_final_database_integrity(ctx):
    test_database_integrity(ctx)


def write_report(runner, path):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        runner.report_text() + "\n",
        encoding="utf-8",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Batería automática de pruebas finales "
            "de Netflix del Temu."
        )
    )

    parser.add_argument(
        "--skip-demo100",
        action="store_true",
        help=(
            "Omite la prueba del generador "
            "de 100 usuarios."
        ),
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help=(
            "No guarda el informe de texto."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print()
    print(
        "=" * 72
    )
    print(
        "NETFLIX DEL TEMU — FASE 13 — TESTING AUTOMÁTICO"
    )
    print(
        "=" * 72
    )
    print(
        "La base de datos real NO será modificada."
    )
    print()

    runner = Runner()

    with tempfile.TemporaryDirectory(
        prefix="netflix_temu_phase13_"
    ) as directory:
        ctx = Context(
            Path(directory)
        )

        runner.run(
            "1. Compilación Python",
            test_python_compilation,
        )

        runner.run(
            "2. Copia segura de SQLite",
            lambda: create_database_backup(
                ctx
            ),
        )

        if not ctx.database.exists():
            print()
            print(
                "No se pudo preparar la base "
                "temporal. Pruebas detenidas."
            )
            return 1

        runner.run(
            "3. Integridad SQLite inicial",
            lambda: test_database_integrity(
                ctx
            ),
        )

        runner.run(
            "4. Esquema de 16 tablas",
            lambda: test_database_schema(
                ctx
            ),
        )

        runner.run(
            "5. Preparación de usuarios de prueba",
            lambda: create_test_users(
                ctx
            ),
        )

        runner.run(
            "6. Descubrimiento de contenido",
            lambda: discover_catalog(
                ctx
            ),
        )

        runner.run(
            "7. Creación de Flask de testing",
            lambda: create_app(
                ctx
            ),
        )

        if ctx.app is None:
            print()
            print(
                "Flask no pudo inicializarse. "
                "Pruebas detenidas."
            )
            return 1

        runner.run(
            "8. Plantillas Jinja",
            lambda: test_jinja_templates(
                ctx
            ),
        )

        runner.run(
            "9. Assets CSS/JS",
            lambda: test_static_assets(
                ctx
            ),
        )

        runner.run(
            "10. Mapa de rutas Flask",
            lambda: test_route_map(
                ctx
            ),
        )

        runner.run(
            "11. Rutas públicas y 404",
            lambda: test_public_routes(
                ctx
            ),
        )

        runner.run(
            "12. Protección de rutas",
            lambda: test_protected_routes(
                ctx
            ),
        )

        runner.run(
            "13. Validaciones de registro",
            lambda: test_register_validation(
                ctx
            ),
        )

        runner.run(
            "14. Registro y duplicados",
            lambda: test_register_and_duplicate(
                ctx
            ),
        )

        runner.run(
            "15. Login activo/inactivo/admin",
            lambda: test_login_behaviour(
                ctx
            ),
        )

        runner.run(
            "16. Logout solo por POST",
            lambda: test_logout_method(
                ctx
            ),
        )

        runner.run(
            "17. Permisos cliente/admin",
            lambda: test_role_permissions(
                ctx
            ),
        )

        runner.run(
            "18. Catálogo, filtros y seguridad",
            lambda: test_catalog_filters(
                ctx
            ),
        )

        runner.run(
            "19. Fichas y temporadas",
            lambda: test_media_details(
                ctx
            ),
        )

        runner.run(
            "20. Política mature/explicit",
            lambda: test_content_policy(
                ctx
            ),
        )

        runner.run(
            "21. Favoritos y películas vistas",
            lambda: test_favorites_and_movie_watch(
                ctx
            ),
        )

        runner.run(
            "22. Episodios y temporadas vistas",
            lambda: test_series_tracking(
                ctx
            ),
        )

        runner.run(
            "23. Perfil y estadísticas cliente",
            lambda: test_profile_statistics(
                ctx
            ),
        )

        runner.run(
            "24. CRUD administrativo de usuarios",
            lambda: test_admin_user_crud(
                ctx
            ),
        )

        runner.run(
            "25. CRUD administrativo película",
            lambda: test_admin_movie_crud(
                ctx
            ),
        )

        runner.run(
            "26. Creación administrativa serie",
            lambda: test_admin_series_creation(
                ctx
            ),
        )

        runner.run(
            "27. Filtros y estadísticas admin",
            lambda: test_admin_filters_statistics(
                ctx
            ),
        )

        if not args.skip_demo100:
            runner.run(
                "28. Generador de 100 usuarios demo",
                lambda: test_demo100_on_temporary_db(
                    ctx,
                    runner,
                ),
            )

        runner.run(
            "29. Integridad SQLite final",
            lambda: test_final_database_integrity(
                ctx
            ),
        )

    report = runner.report_text()

    print()
    print(report)

    if not args.no_report:
        report_path = (
            PROJECT_ROOT
            / "documentation"
            / "sources"
            / "FASE13_TEST_RESULTS.txt"
        )

        write_report(
            runner,
            report_path,
        )

        print()
        print(
            "Informe guardado en:"
        )
        print(
            report_path.relative_to(
                PROJECT_ROOT
            )
        )

    if runner.failures:
        print()
        print(
            "RESULTADO: HAY ERRORES QUE CORREGIR."
        )
        return 1

    print()
    print(
        "RESULTADO: BATERÍA AUTOMÁTICA SUPERADA."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
