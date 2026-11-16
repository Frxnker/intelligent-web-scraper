"""
Configuración del scraper.

Las rutas se calculan a partir de la ubicación de este archivo, así que el
programa funciona igual se lance desde el directorio que se lance.
"""

from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / 'output'
DB_PATH = OUTPUT_DIR / 'scraper.db'
TAREAS_PATH = OUTPUT_DIR / 'tareas_programadas.json'

# Peticiones HTTP (modo sin navegador) y navegador
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}
TIMEOUT = 10  # segundos para cada petición HTTP

# Selenium
PAGE_LOAD_TIMEOUT = 30  # segundos máximos para driver.get()
WAIT_TIMEOUT = 10  # segundos máximos para las esperas explícitas
ESPERA_CONTENIDO = 5  # segundos máximos esperando a que aparezca un listado cargado por JavaScript
SCROLL_ESPERA_MAX = 2  # segundos que se espera a que aparezca contenido nuevo al hacer scroll
SCROLL_MAX_ITERACIONES = 10

# Estrategia de scraping:
#   'auto'     -> petición HTTP + BeautifulSoup; Selenium si falla o no encuentra nada
#   'estatico' -> solo petición HTTP, nunca abre el navegador
#   'selenium' -> siempre con navegador
MODO_SCRAPING = 'auto'

# Pausa entre páginas al usar paginación (segundos)
DELAY_BETWEEN_REQUESTS = 2

# Extracción
PARSER = 'lxml'  # Opciones: 'lxml', 'html.parser', 'html5lib'
MAX_ELEMENTOS = 50  # máximo de elementos por página en la extracción genérica
