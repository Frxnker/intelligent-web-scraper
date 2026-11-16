"""
Acceso a los scripts JavaScript de scripts.js.

scripts.js define un objeto WebScraperJS con las funciones que se ejecutan en el
navegador. Aquí se construye el código para llamarlas con
driver.execute_script() y se decide qué extractor usar según el dominio.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

RUTA_SCRIPTS = Path(__file__).resolve().parent / 'scripts.js'

# (fragmento del dominio, función de scripts.js)
EXTRACTORES_POR_SITIO = (
    ('pccomponentes', 'extraerPcComponentes'),
    ('amazon', 'extraerAmazon'),
    ('ebay', 'extraerEbay'),
    ('aliexpress', 'extraerAliExpress'),
    ('wordpress', 'extraerWordPress'),
)


@lru_cache(maxsize=1)
def codigo_fuente() -> str:
    """Contenido de scripts.js (se lee una sola vez)."""
    return RUTA_SCRIPTS.read_text(encoding='utf-8')


def script_para(funcion: str) -> str:
    """Código listo para driver.execute_script(codigo, *args) que llama a WebScraperJS.<funcion>."""
    if not funcion.isidentifier():
        raise ValueError(f'Nombre de función JavaScript no válido: {funcion!r}')
    return f"{codigo_fuente()}\nreturn WebScraperJS.{funcion}.apply(null, arguments);"


def extractor_para_url(url: str) -> str | None:
    """Nombre de la función de extracción específica para la URL, o None si no hay."""
    partes = urlparse(url)
    dominio = (partes.hostname or '').lower()
    for fragmento, funcion in EXTRACTORES_POR_SITIO:
        if fragmento in dominio:
            return funcion
    if '/wp-content/' in partes.path.lower():
        return 'extraerWordPress'
    return None
