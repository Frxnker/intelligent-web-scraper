# API

La interfaz web se apoya en una API JSON que también se puede usar
directamente mientras `python servidor.py` está en marcha. La documentación
interactiva generada por FastAPI está en <http://127.0.0.1:8000/docs> (y en
formato ReDoc en `/redoc`).

[Volver al README](../README.md)

## Convenciones

- Los cuerpos de las peticiones `POST` son JSON (`Content-Type: application/json`).
  Los campos que no existen se rechazan.
- Las URLs sin `http://` ni `https://` se completan con `https://`. Solo se
  aceptan direcciones `http` y `https`.
- Solo se aceptan peticiones dirigidas a `127.0.0.1` o `localhost` (cabecera
  `Host`), salvo que el servidor se arranque con `--host` en otra dirección.
- Fechas: `fecha_scraping`, `fecha` del historial y de las ejecuciones están en
  UTC con el formato `AAAA-MM-DD HH:MM:SS`. Las fechas de las tareas
  programadas están en hora local con el mismo formato. Las fechas de los jobs
  (`creado`, `iniciado`, `terminado`) son ISO 8601 con zona horaria.

## Resumen de rutas

| Método y ruta | Respuesta correcta | Descripción |
|---------------|--------------------|-------------|
| `POST /api/scrape` | 202 | Lanza un scraping en segundo plano |
| `POST /api/comparar` | 202 | Lanza una comparación en segundo plano |
| `GET /api/jobs/{id}` | 200 | Estado, progreso y resultado de un job |
| `GET /api/productos` | 200 | Productos con filtros, orden y paginación |
| `GET /api/productos/{id}/historial` | 200 | Historial de precios de un producto |
| `GET /api/exportar` | 200 | Descarga los productos filtrados en CSV o JSON |
| `GET /api/estadisticas` | 200 | Totales, precio medio y últimas ejecuciones |
| `GET /api/tareas` | 200 | Tareas programadas |
| `POST /api/tareas` | 201 | Crea una tarea programada |
| `DELETE /api/tareas/{nombre}` | 200 | Elimina una tarea programada |

## Trabajos en segundo plano

### POST /api/scrape

| Campo | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `url` | texto (máx. 2000) | obligatorio | URL del listado |
| `paginas` | entero, 1-10 | 1 | Páginas a scrapear (`?page=2`, `?page=3`...) |

Respuesta (202):

```json
{"job_id": "5d307431d1484e689be19f2cd0d873af", "estado": "pendiente"}
```

El scraping guarda los productos en la base de datos y registra la ejecución,
igual que la opción 1 o 2 del menú de consola.

### POST /api/comparar

| Campo | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `url1`, `url2` | texto (máx. 2000) | obligatorio | URLs de los dos listados |
| `nombre1`, `nombre2` | texto (máx. 60) | `Sitio 1`, `Sitio 2` | Nombres para mostrar |
| `umbral` | número, 0.5-1.0 | 0.6 | Similitud mínima de títulos |

Responde igual que `/api/scrape`. Los productos comparados no se guardan en la
base de datos (solo en `output/temp_sitio1.*` y `output/temp_sitio2.*`).

### GET /api/jobs/{id}

```json
{
  "id": "5d307431d1484e689be19f2cd0d873af",
  "tipo": "scrape",
  "estado": "terminado",
  "progreso": {"actual": 1, "total": 1, "texto": "Página 1 de 1"},
  "productos": 1,
  "error": null,
  "resultado": {"...": "..."},
  "creado": "2026-11-16T17:44:40+01:00",
  "iniciado": "2026-11-16T17:44:40+01:00",
  "terminado": "2026-11-16T17:44:40+01:00"
}
```

- `tipo`: `scrape` o `comparar`.
- `estado`: `pendiente` (en cola), `en_curso`, `terminado` o `error`. Como
  mucho se ejecutan a la vez `MAX_JOBS_SIMULTANEOS` jobs (2 por defecto).
- `progreso.texto`: `Página X de Y` en un scraping, `Sitio X de 2` en una
  comparación, `En cola` mientras está pendiente.
