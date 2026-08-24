# GUÍA MAESTRA — NETFLIX DEL TEMU

> Manual de traspaso. Está pensado para que otra persona pueda abrir el proyecto, entender cómo funciona, trabajar con él y saber dónde mirar cuando algo falle.

---

# 1. Qué es el proyecto

**Netflix del Temu** es una aplicación web de catálogo y seguimiento audiovisual.

No reproduce vídeo. Sirve para:

- consultar películas y series;
- buscar, filtrar y ordenar;
- guardar favoritos;
- marcar películas vistas;
- marcar episodios y temporadas;
- calcular progreso de series;
- ver un perfil y estadísticas;
- gestionar usuarios y catálogo desde administración;
- comparar actividad entre clientes.

El catálogo usa información real de **TMDB**, pero la aplicación guarda sus propios datos y la actividad de usuarios en **SQLite**.

Roles:

| Rol | Acceso |
|---|---|
| `client` | catálogo, favoritos, vistos, perfil, estadísticas y preferencias |
| `admin` | todo lo anterior + usuarios, catálogo y estadísticas administrativas |

---

# 2. Mapa mental

```text
NAVEGADOR
HTML + Jinja ya renderizado
CSS + Bootstrap
JavaScript + Chart.js
      │
      │ HTTP
      ▼
FLASK
 ├─ auth
 ├─ catalog
 ├─ activity
 ├─ statistics
 └─ admin
      │
      │ SQL parametrizado
      ▼
SQLITE

TMDB API
   │
   ▼
TMDBClient + import_tmdb.py
   │
   ▼
SQLITE
```

La regla mental más importante:

> La plantilla no es la base de datos. Flask consulta SQLite, prepara datos y Jinja genera el HTML.

---

# 3. Tecnologías usadas

| Tecnología | Uso |
|---|---|
| Python 3.10 | backend |
| Flask | framework web |
| Flask-Login | sesión y autenticación |
| `sqlite3` | SQL directo |
| SQLite | base relacional |
| Werkzeug | hash de contraseñas |
| python-dotenv | `.env` |
| Requests | llamadas a TMDB |
| Jinja | HTML dinámico |
| Bootstrap 5.3.8 | responsive y componentes |
| Bootstrap Icons 1.13.1 | iconos |
| CSS propio | diseño |
| JavaScript | interacción y gráficos |
| Chart.js 4.5.1 | visualización estadística |
| Git | control de versiones |

No se usa SQLAlchemy.

---

# 4. Puesta en marcha

## Activar entorno

```powershell
cd C:\ruta\netflix-del-temu
.\.venv\Scripts\Activate.ps1
```

## Variables privadas

`.env`:

```env
SECRET_KEY=clave_privada
TMDB_TOKEN=token_bearer_tmdb
SUPPORT_EMAIL=soporte@netflixdeltemu.test
```

No subir secretos reales a Git.

## Inicializar una base nueva

```powershell
python -m flask --app run init-db
```

Crea la estructura de `database/schema.sql` en:

```text
instance/netflix_del_temu.sqlite3
```

## Crear administrador

```powershell
python -m flask --app run create-admin
```

## Ejecutar

```powershell
python -m flask --app run --debug run
```

Abrir:

```text
http://localhost:5000
```

---

# 5. Recorrido por la aplicación

## Landing

![Landing final](screenshots/fase12_01_landing_publica.png)

Sin sesión permite iniciar sesión o crear cuenta.

## Catálogo

![Catálogo de películas](screenshots/fase12_02_catalogo_peliculas.png)

![Catálogo de series](screenshots/fase12_03_catalogo_series.png)

Filtros:

```text
tipo
búsqueda
género
orden
página
10 / 30 / 50 / 100 por página
```

## Biblioteca personal

![Favoritos](screenshots/fase12_04_favoritos.png)

![Vistos](screenshots/fase12_05_vistos.png)

## Perfil y estadísticas

![Perfil](screenshots/fase12_06_perfil.png)

![Estadísticas personales](screenshots/fase12_07_estadisticas.png)

## Administración

![Catálogo administrativo](screenshots/fase12_08_catalogo_admin.png)

![Estadísticas administrativas](screenshots/fase12_09_estadisticas_usuarios.png)

---

# 6. Estructura del proyecto

