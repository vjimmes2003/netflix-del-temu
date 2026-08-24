# GUÍA DE DEFENSA — NETFLIX DEL TEMU

> Guía de estudio. El objetivo no es memorizar código, sino poder explicar con claridad qué hace cada capa, por qué se tomó cada decisión y qué ocurre cuando una persona usa la aplicación.

---

# 1. Presentación de 20 segundos

> Netflix del Temu es una aplicación web desarrollada con Python y Flask para gestionar un catálogo de películas y series. Los contenidos se importan desde TMDB y se almacenan en SQLite. Los clientes pueden guardar favoritos, registrar películas y episodios vistos, seguir series y consultar estadísticas. Existe además un rol administrador para gestionar usuarios, catálogo y estadísticas globales.

# 2. Presentación de 1 minuto

> El backend está dividido en blueprints de Flask: autenticación, catálogo, actividad, estadísticas y administración. La persistencia se realiza con SQLite mediante SQL directo parametrizado. Flask-Login controla sesiones y permisos. TMDB se encapsula en una clase propia y se usa para importar datos reales. El frontend emplea Jinja, Bootstrap, CSS propio y JavaScript; Chart.js representa estadísticas calculadas desde la actividad. La versión final se validó con 29 grupos de pruebas ejecutados sobre una copia temporal de SQLite, con 29 PASS, 0 FAIL y 0 SKIP.

---

# 3. Arquitectura

```text
Navegador
   │
   ▼
Flask
   ├── auth
   ├── catalog
   ├── activity
   ├── statistics
   └── admin
   │
   ▼
sqlite3 / SQLite

TMDB → TMDBClient → importador → SQLite
```

Frase clave:

> TMDB aporta catálogo; SQLite contiene el estado de la aplicación.

---

# 4. Qué es Flask

Framework web de Python.

Hace:

```text
recibir request
elegir ruta
validar usuario
consultar BD
preparar datos
renderizar Jinja
devolver response
```

# 5. Application Factory

`app/__init__.py` define:

```python
create_app()
```

Ventajas:

- configuración centralizada;
- testing sencillo;
- registro modular;
- no mezclar toda la app en `run.py`.

# 6. Blueprints

| Blueprint | Área |
|---|---|
| `auth` | login/registro/logout |
| `catalog` | catálogo |
| `activity` | favoritos/vistos |
| `statistics` | perfil/stats |
| `admin` | gestión |

`auth` tiene `/auth`.

`admin` tiene `/admin`.

# 7. Request y Response

Ejemplo:

```text
GET /catalog?type=movie&q=alien
→ catalog()
→ SQL
→ render_template()
→ HTML
```

# 8. GET vs POST

GET consulta.

POST cambia estado.

Ejemplos POST:

```text
login
registro
logout
favorito
visto
mature
crear/editar
suspender
ocultar
```

# 9. Flask-Login

Debes conocer:

```text
User(UserMixin)
current_user
login_user
logout_user
@login_required
user_loader
```

`current_user` representa a la persona autenticada en la petición.

# 10. Login

Flujo:

```text
identificador
→ SELECT usuario/email
→ check_password_hash
→ is_active
→ login_user
→ redirección por rol
```

# 11. Passwords

Se almacena `password_hash`, no la contraseña.

Funciones:

```text
generate_password_hash
check_password_hash
```

# 12. Permisos admin

`admin_required` comprueba backend.

Pregunta típica:

**¿Ocultar el botón Administración es suficiente?**

> No. La ruta también valida el rol y devuelve 403 si un cliente intenta acceder.

---

# 13. SQLite

Archivo:

```text
instance/netflix_del_temu.sqlite3
```

Se usa `sqlite3`, sin ORM.

Respuesta a “¿por qué SQLite?”:

> Porque ofrece una base relacional completa sin servidor independiente y encaja con el alcance académico y demostrable del proyecto.

