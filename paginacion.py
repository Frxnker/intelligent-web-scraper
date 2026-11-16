"""
Scraping de varias páginas de un listado.

Las URLs de las páginas siguientes se generan con un parámetro de página en la
query string (?page=2, ?p=2, ?pg=2 o ?pagina=2; si la URL no trae ninguno se
añade ?page=N). Si el sitio pagina de otra forma, el parámetro se ignora y el
servidor devuelve la misma página: en ese caso la paginación se detiene en
cuanto una página no aporta elementos nuevos.
"""

from __future__ import annotations

import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from colorama import Fore

import config
from utils import nombre_desde_url

PARAMETROS_PAGINA = ('page', 'p', 'pg', 'pagina')


class Paginador:
    """Generación de URLs paginadas."""

    @staticmethod
    def generar_urls_paginadas(url_base, max_paginas=5) -> list[str]:
        """
        Genera las URLs de `max_paginas` páginas empezando por url_base.

        Si url_base ya trae un número de página (?page=3) se continúa desde ahí.
        """
        if max_paginas < 1:
            return []

        partes = urlparse(url_base)
        params = parse_qs(partes.query, keep_blank_values=True)
        parametro = next((p for p in PARAMETROS_PAGINA if p in params), 'page')
        valor_actual = params.get(parametro, ['1'])[0]
        pagina_inicial = int(valor_actual) if valor_actual.isdigit() else 1

        urls = [url_base]
        for pagina in range(pagina_inicial + 1, pagina_inicial + max_paginas):
            nuevos_params = {**params, parametro: [str(pagina)]}
            urls.append(urlunparse(partes._replace(query=urlencode(nuevos_params, doseq=True))))
        return urls


def _clave(dato: dict) -> tuple:
    """Identificador de un elemento para detectar repetidos entre páginas."""
    enlace = dato.get('enlace')
    if enlace and enlace != 'N/A':
        return ('enlace', enlace)
    return ('contenido', dato.get('titulo'), dato.get('precio'))


def scrapear_con_paginacion(scraper, url_base, max_paginas=5, delay=None, nombre_base=None, progreso=None):
    """
    Scrapea varias páginas seguidas.

    Args:
        scraper: instancia con scrapear_pagina_universal(url, nombre) (Scraper o SeleniumScraper).
        url_base: URL de la primera página.
        max_paginas: número máximo de páginas a scrapear.
        delay: pausa entre páginas en segundos, para no sobrecargar el servidor
            (por defecto config.DELAY_BETWEEN_REQUESTS).
        nombre_base: prefijo de los archivos generados (por defecto, el dominio).
        progreso: función opcional progreso(pagina, total) que se llama antes de
            cada página. Si lanza una excepción, la paginación se interrumpe.

    Returns:
        Lista con los elementos de todas las páginas, sin repetidos.
    """
    if delay is None:
        delay = config.DELAY_BETWEEN_REQUESTS
    print(f"\n{Fore.CYAN}{'=' * 70}")
    print(f"{Fore.YELLOW}📄 SCRAPING CON PAGINACIÓN")
    print(f"{Fore.CYAN}{'=' * 70}\n")
    print(f"{Fore.WHITE}🔗 URL base: {url_base}")
    print(f"{Fore.WHITE}📊 Páginas máximas: {max_paginas}\n")

    nombre_base = nombre_base or nombre_desde_url(url_base)
    urls = Paginador.generar_urls_paginadas(url_base, max_paginas)
    todos_los_datos, vistos = [], set()
    paginas_scrapeadas = 0

    for i, url in enumerate(urls, 1):
        if progreso is not None:
            progreso(i, len(urls))
        print(f"{Fore.CYAN}📄 Scrapeando página {i}/{len(urls)}...")
        print(f"{Fore.WHITE}   URL: {url}\n")

        try:
            datos = scraper.scrapear_pagina_universal(url, f'{nombre_base}_pagina_{i}')
        except Exception as e:  # noqa: BLE001 - se conservan las páginas ya obtenidas
            if not todos_los_datos:
                # Sin páginas que conservar: el error se propaga para que quien llama lo vea
                # (si no, un fallo al abrir el navegador parecería una página sin productos)
                raise
            print(f"{Fore.RED}❌ Error en página {i}: {e}; se conservan las páginas anteriores\n")
            break
        paginas_scrapeadas = i

        if not datos:
            print(f"{Fore.YELLOW}⚠️  Página {i}: sin datos, deteniendo paginación\n")
            break

        nuevos = [d for d in datos if _clave(d) not in vistos]
        if not nuevos:
            print(f"{Fore.YELLOW}⚠️  Página {i}: no aporta elementos nuevos (el sitio probablemente "
                  f"no usa este parámetro de página), deteniendo paginación\n")
            break
        vistos.update(_clave(d) for d in nuevos)
        todos_los_datos.extend(nuevos)
        print(f"{Fore.GREEN}✅ Página {i}: {len(nuevos)} elementos nuevos")
        print(f"{Fore.CYAN}   Total acumulado: {len(todos_los_datos)}\n")

        if i < len(urls):
            print(f"{Fore.CYAN}⏳ Esperando {delay} segundos...\n")
            time.sleep(delay)

    print(f"{Fore.GREEN}{'=' * 70}")
    print(f"{Fore.GREEN}✅ PAGINACIÓN COMPLETADA")
    print(f"{Fore.GREEN}{'=' * 70}")
    print(f"{Fore.WHITE}📊 Total de elementos: {len(todos_los_datos)}")
    print(f"{Fore.WHITE}📄 Páginas scrapeadas: {paginas_scrapeadas}/{len(urls)}\n")

    return todos_los_datos
