"""Tests de la API web con TestClient. El scraper es falso: no hay red ni navegador."""

import csv
import io
import json
import threading
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

import config
from database import ScraperDB
from web.app import crear_app


def crear_scraper_falso():
    """Devuelve una clase con la interfaz de scraper.Scraper y estado propio para cada test."""

    class ScraperFalso:
        instancias = []
        en_pagina_2 = threading.Event()  # se activa al llegar a la página 2 si `pausar` está activo
        continuar = threading.Event()
        pausar = False

        def __init__(self, headless=True):
            self.headless = headless
            self.cerrado = False
            self.urls = []
            ScraperFalso.instancias.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.close()

        def close(self):
            self.cerrado = True

        def scrapear_pagina_universal(self, url, nombre_archivo):
            self.urls.append(url)
            partes = urlparse(url)
            pagina = parse_qs(partes.query).get('page', ['1'])[0]
            if 'falla' in partes.hostname:
                raise RuntimeError('Fallo simulado del navegador\nStacktrace que no debe verse')
            if 'vacia' in partes.hostname:
                return []
            if ScraperFalso.pausar and pagina == '2':
                ScraperFalso.en_pagina_2.set()
                ScraperFalso.continuar.wait(5)
            caro = 'tienda-b' not in partes.hostname
            return [
                {'numero': 1, 'titulo': f'Portátil Lenovo Legion {pagina}', 'precio': '1.299,99 €' if caro else '1.199,99 €',
                 'descripcion': 'N/A', 'enlace': f'https://{partes.hostname}/p/lenovo-{pagina}', 'imagen': 'N/A'},
                {'numero': 2, 'titulo': f'Ratón Logitech MX {pagina}', 'precio': '25 €' if caro else '29,99 €',
                 'descripcion': 'N/A', 'enlace': f'https://{partes.hostname}/p/raton-{pagina}', 'imagen': 'N/A'},
            ]

    return ScraperFalso


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'DELAY_BETWEEN_REQUESTS', 0)
    scraper = crear_scraper_falso()
    db_path = tmp_path / 'api.db'
    tareas_path = tmp_path / 'tareas.json'
    app = crear_app(db_path=db_path, tareas_path=tareas_path, scraper_class=scraper, iniciar_programador=False)
    with TestClient(app, base_url='http://127.0.0.1') as cliente:
        yield SimpleNamespace(cliente=cliente, app=app, scraper=scraper, db_path=db_path, tareas_path=tareas_path)
    scraper.continuar.set()


def esperar_job(cliente, job_id, timeout=10):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        job = cliente.get(f'/api/jobs/{job_id}').json()
        if job['estado'] in ('terminado', 'error'):
            return job
        time.sleep(0.02)
    raise AssertionError(f'El job no terminó a tiempo: {job}')


def lanzar(cliente, ruta, cuerpo):
    respuesta = cliente.post(ruta, json=cuerpo)
    assert respuesta.status_code == 202, respuesta.text
    assert respuesta.json()['estado'] == 'pendiente'
    return respuesta.json()['job_id']


def sembrar(db_path):
    with ScraperDB(db_path) as db:
        db.insertar_productos_bulk([
            {'titulo': 'Portátil Lenovo Legion', 'precio': '1.299,99 €', 'enlace': 'https://a.test/1'},
            {'titulo': 'Ratón Logitech', 'precio': '25 €', 'enlace': 'https://a.test/2'},
            {'titulo': 'Teclado 100% mecánico', 'precio': 'N/A', 'enlace': 'https://a.test/3'},
        ], 'tienda_a')
        db.insertar_productos_bulk([{'titulo': 'Monitor LG', 'precio': '$199.99', 'enlace': 'https://b.test/1'}], 'tienda_b')


def detalles(respuesta):
    assert respuesta.status_code == 422, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo['error'] == 'Datos no válidos'
    return {(d['campo'], d['mensaje']) for d in cuerpo['detalles']}


# ---------------------------------------------------------------------------
# Scraping en segundo plano
# ---------------------------------------------------------------------------