# 14. `get_db()` y `g`

`app/db.py` guarda una conexión por contexto de petición.

Activa foreign keys.

Usa `sqlite3.Row` para acceder:

```python
row["username"]
```

# 15. Foreign Keys

```sql
PRAGMA foreign_keys = ON;
```

Evitan referencias inválidas.

# 16. Las 16 tablas

```text
1  users
2  media
3  seasons
4  episodes
5  genres
6  media_genres
7  countries
8  media_countries
9  tags
10 media_tags
11 favorites
12 movie_watches
13 episode_watches
14 media_ratings
15 season_ratings
16 episode_ratings
```

Agrúpalas mentalmente:

```text
usuarios
catálogo
relaciones
actividad
ratings
```

# 17. `users`

Ideas:

```text
role
password_hash
is_active
mature_content_enabled
mature_content_confirmed_at
```

`is_active = 0` suspende sin borrar.

# 18. `media`

Película y serie comparten tabla.

```text
media_type = movie / series
```

Además:

```text
tmdb_id
source
is_visible
content_level
certification
```

# 19. Series

```text
media
→ seasons
→ episodes
```

Relación 1:N.

# 20. N:M

Ejemplo:

```text
users ↔ favorites ↔ media
```

Un usuario tiene muchos favoritos y un contenido pertenece a favoritos de muchos usuarios.

También:

```text
media ↔ media_genres ↔ genres
```

# 21. Por qué no existe `series_watches`

Se guarda la unidad mínima real:

```text
episode_watches
```

El progreso se calcula.

Ventaja:

> No hay un porcentaje redundante que pueda quedar desactualizado.

# 22. SQL parametrizado

```python
db.execute(
    "SELECT * FROM users WHERE id = ?",
    (user_id,),
)
```

Respuesta:

> El valor se envía separado de la consulta; evita construir SQL concatenando directamente entrada del usuario.

# 23. JOIN

`JOIN` combina filas relacionadas.

`LEFT JOIN` permite conservar la fila principal aunque no exista actividad.

Muy usado en estadísticas.

# 24. Agregaciones

```text
COUNT
SUM
AVG
GROUP BY
HAVING
DISTINCT
COALESCE
CASE
```

`COALESCE` convierte NULL a un valor seguro, normalmente 0.

# 25. Paginación

```text
LIMIT + OFFSET
```

Ejemplo:

```text
page 3
30 elementos
offset 60
```

# 26. Búsqueda

Usa:

```text
LIKE
```

pero escapa:

```text
%
_
\
```

La entrada se limita y se pasa parametrizada.

---

# 27. Política de contenido

```text
general
mature
explicit
```

`general`: normal.

`mature`: +18 confirmado y toggle.

`explicit`: bloqueado a clientes siempre.

Pregunta clave:

**¿Es solo CSS?**

> No, las consultas SQL y las fichas aplican el filtro en backend.

# 28. Soft delete

Usuario:

```text
is_active = 0
```

Media:

```text
is_visible = 0
```

¿Por qué?

> Preserva relaciones e historial y permite restaurar.

# 29. TMDB

API externa.

`TMDBClient` encapsula:

```text
token
Session
headers
timeout
endpoints
```

TMDB no se consulta para cada página del catálogo: se importa a SQLite.

# 30. POO

Dos ejemplos claros:

```text
User
TMDBClient
```

`TMDBClient` combina estado y comportamiento de acceso a API.

# 31. Importador

```text
Discover
→ IDs
→ detalles
→ saneamiento
→ clasificación
→ UPSERT
→ relaciones
→ temporadas/episodios
```

UPSERT = insertar o actualizar sin duplicar.

---

# 32. Jinja

```jinja2
{{ dato }}
{% if ... %}
{% for ... %}
{{ url_for(...) }}
```

La plantilla `base.html` evita duplicar navbar, CSS y JS.

# 33. Herencia HTML