- `error`: mensaje del error si `estado` es `error`. Los jobs cancelados al
  apagar el servidor también acaban en `error`, con un mensaje que empieza por
  `Cancelado`.
- `resultado`: solo cuando `estado` es `terminado`; `null` en otro caso.

Resultado de un scraping:

| Campo | Descripción |
|-------|-------------|
| `url`, `sitio` | URL scrapeada y nombre con el que se guardó (el dominio, p. ej. `tienda_test`) |
| `productos`, `guardados` | Elementos encontrados y guardados en la base de datos |
| `duracion` | Segundos |
| `muestra` | Los primeros 20 elementos tal como se extrajeron (`numero`, `titulo`, `precio`, `descripcion`, `enlace`, `imagen`; los campos vacíos valen `"N/A"`) |

Resultado de una comparación:

| Campo | Descripción |
|-------|-------------|
| `nombre1`, `nombre2`, `url1`, `url2`, `umbral` | Datos de la petición |
| `productos1`, `productos2` | Productos encontrados en cada sitio |
| `coincidencias` | Lista de parejas (ver abajo) |
| `resumen` | `comparados`, `mas_baratos_sitio1`, `mas_baratos_sitio2`, `mismo_precio` y `ahorro` (lista de `{"moneda", "importe"}`) |

Cada coincidencia tiene `producto1` y `producto2` (`titulo`, `precio`,
`enlace`, `imagen`), `similitud` (0-1), `precio1`, `precio2`, `moneda1`,
`moneda2`, `diferencia`, `porcentaje_diferencia` y `mas_barato` (`sitio1`,
`sitio2`, `igual`, o `null` si falta algún precio o las monedas son distintas).

Los jobs se guardan en memoria y se pierden al reiniciar el servidor; el
registro permanente de cada ejecución está en `GET /api/estadisticas`.

## Productos

### GET /api/productos

| Parámetro | Valores | Por defecto | Descripción |
|-----------|---------|-------------|-------------|
| `sitio` | texto | | Solo productos de ese sitio |
| `q` | texto (máx. 200) | | Texto que debe aparecer en el título (los `%` y `_` se buscan literalmente) |
| `precio_min`, `precio_max` | número >= 0 | | Rango de precio; excluye los productos sin precio |
| `orden` | `fecha`, `precio`, `titulo` | `fecha` | `fecha` es la última vez que se vio el producto |
| `direccion` | `asc`, `desc` | `desc` | Al ordenar por precio, los productos sin precio van al final |
| `pagina` | entero >= 1 | 1 | |
| `por_pagina` | entero, 1-100 | 24 | |

Respuesta:

```json
{
  "productos": [
    {"id": 1, "titulo": "Producto de ejemplo", "precio": 19.99, "moneda": "EUR",
     "precio_texto": "19,99 €", "descripcion": null, "enlace": "https://tienda.test/p/1",
     "imagen": null, "sitio": "tienda_test", "categoria": null,
     "fecha_scraping": "2026-11-16 16:44:40"}
  ],
  "total": 1, "pagina": 1, "por_pagina": 24, "paginas": 1
}
```

Las columnas se explican en [Base de datos](base-de-datos.md).

### GET /api/productos/{id}/historial

Devuelve `{"producto": {...}, "historial": [...]}`. Cada elemento del
historial tiene `precio`, `moneda`, `precio_texto` y `fecha`, del más reciente
al más antiguo. Si el producto no existe responde 404.

### GET /api/exportar

Acepta los mismos filtros que `/api/productos` (sin paginación) y además
`formato` (`csv` o `json`, por defecto `csv`). Descarga un archivo
`productos_AAAAMMDD_HHMMSS.csv` o `.json` con todas las columnas de la tabla
`productos`. El CSV está separado por comas, en UTF-8 con BOM (para que Excel
reconozca las tildes) y deja vacíos los valores nulos.

## Estadísticas

### GET /api/estadisticas

