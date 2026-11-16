"""
Scraper basado en Selenium (Chrome) para páginas que necesitan JavaScript.

Normalmente no se usa directamente: scraper.Scraper lo abre solo cuando una
petición HTTP simple no basta. También se puede ejecutar como script:

    python scraper_selenium.py
"""

from __future__ import annotations

import subprocess
import sys

from colorama import Fore, Style, init
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

import config
from extractor import SELECTORES_CONTENEDOR, extraer_productos_html, normalizar_items
from js_scripts import extractor_para_url, script_para
from utils import guardar_y_mostrar, nombre_desde_url, normalizar_url

init(autoreset=True)

JS_DOCUMENTO_CARGADO = "return document.readyState === 'complete';"
JS_JQUERY_INACTIVO = "return !window.jQuery || window.jQuery.active === 0;"
JS_ALTURA_DOCUMENTO = (
    "return Math.max(document.body ? document.body.scrollHeight : 0, "
    "document.documentElement.scrollHeight);"
)


def _mensaje(error: WebDriverException) -> str:
    """Primera línea del mensaje de Selenium (el resto suele ser un stacktrace)."""
    texto = (error.msg or str(error)).strip()
    return texto.splitlines()[0] if texto else type(error).__name__


class SeleniumScraper:
    """
    Scraper con un navegador Chrome real.

    Se puede usar como context manager para asegurar que el navegador se
    cierra aunque haya una excepción:

        with SeleniumScraper() as scraper:
            datos = scraper.scrapear_pagina_universal(url, 'nombre')
    """

    def __init__(self, headless=True):
        """
        Inicializa el navegador Chrome.

        Args:
            headless: si es True, el navegador se ejecuta sin ventana visible.
        """
        print(f"{Fore.CYAN}🚀 Inicializando navegador Chrome...")
        opciones = Options()
        if headless:
            opciones.add_argument('--headless=new')
            print(f"{Fore.CYAN}   Modo: Headless (sin ventana)")
        else:
            print(f"{Fore.CYAN}   Modo: Con ventana visible")

        opciones.add_argument('--disable-blink-features=AutomationControlled')
        opciones.add_argument(f'--user-agent={config.USER_AGENT}')
        opciones.add_argument('--disable-gpu')
        opciones.add_argument('--no-sandbox')
        opciones.add_argument('--disable-dev-shm-usage')
        opciones.add_experimental_option('excludeSwitches', ['enable-automation'])
        opciones.add_experimental_option('useAutomationExtension', False)

        servicio = Service()
        if sys.platform == 'win32' and hasattr(servicio, 'creation_flags'):
            # En Windows, el Ctrl+C de la consola llega a todos sus procesos: mataría a
            # chromedriver y dejaría Chrome abierto sin dueño. En su propio grupo de
            # procesos lo ignora y lo cierra driver.quit(), que cierra también Chrome.
            servicio.creation_flags |= subprocess.CREATE_NEW_PROCESS_GROUP

        self.driver = None
        try:
            # Selenium Manager (incluido en selenium >= 4.6) localiza o descarga chromedriver
            self.driver = webdriver.Chrome(service=servicio, options=opciones)
        except WebDriverException as e:
            print(f"{Fore.RED}✗ Error al iniciar navegador: {_mensaje(e)}")
            raise

        try:
            self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except WebDriverException:
            self.close()
            raise
        print(f"{Fore.GREEN}✓ Navegador iniciado correctamente\n")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # Navegación y esperas
    # ------------------------------------------------------------------

    def get_page(self, url, timeout=config.WAIT_TIMEOUT) -> bool:
        """
        Carga una página y espera a que termine de cargar.

        driver.get() ya bloquea hasta el evento load; después se espera a que
        document.readyState sea 'complete' y a que jQuery (si la página lo usa)
        no tenga peticiones pendientes.
        """
        print(f"{Fore.CYAN}📡 Cargando: {url}")
        try:
            self.driver.get(url)
        except TimeoutException:
            print(f"{Fore.YELLOW}⚠️  La página tardó más de {config.PAGE_LOAD_TIMEOUT}s en cargar; "
                  f"se continúa con lo que haya cargado")
            try:
                self.driver.execute_script('window.stop();')
            except WebDriverException as e:
                print(f"{Fore.YELLOW}⚠️  No se pudo detener la carga: {_mensaje(e)}")
        except WebDriverException as e:
            print(f"{Fore.RED}✗ Error al cargar página: {_mensaje(e)}\n")
            return False

        # Algunos errores de red (p. ej. conexión rechazada) no lanzan excepción:
        # Chrome muestra su página de error interna
        try:
            documento = str(self.driver.execute_script('return document.documentURI;'))
        except WebDriverException as e:
            print(f"{Fore.YELLOW}⚠️  No se pudo comprobar la página cargada: {_mensaje(e)}")
            documento = ''
        if documento.startswith('chrome-error://'):
            print(f"{Fore.RED}✗ Error al cargar página: el navegador no pudo conectar con {url}\n")
            return False

        self.esperar_carga_completa(timeout)
        print(f"{Fore.GREEN}✓ Página cargada\n")
        return True

    def esperar_carga_completa(self, timeout=config.WAIT_TIMEOUT) -> bool:
        """Espera a document.readyState == 'complete' y a que jQuery no tenga peticiones activas."""
        espera = WebDriverWait(self.driver, timeout)
        try:
            espera.until(lambda d: d.execute_script(JS_DOCUMENTO_CARGADO))
            espera.until(lambda d: d.execute_script(JS_JQUERY_INACTIVO))
        except TimeoutException:
            print(f"{Fore.YELLOW}⚠️  Timeout ({timeout}s) esperando a que la página termine de cargar")
            return False
        return True

    def esperar_contenido(self, timeout=config.ESPERA_CONTENIDO) -> bool:
        """
        Espera a que la página tenga algún contenedor de listado.

        Cubre el contenido que se carga con JavaScript después del evento load.
        Usa los mismos selectores que la extracción genérica (extractor.py).
        """
        selector = ', '.join(SELECTORES_CONTENEDOR)
        try:
            WebDriverWait(self.driver, timeout, poll_frequency=0.25).until(
                lambda d: d.execute_script('return document.querySelector(arguments[0]) !== null;', selector)
            )
        except TimeoutException:
            print(f"{Fore.YELLOW}⚠️  En {timeout}s no apareció ningún listado reconocible; se continúa")
            return False
        except WebDriverException as e:
            print(f"{Fore.YELLOW}⚠️  No se pudo comprobar si el contenido había cargado: {_mensaje(e)}")
            return False
        return True

    def _altura_documento(self) -> int:
        return self.driver.execute_script(JS_ALTURA_DOCUMENTO)

    def scroll_automatico_hasta_final(self, espera_max=config.SCROLL_ESPERA_MAX,
                                      max_iteraciones=config.SCROLL_MAX_ITERACIONES) -> int:
        """
        Hace scroll hasta el final para cargar contenido con carga diferida.

        Tras cada scroll espera como mucho `espera_max` segundos a que la página
        crezca; si no crece, se considera que se ha llegado al final.
        Devuelve el número de veces que se cargó contenido nuevo.
        """
        print(f"{Fore.CYAN}📜 Haciendo scroll para cargar contenido...")
        altura = self._altura_documento()
        iteraciones = 0
        while iteraciones < max_iteraciones:
            self.driver.execute_script('window.scrollTo(0, arguments[0]);', altura)
            try:
                WebDriverWait(self.driver, espera_max, poll_frequency=0.25).until(
                    lambda d, anterior=altura: self._altura_documento() > anterior
                )
            except TimeoutException:
                break
            altura = self._altura_documento()
            iteraciones += 1

        self.driver.execute_script('window.scrollTo(0, 0);')
        print(f"{Fore.GREEN}✓ Scroll completado ({iteraciones} cargas de contenido)\n")
        return iteraciones

    # ------------------------------------------------------------------
    # JavaScript
    # ------------------------------------------------------------------

    def ejecutar_js(self, funcion: str, *args):
        """Ejecuta una de las funciones de scripts.js en la página actual."""
        return self.driver.execute_script(script_para(funcion), *args)

    def remover_overlays(self) -> int:
        """Elimina avisos de cookies, newsletters y modales que tapan el contenido."""
        try:
            removidos = self.ejecutar_js('removerOverlays') or 0
        except WebDriverException as e:
            print(f"{Fore.YELLOW}⚠️  No se pudieron quitar los overlays: {_mensaje(e)}")
            return 0
        if removidos:
            print(f"{Fore.GREEN}✓ Removidos {removidos} overlays\n")
        return removidos

    # ------------------------------------------------------------------
    # Extracción
    # ------------------------------------------------------------------

    def extraer(self, url) -> tuple[list[dict], str | None]:
        """
        Carga la página y extrae los elementos.

        Orden: script específico del sitio (scripts.js) si lo hay; si no hay o no
        encuentra nada, extracción genérica con BeautifulSoup sobre el HTML renderizado.

        Returns:
            (datos, html). html es None si la página no se pudo cargar.
        """
        if not self.get_page(url):
            return [], None

        self.esperar_contenido()
        self.remover_overlays()
        self.scroll_automatico_hasta_final()

        funcion = extractor_para_url(url)
        if funcion:
            print(f"{Fore.CYAN}🎯 Usando script específico para este sitio ({funcion})...")
            try:
                datos = normalizar_items(self.ejecutar_js(funcion))
            except WebDriverException as e:
                print(f"{Fore.YELLOW}⚠️  El script específico falló: {_mensaje(e)}")
                datos = []
            if datos:
                print(f"{Fore.GREEN}✓ Script específico: {len(datos)} elementos\n")
                return datos, self.driver.page_source
            print(f"{Fore.YELLOW}⚠️  El script específico no encontró nada; se usa la extracción genérica\n")

        html = self.driver.page_source
        datos = extraer_productos_html(html, self.driver.current_url)
        print(f"{Fore.GREEN}✓ Extracción genérica: {len(datos)} elementos\n")
        return datos, html

    def scrapear_pagina_universal(self, url, nombre_archivo='scraping_selenium') -> list[dict]:
        """
        Scrapea una página con el navegador y guarda HTML, CSV y JSON en output/.

        Args:
            url: URL completa de la página.
            nombre_archivo: nombre base de los archivos generados.
        """
        print(f"{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.YELLOW}🌐 SCRAPEANDO CON SELENIUM")
        print(f"{Fore.CYAN}{'=' * 70}\n")
        print(f"{Fore.WHITE}🔗 URL: {url}\n")

        datos, html = self.extraer(url)
        guardar_y_mostrar(datos, nombre_archivo, html)
        return datos

    def close(self):
        """Cierra el navegador. Se puede llamar varias veces."""
        if self.driver is None:
            return
        try:
            self.driver.quit()
        except WebDriverException as e:
            print(f"{Fore.YELLOW}⚠️  Error al cerrar el navegador: {_mensaje(e)}")
        finally:
            self.driver = None
        print(f"\n{Fore.CYAN}👋 Navegador cerrado")