Las páginas extienden `base.html`.

Bloques:

```text
title
head
body_class
content
vendor_scripts
page_data
scripts
```

# 34. `url_for`

Genera URL desde endpoint.

Más mantenible que escribir rutas rígidas.

# 35. Mensajes flash

Backend:

```python
flash(...)
```

Frontend los muestra como alertas.

# 36. HTML y validación

HTML usa:

```text
required
type=email
minlength
labels
ARIA
```

Pero el backend vuelve a validar.

Pregunta:

**¿Por qué validar dos veces?**

> El HTML puede saltarse con una petición manual; la validación real debe existir en servidor.

---

# 37. CSS

Archivo final único:

```text
app/static/css/app.css
```

Razón de consolidación:

> Al final del proyecto se eliminó CSS legacy y se unificó el sistema visual.

Paleta:

```text
violeta
azul
cian
coral
ámbar
verde
```

# 38. Flexbox y Grid

Flexbox:

```text
filas
navbar
acciones
```

Grid:

```text
tarjetas
métricas
dashboard
```

Bootstrap añade su propio grid responsive.

# 39. Bootstrap

Versión:

```text
5.3.8
```

Aporta estructura/comportamiento.

`app.css` aporta la identidad.

# 40. Responsive

Probado aproximadamente a:

```text
956 px
690 px
304 px
```

Se comprobó menú compacto, filtros en columna y ausencia de overflow.

---

# 41. JavaScript

Archivo:

```text
app/static/js/app.js
```

Funciones:

```text
initMediaForm
initAutoSubmit
initCatalogShortcut
setupChartTheme
renderMonthlyChart
initUserCharts
initAdminCharts
```

No realiza las consultas de negocio.

# 42. Chart.js

Python/SQL calculan.

Jinja entrega datos.

Chart.js representa.

```text
window.statisticsData
window.adminStatisticsData
```

Gráficos:

```text
doughnut
bar
bar horizontal apilada
bar + line
```

---

# 43. Estadísticas usuario

No hay tabla de estadísticas.

Películas:

```text
movie_watches + media.runtime_minutes
```

Series:

```text
episode_watches + episodes.runtime_minutes
```

Series completadas se derivan comparando episodios.

# 44. Estadísticas admin

Métricas por cliente y globales.

Se usan joins y agregaciones.

La Fase 13 comprobó que `/admin/statistics` funcionara después de generar 100 usuarios demo en una BD temporal.

# 45. Datos demo

Final:

```text
100 usuarios por defecto
cantidad configurable
semilla reproducible
prefijo demo_
```

Limpieza solo de `demo_`.

---

# 46. Testing

Script:

```text
scripts/run_phase13_tests.py
```

Decisión importante:

> Hace backup temporal de SQLite antes de las pruebas destructivas.

Resultado:

```text
29 PASS
0 FAIL
0 SKIP
```

Incluye:

```text
Python
Jinja
SQLite
rutas
auth
permisos
filtros
SQLi/XSS básica
mature
favoritos
vistos
progreso
stats
CRUD
soft delete
100 demo
integridad final
```

# 47. Testing visual

Se revisó:

```text
DevTools
console
Chart.js
posters
responsive
overflow
```

El único 404 final era favicon; se corrigió y se repitió la comprobación.

---

# 48. Errores HTTP

```text
401 no autorizado
403 sin permiso
404 no encontrado
405 método no permitido
500 error interno
```

Diferencia:

> 401 = problema de autenticación; 403 = autenticado pero sin permiso.

# 49. Transacciones

Tras cambios:

```python
db.commit()
```

En error:

```python
db.rollback()
```

# 50. `IntegrityError`

Puede venir de:

```text
UNIQUE
FOREIGN KEY
CHECK
```

La app captura varios de estos casos.

# 51. `UNIQUE`

Ejemplos:

```text
username
email
favorito usuario/contenido
```

# 52. `CHECK`

