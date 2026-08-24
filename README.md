# Netflix del Temu

Aplicación web para gestionar un catálogo de películas y series, registrar favoritos y contenido visto, seguir el progreso de series y consultar estadísticas personales y administrativas.

## Stack

```text
Python 3.10
Flask
Flask-Login
SQLite / sqlite3
TMDB API
HTML + Jinja
Bootstrap
CSS
JavaScript
Chart.js
```

## Instalación rápida

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Crear `.env` a partir de `.env.example`.

Ejecutar:

```powershell
python -m flask --app run --debug run
```

Abrir:

```text
http://localhost:5000
```

## Funciones

Cliente:

```text
catálogo
búsqueda
filtros
favoritos
vistos
progreso de series
perfil
estadísticas
contenido mature
```

Administrador:

```text
usuarios
catálogo
soft delete
restauración
estadísticas globales
```

## Base de datos

SQLite:

```text
instance/netflix_del_temu.sqlite3
```

El esquema contiene 16 tablas.

## Testing

```powershell
python scripts/run_phase13_tests.py
```

Resultado final validado:

```text
29 PASS
0 FAIL
0 SKIP
```

## Documentación

```text
documentation/GUIA_DESARROLLO.md
documentation/GUIA_MAESTRA_NETFLIX_DEL_TEMU.md
documentation/GUIA_DEFENSA_NETFLIX_DEL_TEMU.md
documentation/GUIA_SARAY_GIT_Y_RECUPERACION.md
```

## Historial

El repositorio conserva una evolución incremental por fases. Se recomienda etiquetar los commits como `fase-01` ... `fase-13` para poder estudiar cada versión con Git.

## Estado

Desarrollo técnico finalizado. Solo deben realizarse correcciones críticas y tareas de documentación/entrega.
