# Menú de consola

[Volver al README](../README.md)

```bash
python main.py
```

Comparte la base de datos, las tareas y los archivos de `output/` con la
[interfaz web](interfaz-web.md).

## Opciones

| Opción | Qué hace | Qué pide |
|--------|----------|----------|
| 1 | Scrapea una URL y guarda los productos en la base de datos | URL |
| 2 | Scrapea varias páginas seguidas (`?page=2`, `?page=3`...) y las guarda | URL y número de páginas (1-10, por defecto 3) |
| 3 | Scrapea dos URLs y compara los precios de los productos parecidos (no los guarda en la base de datos) | Dos URLs, un nombre para cada sitio y la similitud mínima (0.5-1.0, por defecto 0.6) |
| 4 | Lista los productos guardados | Sitio (opcional) y cantidad (por defecto 20) |
| 5 | Busca productos por texto en el título | Texto |
| 6 | Muestra el total de productos, de ejecuciones y los productos por sitio | |
| 7 | Borra los productos que no se han visto en los últimos N días, con su historial | Días (por defecto 30) y confirmación |
| 8 | Crea una tarea programada | Nombre (único), URL, intervalo en minutos (por defecto 60) y páginas (por defecto 1) |
| 9 | Lista las tareas programadas | |
| 10 | Arranca el programador en segundo plano; se detiene pulsando Enter | |
| 11 | Elimina una tarea programada | Nombre |
| 12 | Sale | |

Después de cada opción pregunta si se quiere continuar. Si la URL no lleva
`http://` o `https://` se añade `https://`; si no es una dirección web válida se
avisa y se vuelve al menú. Si un número no es válido se avisa y se usa el valor
por defecto; si está fuera de rango se ajusta al límite más cercano.

`python scraper_selenium.py` scrapea una sola URL usando siempre el navegador,
sin guardar en la base de datos (solo genera los archivos de `output/`).

## Archivos generados

Todo se guarda en `output/`, dentro de la carpeta del proyecto (o junto al
`.exe` si se usa el ejecutable), se lance el programa desde donde se lance.

| Archivo | Contenido |
|---------|-----------|
| `<dominio>.html`, `.csv`, `.json` | HTML de la página y elementos extraídos al scrapear una sola página (opción 1, opción 2 con una página, tareas y web) |
| `<dominio>_pagina_N.*` | Lo mismo para cada página cuando se scrapea más de una |
| `<dominio>_selenium.*` | Resultado de `python scraper_selenium.py` |
| `temp_sitio1.*`, `temp_sitio2.*` | Páginas descargadas por el comparador |
| `scraper.db` | Base de datos SQLite (ver [Base de datos](base-de-datos.md)) |
| `tareas_programadas.json` | Tareas programadas |

`<dominio>` es el dominio sin `www.` y con los caracteres no válidos en nombres
de archivo cambiados por `_` (`www.amazon.es` pasa a `amazon_es`). El HTML se
guarda también cuando no se encuentra nada, para poder revisar la estructura
de la página. Los CSV y JSON contienen las columnas `numero`, `titulo`,
`precio` (texto original), `descripcion`, `enlace` e `imagen`, con `N/A` en
los campos vacíos.

## Uso desde código

```python
from database import ScraperDB
from precios import parsear_precio
from scraper import Scraper
from servicios import scrapear_y_guardar

# Scrapear, guardar en la base de datos y registrar la ejecución (lo que hacen el menú y la web)
resultado = scrapear_y_guardar('https://books.toscrape.com/', paginas=2)
print(resultado.sitio, len(resultado.datos), resultado.guardados)

# Solo extraer, sin guardar en la base de datos
with Scraper() as scraper:
    datos = scraper.scrapear_pagina_universal('https://books.toscrape.com/', 'libros')
    print(scraper.ultimo_metodo)  # 'estatico' o 'selenium'

# Consultar la base de datos
with ScraperDB() as db:
    productos, total = db.consultar_productos(texto='python', orden='precio', descendente=False)
    print(total, db.obtener_historial_precios(productos[0]['id']) if productos else [])

parsear_precio('1.299,99 €')  # (1299.99, 'EUR')
```

`Scraper` y `SeleniumScraper` se usan con `with` para asegurar que el navegador
se cierra aunque haya un error. `scrapear_y_guardar` ya lo hace por su cuenta.