```text
netflix-del-temu/
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── catalog.py
│   ├── activity.py
│   ├── statistics.py
│   ├── admin.py
│   ├── content_policy.py
│   ├── db.py
│   ├── tmdb_client.py
│   ├── templates/
│   └── static/
│       ├── css/app.css
│       ├── js/app.js
│       └── favicon.ico
├── database/schema.sql
├── instance/netflix_del_temu.sqlite3
├── scripts/
├── documentation/
└── run.py
```

Snapshot al final del gran rediseño:

```text
40 archivos fuente
16.868 líneas aproximadas
19 Python
19 HTML
1 CSS
1 JS
```

La fase final añadió el test automático y el favicon.

---

# 7. Backend Python: archivo por archivo

## `run.py`

Punto de entrada mínimo.

```python
from app import create_app
app = create_app()
```

## `app/__init__.py`

Crea Flask y registra:

- `.env`;
- `SECRET_KEY`;
- ruta de SQLite;
- módulo `db`;
- Flask-Login;
- blueprints;
- `/`;
- filtros Jinja;
- handlers 401/403/404/405/500.

Blueprints:

```text
auth
catalog
activity
statistics
admin
```

## `app/db.py`

Funciones:

```text
get_db
close_db
init_db
init_db_command
init_app
```

Activa:

```sql
PRAGMA foreign_keys = ON;
```

y:

```python
db.row_factory = sqlite3.Row
```

## `app/auth.py`

Gestiona:

```text
User(UserMixin)
login
register
logout
load_user
admin_required
create-admin
cuentas activas/inactivas
```

Prefijo:

```text
/auth
```

Rutas:

```text
/auth/login
/auth/register
/auth/logout
```

Contraseñas:

```text
generate_password_hash
check_password_hash
```

## `app/catalog.py`

Responsable de:

```text
/catalog
filtros
búsqueda
paginación
fichas
temporadas
preferencias mature
```

Valores finales:

```text
per_page: 10, 30, 50, 100
tipo: movie, series
orden: newest, oldest, rating, popularity
búsqueda máxima: 100 caracteres
```

## `app/activity.py`

Responsable de:

```text
favoritos
películas vistas
episodios vistos
temporadas vistas
/favorites
/watched
```

No hay una tabla `series_watched`: el progreso se calcula desde episodios.

## `app/statistics.py`

Calcula:

```text
tiempo total
películas vistas
episodios
series empezadas
series completadas
favoritos
géneros
actividad mensual
```

Rutas:

```text
/profile
/statistics
```

No hay tabla de estadísticas.

## `app/admin.py`

Tres grandes bloques:

### Usuarios

```text
/admin/users
crear
editar
desactivar
reactivar
```

### Catálogo

```text
/admin/catalog
buscar
filtrar
crear
editar
ocultar
restaurar
```

### Estadísticas

```text
/admin/statistics
comparar clientes
actividad mensual
filtros
ordenación
```

## `app/content_policy.py`

Clasificación:

```text
general
mature
explicit
```

Regla:

```text
general  → visible
mature   → requiere confirmación +18 y activación
explicit → nunca visible a clientes
```

Se basa en:

- campo `adult` de TMDB;
- keywords;
- certificaciones.

## `app/tmdb_client.py`

Clase OOP `TMDBClient`.

Encapsula:

```text
Bearer token
requests.Session
movie_details
series_details
season_details
discover_movies
discover_series
image_url
```

---

# 8. Base de datos: 16 tablas

## Grupos

```text
USUARIOS
1  users

CATÁLOGO
2  media
3  seasons
4  episodes
5  genres
6  media_genres
7  countries
8  media_countries
9  tags
10 media_tags

ACTIVIDAD
11 favorites
12 movie_watches
13 episode_watches
14 media_ratings
15 season_ratings
16 episode_ratings
```

## Relaciones

```text
users ── favorites ───────── media
users ── movie_watches ───── media
users ── episode_watches ─── episodes

media ── media_genres ────── genres
media ── media_countries ─── countries
media ── media_tags ──────── tags

media(series)
   │
   └── seasons
          │
          └── episodes
```

## `users`

Campos importantes usados por la aplicación:

```text
id
username
email
password_hash
display_name
role
country_code
is_active
mature_content_enabled
mature_content_confirmed_at
created_at
updated_at
```

