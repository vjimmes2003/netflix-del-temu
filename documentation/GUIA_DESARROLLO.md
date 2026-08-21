# Guía de desarrollo — Netflix del Temu

## 1. Introducción

Aplicación web privada para gestionar y hacer seguimiento de contenidos audiovisuales. Permitirá consultar películas y series, registrar contenido visto, guardar favoritos, valorar contenido, consultar progreso y visualizar estadísticas.

El proyecto se desarrolla a partir de la **Propuesta B del Proyecto Final de Python**.

---

# Fase 1 — Preparación del proyecto

## 1.1 Objetivo

Preparar el entorno de desarrollo, definir la estructura inicial del proyecto y comprobar que Flask funciona correctamente.

## 1.2 Stack inicial

- **Python:** 3.10.10
- **Framework:** Flask
- **Base de datos:** SQLite mediante `sqlite3`
- **Frontend:** HTML5, CSS3, JavaScript y Bootstrap
- **Gráficas:** Chart.js
- **Datos externos:** API de TMDB
- **Control de versiones:** Git

Se descarta el uso de ORM para trabajar con SQL directo y mantener el acceso a datos más transparente y fácil de explicar.

## 1.3 Entorno virtual

Creación:

```powershell
python -m venv .venv
```

Activación:

```powershell
.venv\Scripts\activate
```

Versión comprobada:

```text
Python 3.10.10
```

## 1.4 Estructura inicial

```text
netflix-del-temu/
├── app/
│   ├── __init__.py
│   ├── admin.py
│   ├── auth.py
│   ├── catalog.py
│   ├── db.py
│   ├── statistics.py
│   ├── tmdb_client.py
│   ├── static/
│   └── templates/
├── database/
│   └── schema.sql
├── documentation/
│   ├── diagrams/
│   ├── screenshots/
│   ├── sources/
│   └── GUIA_DESARROLLO.md
├── scripts/
│   └── import_tmdb.py
├── .env
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run.py
```

La estructura separa autenticación, administración, catálogo, estadísticas, acceso a datos y servicios externos.

## 1.5 Git y archivos ignorados

Se inicializó Git y se estableció `main` como rama principal.

Primer commit:

```text
chore: initialize project structure
```

El archivo `.gitignore` excluye, entre otros:

- `.venv/`
- `.env`
- cachés de Python
- bases de datos locales
- archivos temporales del editor o del sistema

## 1.6 Esqueleto Flask

Se configuró `create_app()` en `app/__init__.py` y `run.py` como punto de entrada.

La variable `SECRET_KEY` se carga desde `.env`, mientras que `.env.example` sirve como plantilla de configuración.

También se creó una landing inicial con:

- mensaje principal;
- descripción de la aplicación;
- botón **Crear una cuenta**;
- botón **Iniciar sesión**;
- aviso de registro obligatorio para acceder al catálogo.

Archivos principales:

```text
app/templates/index.html
app/static/css/style.css
```

El diseño inicial utiliza una paleta oscura azulada con acento violeta.

## 1.7 Verificación

Ejecución:

```powershell
python run.py
```

Resultado:

```text
* Serving Flask app 'app'
* Debug mode: on
* Running on http://127.0.0.1:5000
```

Comprobaciones realizadas:

| Prueba | Resultado |
|---|---|
| Acceso a `/` | Correcto — HTTP 200 |
| Carga de CSS | Correcta |
| Ruta `/prueba` | HTTP 404 esperado |
| `/favicon.ico` | HTTP 404 esperado en esta fase |

La aplicación quedó correctamente operativa en entorno de desarrollo.

## 1.8 Evidencia

Captura guardada en:

```text
documentation/screenshots/fase1_01_flask_funcionando.png
```

La imagen demuestra la carga correcta de la landing y del diseño CSS.

## 1.9 Flujo de trabajo

Cada fase seguirá este proceso:

1. Diseñar.
2. Implementar.
3. Probar.
4. Corregir.
5. Capturar evidencias.
6. Documentar.
7. Revisar.
8. Crear commit.
9. Pasar a la siguiente fase.

## 1.10 Fuentes técnicas iniciales

- Flask: https://flask.palletsprojects.com/
- Python `sqlite3`: https://docs.python.org/3/library/sqlite3.html
- TMDB API: https://developer.themoviedb.org/
- Bootstrap: https://getbootstrap.com/
- Chart.js: https://www.chartjs.org/

## 1.11 Estado de la fase

**Fase 1 completada.**

Se dispone de:

- entorno virtual operativo;
- estructura inicial del proyecto;
- Git configurado;
- Flask funcionando;
- landing inicial;
- estilos básicos;
- primera evidencia gráfica;
- documentación inicial.

### Commit de cierre previsto

```text
feat: create Flask application skeleton
```

La siguiente fase será el **diseño del modelo de datos y la creación del esquema SQL**.