Restringe valores válidos.

Ejemplos conceptuales:

```text
role
content_level
booleanos
rating
```

# 53. Índices

Se creó un índice orientado a filtros frecuentes de catálogo:

```text
media_type
is_visible
content_level
```

---

# 54. Seguridad: qué sí y qué no

Sí:

```text
password hash
SQL parametrizado
permisos backend
POST para acciones
foreign keys
validación servidor
filtro contenido backend
```

No afirmar que existe:

```text
auditoría profesional
pentesting
CSRF dedicado
WCAG certificada
servidor producción
```

Si preguntan por CSRF:

> No se añadió una extensión dedicada. Una mejora de producción sería incorporar tokens CSRF, por ejemplo con Flask-WTF.

# 55. Producción

No usar:

```text
flask --debug
```

como servidor final.

Para producción:

```text
WSGI
SECRET_KEY segura
DB de servidor si escala
logs
HTTPS
CSRF
```

# 56. SQLite si escala

Respuesta:

> Es apropiado para el proyecto académico. Para alta concurrencia migraría a PostgreSQL o MariaDB manteniendo el modelo relacional.

# 57. CDN

Bootstrap/Icons/Chart.js se cargan por CDN.

Pro:

```text
simplicidad
```

Contra:

```text
dependencia de red
```

Podrían servirse localmente.

# 58. Accesibilidad

Hay:

```text
lang=es
viewport
labels
aria
skip-link
focus
reduced-motion
```

No afirmar auditoría WCAG formal.

---

# 59. Guion de demo recomendado

```text
1 landing
2 login
3 películas
4 búsqueda/filtro
5 ficha
6 favorito/visto
7 serie/temporada
8 perfil
9 estadísticas
10 admin
11 usuarios
12 catálogo admin
13 estadísticas admin
14 resultado testing
```

# 60. Guion oral de 5 minutos

## Inicio

> “Es una aplicación web para organizar películas y series y registrar actividad de usuarios.”

## Arquitectura

> “Flask está dividido en blueprints y consulta SQLite con SQL directo parametrizado.”

## Cliente

> “El usuario filtra catálogo, guarda favoritos y registra películas y episodios vistos. El progreso de series se calcula desde episodios.”

## Seguridad

> “Uso Flask-Login, hashes de contraseña, roles y una política general/mature/explicit aplicada en backend.”

## Administración

> “El administrador gestiona cuentas y contenido mediante soft delete y consulta estadísticas globales.”

## Cierre

> “La versión final se validó con 29 grupos automáticos más pruebas visuales responsive y DevTools.”

---

# 61. Preguntas probables

## ¿Por qué Flask?

> Ligero, modular y suficiente para el alcance.

## ¿Por qué SQLite?

> Relacional, fácil de desplegar y suficiente para demostración.

## ¿Por qué SQL directo?

> Hace explícitas las consultas y no necesitaba la complejidad de un ORM.

## ¿Cómo evitas SQL injection?

> Placeholders `?` y valores separados.

## ¿Cómo calculas una serie completada?

> Episodios vistos frente a episodios visibles disponibles.

## ¿Dónde guardas las estadísticas?

> No se guardan; se calculan.

## ¿Qué pasa al suspender usuario?

> `is_active=0`; datos conservados.

## ¿Qué pasa al eliminar contenido?

> `is_visible=0`; puede restaurarse.

## ¿Cómo diferencias película y serie?

> `media.media_type`.

## ¿De dónde salen imágenes?

> Paths de TMDB convertidos a URL de imagen.

## ¿Qué es `current_user`?

> Usuario autenticado de Flask-Login.

## ¿Qué es Blueprint?

> Módulo de rutas y responsabilidades dentro de Flask.

---

# 62. Preguntas de BD

## PK

Identifica fila.

## FK

Referencia otra tabla.

## 1:N

Una serie tiene muchas temporadas.