## `media`

Representa película o serie:

```text
id
tmdb_id
media_type
title
original_title
overview
release_date
release_year
runtime_minutes
original_language
poster_path
backdrop_path
tmdb_rating
tmdb_vote_count
popularity
source
is_visible
content_level
content_reason
certification
certification_country
```

## `seasons`

Pertenece a una serie mediante `media_id`.

## `episodes`

Pertenece a una temporada mediante `season_id`.

## Tablas N:M

```text
media_genres
media_countries
media_tags
favorites
```

## Actividad

`movie_watches` registra películas vistas.

`episode_watches` registra episodios vistos.

El progreso de series se deriva de `episode_watches`.

## Ratings

Las tablas de ratings están modeladas y validadas en el esquema, aunque la UI final no las convierte en su función principal.

---

# 9. SQL que debes entender

Se usa SQL directo:

```python
db.execute(
    "SELECT * FROM users WHERE id = ?",
    (user_id,),
)
```

El `?` separa código SQL de valores.

Operaciones usadas:

```text
SELECT
INSERT
UPDATE
DELETE
JOIN
LEFT JOIN
COUNT
SUM
AVG
GROUP BY
HAVING
ORDER BY
LIMIT
OFFSET
COALESCE
CASE
DISTINCT
```

## Progreso

```text
vistos = COUNT(episode_watches)
total = COUNT(episodes)
porcentaje = vistos * 100 / total
```

Completada:

```text
total > 0 AND vistos == total
```

---

# 10. Autenticación y seguridad

## Flask-Login

Conceptos:

```text
current_user
login_user
logout_user
@login_required
```

## Administrador

Además usa `admin_required`.

Ocultar un botón no es seguridad: el backend también bloquea la ruta.

## Contraseñas

Se almacenan como hash.

## Suspensión

```text
is_active = 0
```

Conserva historial.

## Soft delete de contenido

```text
is_visible = 0
```

Conserva relaciones y permite restaurar.

## SQL injection

Se usan placeholders y entradas validadas.

## XSS

Jinja escapa valores al renderizar. El test final incluyó una búsqueda con aspecto de `<script>`.

---

# 11. Política `general / mature / explicit`

Primera activación de mature:

```text
confirmar mayoría de edad
+
introducir contraseña actual
```

Después existe un toggle rápido.

`explicit` sigue bloqueado incluso si mature está activado.

El filtro se aplica en backend/SQL, no solo con CSS.

![Confirmación de contenido mature](screenshots/fase5_06_confirmacion_mature.png)

![Contenido explicit bloqueado](screenshots/fase5_08_explicito_bloqueado.png)

---

# 12. Favoritos y seguimiento

Favoritos:

```text
users ↔ favorites ↔ media
```

Películas:

```text
movie_watches
```

Series:

```text
episode_watches
```

Marcar temporada completa inserta todos los episodios visibles.

![Progreso de serie](screenshots/fase7_09_progreso_serie.png)

![Serie completada](screenshots/fase7_10_serie_completada.png)

---

# 13. Estadísticas

## Usuario

Los minutos de películas vienen de:

```text
movie_watches + media.runtime_minutes
```

Los minutos de series:

```text
episode_watches + episodes.runtime_minutes
```

Un `NULL` de duración aporta 0 mediante `COALESCE`.

## Administración

Agrupa actividad por usuario y mes.

No se almacenan resultados precalculados.

---

# 14. TMDB

Flujo:

```text
TMDB Discover
→ detalles
→ normalización
→ política de contenido
→ UPSERT
→ SQLite
```

Scripts relacionados:

```text
test_tmdb.py
import_tmdb.py
clean_catalog.py
check_catalog.py
migrate_content_levels.py
```

TMDB es **fuente externa**, no la base principal de la aplicación.

---

# 15. HTML y Jinja

Plantilla base:

```text
app/templates/base.html
```

Contiene:

```text
Bootstrap
Bootstrap Icons
app.css
navbar
flashes
bloques Jinja
Bootstrap JS
app.js
```

Plantillas cliente:

```text
index.html
catalog.html
media_detail.html
season_detail.html
favorites.html
watched.html
profile.html
statistics.html
content_settings.html
```

Autenticación:

