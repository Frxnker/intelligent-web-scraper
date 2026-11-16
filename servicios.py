"""
Operaciones de alto nivel compartidas por el menú de consola (main.py), el
programador de tareas (programador.py) y la interfaz web (web/app.py).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import config
from database import ScraperDB
from paginacion import scrapear_con_paginacion
from utils import nombre_desde_url


class OperacionCancelada(Exception):
    """Se lanza desde una función de progreso para interrumpir un scraping."""


@dataclass
class ResultadoScraping:
    url: str
    sitio: str
    datos: list[dict] = field(default_factory=list)
    guardados: int = 0
    duracion: float = 0.0


def _registrar(db_path, url, sitio, total, estado, duracion):
    with ScraperDB(db_path or config.DB_PATH) as db:
        db.registrar_job(url, sitio, total, estado=estado, duracion=duracion)


def scrapear_y_guardar(url, paginas=1, *, scraper_class=None, sitio=None, db_path=None,
                       progreso=None) -> ResultadoScraping:
    """
    Scrapea una URL (una o varias páginas), guarda los productos en la base de
    datos y registra la ejecución en scraping_jobs.

    Se usa un único scraper (y como mucho un navegador) para todas las páginas,
    y se cierra siempre, también si hay un error.

    Args:
        url: URL ya validada (utils.normalizar_url).
        paginas: 1 para una sola página; más de 1 usa la paginación.
        scraper_class: clase del scraper (por defecto scraper.Scraper).
        sitio: valor de la columna `sitio` (por defecto, el dominio).
        db_path: base de datos a usar (por defecto config.DB_PATH).
        progreso: función opcional progreso(pagina, total) llamada antes de cada página.

    Raises:
        La excepción original si el scraping falla (después de registrarla en scraping_jobs).
    """
    if scraper_class is None:
        from scraper import Scraper
        scraper_class = Scraper

    nombre_archivo = nombre_desde_url(url)
    resultado = ResultadoScraping(url=url, sitio=sitio or nombre_archivo)
    inicio = time.time()

    try:
        with scraper_class(headless=True) as scraper:
            if paginas > 1:
                resultado.datos = scrapear_con_paginacion(scraper, url, paginas, progreso=progreso)
            else:
                if progreso is not None:
                    progreso(1, 1)
                resultado.datos = scraper.scrapear_pagina_universal(url, nombre_archivo)
    except OperacionCancelada:
        _registrar(db_path, url, resultado.sitio, 0, 'cancelado', time.time() - inicio)
        raise
    except Exception:
        _registrar(db_path, url, resultado.sitio, 0, 'error', time.time() - inicio)
        raise

    resultado.duracion = time.time() - inicio
    with ScraperDB(db_path or config.DB_PATH) as db:
        if resultado.datos:
            resultado.guardados = db.insertar_productos_bulk(resultado.datos, resultado.sitio)
        estado = 'completado' if resultado.datos else 'sin_datos'
        db.registrar_job(url, resultado.sitio, len(resultado.datos), estado=estado, duracion=resultado.duracion)
    return resultado
