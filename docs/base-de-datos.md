# Base de datos

[Volver al README](../README.md)

Los resultados se guardan en SQLite, en `output/scraper.db` (junto al `.exe` si
se usa el ejecutable). `schema.sql` define las tablas y `database.py` lo
ejecuta cada vez que abre la base de datos, así que los dos siempre coinciden.
La versión del esquema se guarda en `PRAGMA user_version` (actualmente 1).

Se puede abrir con cualquier cliente de SQLite (por ejemplo, DB Browser for
SQLite) o con el módulo `database.py` (ver [Uso desde código](consola.md#uso-desde-código)).

## Tablas

### productos

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER | Clave primaria |
| `titulo` | TEXT | Título del producto (`N/A` si no se encontró) |
| `precio` | REAL | Importe numérico; `NULL` si no se pudo interpretar |
| `moneda` | TEXT | `EUR`, `USD`, `GBP` o `JPY`; `NULL` si no aparece |
| `precio_texto` | TEXT | Texto original del precio tal como venía en la página |
| `descripcion` | TEXT | Descripción corta (en la extracción genérica, el primer párrafo hasta 100 caracteres) |
| `enlace` | TEXT | URL del producto; único. `NULL` si no tiene |
| `imagen` | TEXT | URL de la imagen |
| `sitio` | TEXT | Dominio desde el que se scrapeó (`books_toscrape_com`) o nombre de la tarea programada |
| `categoria` | TEXT | No la rellena el scraper; se conserva si se escribe a mano |
| `fecha_scraping` | TIMESTAMP | Última vez que se vio el producto (UTC) |

Un producto con enlace se identifica por su enlace; sin enlace, por título y
sitio. Al volver a scrapearlo se actualiza la fila existente (título, precio,
descripción, imagen, sitio y fecha) en lugar de crear otra. Los campos vacíos o
`N/A` se guardan como `NULL`.

Índices: `sitio` y `fecha_scraping`.

### historial_precios

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER | Clave primaria |
| `producto_id` | INTEGER | Producto (`productos.id`) |
| `precio`, `moneda`, `precio_texto` | | Como en `productos` |
| `fecha` | TIMESTAMP | Momento del registro (UTC) |

Se añade una fila cada vez que se guarda un producto con un precio que se ha
podido interpretar. Al borrar un producto se borra su historial
(`ON DELETE CASCADE`; `database.py` activa las claves foráneas, otros clientes
de SQLite pueden no hacerlo). Índice: `producto_id, fecha`.

### scraping_jobs

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER | Clave primaria |
| `url` | TEXT | URL scrapeada |
| `sitio` | TEXT | Como en `productos` |
| `total_items` | INTEGER | Elementos encontrados |
| `estado` | TEXT | `completado`, `sin_datos`, `error` o `cancelado` |
| `fecha` | TIMESTAMP | Momento del registro (UTC) |
| `duracion_segundos` | REAL | Duración de la ejecución |

Se registra cada ejecución de scraping del menú de consola, la interfaz web y
el programador de tareas (el comparador no registra nada).

## Borrar datos antiguos

La opción 7 del menú borra los productos cuya `fecha_scraping` tiene más de N
días, es decir, los que no se han vuelto a ver en ese tiempo, junto con su
historial.

## Migración desde versiones anteriores

Las versiones anteriores del proyecto guardaban el precio como texto, sin
moneda. Al abrir una de esas bases de datos se migra automáticamente:

- se conservan los ids y las fechas;
- se interpreta cada precio (ver [Precios](precios.md)) y el texto original se
  guarda en `precio_texto`;
- los enlaces, descripciones e imágenes `N/A` pasan a `NULL`;
- se descartan los registros de historial de productos que ya no existían.

Todo se hace en una sola transacción: si algo falla, la base de datos queda
como estaba. Aun así, conviene copiar `output/scraper.db` antes de actualizar.
La migración solo se hace una vez.
