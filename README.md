# Intelligent Web Scraper

Herramienta de línea de comandos en Python para extraer listados de páginas web
(productos, artículos), guardarlos en CSV, JSON y SQLite, comparar precios entre
dos sitios y repetir el scraping de forma periódica.

## Qué hace

- **Extracción genérica.** Busca elementos repetidos en la página (tarjetas de
  producto, `<article>`, listas...) y de cada uno saca título, precio,
  descripción, enlace e imagen. Usa heurísticas (atributos `data-*`,
  encabezados, clases que contienen `price`/`precio`, símbolos de moneda), así
  que no necesita configuración por sitio, pero tampoco acierta siempre.
- **Primero sin navegador, Selenium solo si hace falta.** Descarga la página con
  `requests` y la analiza con BeautifulSoup. Si la descarga falla (error de red,
  403, 503...), la respuesta no es HTML o no aparece ningún elemento, abre Chrome
  con Selenium y repite la extracción sobre la página ya renderizada. El
  navegador se arranca una sola vez por sesión de scraping y solo si se necesita.
- **Scripts específicos** para Amazon, PcComponentes, eBay, AliExpress y blogs
  de wordpress.com (`scripts.js`). Se ejecutan dentro del navegador, así que esos
  dominios van directamente a Selenium. Si el script no encuentra nada, se usa
  la extracción genérica.
- **Con Selenium:** espera a que el documento termine de cargar y a que no haya
  peticiones jQuery pendientes, espera hasta 5 s a que aparezca algo con forma de
  listado (contenido cargado por JavaScript), elimina los avisos de cookies,
  newsletter o modales que flotan sobre la página (posición `fixed` o
  `absolute`) y hace scroll hasta el final para cargar el contenido diferido.
- **Precios.** Interpreta formatos español e inglés (`1.299,99 €`, `$1,299.99`)
  y guarda por separado el importe numérico, la moneda y el texto original.
- **Base de datos SQLite** con los productos (un producto con enlace se
  actualiza al volver a scrapearlo), el historial de precios y un registro de
  cada ejecución.
- **Paginación** añadiendo un parámetro de página a la URL (`?page=2`...).
- **Comparador de precios** entre dos URLs, emparejando productos por similitud
  de título.
- **Tareas programadas** que se repiten cada N minutos mientras el programa está
  abierto.

## Requisitos

- Python 3.9 o superior (probado con 3.13).
- Google Chrome, solo para las páginas que necesitan navegador. Selenium
  (Selenium Manager, incluido desde la versión 4.6) descarga automáticamente el
  chromedriver compatible la primera vez, así que esa primera ejecución necesita
  conexión a internet.

## Instalación

### Windows (PowerShell)

```powershell
git clone https://github.com/Frxnker/intelligent-web-scraper.git
cd intelligent-web-scraper
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell no deja ejecutar `Activate.ps1`, usa `.venv\Scripts\activate.bat`
desde `cmd`, o permite scripts locales para tu usuario con
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Linux y macOS

```bash
git clone https://github.com/Frxnker/intelligent-web-scraper.git
cd intelligent-web-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En un servidor Linux sin entorno gráfico hace falta tener Chrome o Chromium
instalado; el navegador se ejecuta en modo headless.

## Uso

```bash
python main.py
```

| Opción | Qué hace |
|--------|----------|
| 1 | Scrapea una URL y guarda los productos en la base de datos |
| 2 | Scrapea varias páginas seguidas (`?page=2`, `?page=3`...), de 1 a 10 |
| 3 | Scrapea dos URLs y compara los precios de los productos parecidos |
| 4 | Lista los productos guardados (filtrando por sitio si se quiere) |
| 5 | Busca productos por texto en el título |
| 6 | Muestra estadísticas: total de productos, ejecuciones y productos por sitio |
| 7 | Borra los productos que no se han visto en los últimos N días, con su historial |
| 8 | Crea una tarea programada (URL, intervalo en minutos, número de páginas) |
| 9 | Lista las tareas programadas |
| 10 | Arranca el programador en segundo plano; se detiene pulsando Enter |
| 11 | Elimina una tarea programada |
| 12 | Sale |