def test_scrape_de_una_pagina(entorno):
    job_id = lanzar(entorno.cliente, '/api/scrape', {'url': 'tienda.test/portatiles'})
    job = esperar_job(entorno.cliente, job_id)

    assert job['estado'] == 'terminado', job
    assert job['tipo'] == 'scrape'
    assert job['progreso'] == {'actual': 1, 'total': 1, 'texto': 'Página 1 de 1'}
    assert job['productos'] == 2
    assert job['error'] is None
    resultado = job['resultado']
    assert resultado['url'] == 'https://tienda.test/portatiles'
    assert (resultado['sitio'], resultado['productos'], resultado['guardados']) == ('tienda_test', 2, 2)
    assert [p['titulo'] for p in resultado['muestra']] == ['Portátil Lenovo Legion 1', 'Ratón Logitech MX 1']

    # Un solo scraper (navegador) por job, y cerrado
    assert len(entorno.scraper.instancias) == 1
    assert entorno.scraper.instancias[0].cerrado
    assert entorno.cliente.get('/api/productos').json()['total'] == 2


def test_scrape_de_varias_paginas_informa_del_progreso(entorno):
    entorno.scraper.pausar = True
    job_id = lanzar(entorno.cliente, '/api/scrape', {'url': 'https://tienda.test/lista', 'paginas': 3})

    assert entorno.scraper.en_pagina_2.wait(5)
    en_curso = entorno.cliente.get(f'/api/jobs/{job_id}').json()
    assert en_curso['estado'] == 'en_curso'
    assert en_curso['progreso'] == {'actual': 2, 'total': 3, 'texto': 'Página 2 de 3'}
    assert en_curso['resultado'] is None

    entorno.scraper.continuar.set()
    job = esperar_job(entorno.cliente, job_id)
    assert job['estado'] == 'terminado'
    assert job['progreso']['actual'] == 3
    assert job['resultado']['guardados'] == 6

    [scraper] = entorno.scraper.instancias  # las tres páginas con el mismo navegador
    assert scraper.cerrado
    assert scraper.urls == ['https://tienda.test/lista', 'https://tienda.test/lista?page=2', 'https://tienda.test/lista?page=3']


def test_scrape_con_error_cierra_el_scraper_y_lo_registra(entorno):
    job = esperar_job(entorno.cliente, lanzar(entorno.cliente, '/api/scrape', {'url': 'https://falla.test/'}))

    assert job['estado'] == 'error'
    assert job['error'] == 'Fallo simulado del navegador'  # solo la primera línea
    assert job['resultado'] is None
    assert entorno.scraper.instancias[0].cerrado
    ultimo = entorno.cliente.get('/api/estadisticas').json()['ultimos_jobs'][0]
    assert (ultimo['url'], ultimo['estado']) == ('https://falla.test/', 'error')


def test_error_en_la_primera_de_varias_paginas_no_parece_una_pagina_vacia(entorno):
    job = esperar_job(entorno.cliente, lanzar(entorno.cliente, '/api/scrape', {'url': 'https://falla.test/', 'paginas': 3}))
    assert job['estado'] == 'error'
    assert job['error'] == 'Fallo simulado del navegador'
    assert entorno.scraper.instancias[0].cerrado


def test_scrape_sin_productos(entorno):
    job = esperar_job(entorno.cliente, lanzar(entorno.cliente, '/api/scrape', {'url': 'https://vacia.test/'}))
    assert job['estado'] == 'terminado'
    assert job['productos'] == 0
    assert entorno.cliente.get('/api/estadisticas').json()['ultimos_jobs'][0]['estado'] == 'sin_datos'


