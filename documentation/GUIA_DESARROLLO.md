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

## Evidencias
Directorio: `documentation/screenshots/`

```text
fase5_01_catalogo_peliculas.png
fase5_02_catalogo_series.png
fase5_03_detalle_pelicula.png
fase5_04_detalle_serie.png
fase5_05_mature_desactivado.png
fase5_06_confirmacion_mature.png
fase5_07_mature_activado.png
fase5_08_explicito_bloqueado.png
fase5_08_explicito_bloqueado2.png
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

## Evidencias
Directorio: `documentation/screenshots/`

```text
fase6_01_busqueda_titulo.png
fase6_02_filtro_genero.png
fase6_03_busqueda_combinada.png
fase6_04_orden_popularidad.png
fase6_05_orden_recientes.png
fase6_06_sin_resultados.png
```

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
Directorio: `documentation/screenshots/`

```text
fase7_01_favorito_ficha.png
fase7_02_lista_favoritos.png
fase7_03_pelicula_vista.png
fase7_04_lista_vistos.png
fase7_05_temporadas_serie.png
fase7_06_episodios_temporada.png
fase7_07_episodios_vistos.png
fase7_08_temporada_completada.png
fase7_09_progreso_serie.png
fase7_10_serie_completada.png
fase7_11_serie_en_vistos.png
fase7_12_con_mature_favoritos.png
fase7_12_sin_mature_favoritos.png
fase7_13_con_mature_vistos.png
fase7_13_sin_mature_vistos.png
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
Directorio: `documentation/screenshots/`