## N:M

Muchos usuarios ↔ muchos favoritos.

## `GROUP BY`

Agrupa para calcular métricas.

## `COALESCE`

Sustituye `NULL`.

## `DISTINCT`

Evita dobles conteos.

---

# 63. Preguntas frontend

## Jinja vs HTML

Jinja inyecta datos y lógica de presentación.

## Bootstrap vs CSS

Bootstrap estructura; CSS propio diseña.

## JavaScript

Interfaz y gráficos, no SQL.

## Viewport

Permite responsive real.

---

# 64. Preguntas API

## ¿TMDB caído?

El catálogo importado sigue en SQLite; nuevas importaciones o imágenes externas pueden fallar.

## ¿Token en código?

No, `.env`.

## ¿Timeout?

Evita esperas indefinidas.

---

# 65. Cosas que NO debes decir

No:

```text
“Es un Netflix”
```

Sí:

```text
“Es un gestor de catálogo y seguimiento audiovisual.”
```

No:

```text
“TMDB es la base de datos”
```

Sí:

```text
“TMDB es una fuente externa; SQLite es la persistencia.”
```

No:

```text
“Bootstrap hace toda la web”
```

No:

```text
“Se guarda el porcentaje de series”
```

No:

```text
“Los usuarios se borran”
```

No:

```text
“Explicit se activa con mature”
```

---

# 66. Limitaciones honestas

```text
no streaming
no CSRF dedicado
SQLite para alcance académico
CDN frontend
ratings modelados pero no centrales en UI
sin auditoría formal WCAG
sin pentesting profesional
servidor debug solo desarrollo
```

Presentarlas como mejoras futuras, no como errores ocultos.

# 67. Mejoras futuras

```text
PostgreSQL/MariaDB
CSRF
pytest/CI
Docker
recomendaciones
ratings UI
proveedores streaming
recuperación contraseña
correo real
logs
assets offline
```

---

# 68. Chuleta de rutas

```text
/                         landing
/auth/login               login
/auth/register            registro
/auth/logout              logout POST

/catalog                   catálogo
/catalog/<id>              ficha
/catalog/<id>/season/<id>  temporada
/settings/content          mature

/favorites
/watched
/profile
/statistics

/admin/
/admin/users
/admin/catalog
/admin/statistics
```

# 69. Chuleta de archivos

```text
__init__.py       aplicación
db.py             SQLite
auth.py           auth
catalog.py        catálogo
activity.py       favoritos/vistos
statistics.py     perfil/stats
admin.py          admin
content_policy.py clasificación
tmdb_client.py    API

base.html         estructura común
app.css           diseño
app.js            JS/gráficos
schema.sql        modelo

import_tmdb.py
generate_demo_users.py
run_phase13_tests.py
```

# 70. Checklist de estudio

Debes poder explicar:

```text
Flask
Blueprint
request/response
GET/POST
Flask-Login
hash
SQLite
16 tablas
FK
N:M
SQL parametrizado
JOIN
soft delete
progreso
mature/explicit
TMDB
Jinja
Bootstrap
CSS
JS
Chart.js
testing
```

# 71. Resumen de memoria

```text
Backend: Python + Flask
DB: SQLite + SQL directo
Auth: Flask-Login + hashes
API: TMDB
Frontend: Jinja + Bootstrap + CSS
Charts: Chart.js

Roles: client/admin
Contenido: general/mature/explicit
Soft delete: is_active/is_visible

Actividad:
favorites
movie_watches
episode_watches

Series:
media → seasons → episodes

Stats:
se calculan, no se almacenan

Testing:
29 PASS / 0 FAIL / 0 SKIP
```

# 72. Frase final

> “El proyecto une un modelo relacional con integridad, autenticación y roles, integración con una API externa, actividad persistente por usuario, estadísticas calculadas y una administración completa; además, la versión final se comprobó con testing automático y revisión visual.”