```text
auth/login.html
auth/register.html
```

Administración:

```text
admin/dashboard.html
admin/users.html
admin/user_form.html
admin/media_list.html
admin/media_form.html
admin/statistics.html
```

Errores:

```text
errors/error.html
```

Jinja:

```jinja2
{{ variable }}
{% if condicion %}
{% for item in items %}
{{ url_for("endpoint") }}
```

---

# 16. CSS

Archivo final único:

```text
app/static/css/app.css
```

Contiene:

```text
tokens de color
tipografía
navbar
botones
formularios
hero
catálogo
fichas
actividad
perfil
estadísticas
administración
responsive
```

Paleta:

```text
violeta → marca/películas
azul    → series
cian    → actividad/estadísticas
coral   → favoritos
ámbar   → rating/mature
verde   → éxito/completado
```

---

# 17. Bootstrap y responsive

Bootstrap 5.3.8 y Bootstrap Icons 1.13.1.

Aporta:

```text
navbar collapse
dropdown
grid
forms
alerts
buttons
utilities
responsive
```

El aspecto no es Bootstrap por defecto: `app.css` define el diseño.

Pruebas visuales finales:

![Responsive ~956 px](screenshots/fase13_03_responsive_1.png)

![Responsive ~690 px](screenshots/fase13_04_responsive_2.png)

![Responsive ~304 px](screenshots/fase13_05_responsive_3.png)

---

# 18. JavaScript y Chart.js

Archivo:

```text
app/static/js/app.js
```

Funciones principales:

```text
initMediaForm
initAutoSubmit
initCatalogShortcut
setupChartTheme
renderMonthlyChart
initUserCharts
initAdminCharts
```

Python calcula los datos.

Las plantillas los exponen como:

```text
window.statisticsData
window.adminStatisticsData
```

JavaScript configura Chart.js para representarlos.

---

# 19. Administración

## Usuarios

```text
listar
crear
editar
desactivar
reactivar
```

## Catálogo

```text
listar
buscar
filtrar
crear película
crear serie
editar
ocultar
restaurar
```

Una serie manual puede crear estructura inicial con temporadas y episodios.

## Estadísticas

```text
clientes totales
clientes con actividad
registros
horas
cliente con más actividad
comparación
actividad mensual
tabla individual
```

---

# 20. Scripts de trabajo

```text
check_db.py                comprueba BD
validate_schema.py         valida esquema/restricciones
check_catalog.py           contadores catálogo
test_tmdb.py               prueba API
import_tmdb.py             importa
clean_catalog.py           sanea
migrate_content_levels.py  migra clasificación
generate_demo_users.py     actividad demo
run_phase13_tests.py       batería final
export_project_snapshot.py snapshot técnico
```

## Demo

```powershell
python scripts/generate_demo_users.py
python scripts/generate_demo_users.py --count 50
python scripts/generate_demo_users.py --clean
```

Final: 100 usuarios por defecto.

---

# 21. Testing final

```powershell
python scripts/run_phase13_tests.py
```

Trabaja sobre una copia temporal de SQLite.

Resultado real:

```text
PASS: 29
FAIL: 0
SKIP: 0
```

Carga temporal:

```text
100 usuarios demo
3.322 registros de películas
7.877 episodios
```

![Resultado final de testing](screenshots/fase13_01_resultado_testing_consola.png)

DevTools quedó sin errores de JavaScript tras corregir el favicon:

![DevTools final](screenshots/fase13_02_devtools.png)

---

# 22. Dónde tocar cada cosa

| Cambio | Archivo |
|---|---|
| configuración Flask | `app/__init__.py` |
| BD/conexión | `app/db.py` |
| login/registro | `app/auth.py` |
| catálogo | `app/catalog.py` |
| favoritos/vistos | `app/activity.py` |
| perfil/stats | `app/statistics.py` |
| administración | `app/admin.py` |
| mature/explicit | `app/content_policy.py` |
| TMDB | `app/tmdb_client.py` |
| estructura SQL | `database/schema.sql` |
| diseño | `app/static/css/app.css` |
| JS/gráficos | `app/static/js/app.js` |
| navegación base | `app/templates/base.html` |
| importación | `scripts/import_tmdb.py` |
| tests | `scripts/run_phase13_tests.py` |

---

