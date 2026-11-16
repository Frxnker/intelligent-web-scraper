"""Tests de servicios.scrapear_y_guardar, web/jobs.py, rutas empaquetadas y servidor.py."""

import importlib
import socket
import sys
import threading
import time

import pytest

import config
from database import ScraperDB
from servicios import OperacionCancelada, scrapear_y_guardar
from web.jobs import GestorJobs


class ScraperFalso:
    instancias = []

    def __init__(self, headless=True):
        self.cerrado = False
        self.urls = []
        ScraperFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cerrado = True

    def scrapear_pagina_universal(self, url, nombre_archivo):
        self.urls.append((url, nombre_archivo))
        if 'falla' in url:
            raise RuntimeError('fallo')
        if 'vacia' in url:
            return []
        return [{'titulo': f'Producto {url}', 'precio': '10 €', 'enlace': url}]


@pytest.fixture(autouse=True)
def limpiar(monkeypatch):
    ScraperFalso.instancias = []
    monkeypatch.setattr(config, 'DELAY_BETWEEN_REQUESTS', 0)


def ultimo_job(db_path):
    with ScraperDB(db_path) as db:
        return db.obtener_ultimos_jobs(1)[0]


# ---------------------------------------------------------------------------
# servicios.scrapear_y_guardar
# ---------------------------------------------------------------------------

def test_una_pagina_guarda_y_registra(tmp_path):
    db_path = tmp_path / 's.db'
    progreso = []
    resultado = scrapear_y_guardar('https://www.tienda.test/', 1, scraper_class=ScraperFalso, db_path=db_path,
                                   progreso=lambda actual, total: progreso.append((actual, total)))

    assert (resultado.sitio, resultado.guardados, len(resultado.datos)) == ('tienda_test', 1, 1)
    assert progreso == [(1, 1)]
    [scraper] = ScraperFalso.instancias
    assert scraper.cerrado
    assert scraper.urls == [('https://www.tienda.test/', 'tienda_test')]
    job = ultimo_job(db_path)
    assert (job['sitio'], job['total_items'], job['estado']) == ('tienda_test', 1, 'completado')


def test_varias_paginas_con_un_solo_scraper(tmp_path):
    progreso = []
    resultado = scrapear_y_guardar('https://tienda.test/', 3, scraper_class=ScraperFalso, sitio='mi tarea',
                                   db_path=tmp_path / 's.db', progreso=lambda a, t: progreso.append((a, t)))
    assert progreso == [(1, 3), (2, 3), (3, 3)]
    assert len(resultado.datos) == 3
    assert len(ScraperFalso.instancias) == 1
    with ScraperDB(tmp_path / 's.db') as db:
        assert db.obtener_estadisticas()['por_sitio'] == {'mi tarea': 3}


def test_sin_datos_se_registra(tmp_path):
    resultado = scrapear_y_guardar('https://vacia.test/', 1, scraper_class=ScraperFalso, db_path=tmp_path / 's.db')
    assert resultado.datos == []
    assert ultimo_job(tmp_path / 's.db')['estado'] == 'sin_datos'


def test_error_cierra_el_scraper_registra_y_relanza(tmp_path):
    with pytest.raises(RuntimeError, match='fallo'):
        scrapear_y_guardar('https://falla.test/', 1, scraper_class=ScraperFalso, db_path=tmp_path / 's.db')
    assert ScraperFalso.instancias[0].cerrado
    assert ultimo_job(tmp_path / 's.db')['estado'] == 'error'


def test_cancelacion_entre_paginas(tmp_path):
    def progreso(actual, total):
        if actual == 2:
            raise OperacionCancelada('cancelado')

    with pytest.raises(OperacionCancelada):
        scrapear_y_guardar('https://tienda.test/', 3, scraper_class=ScraperFalso, db_path=tmp_path / 's.db',
                           progreso=progreso)
    [scraper] = ScraperFalso.instancias
    assert scraper.cerrado
    assert len(scraper.urls) == 1
    assert ultimo_job(tmp_path / 's.db')['estado'] == 'cancelado'


# ---------------------------------------------------------------------------
# web/jobs.py
# ---------------------------------------------------------------------------

def test_apagar_cancela_los_jobs_y_espera_a_los_que_estan_en_curso():
    gestor = GestorJobs(max_simultaneos=1)
    empezado, seguir = threading.Event(), threading.Event()

    def trabajo(job):
        job.avanzar(1, 3)
        empezado.set()
        seguir.wait(5)
        job.avanzar(2, 3)  # aquí detecta la cancelación
        return 0, None

    en_curso = gestor.lanzar('scrape', 'Página', trabajo)
    pendiente = gestor.lanzar('scrape', 'Página', trabajo)
    assert empezado.wait(5)
    assert pendiente.a_dict()['estado'] == 'pendiente'
    assert pendiente.a_dict()['progreso']['texto'] == 'En cola'

    apagado = threading.Thread(target=gestor.apagar)
    apagado.start()
    limite = time.monotonic() + 5
    while not en_curso.cancelado and time.monotonic() < limite:
        time.sleep(0.01)
    seguir.set()
    apagado.join(5)

    assert not apagado.is_alive()
    assert en_curso.a_dict()['estado'] == 'error'
    assert en_curso.a_dict()['error'].startswith('Cancelado')
    assert pendiente.a_dict()['estado'] == 'error'
    with pytest.raises(RuntimeError):
        gestor.lanzar('scrape', 'Página', trabajo)


def test_se_olvidan_los_jobs_terminados_mas_antiguos():
    gestor = GestorJobs(max_simultaneos=1, max_guardados=3)
    jobs = [gestor.lanzar('scrape', 'Página', lambda job: (0, None)) for _ in range(5)]
    gestor.apagar()
    assert [gestor.obtener(j.id) is not None for j in jobs][-3:] == [True, True, True]
    assert sum(gestor.obtener(j.id) is not None for j in jobs) <= 4


# ---------------------------------------------------------------------------
# Rutas al ejecutar el .exe de PyInstaller
# ---------------------------------------------------------------------------

def test_rutas_empaquetado(monkeypatch, tmp_path):
    ejecutable = tmp_path / 'dist' / 'IntelligentWebScraper.exe'
    extraccion = tmp_path / '_MEI12345'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(ejecutable))
    monkeypatch.setattr(sys, '_MEIPASS', str(extraccion), raising=False)
    try:
        importlib.reload(config)
        assert config.BASE_DIR == ejecutable.resolve().parent  # datos junto al .exe
        assert config.OUTPUT_DIR == ejecutable.resolve().parent / 'output'
        assert config.DB_PATH == ejecutable.resolve().parent / 'output' / 'scraper.db'
        assert config.RECURSOS_DIR == extraccion  # recursos empaquetados
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_recursos_en_modo_codigo_fuente():
    for recurso in ('schema.sql', 'scripts.js', 'web/static/index.html', 'web/static/app.js', 'web/static/styles.css'):
        assert (config.RECURSOS_DIR / recurso).is_file(), recurso


# ---------------------------------------------------------------------------
# servidor.py
# ---------------------------------------------------------------------------

def test_servidor_avisa_si_el_puerto_esta_ocupado(capsys):
    import servidor

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ocupado:
        ocupado.bind(('127.0.0.1', 0))
        ocupado.listen()
        puerto = ocupado.getsockname()[1]
        assert servidor.main(['--port', str(puerto), '--no-abrir']) == 1
    assert f'El puerto {puerto} ya está en uso' in capsys.readouterr().out