Si la URL no lleva `http://` o `https://` se añade `https://`.

`python scraper_selenium.py` scrapea una sola URL usando siempre el navegador.

### Archivos generados

Todo se guarda en `output/`, dentro de la carpeta del proyecto, se lance el
programa desde donde se lance:

| Archivo | Contenido |
|---------|-----------|
| `<dominio>.html`, `.csv`, `.json` | HTML de la página y elementos extraídos (opción 1) |
| `<dominio>_pagina_N.*` | Lo mismo para cada página de la opción 2 |
| `temp_sitio1.*`, `temp_sitio2.*` | Páginas descargadas por el comparador |
| `scraper.db` | Base de datos SQLite |
| `tareas_programadas.json` | Tareas programadas |

El HTML se guarda también cuando no se encuentra nada, para poder revisar la
estructura de la página.

### Uso desde código

```python
from scraper import Scraper
from database import ScraperDB
from precios import parsear_precio

with Scraper() as scraper:
    datos = scraper.scrapear_pagina_universal('https://books.toscrape.com/', 'libros')
    print(scraper.ultimo_metodo)  # 'estatico' o 'selenium'

with ScraperDB() as db:
    db.insertar_productos_bulk(datos, 'books_toscrape_com')
    print(db.buscar_productos('python'))

parsear_precio('1.299,99 €')  # (1299.99, 'EUR')
```

### Configuración

Las opciones están en `config.py`:

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `MODO_SCRAPING` | `'auto'` | `'auto'` (sin navegador y Selenium si hace falta), `'estatico'` (nunca abre el navegador) o `'selenium'` (siempre navegador) |
| `TIMEOUT` | 10 | Segundos por petición HTTP sin navegador |
| `PAGE_LOAD_TIMEOUT` | 30 | Segundos máximos de carga de una página en Selenium |
| `WAIT_TIMEOUT` | 10 | Segundos máximos de espera a que termine de cargar |
| `ESPERA_CONTENIDO` | 5 | Segundos máximos esperando a que aparezca un listado cargado por JavaScript |
| `SCROLL_ESPERA_MAX`, `SCROLL_MAX_ITERACIONES` | 2, 10 | Espera tras cada scroll y número máximo de cargas de contenido |
| `DELAY_BETWEEN_REQUESTS` | 2 | Pausa en segundos entre páginas al paginar |
| `MAX_ELEMENTOS` | 50 | Máximo de elementos por página en la extracción genérica |
| `USER_AGENT`, `DEFAULT_HEADERS` | | Cabeceras de las peticiones |

## Precios

`precios.py` convierte el texto del precio en un número y una moneda:

| Texto | Importe | Moneda |
|-------|---------|--------|
| `1.299,99 €` | 1299.99 | EUR |
| `$1,299.99` | 1299.99 | USD |
| `£12.50` | 12.5 | GBP |
| `¥1,000` | 1000.0 | JPY |
| `1 299,99 €` | 1299.99 | EUR |
| `EUR 1.299,99` | 1299.99 | EUR |
| `1299` | 1299.0 | (ninguna) |
| `Gratis`, `N/A` | (ninguno) | (ninguna) |

Reglas:

- Si aparecen tanto el punto como la coma, el que va último es el separador decimal.
- Si solo hay un separador y le siguen exactamente tres cifras, se toma como
  separador de miles: `1.299` es 1299. Con otro número de cifras es decimal:
  `12,5` es 12.5.
- Si el texto tiene varios números, se usa el que va pegado al símbolo de moneda
  (`-20% 1.299,99 €` da 1299.99).
- `$` se interpreta como USD y `¥` como JPY.

## Base de datos

`schema.sql` define las tablas y `database.py` lo ejecuta al abrir la base de
datos, así que los dos siempre coinciden.

- `productos`: `precio` (REAL), `moneda`, `precio_texto` (texto original), título,
  descripción, enlace (único), imagen, sitio y fecha de la última vez que se vio.
  Si un producto no tiene enlace se identifica por título y sitio.