# 23. Diagnóstico rápido

## Flask no arranca

```powershell
python -m flask --app run --debug run
```

Leer traceback.

## BD

```powershell
python scripts/check_db.py
python scripts/validate_schema.py
```

## TMDB

```powershell
python scripts/test_tmdb.py
```

Revisar `TMDB_TOKEN`.

## Admin devuelve 403

Comprobar:

```text
role = admin
is_active = 1
```

## Mature no aparece

Comprobar:

```text
mature_content_confirmed_at
mature_content_enabled
```

## Estadísticas raras

Revisar primero:

```text
movie_watches
episode_watches
favorites
```

---

# 24. Qué no tocar sin saber por qué

Especial cuidado con:

```text
schema.sql
foreign keys
content_level
is_active
is_visible
admin_required
login_required
consultas de progreso
consultas estadísticas
tmdb_id
```

No:

- guardar contraseñas en claro;
- concatenar entrada de usuario en SQL;
- convertir acciones destructivas a GET;
- borrar físicamente cuando basta soft delete.

---

# 25. Comandos frecuentes

```powershell
.\.venv\Scripts\Activate.ps1
python -m flask --app run --debug run
python -m flask --app run init-db
python -m flask --app run create-admin
python scripts/test_tmdb.py
python scripts/check_catalog.py
python scripts/generate_demo_users.py
python scripts/generate_demo_users.py --clean
python scripts/run_phase13_tests.py
git status
git log --oneline -10
```

---

# 26. Evolución por fases

| Fase | Resultado |
|---:|---|
| 1 | preparación Flask |
| 2 | 16 tablas SQLite |
| 3 | auth/roles |
| 4 | TMDB |
| 5 | catálogo + contenido |
| 6 | filtros |
| 7 | favoritos/vistos/progreso |
| 8 | admin usuarios |
| 9 | admin catálogo |
| 10 | perfil/stats |
| 11 | stats admin |
| 12 | rediseño global |
| 13 | testing final |

Últimos commits antes de Fase 13:

```text
5d4870c refactor: modernize and consolidate application design
7cc3c01 feat: add admin statistics and demo activity generator
436ca5c feat: add user profile and viewing statistics
5cbd5d2 feat: add admin media catalog management
```

---

# 27. Estado del proyecto

La parte técnica está terminada.

A partir de aquí:

```text
no nuevas features
solo correcciones críticas
documentación
defensa
empaquetado
```

Para entender **cómo se construyó cronológicamente**, consultar:

```text
documentation/GUIA_DESARROLLO.md
```

Para estudiar la exposición:

```text
documentation/GUIA_DEFENSA_NETFLIX_DEL_TEMU.md
```

---



---

# ANEXO — GALERÍA COMPLETA DE EVIDENCIAS

Este anexo referencia las **86 capturas reales** disponibles. Los enlaces funcionan si este Markdown está dentro de `documentation/`.

## Fase 1

![fase1_01_flask_funcionando.png](screenshots/fase1_01_flask_funcionando.png)

`screenshots/fase1_01_flask_funcionando.png`

## Fase 2

![fase2_01_validacion_schema.png](screenshots/fase2_01_validacion_schema.png)

`screenshots/fase2_01_validacion_schema.png`

![fase2_02_modelo_er.png](screenshots/fase2_02_modelo_er.png)

`screenshots/fase2_02_modelo_er.png`

## Fase 3

![fase3_01_login.png](screenshots/fase3_01_login.png)

`screenshots/fase3_01_login.png`

![fase3_02_cliente_autenticado.png](screenshots/fase3_02_cliente_autenticado.png)

`screenshots/fase3_02_cliente_autenticado.png`

![fase3_03_acceso_denegado.png](screenshots/fase3_03_acceso_denegado.png)

`screenshots/fase3_03_acceso_denegado.png`

![fase3_04_panel_admin.png](screenshots/fase3_04_panel_admin.png)

`screenshots/fase3_04_panel_admin.png`

## Fase 4

![fase4_01_conexion_tmdb.png](screenshots/fase4_01_conexion_tmdb.png)

`screenshots/fase4_01_conexion_tmdb.png`

![fase4_02_catalogo_importado.png](screenshots/fase4_02_catalogo_importado.png)

`screenshots/fase4_02_catalogo_importado.png`

