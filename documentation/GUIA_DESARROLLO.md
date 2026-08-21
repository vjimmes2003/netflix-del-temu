# Guía de desarrollo — Netflix del Temu

## 1. Introducción

Aplicación web privada para gestionar y hacer seguimiento de contenidos audiovisuales. Permitirá consultar películas y series, registrar contenido visto, guardar favoritos, valorar contenido, consultar progreso y visualizar estadísticas.

El proyecto se desarrolla a partir de la **Propuesta B del Proyecto Final de Python**.

---

# Fase 1 — Preparación del proyecto

## Objetivo

Preparar el entorno de desarrollo, definir la estructura inicial y comprobar el funcionamiento básico de Flask.

## Tecnologías

- Python 3.10.10
- Flask
- SQLite mediante `sqlite3`
- HTML5, CSS3 y JavaScript
- Bootstrap
- Chart.js
- API de TMDB
- Git

Se optó por SQL directo, sin ORM, para mantener las consultas visibles y facilitar su explicación.

## Implementación

Se creó el entorno virtual:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Se preparó una estructura modular con carpetas para aplicación, base de datos, scripts y documentación.

Flask se configuró mediante `create_app()` en `app/__init__.py`, utilizando `run.py` como punto de entrada.

También se creó una landing inicial con:

- mensaje principal;
- acceso a registro e inicio de sesión;
- estilos propios en tonos oscuros y violeta.

## Verificación

```powershell
python run.py
```

Resultados:

| Prueba | Resultado |
|---|---|
| Ruta `/` | HTTP 200 |
| Carga de CSS | Correcta |
| Ruta inexistente `/prueba` | HTTP 404 esperado |

## Evidencia

```text
documentation/screenshots/fase1_01_flask_funcionando.png
```

## Commits

```text
chore: initialize project structure
feat: create Flask application skeleton
```

**Estado: Fase 1 completada.**

---

# Fase 2 — Base de datos

## Objetivo

Diseñar e implementar el modelo de datos de la aplicación utilizando SQLite y SQL directo.

## Modelo

El esquema incluye **16 tablas** organizadas en cuatro bloques:

- usuarios;
- catálogo audiovisual;
- actividad y valoraciones;
- clasificación mediante géneros, países y etiquetas.

Las series se estructuran mediante:

```text
MEDIA → SEASONS → EPISODES
```

Las relaciones N:M se resuelven mediante tablas intermedias como `favorites`, `media_genres`, `media_countries` y `media_tags`.

El modelo también incorpora borrado lógico mediante `is_active` e `is_visible`.

## Implementación

El esquema completo se definió en:

```text
database/schema.sql
```

El acceso a SQLite se implementó en:

```text
app/db.py
```

La base de datos se crea en:

```text
instance/netflix_del_temu.sqlite3
```

y puede inicializarse mediante:

```powershell
python -m flask --app run init-db
```

Se añadieron claves primarias, claves foráneas, restricciones `UNIQUE`, `CHECK` e índices para las consultas más habituales.

## Validación

Se crearon dos scripts auxiliares:

```text
scripts/check_db.py
scripts/validate_schema.py
```

Resultados obtenidos:

| Comprobación | Resultado |
|---|---|
| Tablas creadas | 16 |
| Foreign Keys | Activadas |
| `PRAGMA integrity_check` | `ok` |
| Usuarios duplicados | Bloqueados |
| Roles inválidos | Bloqueados |
| Foreign Keys inválidas | Bloqueadas |
| Favoritos duplicados | Bloqueados |
| Valoraciones fuera de 1–10 | Bloqueadas |
| Relación serie → temporada → episodio | Correcta |
| Relaciones N:M | Correctas |

Las pruebas se ejecutan sobre una base de datos temporal en memoria, evitando modificar los datos reales.

## Diagrama

El modelo entidad-relación se documentó en:

```text
documentation/diagrams/modelo_er.md
```

## Evidencias

```text
documentation/screenshots/fase2_01_validacion_schema.png
documentation/screenshots/fase2_02_modelo_er.png
```

## Decisiones técnicas

- `tmdb_id` puede ser `NULL` para permitir contenido creado manualmente.
- Las estadísticas se calcularán mediante consultas SQL y no mediante una tabla específica.
- Reglas como impedir temporadas en películas o películas dentro de `movie_watches` se controlarán desde la lógica de aplicación.

## Commit de cierre

```text
feat: implement SQLite database schema
```

**Estado: Fase 2 completada.**

---

# Flujo de trabajo

Cada fase seguirá el mismo proceso:

1. Diseñar.
2. Implementar.
3. Probar y corregir.
4. Guardar evidencias.
5. Documentar.
6. Revisar.
7. Crear commit.
8. Continuar con la siguiente fase.

---

# Fuentes técnicas

- Flask: https://flask.palletsprojects.com/
- Python `sqlite3`: https://docs.python.org/3/library/sqlite3.html
- TMDB API: https://developer.themoviedb.org/
- Bootstrap: https://getbootstrap.com/
- Chart.js: https://www.chartjs.org/