```text
fase8_01_panel_admin.png
fase8_02_lista_usuarios.png
fase8_03_crear_cliente.png
fase8_04_cliente_editado.png
fase8_04__editar_cliente.png
fase8_05_cliente_inactivo_antes_de_morir.png
fase8_05_cliente_inactivo_ya_murio.png
fase8_05__cliente_inactivo.png
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

# Fase 9 — Administración del catálogo

## Objetivo
Implementar el CRUD administrativo de películas y series.

## Implementación
Se habilitó `/admin/catalog` con contadores, búsqueda, paginación y filtros por tipo, estado, origen y clasificación.

Clasificaciones disponibles:
```text
general
mature
explicit
```

## Creación manual
Desde `/admin/catalog/create` se pueden crear películas y series.

Campos principales:
- título y título original;
- sinopsis, fecha e idioma;
- portada y fondo;
- certificación y nivel de contenido;
- géneros/categorías.

Las películas requieren duración.

Las series pueden generar estructura inicial indicando temporadas, episodios por temporada y duración de episodio.
La estructura queda integrada con el seguimiento de la Fase 7.

## Edición
Se pueden editar contenidos manuales o importados desde TMDB.

En contenido TMDB se conservan `tmdb_id` y origen.
El tipo película/serie queda bloqueado después de crear para proteger temporadas, episodios y actividad.

## Eliminación lógica
Eliminar usa `is_visible = 0`.
El contenido deja de mostrarse al cliente y su acceso directo devuelve 404.

Restaurar usa `is_visible = 1`.
Así se conservan temporadas, relaciones, favoritos y progreso.

## Política de contenido
El administrador puede gestionar `general`, `mature` y `explicit`.
Para clientes, `explicit` sigue bloqueado y `mature` depende de su preferencia.

## Archivos principales
```text
app/admin.py
app/templates/admin/dashboard.html
app/templates/admin/media_list.html
app/templates/admin/media_form.html
app/static/css/admin_catalog.css
```

## Evidencias
```text
documentation/screenshots/fase9_01_listado_admin.png
documentation/screenshots/fase9_02_filtros_catalogo.png
documentation/screenshots/fase9_03_contenido_explicito.png
documentation/screenshots/fase9_04_pelicula_manual.png
documentation/screenshots/fase9_05_pelicula_manual_resultado.png
documentation/screenshots/fase9_06_serie_manual.png
documentation/screenshots/fase9_07_serie_manual_resultado.png
documentation/screenshots/fase9_08_editar_contenido.png
documentation/screenshots/fase9_09_eliminar_media.png
documentation/screenshots/fase9_10_eliminar_media_resultado.png
documentation/screenshots/fase9_10_eliminar_media_resultado2.png
documentation/screenshots/fase9_11__restaurar_media.png
documentation/screenshots/fase9_11_restaurar_media_resultado.png
```

## Validación
- listado, búsqueda, filtros y paginación correctos;
- filtro general/mature/explicit correcto;
- creación de películas y series manuales;
- creación de temporadas/episodios correcta;
- edición TMDB conserva identificadores;
- eliminación lógica oculta al cliente;
- acceso eliminado devuelve 404;
- restauración recupera el contenido;
- rutas restringidas al administrador.

## Commit
```text
feat: add admin media catalog management
```

**Estado: completada.**

---

# Fase 10 — Perfil y estadísticas del usuario

## Objetivo
Añadir un perfil personal y estadísticas calculadas desde la actividad real del cliente.

## Perfil
Se creó `/profile`.

`Perfil` aparece únicamente en la navegación global y no como pestaña interna del catálogo.

Muestra identidad del usuario, tiempo total, películas vistas, series empezadas, episodios vistos, series completadas, favoritos y accesos a estadísticas, historial y preferencias.

## Estadísticas
Se creó `/statistics`.

El resumen calcula mediante SQL:
- tiempo total y reparto películas/series;
- películas vistas;
- series empezadas y completadas;
- episodios vistos;
- favoritos;
- géneros principales;
- actividad mensual.

No existe una tabla de estadísticas: se consultan las tablas de actividad y catálogo directamente.

## Visualización
Chart.js representa el reparto de tiempo, los géneros más vistos y la actividad mensual.

La interfaz utiliza una paleta reducida:
```text
azul noche
violeta
azul
```

Blanco y grises se reservan como neutros.

El resumen es permanente y se actualiza con cada cambio en la actividad registrada.

## Cálculos
Las películas usan `media.runtime_minutes`.

Las series suman `episodes.runtime_minutes` de episodios vistos.

Un registro sin duración aporta 0 minutos.

Una serie se considera completada cuando están vistos todos los episodios disponibles localmente.

## Diseño pendiente
La versión actual queda funcional y responsive.

El aprovechamiento de pantallas 16:9, anchos, Flexbox/Grid y el pulido responsive global se revisarán en la Fase 12 de diseño y UX.

## Archivos principales
```text
app/__init__.py
app/statistics.py
app/templates/base.html
app/templates/profile.html
app/templates/statistics.html
app/templates/catalog.html
app/templates/favorites.html
app/templates/watched.html
app/static/css/shell.css
app/static/css/profile.css
app/static/css/statistics.css
app/static/js/statistics.js
```

## Evidencias
```text
documentation/screenshots/fase10_01_perfil_completo.png
documentation/screenshots/fase10_02_estadisticas_usuario.png
documentation/screenshots/fase10_03_resto_estadisticas.png
documentation/screenshots/fase10_04_estadisticas_usuario_actual.png
documentation/screenshots/fase10_05_resto_estadisticas_actual.png
```

## Validación
- perfil independiente por usuario;
- estadísticas obtenidas desde SQLite;
- tiempos, contadores y series completadas correctos;
- géneros y actividad mensual representados;
- actualización al modificar historial;
- comprobación con cuentas de distinto volumen;
- navegación Perfil → Estadísticas correcta;
- Perfil eliminado de las pestañas del catálogo;
- acceso protegido por autenticación.

## Commit
```text
feat: add user profile and viewing statistics
```

**Estado: completada.**

---

# Fase 11 — Estadísticas administrativas

## Objetivo
Permitir al administrador consultar y comparar la actividad de los clientes mediante métricas, gráficas y tablas.

## Acceso
Se añadió `/admin/statistics`, integrado en `/admin/` junto a Usuarios y Catálogo.

La ruta está protegida para administradores.

## Resumen global
La vista calcula mediante SQL:
- clientes totales y con actividad;
- registros de películas y episodios;
- tiempo total registrado;
- cliente con mayor tiempo de reproducción.

## Comparación
Chart.js muestra:
- tiempo por cliente, separado entre películas y series;
- actividad global agrupada por mes.

La tabla individual incluye estado, películas, series empezadas, episodios, favoritos, registros y tiempo total.

Puede buscarse por usuario, nombre o correo, filtrar por estado y ordenar por tiempo, registros, favoritos o nombre.

## Datos de demostración
Se añadió:
```text
scripts/generate_demo_users.py
```

El script genera 10 clientes de prueba con perfiles de uso diferentes y actividad distribuida durante los últimos seis meses.

Utiliza una semilla fija para obtener datos reproducibles y emplea contenidos reales ya almacenados en SQLite.

Ejecución:
```powershell
python scripts/generate_demo_users.py
```

Limpieza:
```powershell
python scripts/generate_demo_users.py --clean
```

Solo elimina cuentas cuyo usuario empieza por `demo_` y sus relaciones de actividad.

No modifica el catálogo ni los usuarios reales.

## Base de datos
No se añadieron tablas nuevas.

Las estadísticas se obtienen dinámicamente desde `users`, `movie_watches`, `episode_watches`, `favorites`, `media`, `seasons` y `episodes`.

## Archivos principales
```text
app/admin.py
app/templates/admin/dashboard.html
app/templates/admin/statistics.html
app/static/css/admin_statistics.css
app/static/js/admin_statistics.js
scripts/generate_demo_users.py
```

## Evidencias
```text
documentation/screenshots/fase11_01_estadisticas_panel_administracion.png
documentation/screenshots/fase11_02_vista_estadisticas.png
documentation/screenshots/fase11_03_resto_vista_estadisticas.png
documentation/screenshots/fase11_04_uso_de_filtros_en_tabla_de_actividad_individual.png
documentation/screenshots/fase11_05_intento_acceder_admin_sin_permisos.png
documentation/screenshots/fase11_06_vista_estadisticas_usuarios_demo.png
documentation/screenshots/fase11_07_vista_estadisticas_usuarios_demo_tabla.png
```

## Validación
- métricas globales calculadas desde SQLite;
- comparación entre clientes operativa;
- actividad mensual representada;
- búsqueda, filtros y ordenación correctos;
- clientes activos e inactivos diferenciados;
- acceso de cliente normal bloqueado;
- generación demo reproducible;
- limpieza limitada a cuentas `demo_`;
- estadísticas actualizadas al generar o limpiar datos.

## Commit
```text
feat: add admin statistics and demo activity generator
```

**Estado: completada.**

---


# Fase 12 — Rediseño global y UX
## Objetivo
Modernizar toda la interfaz, aprovechar mejor pantallas de escritorio y unificar el frontend sin alterar la funcionalidad existente.

## Implementación
Se rehízo la capa visual con Bootstrap 5.3.8, Bootstrap Icons y componentes propios.

Paleta semántica:
```text
violeta → marca/películas
azul    → series
cian    → actividad/estadísticas
coral   → favoritos
ámbar   → rating/mature
verde   → completado/correcto
```

Grid y Flexbox organizan los layouts de escritorio y Bootstrap junto a media queries propias mantiene el comportamiento responsive.
La navegación global quedó en Películas, Series, Perfil, Administración y Usuario. `Perfil` aparece una sola vez; las pestañas del catálogo son Películas, Series, Favoritos y Vistos.

## Catálogo y biblioteca
Se rediseñaron catálogo, fichas, temporadas, Favoritos y Vistos con:
- hero destacado;
- tarjetas con poster, rating, tipo y clasificación;
- filtros compactos y conservación durante la paginación;
- selector de 10, 30, 50 o 100 resultados;
- badges `mature` cuando corresponde.

## Perfil y estadísticas
El perfil aprovecha mejor el ancho de escritorio y presenta sus métricas mediante tarjetas.
Chart.js mantiene los cálculos existentes y mejora distribución, colores, responsive, accesibilidad de los `canvas` y animaciones compatibles con `prefers-reduced-motion`.

## Administración
La administración conserva la identidad visual, pero usa mayor densidad de información.
El catálogo administrativo utiliza una tabla compacta, los formularios se uniformaron y las estadísticas recibieron márgenes, colores semánticos y una presentación más clara.

## Datos demo
`scripts/generate_demo_users.py` genera 100 clientes demo por defecto, con perfiles variados y actividad reproducible durante seis meses.
```powershell
python scripts/generate_demo_users.py
python scripts/generate_demo_users.py --count 50
python scripts/generate_demo_users.py --clean
```
Admite entre 1 y 500 usuarios. La limpieza solo afecta a cuentas `demo_`.

## Simplificación
Se retiraron los CSS/JS específicos acumulados en fases anteriores.

Frontend final:
```text
app/static/css/app.css
app/static/js/app.js
```

Snapshot final:
```text
40 archivos
16.868 líneas aprox.
19 Python · 19 HTML · 1 CSS · 1 JavaScript
```

## Evidencias
```text
documentation/screenshots/fase12_01_landing_publica.png
documentation/screenshots/fase12_02_catalogo_peliculas.png
documentation/screenshots/fase12_03_catalogo_series.png
documentation/screenshots/fase12_04_favoritos.png
documentation/screenshots/fase12_05_vistos.png
documentation/screenshots/fase12_06_perfil.png
documentation/screenshots/fase12_07_estadisticas.png
documentation/screenshots/fase12_08_catalogo_admin.png
documentation/screenshots/fase12_09_estadisticas_usuarios.png
```

No se añadió captura responsive específica; el comportamiento adaptativo se apoya en Bootstrap y reglas globales y volverá a comprobarse en las pruebas finales.

## Validación
- diseño coherente en cliente y administración;
- selector 10/30/50/100 operativo;
- navegación sin duplicados;
- Favoritos/Vistos conservan clasificación y actividad;
- perfil, estadísticas, CRUD, filtros y permisos sin regresiones;
- Chart.js responsive;
- assets legacy eliminados;
- frontend consolidado en un CSS y un JS.

## Commit
```text
refactor: modernize and consolidate application design
```
**Estado: completada.**

---



# Fase 13 — Pruebas finales
## Objetivo
Validar de forma reproducible toda la aplicación antes de congelar el desarrollo y pasar a la documentación de entrega y defensa.

## Batería automática
Se añadió:
```text
scripts/run_phase13_tests.py
```

El script trabaja sobre una copia temporal de `instance/netflix_del_temu.sqlite3`, por lo que las pruebas no modifican la base real.

Ejecución:
```powershell
python scripts/run_phase13_tests.py
```

Se comprobaron 29 grupos:
- compilación Python, Jinja y assets;
- integridad SQLite y 16 tablas;
- mapa de rutas, autenticación y errores;
- registro, duplicados, login, suspensión y logout;
- permisos cliente/administrador;
- catálogo, búsqueda, ordenación y paginación 10/30/50/100;
- entradas SQL/XSS básicas y valores inválidos;
- películas, series, temporadas y episodios;
- política `general/mature/explicit`;
- favoritos, vistos y progreso;
- perfil y estadísticas;
- CRUD de usuarios y catálogo;
- creación manual, soft delete y restauración;
- filtros/estadísticas administrativas;
- generador de 100 usuarios demo;
- integridad SQLite final.

## Resultado
```text
PASS: 29
FAIL: 0
SKIP: 0

