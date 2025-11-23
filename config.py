"""
Archivo de configuración para el web scraper
"""

# Configuración de requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TIMEOUT = 10  # segundos
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 1  # segundos

# Configuración de parseo
PARSER = 'lxml'  # Opciones: 'html.parser', 'lxml', 'html5lib'

# Configuración de salida
OUTPUT_DIR = 'output'
OUTPUT_FORMAT = 'csv'  # Opciones: 'csv', 'json'

# Headers por defecto para las peticiones HTTP
DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# URLs de ejemplo para testing
EXAMPLE_URLS = [
    'https://quotes.toscrape.com/',
    'https://books.toscrape.com/'
]
