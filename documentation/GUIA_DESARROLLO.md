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

# Fase 6 — Búsqueda, filtros y ordenación

## Objetivo
Facilitar la localización de películas y series dentro de un catálogo más amplio.

## Preparación del catálogo
Antes de probar la búsqueda se amplió la importación desde TMDB.

```text
1.000 películas solicitadas
500 series solicitadas

1.376 contenidos revisados
1.200 general
167 mature
9 explicit
1 título actualizado
0 errores
```

La ampliación permite probar los filtros sobre un catálogo más representativo.

## Implementación
Se añadieron:
- búsqueda por título y título original;
- filtro por género;
- combinación de búsqueda y género;
- conservación de filtros durante la paginación;
- conservación al cambiar entre películas y series;
- compatibilidad con el slider `mature`;
- botón para limpiar filtros;
- estado específico sin resultados.

Archivos:
```text
app/catalog.py
app/templates/catalog.html
app/static/css/search_filters.css
```

## Seguridad
Los valores del usuario se envían a SQLite mediante parámetros.

La búsqueda usa `LIKE` escapando `%`, `_` y `\`.

El control de contenido sigue aplicándose:
```text
general  → permitido
mature   → depende del usuario
explicit → bloqueado
```

## Ordenación
Opciones disponibles:
```text
Más populares
Más recientes estrenadas
Más antiguas
Mejor valoradas
```

**Más populares** es la opción predeterminada.

En **Más recientes estrenadas**, las obras ya publicadas aparecen primero. Los próximos estrenos quedan después y los contenidos sin fecha al final.

## Navegación
Los filtros se almacenan como parámetros GET:
```text
/catalog?type=movie&q=alien&genre=18&sort=popularity
```

Esto permite mantener búsqueda, género, orden y tipo durante la navegación.

## Validación
- búsqueda parcial por título correcta;
- búsqueda por título original correcta;
- filtro por género correcto;
- título + género funcionan conjuntamente;
- paginación conserva parámetros;
- películas/series conservan los filtros;
- popularidad es el orden por defecto;
- ordenaciones alternativas correctas;
- limpiar restaura el catálogo base;
- el slider `mature` conserva los filtros;
- `explicit` continúa bloqueado;
- búsquedas vacías muestran un estado específico.

El estilo definitivo se revisará en la fase general de diseño y UX.

## Commit
```text
feat: add catalog and filtering
```

**Estado: completada.**

---

# Fase 7 — Favoritos, vistos y seguimiento de series

## Objetivo
Permitir que cada usuario organice contenido y registre su progreso de visualización.

## Implementación
Se añadió `app/activity.py` para gestionar favoritos, películas vistas, episodios vistos y temporadas completas.
Las operaciones usan SQL directo y quedan asociadas al usuario autenticado.

## Favoritos y vistos
Rutas personales:
```text
/favorites
/watched
```
Tablas utilizadas:
```text
favorites
movie_watches
episode_watches
```
`/favorites` muestra películas y series guardadas.
`/watched` muestra películas vistas y series con episodios registrados.

## Seguimiento de series
La ficha de una serie permite acceder a temporadas y episodios.
Cada episodio puede marcarse o desmarcarse como visto.
También se añadió `Marcar temporada como vista` y `Desmarcar temporada`.
La acción afecta únicamente a episodios disponibles en SQLite.
Las temporadas sin episodios importados muestran un estado vacío sin generar actividad.

## Progreso
El progreso se calcula dinámicamente mediante SQL, sin una tabla específica.
Se muestran episodios vistos, episodios disponibles y porcentaje.
La ficha de serie incorpora `RETO DE SERIE`.
Al alcanzar el 100 % cambia a `✓ Serie completada`.
Las temporadas al 100 % también muestran un estado visual de completadas.

## Control de contenido
Favoritos y Vistos mantienen la política:
```text
general  → visible
mature   → depende del usuario
explicit → bloqueado
```
El slider `mature` está disponible en ambas páginas.
Desactivarlo oculta registros maduros, pero no los elimina.

## Archivos principales
```text
app/activity.py
app/catalog.py
app/__init__.py
app/templates/media_detail.html
app/templates/season_detail.html
app/templates/favorites.html
app/templates/watched.html
app/static/css/activity.css
```

## Evidencias
Se guardaron capturas de:
- favorito desde ficha y lista de favoritos;
- película vista y lista de vistos;
- temporadas y episodios;
- episodios y temporada completados;
- progreso global y serie al 100 %;
- serie dentro de Vistos;
- control `mature` en Favoritos y Vistos.

Rango de evidencias:
```text
documentation/screenshots/fase7_01_*.png
...
documentation/screenshots/fase7_13_*.png
```

## Validación
- favoritos e historial independientes por usuario;
- persistencia después de recargar y volver a iniciar sesión;
- temporadas completas y progreso correctos;
- serie completada al 100 %;
- listas protegidas por autenticación;
- `mature` operativo sin borrar datos;
- `explicit` continúa bloqueado;
- temporadas sin episodios no producen errores.

## Commit
```text
feat: add favorites watched tracking and series progress
```

**Estado: completada.**

---

# Fase 8 — Administración de usuarios

## Objetivo
Implementar la gestión de cuentas de cliente desde el área administrativa.

## Implementación
Se amplió `/admin/` con contadores de clientes, películas y series.

La ruta `/admin/users` muestra usuario, correo, país, rol, estado y fecha de alta.

El administrador puede:
```text
Crear cliente
Editar cliente
Desactivar cliente
Reactivar cliente
```

Las cuentas `admin` aparecen protegidas y no pueden modificarse desde este CRUD.

## Creación y edición
La creación permite definir usuario, correo, nombre visible, país y contraseña.

Las cuentas nuevas reciben:
```text
role = client
is_active = 1
```

En edición la contraseña es opcional; si queda vacía se mantiene la existente.

Se validan correo, longitud mínima de contraseña y duplicados de usuario/correo.

## Suspensión de cuentas
No se utiliza `DELETE` sobre usuarios.

La desactivación usa `is_active = 0` y la reactivación `is_active = 1`.

Así se conservan favoritos, historial y progreso.

## Login de usuario suspendido
Una cuenta suspendida no puede iniciar sesión.

Con credenciales correctas se informa de la suspensión y se muestra:
```text
soporte@netflixdeltemu.test
```

El correo puede configurarse mediante `SUPPORT_EMAIL`.

Si la contraseña es incorrecta se mantiene el mensaje genérico de credenciales para no revelar el estado de la cuenta.

## Archivos principales
```text
app/admin.py
app/auth.py
app/templates/admin/dashboard.html
app/templates/admin/users.html
app/templates/admin/user_form.html
app/static/css/admin_users.css
```

## Evidencias
```text
documentation/screenshots/fase8_01_panel_admin.png
documentation/screenshots/fase8_02_lista_usuarios.png
documentation/screenshots/fase8_03_crear_cliente.png
documentation/screenshots/fase8_04_editar_cliente.png
documentation/screenshots/fase8_05_cliente_inactivo.png
documentation/screenshots/fase8_06_login_usuario_baneado.png
```

## Validación
- acceso restringido a administradores;
- creación y edición correctas;
- administradores protegidos;
- desactivación/reactivación funcional;
- datos conservados tras suspender;
- login bloqueado al usuario suspendido;
- aviso de soporte solo con contraseña correcta;
- login restaurado tras reactivar.

## Commit
```text
feat: add admin user management and account suspension
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
