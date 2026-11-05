<div align="center">

# 🎬 Netflix del Temu
### Tu catálogo de películas y series, sin pagar una suscripción por mirar lo que ya has visto.

**Aplicación web para organizar películas, series, favoritos, progreso y estadísticas personales.**

[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-111111?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Base_de_datos-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-Interfaz-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)

**[Cómo instalarlo](#-puesta-en-marcha) · [Funciones](#-funcionalidades) · [Estructura](#-estructura-del-proyecto) · [Documentación](#-documentación)**

</div>

---

## 🍿 ¿Qué es?

**Netflix del Temu** es un proyecto de gestión de contenido audiovisual desarrollado con **Python y Flask**. Permite explorar un catálogo de películas y series, registrar lo que has visto y consultar tu progreso. La información de las obras se integra con **TMDB**.

> **Importante:** no es un servicio de streaming ni aloja o distribuye películas. Es una aplicación para **organizar un catálogo y realizar seguimiento personal**.

## ✨ Funcionalidades

| 🎞️ Para usuarios | 🛠️ Para administradores |
| --- | --- |
| Explorar, buscar y filtrar el catálogo | Gestionar usuarios |
| Guardar películas y series favoritas | Administrar el catálogo |
| Marcar contenido como visto | Eliminación lógica y restauración |
| Seguir el progreso de las series | Consultar estadísticas globales |
| Consultar perfil y estadísticas personales | Supervisar la gestión de contenidos |
| Gestionar las preferencias de contenido | |

## 🧰 Tecnologías

- **Backend:** Python 3.10, Flask, Flask-Login.
- **Datos:** SQLite y `sqlite3` (esquema de 16 tablas).
- **Frontend:** HTML, Jinja2, Bootstrap, CSS y JavaScript.
- **Gráficos:** Chart.js.
- **Información audiovisual:** API de TMDB.

## 🚀 Puesta en marcha

**Requisitos:** Python 3.10 y acceso a una terminal (por ejemplo, la integrada en Visual Studio Code).

**1. Clonar el repositorio**
```powershell
git clone https://github.com/vjimmes2003/netflix-del-temu.git
cd netflix-del-temu
```

**2. Crear y activar un entorno virtual en Windows**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**3. Instalar dependencias**
```powershell
python -m pip install -r requirements.txt
```

**4. Configurar las variables de entorno**

Copia `.env.example` a `.env`, define una `SECRET_KEY` propia y configura `TMDB_TOKEN` si deseas utilizar la integración con TMDB.

```powershell
Copy-Item .env.example .env
```

> 🔒 Nunca subas tu archivo `.env` real ni credenciales personales a GitHub.

**5. Iniciar la aplicación**
```powershell
python -m flask --app run run
```

Abre **http://127.0.0.1:5000** en tu navegador.

Si la base de datos todavía no está inicializada, consulta los scripts y la documentación del repositorio antes de usarla; la aplicación emplea un esquema SQLite propio.

## 🗂️ Estructura del proyecto

```text
netflix-del-temu/
├── app/                    # Aplicación Flask y funcionalidades
│   ├── static/             # CSS, JavaScript y otros recursos
│   ├── templates/          # Vistas HTML con Jinja2
│   ├── auth.py             # Autenticación
│   ├── catalog.py          # Catálogo
│   ├── activity.py         # Actividad y progreso
│   ├── statistics.py       # Estadísticas
│   ├── admin.py            # Administración
│   ├── tmdb_client.py      # Integración con TMDB
│   └── db.py               # Acceso a SQLite
├── database/               # Esquema de base de datos
├── documentation/          # Guías del proyecto
├── scripts/                # Utilidades y pruebas
├── run.py                  # Punto de entrada de Flask
├── requirements.txt        # Dependencias Python
└── .env.example            # Ejemplo de configuración
```

## ✅ Pruebas

El proyecto incluye un script de pruebas:

```powershell
python scripts/run_phase13_tests.py
```

El resultado documentado en el proyecto fue **29 PASS · 0 FAIL · 0 SKIP**. Puede variar si se modifican dependencias, código o entorno.

## 📚 Documentación

En la carpeta [`documentation/`](documentation/) encontrarás:

- [Guía de desarrollo](documentation/GUIA_DESARROLLO.md)
- [Guía maestra](documentation/GUIA_MAESTRA_NETFLIX_DEL_TEMU.md)
- [Guía de defensa del proyecto](documentation/GUIA_DEFENSA_NETFLIX_DEL_TEMU.md)
- [Guía de Git y recuperación](documentation/GUIA_SARAY_GIT_Y_RECUPERACION.md)

El repositorio recoge una evolución del desarrollo por fases y admite su estudio mediante el historial de Git.

---

<div align="center">

**Hecho con Python, Flask y muchas ganas de tener las series controladas. 🍿**

Proyecto de **Víctor Hugo Jiménez Meseguer**.

*Netflix del Temu es un proyecto académico/personal, no afiliado a Netflix ni a TMDB.*

</div>