def ejemplo_universal():
    """Pide una URL por consola y la scrapea con Selenium."""
    print(f"\n{Fore.CYAN}{'=' * 62}")
    print(f"{Fore.YELLOW}  SCRAPER CON SELENIUM")
    print(f"{Fore.CYAN}{'=' * 62}{Style.RESET_ALL}\n")

    print(f"{Fore.YELLOW}Ejemplos de URLs:")
    print(f"{Fore.WHITE}  - https://quotes.toscrape.com/")
    print(f"{Fore.WHITE}  - https://books.toscrape.com/\n")

    texto = input(f"{Fore.GREEN}Ingresa la URL completa: {Style.RESET_ALL}").strip()
    if not texto:
        texto = 'https://quotes.toscrape.com/'
        print(f"{Fore.CYAN}Usando URL por defecto: {texto}\n")
    url = normalizar_url(texto)
    if not url:
        print(f"{Fore.RED}✗ URL no válida: {texto}")
        return

    nombre_archivo = f"{nombre_desde_url(url)}_selenium"
    try:
        with SeleniumScraper(headless=True) as scraper:
            datos = scraper.scrapear_pagina_universal(url, nombre_archivo)
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Proceso interrumpido por el usuario")
        return
    except WebDriverException as e:
        print(f"\n{Fore.RED}✗ Error del navegador: {_mensaje(e)}")
        return

    if datos:
        print(f"{Fore.GREEN}✅ Scraping completado: {len(datos)} elementos extraídos")
        print(f"{Fore.CYAN}📁 Archivos guardados en {config.OUTPUT_DIR}")


if __name__ == "__main__":
    ejemplo_universal()
