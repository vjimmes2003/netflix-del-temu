# Guía de desarrollo — Netflix del Temu

## Introducción

Aplicación web privada para consultar, organizar y hacer seguimiento de películas y series.

Tecnologías principales:

- Python 3.10.10
- Flask
- Flask-Login
- SQLite mediante `sqlite3`
- HTML/CSS/JavaScript
- TMDB API
- Bootstrap
- Chart.js
- Git

Flujo de trabajo:

```text
Diseñar → Implementar → Probar → Corregir → Capturar → Documentar → Commit
```

---

# Fase 1 — Preparación del proyecto

## Objetivo
Crear la estructura inicial, entorno virtual y aplicación Flask mínima.

## Implementación
- Entorno virtual `.venv`.
- Patrón `create_app()`.
- `run.py` como punto de entrada.
- Landing inicial.
- CSS propio.
- `.env` para variables privadas.
- `.gitignore` para excluir entorno, secretos y base local.

## Validación
- `/` devuelve HTTP 200.
- CSS carga correctamente.
- Ruta inexistente devuelve 404.

## Evidencia
```text
documentation/screenshots/fase1_01_flask_funcionando.png
```

## Commits
```text
chore: initialize project structure
feat: create Flask application skeleton
```

**Estado: completada.**

---

# Fase 2 — Base de datos

## Objetivo
Diseñar el modelo de datos completo utilizando SQLite y SQL directo.

## Implementación
- 16 tablas.
- Usuarios, contenido, temporadas y episodios.
- Géneros/subgéneros, países y etiquetas.
- Favoritos, contenido visto y valoraciones.
- Relaciones N:M mediante tablas intermedias.
- Foreign Keys, `UNIQUE`, `CHECK` e índices.
- Base local en `instance/netflix_del_temu.sqlite3`.

Archivos principales:
```text
database/schema.sql
app/db.py
scripts/check_db.py
scripts/validate_schema.py
```

## Validación
- 16 tablas creadas.
- Foreign Keys activadas.
- Restricciones verificadas.
- Relaciones N:M correctas.
- Serie → temporada → episodio correcta.
- `PRAGMA integrity_check = ok`.

## Evidencias
```text
documentation/screenshots/fase2_01_validacion_schema.png
documentation/screenshots/fase2_02_modelo_er.png
```

## Commit
```text
feat: implement SQLite database schema
```

**Estado: completada.**

---

# Fase 3 — Autenticación y acceso

## Objetivo
Implementar usuarios, sesiones y separación entre clientes y administradores.

## Implementación
- Flask-Login.
- Clase `User(UserMixin)`.
- Registro de clientes.
- Login por usuario o email.
- Logout por POST.
- Contraseñas almacenadas mediante hash.
- Usuarios activos/inactivos.
- Creación de administradores por CLI.
- `@login_required`.
- Decorador `@admin_required`.
- Errores personalizados 401, 403, 404, 405 y 500.

## Validación
- Registro correcto.
- Login y logout correctos.
- `/catalog` protegido.
- Cliente recibe 403 en `/admin/`.
- Administrador puede entrar al panel.

## Evidencias
```text
documentation/screenshots/fase3_01_login.png
documentation/screenshots/fase3_02_cliente_autenticado.png
documentation/screenshots/fase3_03_acceso_denegado.png
documentation/screenshots/fase3_04_panel_admin.png
```

## Commit
```text
feat: implement authentication and access control
```

**Estado: completada.**

---

# Fase 4 — Integración con TMDB

## Objetivo
Importar contenido audiovisual real desde TMDB a SQLite.

## Implementación
Se creó `TMDBClient` para:
- autenticación Bearer;
- películas y series;
- temporadas y episodios;
- imágenes;
- Discover.

El importador sincroniza:
- películas;
- series;
- temporadas;
- episodios opcionales;
- géneros;
- países;
- etiquetas.

Archivos:
```text
app/tmdb_client.py
scripts/test_tmdb.py
scripts/import_tmdb.py
scripts/check_catalog.py
```

## Mejoras
- `UPSERT` para evitar duplicados.
- IDs de Discover deduplicados.
- Duraciones `0` convertidas a `NULL`.
- Episodios no se importan masivamente por defecto.

## Resultado de prueba
```text
100 películas
50 series
673 temporadas
57.637 episodios
Integridad: ok
```

## Evidencias
```text
documentation/screenshots/fase4_01_conexion_tmdb.png
documentation/screenshots/fase4_02_catalogo_importado.png
```

## Commit
```text
feat: integrate TMDB catalog import
```

**Estado: completada.**

---

# Fase 5 — Catálogo y control de contenido

## Objetivo
Crear el catálogo de cliente y sanear los datos externos antes de mostrarlos.

## Implementación
- Catálogos separados de películas y series.
- Paginación de 24 elementos.
- Ficha individual con géneros, países, etiquetas y temporadas.
- Protección de acceso directo por URL.
- Archivos principales: `app/catalog.py`, `app/content_policy.py`, `scripts/clean_catalog.py` y `scripts/migrate_content_levels.py`.

## Saneamiento TMDB
Se detectaron títulos sin traducción legible y contenido explícito dentro de Discover.

Prioridad de título:
```text
Español → Inglés → Original latino → excluir
```

Clasificación:
```text
general  → visible normalmente
mature   → opcional para usuarios +18
explicit → nunca visible para clientes
```

`mature` incluye 18+, TV-MA, NC-17 y determinadas keywords maduras.
`explicit` incluye hentai, softcore, pornografía y equivalentes.

Se corrigieron falsos positivos:
- `16` y `R` no implican `mature`;
- `adult animation` no implica `mature`.

## Base de datos
Nuevos campos en `media`:
```text
content_level
content_reason
certification
certification_country
```

Nuevos campos en `users`:
```text
mature_content_enabled
mature_content_confirmed_at
```

`is_visible` queda reservado para ocultación administrativa.

## Resultado
```text
150 contenidos revisados
126 general
17 mature
7 explicit
7 títulos actualizados
0 errores
```

## Control de contenido maduro
La primera activación requiere confirmar mayoría de 18 años y validar la contraseña actual.
La confirmación se guarda en `mature_content_confirmed_at`.

Después aparece un slider rápido en el catálogo:
```text
OFF → solo general
ON  → general + mature
```

El slider puede cambiarse sin volver a introducir la contraseña. `explicit` permanece bloqueado siempre.

## Seguridad y validación
- El filtrado se realiza mediante SQL, no solo desde HTML.
- Catálogo y paginación correctos.
- Filtros `general/mature/explicit` correctos.
- Acceso directo a contenido restringido bloqueado.
- Confirmación +18 y slider operativo.

El estilo visual se refinará junto al diseño general de la aplicación en una fase posterior.

## Desarrollo
```powershell
# Terminal 1
python -m flask --app run --debug run
# Terminal 2: scripts, pruebas, migraciones y Git
```

## Commit
```text
feat: build catalog and content filtering
```

**Estado: completada.**

---

# Fuentes técnicas

- Flask: https://flask.palletsprojects.com/
- Flask-Login: https://flask-login.readthedocs.io/
- Werkzeug: https://werkzeug.palletsprojects.com/
- Python sqlite3: https://docs.python.org/3/library/sqlite3.html
- TMDB API: https://developer.themoviedb.org/
- Bootstrap: https://getbootstrap.com/
- Chart.js: https://www.chartjs.org/