@pytest.mark.parametrize('cuerpo, esperado', [
    ({'url': 'ftp://tienda.test'}, ('url', 'URL no válida: usa una dirección web como https://tienda.com/categoria')),
    ({'url': 'no es una url'}, ('url', 'URL no válida: usa una dirección web como https://tienda.com/categoria')),
    ({'url': 'tienda.test', 'paginas': 0}, ('paginas', 'Debe ser mayor o igual que 1')),
    ({'url': 'tienda.test', 'paginas': 11}, ('paginas', 'Debe ser menor o igual que 10')),
    ({'url': 'tienda.test', 'paginas': 'tres'}, ('paginas', 'Debe ser un número entero')),
    ({'url': 'tienda.test', 'paginas': 2.5}, ('paginas', 'Debe ser un número entero')),
    ({'paginas': 2}, ('url', 'Campo obligatorio')),
    ({'url': 'tienda.test', 'otro': 1}, ('otro', 'Campo no permitido')),
])
def test_scrape_valida_la_entrada(entorno, cuerpo, esperado):
    assert esperado in detalles(entorno.cliente.post('/api/scrape', json=cuerpo))
    assert entorno.scraper.instancias == []


def test_cuerpo_que_no_es_json(entorno):
    assert (None, 'El cuerpo de la petición no es un JSON válido') in detalles(
        entorno.cliente.post('/api/scrape', content='{no json', headers={'Content-Type': 'application/json'}))
    # Un formulario de otra web (text/plain) no puede lanzar scrapings
    assert entorno.cliente.post('/api/scrape', content='{"url": "tienda.test"}',
                                headers={'Content-Type': 'text/plain'}).status_code == 422


def test_job_inexistente(entorno):
    respuesta = entorno.cliente.get('/api/jobs/no-existe')
    assert respuesta.status_code == 404
    assert 'No existe ese job' in respuesta.json()['error']


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

