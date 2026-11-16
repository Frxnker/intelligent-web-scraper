"""
Scraper principal: intenta primero sin navegador y usa Selenium solo si hace falta.

1. Descarga la página con requests y extrae los elementos con BeautifulSoup.
   Es rápido y no abre Chrome.
2. Si la descarga falla (error de red, 403, 503...), la respuesta no es HTML o
   no se encuentra ningún elemento, abre Chrome con Selenium y extrae sobre la
   página ya renderizada (contenido cargado con JavaScript, scroll, etc.).

Los sitios con un script específico en scripts.js (Amazon, PcComponentes,
eBay, AliExpress, WordPress) van directamente a Selenium.

El comportamiento se cambia con config.MODO_SCRAPING ('auto', 'estatico', 'selenium').
"""

from __future__ import annotations

import requests
from colorama import Fore

import config
from extractor import extraer_productos_html
from js_scripts import extractor_para_url
from utils import guardar_y_mostrar

MODOS = ('auto', 'estatico', 'selenium')


def _abrir_selenium(headless: bool):
    # Import diferido: selenium solo se carga si de verdad hace falta el navegador
    from scraper_selenium import SeleniumScraper
    return SeleniumScraper(headless=headless)


class Scraper:
    """
    Scraper con la misma interfaz que SeleniumScraper (scrapear_pagina_universal,
    close, context manager). El navegador se abre la primera vez que se necesita
    y se reutiliza para las páginas siguientes.
    """

    def __init__(self, headless=True, modo=None, session=None, fabrica_navegador=None):
        """
        Args:
            headless: ejecutar Chrome sin ventana cuando haga falta abrirlo.
            modo: 'auto', 'estatico' o 'selenium' (por defecto config.MODO_SCRAPING).
            session: sesión de requests a usar (útil para tests).
            fabrica_navegador: función headless -> navegador (útil para tests).
        """
        self.headless = headless
        self.modo = modo or config.MODO_SCRAPING
        if self.modo not in MODOS:
            raise ValueError(f"Modo de scraping no válido: {self.modo!r}. Opciones: {', '.join(MODOS)}")
        if session is None:
            session = requests.Session()
            session.headers.update(config.DEFAULT_HEADERS)
        self.session = session
        self._fabrica_navegador = fabrica_navegador or _abrir_selenium
        self._navegador = None
        self.ultimo_metodo = None  # 'estatico' o 'selenium'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def navegador(self):
        if self._navegador is None:
            self._navegador = self._fabrica_navegador(self.headless)
        return self._navegador

    # ------------------------------------------------------------------
    # Sin navegador
    # ------------------------------------------------------------------

    def descargar_html(self, url) -> tuple[str, str] | None:
        """Descarga la página. Devuelve (html, url_final) o None si no se puede usar."""
        try:
            respuesta = self.session.get(url, timeout=config.TIMEOUT)
            respuesta.raise_for_status()
        except requests.RequestException as e:
            print(f"{Fore.YELLOW}⚠️  No se pudo descargar sin navegador: {e}")
            return None

        tipo = respuesta.headers.get('Content-Type', '').lower()
        if 'html' not in tipo:
            print(f"{Fore.YELLOW}⚠️  La respuesta no es HTML ({tipo or 'sin Content-Type'})")
            return None
        if 'charset' not in tipo:
            # Sin charset, requests asume ISO-8859-1 y estropea las tildes
            respuesta.encoding = respuesta.apparent_encoding
        return respuesta.text, respuesta.url

    def extraer_sin_navegador(self, url) -> tuple[list[dict], str | None]:
        descarga = self.descargar_html(url)
        if descarga is None:
            return [], None
        html, url_final = descarga
        return extraer_productos_html(html, url_final), html

    # ------------------------------------------------------------------
    # Estrategia
    # ------------------------------------------------------------------

    def extraer(self, url) -> tuple[list[dict], str | None]:
        """Extrae los elementos de una página eligiendo el método. Devuelve (datos, html)."""
        if self.modo != 'selenium':
            funcion = extractor_para_url(url)
            if self.modo == 'auto' and funcion:
                print(f"{Fore.CYAN}🎯 Sitio con script específico ({funcion}): se usa el navegador\n")
            else:
                print(f"{Fore.CYAN}📡 Descargando sin navegador: {url}")
                datos, html = self.extraer_sin_navegador(url)
                if datos or self.modo == 'estatico':
                    self.ultimo_metodo = 'estatico'
                    print(f"{Fore.GREEN}✓ Extracción sin navegador: {len(datos)} elementos\n")
                    return datos, html
                print(f"{Fore.YELLOW}⚠️  Sin resultados sin navegador; se prueba con Selenium\n")

        self.ultimo_metodo = 'selenium'
        return self.navegador.extraer(url)

    def scrapear_pagina_universal(self, url, nombre_archivo='scraping') -> list[dict]:
        """
        Scrapea una página y guarda HTML, CSV y JSON en output/.

        Args:
            url: URL completa de la página.
            nombre_archivo: nombre base de los archivos generados.
        """
        print(f"{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.YELLOW}🌐 SCRAPEANDO")
        print(f"{Fore.CYAN}{'=' * 70}\n")
        print(f"{Fore.WHITE}🔗 URL: {url}\n")

        datos, html = self.extraer(url)
        guardar_y_mostrar(datos, nombre_archivo, html)
        return datos

    def close(self):
        """Cierra el navegador (si se llegó a abrir) y la sesión HTTP."""
        try:
            if self._navegador is not None:
                self._navegador.close()
        finally:
            self._navegador = None
            self.session.close()
