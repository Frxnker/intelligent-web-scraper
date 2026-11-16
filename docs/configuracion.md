# Configuración

[Volver al README](../README.md)

Las opciones están en `config.py`. Se cambian editando el archivo; no hay
variables de entorno ni archivo de configuración aparte.

## Scraping

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `MODO_SCRAPING` | `'auto'` | `'auto'`: sin navegador y Selenium si hace falta; `'estatico'`: nunca abre el navegador; `'selenium'`: siempre con navegador (ver [Cómo funciona](funcionamiento.md)) |
| `TIMEOUT` | 10 | Segundos máximos por petición HTTP sin navegador |
| `PAGE_LOAD_TIMEOUT` | 30 | Segundos máximos de carga de una página en Selenium |
| `WAIT_TIMEOUT` | 10 | Segundos máximos de espera a que la página termine de cargar |
| `ESPERA_CONTENIDO` | 5 | Segundos máximos esperando a que aparezca un listado cargado por JavaScript |
| `SCROLL_ESPERA_MAX` | 2 | Segundos que se espera contenido nuevo tras cada scroll |
| `SCROLL_MAX_ITERACIONES` | 10 | Máximo de cargas de contenido al hacer scroll |
| `DELAY_BETWEEN_REQUESTS` | 2 | Pausa en segundos entre páginas al paginar |
| `PARSER` | `'lxml'` | Analizador de BeautifulSoup (`'lxml'`, `'html.parser'` o `'html5lib'`; este último no está en `requirements.txt`) |
| `MAX_ELEMENTOS` | 50 | Máximo de elementos por página en la extracción genérica |
| `USER_AGENT` | Chrome 120 en Windows | Navegador con el que se identifican las peticiones y Selenium |
| `DEFAULT_HEADERS` | | Cabeceras de las peticiones sin navegador (`User-Agent`, `Accept`, `Accept-Language`) |

## Interfaz web

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `SERVIDOR_HOST` | `'127.0.0.1'` | Dirección por defecto de `servidor.py` (se cambia con `--host`) |
| `SERVIDOR_PUERTO` | 8000 | Puerto por defecto (se cambia con `--port`) |
| `MAX_JOBS_SIMULTANEOS` | 2 | Scrapings o comparaciones a la vez desde la web; cada uno puede abrir su propio Chrome |

## Rutas

Se calculan solas; normalmente no hay que tocarlas.

| Opción | Valor |
|--------|-------|
| `BASE_DIR` | Carpeta del proyecto, o la carpeta del `.exe` si se usa el ejecutable |
| `RECURSOS_DIR` | Carpeta de `schema.sql`, `scripts.js` y `web/static`: la del proyecto, o la carpeta temporal donde se descomprime el `.exe` |
| `OUTPUT_DIR` | `BASE_DIR/output` |
| `DB_PATH` | `OUTPUT_DIR/scraper.db` |
| `TAREAS_PATH` | `OUTPUT_DIR/tareas_programadas.json` |

Como las rutas no dependen del directorio actual, el programa guarda los datos
en el mismo sitio se lance desde donde se lance.