def titulos(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return [p['titulo'] for p in respuesta.json()['productos']]


def test_listar_productos(entorno):
    sembrar(entorno.db_path)
    datos = entorno.cliente.get('/api/productos').json()
    assert (datos['total'], datos['pagina'], datos['paginas'], datos['por_pagina']) == (4, 1, 1, 24)
    portatil = next(p for p in datos['productos'] if p['titulo'] == 'Portátil Lenovo Legion')
    assert (portatil['precio'], portatil['moneda'], portatil['precio_texto']) == (1299.99, 'EUR', '1.299,99 €')


@pytest.mark.parametrize('parametros, esperado', [
    ({'sitio': 'tienda_b'}, ['Monitor LG']),
    ({'q': 'lenovo'}, ['Portátil Lenovo Legion']),
    ({'q': '100%'}, ['Teclado 100% mecánico']),
    ({'precio_min': 20, 'precio_max': 300, 'orden': 'precio', 'direccion': 'asc'}, ['Ratón Logitech', 'Monitor LG']),
    ({'orden': 'precio', 'direccion': 'asc'}, ['Ratón Logitech', 'Monitor LG', 'Portátil Lenovo Legion', 'Teclado 100% mecánico']),
    ({'orden': 'precio', 'direccion': 'desc'}, ['Portátil Lenovo Legion', 'Monitor LG', 'Ratón Logitech', 'Teclado 100% mecánico']),
    ({'orden': 'titulo', 'direccion': 'asc'}, ['Monitor LG', 'Portátil Lenovo Legion', 'Ratón Logitech', 'Teclado 100% mecánico']),
    ({'sitio': 'no-existe'}, []),
])
def test_filtros_y_orden(entorno, parametros, esperado):
    sembrar(entorno.db_path)
    assert titulos(entorno.cliente.get('/api/productos', params=parametros)) == esperado


def test_paginacion_de_productos(entorno):
    sembrar(entorno.db_path)
    pagina2 = entorno.cliente.get('/api/productos', params={'orden': 'titulo', 'direccion': 'asc', 'por_pagina': 3, 'pagina': 2}).json()
    assert (pagina2['total'], pagina2['paginas'], pagina2['pagina']) == (4, 2, 2)
    assert [p['titulo'] for p in pagina2['productos']] == ['Teclado 100% mecánico']


@pytest.mark.parametrize('parametros, esperado', [
    ({'precio_min': 10, 'precio_max': 5}, (None, 'El precio mínimo no puede ser mayor que el máximo')),
    ({'precio_min': 'barato'}, ('precio_min', 'Debe ser un número')),
    ({'precio_min': -1}, ('precio_min', 'Debe ser mayor o igual que 0')),
    ({'orden': 'popularidad'}, ('orden', "Debe ser uno de estos valores: 'fecha', 'precio' o 'titulo'")),
    ({'por_pagina': 101}, ('por_pagina', 'Debe ser menor o igual que 100')),
    ({'pagina': 0}, ('pagina', 'Debe ser mayor o igual que 1')),
])
def test_filtros_no_validos(entorno, parametros, esperado):
    assert esperado in detalles(entorno.cliente.get('/api/productos', params=parametros))


def test_historial_de_precios(entorno):
    sembrar(entorno.db_path)
    with ScraperDB(entorno.db_path) as db:
        db.insertar_producto({'titulo': 'Ratón Logitech', 'precio': '19,99 €', 'enlace': 'https://a.test/2'}, 'tienda_a')
        producto_id = db.consultar_productos(texto='Ratón')[0][0]['id']

    datos = entorno.cliente.get(f'/api/productos/{producto_id}/historial').json()
    assert datos['producto']['titulo'] == 'Ratón Logitech'
    assert [h['precio'] for h in datos['historial']] == [19.99, 25.0]
    assert datos['historial'][0]['moneda'] == 'EUR'

    respuesta = entorno.cliente.get('/api/productos/9999/historial')
    assert respuesta.status_code == 404
    assert respuesta.json() == {'error': 'No existe el producto 9999'}
    assert entorno.cliente.get('/api/productos/abc/historial').status_code == 422


# ---------------------------------------------------------------------------
# Exportar
# ---------------------------------------------------------------------------

def test_exportar_csv_filtrado(entorno):
    sembrar(entorno.db_path)
    respuesta = entorno.cliente.get('/api/exportar', params={'formato': 'csv', 'sitio': 'tienda_a', 'orden': 'titulo', 'direccion': 'asc'})

    assert respuesta.status_code == 200
    assert respuesta.headers['content-type'].startswith('text/csv')
    assert respuesta.headers['content-disposition'].startswith('attachment; filename="productos_')
    assert respuesta.headers['content-disposition'].endswith('.csv"')
    texto = respuesta.content.decode('utf-8')
    assert texto.startswith('﻿')  # BOM para Excel
    filas = list(csv.DictReader(io.StringIO(texto.lstrip('﻿'))))
    assert [f['titulo'] for f in filas] == ['Portátil Lenovo Legion', 'Ratón Logitech', 'Teclado 100% mecánico']
    assert (filas[0]['precio'], filas[0]['moneda']) == ('1299.99', 'EUR')
    assert filas[2]['precio'] == ''  # sin precio


def test_exportar_json_y_vacio(entorno):
    sembrar(entorno.db_path)
    respuesta = entorno.cliente.get('/api/exportar', params={'formato': 'json', 'q': 'monitor'})
    assert respuesta.headers['content-type'].startswith('application/json')
    assert [p['titulo'] for p in json.loads(respuesta.content)] == ['Monitor LG']

    vacio = entorno.cliente.get('/api/exportar', params={'sitio': 'no-existe'}).content.decode('utf-8').lstrip('﻿')
    assert vacio.splitlines() == ['id,titulo,precio,moneda,precio_texto,descripcion,enlace,imagen,sitio,categoria,fecha_scraping']

    assert ('formato', "Debe ser uno de estos valores: 'csv' o 'json'") in detalles(
        entorno.cliente.get('/api/exportar', params={'formato': 'xml'}))


# ---------------------------------------------------------------------------
# Comparar
# ---------------------------------------------------------------------------

def test_comparar_en_segundo_plano(entorno):
    job_id = lanzar(entorno.cliente, '/api/comparar', {
        'url1': 'tienda-a.test/portatiles', 'url2': 'https://tienda-b.test/portatiles', 'nombre1': 'Tienda A', 'umbral': 0.9,
    })
    job = esperar_job(entorno.cliente, job_id)

    assert job['estado'] == 'terminado', job
    assert job['progreso'] == {'actual': 2, 'total': 2, 'texto': 'Sitio 2 de 2'}
    r = job['resultado']
    assert (r['nombre1'], r['nombre2'], r['productos1'], r['productos2']) == ('Tienda A', 'Sitio 2', 2, 2)
    assert len(r['coincidencias']) == 2
    portatil, raton = r['coincidencias']
    assert portatil['mas_barato'] == 'sitio2'
    assert portatil['diferencia'] == pytest.approx(100.0)
    assert set(portatil['producto1']) == {'titulo', 'precio', 'enlace', 'imagen'}
    assert raton['mas_barato'] == 'sitio1'
    assert r['resumen']['mas_baratos_sitio1'] == 1
    assert r['resumen']['mas_baratos_sitio2'] == 1
    [ahorro] = r['resumen']['ahorro']
    assert ahorro['moneda'] == 'EUR'
    assert ahorro['importe'] == pytest.approx(104.99)

    [scraper] = entorno.scraper.instancias  # un único navegador para los dos sitios
    assert scraper.cerrado


@pytest.mark.parametrize('cuerpo, esperado', [
    ({'url1': 'a.test', 'url2': 'b.test', 'umbral': 0.2}, ('umbral', 'Debe ser mayor o igual que 0,5')),
    ({'url1': 'a.test'}, ('url2', 'Campo obligatorio')),
    ({'url1': 'a.test', 'url2': 'javascript:alert(1)'}, ('url2', 'URL no válida: usa una dirección web como https://tienda.com/categoria')),
    ({'url1': 'a.test', 'url2': 'b.test', 'nombre1': 'x' * 61}, ('nombre1', 'Debe tener como máximo 60 caracteres')),
])
def test_comparar_valida_la_entrada(entorno, cuerpo, esperado):
    assert esperado in detalles(entorno.cliente.post('/api/comparar', json=cuerpo))


# ---------------------------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------------------------

def test_estadisticas(entorno):
    sembrar(entorno.db_path)
    esperar_job(entorno.cliente, lanzar(entorno.cliente, '/api/scrape', {'url': 'https://tienda.test/'}))

    datos = entorno.cliente.get('/api/estadisticas').json()
    assert (datos['total_productos'], datos['total_sitios'], datos['total_jobs']) == (6, 3, 1)
    assert {s['sitio']: s['productos'] for s in datos['por_sitio']} == {'tienda_a': 3, 'tienda_b': 1, 'tienda_test': 2}
    medias = {m['moneda']: (round(m['media'], 2), m['productos']) for m in datos['precio_medio']}
    assert medias == {'EUR': (round((1299.99 + 25 + 1299.99 + 25) / 4, 2), 4), 'USD': (199.99, 1)}
    [job] = datos['ultimos_jobs']
    assert (job['url'], job['sitio'], job['total_items'], job['estado']) == ('https://tienda.test/', 'tienda_test', 2, 'completado')


def test_estadisticas_sin_datos(entorno):
    assert entorno.cliente.get('/api/estadisticas').json() == {
        'total_productos': 0, 'total_jobs': 0, 'total_sitios': 0, 'por_sitio': [], 'precio_medio': [], 'ultimos_jobs': [],
    }


# ---------------------------------------------------------------------------
# Tareas programadas
# ---------------------------------------------------------------------------

def test_crear_listar_y_eliminar_tareas(entorno):
    cliente = entorno.cliente
    assert cliente.get('/api/tareas').json() == {'programador_activo': False, 'tareas': []}

    respuesta = cliente.post('/api/tareas', json={'nombre': 'Portátiles / ofertas', 'url': 'tienda.test/portatiles',
                                                  'intervalo_minutos': 30, 'max_paginas': 2})
    assert respuesta.status_code == 201, respuesta.text
    creada = respuesta.json()
    assert (creada['nombre'], creada['url'], creada['intervalo'], creada['max_paginas']) == (
        'Portátiles / ofertas', 'https://tienda.test/portatiles', 30, 2)
    assert creada['proxima_ejecucion'] is None  # el programador no está en marcha en este test

    duplicada = cliente.post('/api/tareas', json={'nombre': 'Portátiles / ofertas', 'url': 'otra.test'})
    assert duplicada.status_code == 409
    assert duplicada.json() == {'error': "Ya existe una tarea llamada 'Portátiles / ofertas'"}

    assert [t['nombre'] for t in cliente.get('/api/tareas').json()['tareas']] == ['Portátiles / ofertas']
    assert json.loads(entorno.tareas_path.read_text(encoding='utf-8'))[0]['nombre'] == 'Portátiles / ofertas'

    # El nombre lleva una barra: el frontend lo codifica con encodeURIComponent
    assert cliente.delete('/api/tareas/Port%C3%A1tiles%20%2F%20ofertas').json() == {'eliminada': 'Portátiles / ofertas'}
    assert cliente.delete('/api/tareas/Port%C3%A1tiles%20%2F%20ofertas').status_code == 404
    assert cliente.get('/api/tareas').json()['tareas'] == []


@pytest.mark.parametrize('cuerpo, esperado', [
    ({'nombre': '   ', 'url': 'a.test'}, ('nombre', 'No puede estar vacío')),
    ({'nombre': 'x', 'url': 'a.test', 'intervalo_minutos': 0}, ('intervalo_minutos', 'Debe ser mayor o igual que 1')),
    ({'nombre': 'x', 'url': 'a.test', 'max_paginas': 20}, ('max_paginas', 'Debe ser menor o igual que 10')),
    ({'nombre': 'x'}, ('url', 'Campo obligatorio')),
])
def test_tareas_valida_la_entrada(entorno, cuerpo, esperado):
    assert esperado in detalles(entorno.cliente.post('/api/tareas', json=cuerpo))


def test_el_programador_corre_mientras_el_servidor_esta_encendido(tmp_path):
    app = crear_app(db_path=tmp_path / 'p.db', tareas_path=tmp_path / 't.json',
                    scraper_class=crear_scraper_falso(), iniciar_programador=True)
    programador = app.state.programador

    with TestClient(app, base_url='http://127.0.0.1') as cliente:
        assert cliente.get('/api/tareas').json()['programador_activo'] is True
        assert programador.thread.is_alive()

        cliente.post('/api/tareas', json={'nombre': 'cada hora', 'url': 'tienda.test'})
        # El hilo del programador recoge la tarea nueva en su siguiente ciclo (1 s)
        limite = time.monotonic() + 5
        while time.monotonic() < limite:
            [tarea] = cliente.get('/api/tareas').json()['tareas']
            if tarea['proxima_ejecucion']:
                break
            time.sleep(0.1)
        assert tarea['proxima_ejecucion'] is not None

    assert programador.activo is False
    assert not programador.thread.is_alive()


# ---------------------------------------------------------------------------
# Interfaz y errores generales
# ---------------------------------------------------------------------------

def test_sirve_la_interfaz(entorno):
    inicio = entorno.cliente.get('/')
    assert inicio.status_code == 200
    assert 'Intelligent Web Scraper' in inicio.text
    for archivo, tipo in [('app.js', 'javascript'), ('styles.css', 'text/css')]:
        respuesta = entorno.cliente.get(f'/static/{archivo}')
        assert respuesta.status_code == 200
        assert tipo in respuesta.headers['content-type']


def test_errores_en_espanol(entorno):
    assert entorno.cliente.get('/api/no-existe').json() == {'error': 'Recurso no encontrado'}
    assert entorno.cliente.put('/api/scrape', json={}).json() == {'error': 'Método no permitido'}


def test_solo_acepta_el_host_local(entorno):
    # Protege contra páginas web que intenten usar la API mediante DNS rebinding
    assert entorno.cliente.get('/api/estadisticas', headers={'Host': 'malicioso.test'}).status_code == 400
    assert entorno.cliente.get('/api/estadisticas', headers={'Host': 'localhost:8000'}).status_code == 200
