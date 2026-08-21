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

Flask se configuró mediante `create_app()` en `app/__init__.py`, utilizando `run.py` como punto de entrada.

También se creó una landing inicial con estilos propios y accesos a registro e inicio de sesión.

## Verificación

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

El esquema incluye **16 tablas** para usuarios, catálogo audiovisual, actividad, valoraciones y clasificación.

Las series se estructuran mediante:

```text
MEDIA → SEASONS → EPISODES
```

Las relaciones N:M se resuelven mediante tablas intermedias.

## Implementación

Archivos principales:

```text
database/schema.sql
app/db.py
scripts/check_db.py
scripts/validate_schema.py
```

La base de datos se crea en:

```text
instance/netflix_del_temu.sqlite3
```

Inicialización:

```powershell
python -m flask --app run init-db
```

El esquema incluye claves primarias, claves foráneas, restricciones `UNIQUE`, `CHECK` e índices.

## Validación

| Comprobación | Resultado |
|---|---|
| Tablas creadas | 16 |
| Foreign Keys | Activadas |
| `PRAGMA integrity_check` | `ok` |
| Restricciones `UNIQUE` | Correctas |
| Restricciones `CHECK` | Correctas |
| Relaciones N:M | Correctas |
| Serie → temporada → episodio | Correcta |

Las pruebas se realizan sobre una base de datos temporal en memoria.

## Diagrama y evidencias

```text
documentation/diagrams/modelo_er.md
documentation/screenshots/fase2_01_validacion_schema.png
documentation/screenshots/fase2_02_modelo_er.png
```

## Decisiones técnicas

- `tmdb_id` puede ser `NULL` para admitir contenido creado manualmente.
- Las estadísticas se calcularán mediante consultas SQL.
- Algunas reglas de negocio se validarán desde la lógica Python.

## Commit

```text
feat: implement SQLite database schema
```

**Estado: Fase 2 completada.**

---

# Fase 3 — Autenticación y control de acceso

## Objetivo

Implementar registro, inicio y cierre de sesión, control de roles y protección de rutas privadas.

## Implementación

Se incorporó **Flask-Login** para gestionar sesiones y autenticación.

La clase `User`, basada en `UserMixin`, representa al usuario autenticado y aporta una aplicación directa de programación orientada a objetos.

Funciones implementadas:

- registro de clientes;
- inicio de sesión mediante usuario o correo;
- cierre de sesión;
- creación de administradores por CLI;
- control de usuarios activos;
- rutas privadas mediante `@login_required`;
- rutas administrativas mediante `@admin_required`.

Las contraseñas se almacenan mediante hash de Werkzeug.

## Control de acceso

| Prueba | Resultado |
|---|---|
| Registro de cliente | Correcto |
| Login | Correcto |
| Logout | Correcto |
| `/catalog` sin sesión | Redirige a login |
| `/admin/` como cliente | HTTP 403 |
| `/admin/` como administrador | Acceso permitido |

## Errores personalizados

Se añadieron páginas personalizadas para:

- 401
- 403
- 404
- 405
- 500

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

**Estado: Fase 3 completada.**

---
---


# Fase 4 — Integración con TMDB

## Objetivo

Conectar la aplicación con TMDB e importar contenido audiovisual real a la base de datos local.

## Implementación

Se creó la clase `TMDBClient` para centralizar:

- autenticación mediante token;
- peticiones HTTP;
- idioma de respuesta;
- películas;
- series;
- temporadas;
- episodios;
- construcción de URLs de imágenes.

El token se carga desde `.env` y no se almacena en Git.

Archivos principales:

```text
app/tmdb_client.py
scripts/test_tmdb.py
scripts/import_tmdb.py
scripts/check_catalog.py
```

## Importación

El importador sincroniza:

- películas;
- series;
- temporadas;
- episodios;
- géneros;
- países;
- etiquetas.

Se utiliza `UPSERT` para actualizar registros existentes sin duplicarlos.

La importación permite elegir cantidades y decidir si se descargan episodios:

```powershell
python .\scripts\import_tmdb.py --movies 100 --series 50
```

Los episodios pueden incluirse mediante:

```text
--episodes
```

## Validación

La conexión se comprobó con una película y una serie reales.

Resultado final del catálogo de prueba:

| Elemento | Cantidad |
|---|---:|
| Películas | 100 |
| Series | 50 |
| Temporadas | 673 |
| Episodios | 57.637 |
| Géneros | 26 |
| Países | 30 |
| Etiquetas | 1.086 |
| Integridad SQLite | `ok` |

También se verificó que una segunda importación no genera duplicados.

## Ajustes realizados

Durante las pruebas se detectaron y corrigieron dos casos:

- duraciones `0` de TMDB se convierten a `NULL`;
- los resultados de Discover se filtran por ID para evitar duplicados.

Para cargas generales se evita importar episodios de forma masiva salvo que sea necesario.

## Evidencias

```text
documentation/screenshots/fase4_01_conexion_tmdb.png
documentation/screenshots/fase4_02_catalogo_importado.png
```

## Commit de cierre

```text
feat: integrate TMDB catalog import
```

**Estado: Fase 4 completada.**

---

# Flujo de trabajo

Cada fase sigue el mismo proceso:

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
- Flask-Login: https://flask-login.readthedocs.io/
- Werkzeug Security: https://werkzeug.palletsprojects.com/
- Python `sqlite3`: https://docs.python.org/3/library/sqlite3.html
- TMDB API: https://developer.themoviedb.org/
- Bootstrap: https://getbootstrap.com/
- Chart.js: https://www.chartjs.org/