## Fase 5

![fase5_01_catalogo_peliculas.png](screenshots/fase5_01_catalogo_peliculas.png)

`screenshots/fase5_01_catalogo_peliculas.png`

![fase5_02_catalogo_series.png](screenshots/fase5_02_catalogo_series.png)

`screenshots/fase5_02_catalogo_series.png`

![fase5_03_detalle_pelicula.png](screenshots/fase5_03_detalle_pelicula.png)

`screenshots/fase5_03_detalle_pelicula.png`

![fase5_04_detalle_serie.png](screenshots/fase5_04_detalle_serie.png)

`screenshots/fase5_04_detalle_serie.png`

![fase5_05_mature_desactivado.png](screenshots/fase5_05_mature_desactivado.png)

`screenshots/fase5_05_mature_desactivado.png`

![fase5_06_confirmacion_mature.png](screenshots/fase5_06_confirmacion_mature.png)

`screenshots/fase5_06_confirmacion_mature.png`

![fase5_07_mature_activado.png](screenshots/fase5_07_mature_activado.png)

`screenshots/fase5_07_mature_activado.png`

![fase5_08_explicito_bloqueado.png](screenshots/fase5_08_explicito_bloqueado.png)

`screenshots/fase5_08_explicito_bloqueado.png`

![fase5_08_explicito_bloqueado2.png](screenshots/fase5_08_explicito_bloqueado2.png)

`screenshots/fase5_08_explicito_bloqueado2.png`

## Fase 6

![fase6_01_busqueda_titulo.png](screenshots/fase6_01_busqueda_titulo.png)

`screenshots/fase6_01_busqueda_titulo.png`

![fase6_02_filtro_genero.png](screenshots/fase6_02_filtro_genero.png)

`screenshots/fase6_02_filtro_genero.png`

![fase6_03_busqueda_combinada.png](screenshots/fase6_03_busqueda_combinada.png)

`screenshots/fase6_03_busqueda_combinada.png`

![fase6_04_orden_popularidad.png](screenshots/fase6_04_orden_popularidad.png)

`screenshots/fase6_04_orden_popularidad.png`

![fase6_05_orden_recientes.png](screenshots/fase6_05_orden_recientes.png)

`screenshots/fase6_05_orden_recientes.png`

![fase6_06_sin_resultados.png](screenshots/fase6_06_sin_resultados.png)

`screenshots/fase6_06_sin_resultados.png`

## Fase 7

![fase7_01_favorito_ficha.png](screenshots/fase7_01_favorito_ficha.png)

`screenshots/fase7_01_favorito_ficha.png`

![fase7_02_lista_favoritos.png](screenshots/fase7_02_lista_favoritos.png)

`screenshots/fase7_02_lista_favoritos.png`

![fase7_03_pelicula_vista.png](screenshots/fase7_03_pelicula_vista.png)

`screenshots/fase7_03_pelicula_vista.png`

![fase7_04_lista_vistos.png](screenshots/fase7_04_lista_vistos.png)

`screenshots/fase7_04_lista_vistos.png`

![fase7_05_temporadas_serie.png](screenshots/fase7_05_temporadas_serie.png)

`screenshots/fase7_05_temporadas_serie.png`

![fase7_06_episodios_temporada.png](screenshots/fase7_06_episodios_temporada.png)

`screenshots/fase7_06_episodios_temporada.png`

![fase7_07_episodios_vistos.png](screenshots/fase7_07_episodios_vistos.png)

`screenshots/fase7_07_episodios_vistos.png`

![fase7_08_temporada_completada.png](screenshots/fase7_08_temporada_completada.png)

`screenshots/fase7_08_temporada_completada.png`

![fase7_09_progreso_serie.png](screenshots/fase7_09_progreso_serie.png)

`screenshots/fase7_09_progreso_serie.png`

![fase7_10_serie_completada.png](screenshots/fase7_10_serie_completada.png)

`screenshots/fase7_10_serie_completada.png`

![fase7_11_serie_en_vistos.png](screenshots/fase7_11_serie_en_vistos.png)

`screenshots/fase7_11_serie_en_vistos.png`

![fase7_12_con_mature_favoritos.png](screenshots/fase7_12_con_mature_favoritos.png)