100 usuarios demo
3.322 registros de películas
7.877 registros de episodios
```

`/admin/statistics` respondió correctamente con la carga demo y SQLite mantuvo integridad `ok`.

Informe:
```text
documentation/sources/FASE13_TEST_RESULTS.txt
```

## Revisión visual
Con Chrome DevTools se verificó:
- Chart.js renderizado;
- consola sin errores JavaScript;
- posters y fondos cargados;
- navegación y controles operativos;
- ausencia de overflow horizontal;
- adaptación responsive.

El catálogo se revisó aproximadamente a 956 px, 690 px y 304 px. La navegación pasa a menú compacto y los filtros/tarjetas se reorganizan correctamente.

## Favicon
DevTools detectó inicialmente un único `404` de `/favicon.ico`. Se añadió el favicon a los assets estáticos y su referencia en `base.html`; tras recargar, la consola quedó limpia.

## Evidencias
```text
documentation/screenshots/fase13_01_resultado_testing_consola.png
documentation/screenshots/fase13_02_devtools.png
documentation/screenshots/fase13_03_responsive_1.png
documentation/screenshots/fase13_04_responsive_2.png
documentation/screenshots/fase13_05_responsive_3.png
```

## Validación final
- 29/29 grupos superados;
- cero fallos y cero omisiones;
- base real protegida;
- integridad SQLite correcta antes y después;
- permisos, contenido, CRUD y actividad operativos;
- estadísticas válidas con carga elevada;
- consola limpia;
- responsive comprobado.

## Cierre técnico
Con esta fase quedan terminadas las funcionalidades y pruebas. A partir de aquí solo se realizarán correcciones críticas; el trabajo restante es documentación, guía completa del proyecto y preparación de la defensa.

## Commit
```text
test: add final automated and responsive validation
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