```json
{
  "total_productos": 1,
  "total_jobs": 1,
  "total_sitios": 1,
  "por_sitio": [{"sitio": "tienda_test", "productos": 1}],
  "precio_medio": [{"moneda": "EUR", "media": 19.99, "productos": 1}],
  "ultimos_jobs": [
    {"id": 1, "url": "https://tienda.test/lista", "sitio": "tienda_test", "total_items": 1,
     "estado": "completado", "fecha": "2026-11-16 16:44:40", "duracion_segundos": 1.2}
  ]
}
```

`precio_medio` agrupa por moneda (`null` para los precios sin moneda) y solo
cuenta productos con precio. `ultimos_jobs` son las 10 ejecuciones más
recientes, de la consola, la web o el programador; su `estado` puede ser
`completado`, `sin_datos`, `error` o `cancelado`.

## Tareas programadas

### GET /api/tareas

```json
{
  "programador_activo": true,
  "tareas": [
    {"url": "https://tienda.test", "nombre": "Portátiles", "intervalo": 60, "max_paginas": 1,
     "ultima_ejecucion": null, "total_ejecuciones": 0, "proxima_ejecucion": "2026-11-16 18:44:40"}
  ]
}
```

`proxima_ejecucion` es `null` si el programador no está activo. Justo después
de crear una tarea también puede ser `null` durante un segundo, hasta que el
programador la recoge.

### POST /api/tareas

| Campo | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `nombre` | texto, 1-100 caracteres | obligatorio | Tiene que ser único |
| `url` | texto (máx. 2000) | obligatorio | URL a scrapear |
| `intervalo_minutos` | entero, 1-10080 | 60 | Cada cuántos minutos (como máximo, una semana) |
| `max_paginas` | entero, 1-10 | 1 | Páginas a scrapear en cada ejecución |

Responde 201 con la tarea creada, o 409 si ya existe una con ese nombre.

### DELETE /api/tareas/{nombre}

El nombre va codificado en la URL (por ejemplo `Port%C3%A1tiles%20%2F%20ofertas`
para `Portátiles / ofertas`). Responde `{"eliminada": "<nombre>"}` o 404 si no
existe.

## Errores

Los errores de validación (422) incluyen el detalle de cada campo:

```json
{
  "error": "Datos no válidos",
  "detalles": [
    {"campo": "url", "mensaje": "URL no válida: usa una dirección web como https://tienda.com/categoria"},
    {"campo": "paginas", "mensaje": "Debe ser mayor o igual que 1"}
  ]
}
```

`campo` es `null` cuando el error no es de un campo concreto (por ejemplo, un
cuerpo que no es JSON válido o un precio mínimo mayor que el máximo).

El resto de errores solo llevan `error`:

| Código | Cuándo |
|--------|--------|
| 404 | Job, producto, tarea o ruta inexistente (`{"error": "Recurso no encontrado"}` para rutas) |
| 405 | Método no permitido en esa ruta |
| 409 | Ya existe una tarea con ese nombre |
| 503 | El servidor se está cerrando y no acepta trabajos nuevos |

Excepción: si la cabecera `Host` no es `127.0.0.1` ni `localhost`, la respuesta
es un 400 en texto plano (`Invalid host header`), no JSON.

## Ejemplo

Linux y macOS (`curl`):

```bash
curl -X POST http://127.0.0.1:8000/api/scrape -H 'Content-Type: application/json' \
     -d '{"url": "https://books.toscrape.com/", "paginas": 2}'
curl http://127.0.0.1:8000/api/jobs/<job_id>
curl 'http://127.0.0.1:8000/api/productos?q=python&orden=precio&direccion=asc'
```

Windows (PowerShell):

```powershell
$job = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/scrape `
       -ContentType 'application/json' -Body '{"url": "https://books.toscrape.com/", "paginas": 2}'
Invoke-RestMethod "http://127.0.0.1:8000/api/jobs/$($job.job_id)"
Invoke-RestMethod 'http://127.0.0.1:8000/api/productos?q=python&orden=precio&direccion=asc'
```

En Windows PowerShell 5.1, `Invoke-RestMethod` muestra mal las tildes de las
respuestas ("PÃ¡gina" en lugar de "Página") porque no las lee como UTF-8; en
PowerShell 7 se ven bien. Los datos que devuelve la API son correctos.