`screenshots/fase7_12_con_mature_favoritos.png`

![fase7_12_sin_mature_favoritos.png](screenshots/fase7_12_sin_mature_favoritos.png)

`screenshots/fase7_12_sin_mature_favoritos.png`

![fase7_13_con_mature_vistos.png](screenshots/fase7_13_con_mature_vistos.png)

`screenshots/fase7_13_con_mature_vistos.png`

![fase7_13_sin_mature_vistos.png](screenshots/fase7_13_sin_mature_vistos.png)

`screenshots/fase7_13_sin_mature_vistos.png`

## Fase 8

![fase8_01_panel_admin.png](screenshots/fase8_01_panel_admin.png)

`screenshots/fase8_01_panel_admin.png`

![fase8_02_lista_usuarios.png](screenshots/fase8_02_lista_usuarios.png)

`screenshots/fase8_02_lista_usuarios.png`

![fase8_03_crear_cliente.png](screenshots/fase8_03_crear_cliente.png)

`screenshots/fase8_03_crear_cliente.png`

![fase8_04_cliente_editado.png](screenshots/fase8_04_cliente_editado.png)

`screenshots/fase8_04_cliente_editado.png`

![fase8_04__editar_cliente.png](screenshots/fase8_04__editar_cliente.png)

`screenshots/fase8_04__editar_cliente.png`

![fase8_05_cliente_inactivo_antes_de_morir.png](screenshots/fase8_05_cliente_inactivo_antes_de_morir.png)

`screenshots/fase8_05_cliente_inactivo_antes_de_morir.png`

![fase8_05_cliente_inactivo_ya_murio.png](screenshots/fase8_05_cliente_inactivo_ya_murio.png)

`screenshots/fase8_05_cliente_inactivo_ya_murio.png`

![fase8_05__cliente_inactivo.png](screenshots/fase8_05__cliente_inactivo.png)

`screenshots/fase8_05__cliente_inactivo.png`

## Fase 9

![fase9_01_listado_admin.png](screenshots/fase9_01_listado_admin.png)

`screenshots/fase9_01_listado_admin.png`

![fase9_02_filtros_catalogo.png](screenshots/fase9_02_filtros_catalogo.png)

`screenshots/fase9_02_filtros_catalogo.png`

![fase9_03_contenido_explicito.png](screenshots/fase9_03_contenido_explicito.png)

`screenshots/fase9_03_contenido_explicito.png`

![fase9_04_pelicula_manual.png](screenshots/fase9_04_pelicula_manual.png)

`screenshots/fase9_04_pelicula_manual.png`

![fase9_05_pelicula_manual_resultado.png](screenshots/fase9_05_pelicula_manual_resultado.png)

`screenshots/fase9_05_pelicula_manual_resultado.png`

![fase9_06_serie_manual.png](screenshots/fase9_06_serie_manual.png)

`screenshots/fase9_06_serie_manual.png`

![fase9_07_serie_manual_resultado.png](screenshots/fase9_07_serie_manual_resultado.png)

`screenshots/fase9_07_serie_manual_resultado.png`

![fase9_08_editar_contenido.png](screenshots/fase9_08_editar_contenido.png)

`screenshots/fase9_08_editar_contenido.png`

![fase9_09_eliminar_media.png](screenshots/fase9_09_eliminar_media.png)

`screenshots/fase9_09_eliminar_media.png`

![fase9_10_eliminar_media_resultado.png](screenshots/fase9_10_eliminar_media_resultado.png)

`screenshots/fase9_10_eliminar_media_resultado.png`

![fase9_10_eliminar_media_resultado2.png](screenshots/fase9_10_eliminar_media_resultado2.png)

`screenshots/fase9_10_eliminar_media_resultado2.png`

![fase9_11_restaurar_media_resultado.png](screenshots/fase9_11_restaurar_media_resultado.png)

`screenshots/fase9_11_restaurar_media_resultado.png`

![fase9_11__restaurar_media.png](screenshots/fase9_11__restaurar_media.png)

`screenshots/fase9_11__restaurar_media.png`

## Fase 10

![fase10_01_perfil_completo.png](screenshots/fase10_01_perfil_completo.png)

`screenshots/fase10_01_perfil_completo.png`

![fase10_02_estadisticas_usuario.png](screenshots/fase10_02_estadisticas_usuario.png)