- `historial_precios`: una fila cada vez que se guarda un producto con precio. Se
  borra junto con su producto.
- `scraping_jobs`: URL, sitio, número de elementos y duración de cada ejecución.

Las bases de datos creadas por versiones anteriores, que guardaban el precio como
texto, se migran automáticamente la primera vez que se abren: se conservan los
ids, se interpreta cada precio y se mantiene el texto original en `precio_texto`.
La migración se hace en una transacción, pero conviene copiar `output/scraper.db`
antes de actualizar.

## Estructura del proyecto

```
intelligent-web-scraper/
├── main.py               Menú de consola
├── scraper.py            Estrategia: sin navegador primero, Selenium si hace falta
├── scraper_selenium.py   Navegador Chrome: carga, esperas, scroll, scripts JS
├── extractor.py          Extracción genérica con BeautifulSoup
├── scripts.js            JavaScript que se ejecuta en el navegador (scripts por sitio)
├── js_scripts.py         Carga scripts.js y elige el script según el dominio
├── precios.py            Interpretación de precios y monedas
├── database.py           Acceso a SQLite y migración del formato antiguo
├── schema.sql            Definición de las tablas
├── comparador.py         Comparación de precios entre dos sitios
├── paginacion.py         Scraping de varias páginas
├── programador.py        Tareas programadas
├── utils.py              Exportación a CSV/JSON y validación de URLs
├── config.py             Configuración
├── requirements.txt      Dependencias
├── requirements-dev.txt  Dependencias para desarrollo (pytest)
├── pytest.ini
├── tests/                Tests
└── output/               Resultados (no se sube al repositorio)
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Los tests no acceden a internet ni necesitan Chrome: usan HTML de ejemplo, una
sesión HTTP y un navegador simulados, y bases de datos temporales. Si Node.js
está instalado, también se comprueba que `scripts.js` es JavaScript válido.

## Limitaciones

- **Las heurísticas fallan a veces.** La extracción genérica puede tomar
  elementos que no son productos (menús, tarjetas decorativas) o no reconocer el
  listado. Revisa el HTML guardado en `output/` cuando el resultado no sea el
  esperado.
- **Los sitios cambian su HTML.** Los scripts específicos de `scripts.js` y los
  selectores genéricos dependen de la estructura actual de cada página y dejan
  de funcionar cuando el sitio la cambia. No hay ninguna garantía de que sigan
  funcionando con Amazon, PcComponentes, eBay o AliExpress.
- **Bloqueos.** Muchas tiendas detectan el acceso automatizado y responden con
  captchas o errores. Esta herramienta no intenta saltarse esas protecciones.
- **Modo automático.** Si la página descargada sin navegador contiene algo que
  parece un listado pero no es el contenido real (que se carga después con
  JavaScript), no se usa Selenium. En ese caso, pon `MODO_SCRAPING = 'selenium'`.
- **Precios ambiguos.** `1.299` se lee como 1299. Si un texto tiene precio
  anterior y actual, normalmente se toma el primero. `$` siempre se trata como
  dólar estadounidense.
- **Paginación.** Solo funciona con sitios que paginan con un parámetro en la
  URL. Si el sitio lo ignora, se detiene al ver que la página se repite.
- **Comparador.** Que dos títulos se parezcan no garantiza que sean el mismo
  producto (variantes, packs). Un producto del segundo sitio puede emparejarse
  con varios del primero.
- **Programador.** Las tareas solo se ejecutan mientras `main.py` está abierto
  con el programador iniciado.

## Uso responsable

- Lee los términos de uso de cada sitio antes de scrapearlo. Muchos prohíben el
  acceso automatizado o la reutilización de sus datos.
- Respeta `robots.txt` (`https://<sitio>/robots.txt`). La herramienta **no** lo
  comprueba automáticamente; es responsabilidad de quien la usa.
- No sobrecargues los servidores: mantén la pausa entre páginas y usa
  intervalos amplios en las tareas programadas (15 minutos o más).
- No recojas datos personales.

## Licencia

MIT.
