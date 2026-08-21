# Guía de desarrollo — Netflix del Temu

## 1. Introducción

Este documento recoge paso a paso el proceso seguido durante el desarrollo del proyecto final de Python.

El objetivo es documentar no solamente el resultado final de la aplicación, sino también las decisiones tomadas durante su diseño, las tecnologías utilizadas, la estructura del proyecto y los problemas encontrados durante el desarrollo.

La aplicación consiste en una plataforma web privada para la gestión y seguimiento de contenidos audiovisuales. Permitirá consultar películas y series, registrar contenido visto, guardar favoritos, realizar valoraciones, consultar el progreso de series y visualizar estadísticas relacionadas con la actividad del usuario.

El proyecto se desarrolla siguiendo los requisitos establecidos en la Propuesta B del Proyecto Final de Python.

---

# Fase 1 — Preparación del proyecto

## 1.1 Decisiones tecnológicas iniciales

Se decidió desarrollar una aplicación web utilizando Python y Flask.

La base de datos utilizada será SQLite mediante el módulo `sqlite3` incluido en Python.

Se decidió no utilizar un ORM como SQLAlchemy para mantener las consultas SQL visibles y facilitar tanto la comprensión como la explicación del funcionamiento de la base de datos.

Las principales tecnologías previstas son:

- Python 3.10.10
- Flask
- SQLite
- HTML5
- CSS3
- JavaScript
- Bootstrap
- Chart.js
- API de TMDB

El proyecto utilizará Git como sistema de control de versiones.

---

## 1.2 Creación del entorno virtual

Se creó un entorno virtual de Python dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
```

Posteriormente se activó mediante:

```powershell
.venv\Scripts\activate
```

Se verificó la versión de Python utilizada:

```text
Python 3.10.10
```

El objetivo del entorno virtual es aislar las dependencias utilizadas por el proyecto del resto de instalaciones de Python disponibles en el equipo.

---

## 1.3 Estructura inicial del proyecto

Se creó una primera estructura modular para separar las distintas responsabilidades de la aplicación:

```text
netflix-del-temu/
├── app/
│   ├── __init__.py
│   ├── admin.py
│   ├── auth.py
│   ├── catalog.py
│   ├── db.py
│   ├── statistics.py
│   └── tmdb_client.py
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

Dentro de `app` se reservaron módulos independientes para autenticación, administración, catálogo, estadísticas, acceso a la base de datos y comunicación con la API de TMDB.

La carpeta `database` almacenará el esquema SQL utilizado para crear la base de datos.

La carpeta `scripts` contendrá herramientas auxiliares, como el futuro proceso de importación de contenidos desde TMDB.

La carpeta `documentation` almacenará la documentación producida durante el desarrollo, diagramas, capturas de pantalla y fuentes consultadas.

---

## 1.4 Control de versiones

Se inicializó un repositorio Git para mantener un historial de cambios del proyecto.

La rama principal del repositorio se configuró con el nombre:

```text
main
```

También se creó un archivo `.gitignore` para evitar incluir en el repositorio archivos que no deben formar parte del código fuente, como:

- El entorno virtual `.venv`.
- El archivo `.env` con variables o secretos.
- Archivos de caché de Python.
- Bases de datos locales generadas durante el desarrollo.
- Archivos temporales del sistema o del editor.

La documentación del proyecto también se almacenará dentro del repositorio para que quede asociada a cada fase del desarrollo.

El primer commit se realizará una vez revisada la estructura inicial:

```text
chore: initialize project structure
```

A partir de este punto se realizarán commits independientes cuando se complete una funcionalidad o una fase relevante del desarrollo.

---

## 1.5 Estrategia de trabajo por fases

El proyecto se desarrollará de forma incremental.

Cada fase seguirá siempre el mismo proceso:

1. Diseñar lo que se va a realizar.
2. Implementar la funcionalidad.
3. Probar manualmente que funciona correctamente.
4. Corregir los errores encontrados.
5. Realizar las capturas necesarias.
6. Actualizar esta guía de desarrollo.
7. Revisar la fase completa.
8. Crear el commit correspondiente.
9. Pasar a la siguiente fase.

Este sistema permite mantener sincronizados el código, las pruebas realizadas, las capturas y la documentación.

---

## 1.6 Fuentes y documentación técnica

Durante el desarrollo se guardarán las fuentes oficiales utilizadas para justificar decisiones técnicas y facilitar posteriormente la elaboración de la memoria y la bibliografía.

Las referencias se almacenarán dentro de:

```text
documentation/sources/
```

Las fuentes principales previstas inicialmente son:

### Flask

Documentación oficial:

https://flask.palletsprojects.com/

Uso previsto en el proyecto:

Framework principal utilizado para desarrollar la aplicación web.

### Python — sqlite3

Documentación oficial:

https://docs.python.org/3/library/sqlite3.html

Uso previsto en el proyecto:

Acceso y gestión de la base de datos SQLite mediante consultas SQL directas.

### TMDB API

Documentación oficial:

https://developer.themoviedb.org/

Uso previsto en el proyecto:

Obtención de metadatos de películas, series, temporadas, episodios e imágenes.

### Bootstrap

Documentación oficial:

https://getbootstrap.com/

Uso previsto en el proyecto:

Base para componentes visuales y diseño responsive.

### Chart.js

Documentación oficial:

https://www.chartjs.org/

Uso previsto en el proyecto:

Representación gráfica de estadísticas del usuario y del administrador.

---

## 1.7 Estado actual de la Fase 1

Actualmente se ha completado:

- Creación de la carpeta del proyecto.
- Creación y activación del entorno virtual.
- Verificación de Python 3.10.10.
- Creación de la estructura inicial de carpetas y archivos.
- Inicialización del repositorio Git.
- Cambio de la rama principal a `main`.
- Creación del archivo `.gitignore`.
- Creación de la estructura inicial de documentación.

Antes de cerrar la Fase 1 todavía será necesario:

- Verificar y documentar las dependencias iniciales instaladas.
- Completar la configuración mínima de Flask.
- Crear una página mínima de prueba.
- Ejecutar la aplicación y comprobar que responde correctamente.
- Realizar una captura de la primera ejecución funcional.
- Revisar esta documentación.
- Crear los commits correspondientes.

La Fase 1 no se considerará terminada hasta completar y verificar estos puntos.