`screenshots/fase10_02_estadisticas_usuario.png`

![fase10_03_resto_estadisticas.png](screenshots/fase10_03_resto_estadisticas.png)

`screenshots/fase10_03_resto_estadisticas.png`

![fase10_04_estadisticas_usuario_actual.png](screenshots/fase10_04_estadisticas_usuario_actual.png)

`screenshots/fase10_04_estadisticas_usuario_actual.png`

![fase10_05_resto_estadisticas_actual.png](screenshots/fase10_05_resto_estadisticas_actual.png)

`screenshots/fase10_05_resto_estadisticas_actual.png`

## Fase 11

![fase11_01_estadisticas_panel_administracion.png](screenshots/fase11_01_estadisticas_panel_administracion.png)

`screenshots/fase11_01_estadisticas_panel_administracion.png`

![fase11_02_vista_estadisticas.png](screenshots/fase11_02_vista_estadisticas.png)

`screenshots/fase11_02_vista_estadisticas.png`

![fase11_03_resto_vista_estadisticas.png](screenshots/fase11_03_resto_vista_estadisticas.png)

`screenshots/fase11_03_resto_vista_estadisticas.png`

![fase11_04_uso_de_filtros_en_tabla_de_actividad_individual.png](screenshots/fase11_04_uso_de_filtros_en_tabla_de_actividad_individual.png)

`screenshots/fase11_04_uso_de_filtros_en_tabla_de_actividad_individual.png`

![fase11_05_intento_acceder_admin_sin_permisos.png](screenshots/fase11_05_intento_acceder_admin_sin_permisos.png)

`screenshots/fase11_05_intento_acceder_admin_sin_permisos.png`

![fase11_06_vista_estadisticas_usuarios_demo.png](screenshots/fase11_06_vista_estadisticas_usuarios_demo.png)

`screenshots/fase11_06_vista_estadisticas_usuarios_demo.png`

![fase11_07_vista_estadisticas_usuarios_demo_tabla.png](screenshots/fase11_07_vista_estadisticas_usuarios_demo_tabla.png)

`screenshots/fase11_07_vista_estadisticas_usuarios_demo_tabla.png`

## Fase 12

![fase12_01_landing_publica.png](screenshots/fase12_01_landing_publica.png)

`screenshots/fase12_01_landing_publica.png`

![fase12_02_catalogo_peliculas.png](screenshots/fase12_02_catalogo_peliculas.png)

`screenshots/fase12_02_catalogo_peliculas.png`

![fase12_03_catalogo_series.png](screenshots/fase12_03_catalogo_series.png)

`screenshots/fase12_03_catalogo_series.png`

![fase12_04_favoritos.png](screenshots/fase12_04_favoritos.png)

`screenshots/fase12_04_favoritos.png`

![fase12_05_vistos.png](screenshots/fase12_05_vistos.png)

`screenshots/fase12_05_vistos.png`

![fase12_06_perfil.png](screenshots/fase12_06_perfil.png)

`screenshots/fase12_06_perfil.png`

![fase12_07_estadisticas.png](screenshots/fase12_07_estadisticas.png)

`screenshots/fase12_07_estadisticas.png`

![fase12_08_catalogo_admin.png](screenshots/fase12_08_catalogo_admin.png)

`screenshots/fase12_08_catalogo_admin.png`

![fase12_09_estadisticas_usuarios.png](screenshots/fase12_09_estadisticas_usuarios.png)

`screenshots/fase12_09_estadisticas_usuarios.png`

## Fase 13

![fase13_01_resultado_testing_consola.png](screenshots/fase13_01_resultado_testing_consola.png)

`screenshots/fase13_01_resultado_testing_consola.png`

![fase13_02_devtools.png](screenshots/fase13_02_devtools.png)

`screenshots/fase13_02_devtools.png`

![fase13_03_responsive_1.png](screenshots/fase13_03_responsive_1.png)

`screenshots/fase13_03_responsive_1.png`

![fase13_04_responsive_2.png](screenshots/fase13_04_responsive_2.png)

`screenshots/fase13_04_responsive_2.png`

![fase13_05_responsive_3.png](screenshots/fase13_05_responsive_3.png)

`screenshots/fase13_05_responsive_3.png`
