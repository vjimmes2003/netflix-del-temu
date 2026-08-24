# Fase 13 — Cierre técnico real

## Objetivo

Realizar la validación definitiva del proyecto, corregir regresiones detectadas durante la revisión visual y congelar el desarrollo antes de la entrega.

## Testing automático

Se creó:

```text
scripts/run_phase13_tests.py
```

La batería trabaja sobre una copia temporal de SQLite y no modifica la base real.

Resultado final:

```text
PASS: 29
FAIL: 0
SKIP: 0
```

Se validaron, entre otros:

- compilación Python;
- integridad SQLite;
- las 16 tablas;
- plantillas Jinja;
- assets CSS/JS;
- mapa de rutas;
- autenticación y logout;
- permisos cliente/admin;
- búsquedas y filtros;
- política mature/explicit;
- favoritos y vistos;
- progreso de series;
- perfil y estadísticas;
- CRUD administrativo;
- generador de 100 usuarios demo;
- integridad final de SQLite.

La prueba temporal de carga generó:

```text
100 usuarios demo
3.322 registros de películas
7.877 registros de episodios
```

## Revisión visual

También se comprobó manualmente:

- consola de Chrome DevTools;
- Chart.js;
- imágenes;
- navegación;
- formularios;
- responsive;
- ausencia de overflow horizontal.

Se probaron aproximadamente:

```text
956 px
690 px
304 px
```

## Corrección del favicon

DevTools detectó inicialmente:

```text
/favicon.ico → 404
```

Se añadió el favicon y su referencia en la plantilla base.

Tras recargar, la consola quedó limpia.

## Regresión encontrada en los fondos

Durante la revisión final se detectó que las fichas de películas y series ya no mostraban correctamente el fondo horizontal de TMDB.

La base de datos conservaba los datos:

```text
Total de contenidos: 4.313
Con backdrop_path: 4.215
Sin backdrop_path: 98
```

Por tanto, no había pérdida general de datos.

El problema estaba en la capa visual de la ficha: durante el rediseño se había dejado el fondo `.detail-backdrop` detrás del fondo global de la página mediante el stacking CSS.

Se corrigió el apilado conservando el diseño aprobado.

## Auditoría de contenidos sin fondo

Se creó temporalmente una comprobación contra TMDB para los 98 registros sin `backdrop_path`.

Resultado:

```text
Recuperados desde TMDB: 0
Sin tmdb_id: 2
TMDB sin backdrop: 96
Errores API: 0
```

Conclusión:

- 96 contenidos realmente no disponían de fondo en TMDB;
- 2 contenidos habían sido añadidos manualmente y no estaban vinculados a TMDB.

## Contenidos manuales

Los dos registros manuales identificados fueron:

```text
Empire of the Sun / Imperio del Sol — película
Gambito de dama / The Queen's Gambit — serie
```

La creación manual había permitido introducir el contenido sin enlazarlo a una entrada TMDB, por lo que podían quedar sin poster y/o backdrop.

La corrección final consiste en:

- asociar el `tmdb_id` oficial cuando no exista conflicto;
- obtener de TMDB el `poster_path`;
- obtener de TMDB el `backdrop_path`;
- conservar el registro local y sus relaciones;
- realizar backup de SQLite antes de escribir.

Esta corrección no requiere reimportar el catálogo completo.

## Regla final para contenido manual

El CRUD administrativo continúa permitiendo contenido manual porque forma parte del proyecto.

Si se desea que un contenido manual use imágenes de TMDB, deberá introducirse o sincronizarse explícitamente con un identificador TMDB válido.

Los contenidos sin backdrop real pueden seguir mostrando el diseño de fondo degradado de la aplicación.

## Evidencias de Fase 13

```text
fase13_01_resultado_testing_consola.png
fase13_02_devtools.png
fase13_03_responsive_1.png
fase13_04_responsive_2.png
fase13_05_responsive_3.png
```

## Validación antes del commit final

Ejecutar:

```powershell
python scripts/run_phase13_tests.py --skip-demo100
```

Abrir además:

```text
una ficha de película
una ficha de serie
Imperio del Sol
Gambito de dama
```

Comprobar:

```text
poster correcto
fondo correcto cuando TMDB disponga de él
sin errores rojos en DevTools
responsive correcto
```

## Cierre

Con esta fase quedan terminados:

```text
funcionalidades
diseño
datos
administración
estadísticas
testing
correcciones visuales
correcciones de contenido manual
```

A partir de este punto no deben añadirse nuevas funcionalidades salvo un error crítico.

Commit recomendado:

```text
fix: finalize media artwork and validation
```

**Estado: cierre técnico definitivo.**
