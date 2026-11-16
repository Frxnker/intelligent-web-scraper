"""Tests de la estrategia "sin navegador primero, Selenium si hace falta" (sin red ni Chrome)."""

import json

import pytest
import requests

from scraper import Scraper

HTML_CON_PRODUCTOS = '''
<html><body>
  <div class="product-card"><h2>Cafetera eléctrica</h2><span class="price">49,99 €</span></div>
  <div class="product-card"><h2>Tostadora</h2><span class="price">25 €</span></div>
</body></html>
'''
HTML_SIN_PRODUCTOS = '<html><body><div id="app"></div><script src="/app.js"></script></body></html>'


def respuesta(url, cuerpo='', estado=200, tipo='text/html; charset=utf-8', codificacion='utf-8'):
    """Construye una requests.Response real sin hacer ninguna petición."""
    r = requests.Response()
    r.status_code = estado
    r.reason = 'OK' if estado == 200 else 'Error'
    r.url = url
    r.headers['Content-Type'] = tipo
    r._content = cuerpo.encode(codificacion)
    # Igual que hace requests al recibir la respuesta (ISO-8859-1 si es text/* sin charset)
    r.encoding = requests.utils.get_encoding_from_headers(r.headers)
    return r


class SesionFalsa:
    def __init__(self, resultado):
        self.resultado = resultado
        self.peticiones = []
        self.cerrada = False

    def get(self, url, timeout=None):
        self.peticiones.append(url)
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado

    def close(self):
        self.cerrada = True


class NavegadorFalso:
    def __init__(self):
        self.urls = []
        self.cerrado = False

    def extraer(self, url):
        self.urls.append(url)
        return [{'numero': 1, 'titulo': 'Desde Selenium', 'precio': '10 €'}], '<html>renderizado</html>'

    def close(self):
        self.cerrado = True


@pytest.fixture
def navegador():
    return NavegadorFalso()


def crear_scraper(resultado_http, navegador, modo='auto'):
    sesion = SesionFalsa(resultado_http)
    aperturas = []

    def fabrica(headless):
        aperturas.append(headless)
        return navegador

    scraper = Scraper(headless=True, modo=modo, session=sesion, fabrica_navegador=fabrica)
    return scraper, sesion, aperturas


def test_pagina_estatica_no_abre_el_navegador(navegador):
    url = 'https://tienda.test/'
    scraper, sesion, aperturas = crear_scraper(respuesta(url, HTML_CON_PRODUCTOS), navegador)

    datos, html = scraper.extraer(url)

    assert [d['titulo'] for d in datos] == ['Cafetera eléctrica', 'Tostadora']
    assert 'product-card' in html
    assert scraper.ultimo_metodo == 'estatico'
    assert aperturas == []


def test_sin_productos_usa_selenium(navegador):
    url = 'https://spa.test/'
    scraper, _, aperturas = crear_scraper(respuesta(url, HTML_SIN_PRODUCTOS), navegador)

    datos, html = scraper.extraer(url)

    assert datos[0]['titulo'] == 'Desde Selenium'
    assert html == '<html>renderizado</html>'
    assert scraper.ultimo_metodo == 'selenium'
    assert navegador.urls == [url]
    assert aperturas == [True]


@pytest.mark.parametrize('resultado', [
    requests.ConnectionError('sin conexión'),
    requests.Timeout('timeout'),
    respuesta('https://x.test/', 'Forbidden', estado=403),
    respuesta('https://x.test/', 'Service Unavailable', estado=503),
    respuesta('https://x.test/', '{"a": 1}', tipo='application/json'),
])
def test_fallo_sin_navegador_usa_selenium(resultado, navegador):
    scraper, _, _ = crear_scraper(resultado, navegador)
    datos, _ = scraper.extraer('https://x.test/')
    assert scraper.ultimo_metodo == 'selenium'
    assert datos[0]['titulo'] == 'Desde Selenium'


def test_sitio_con_script_especifico_va_directo_a_selenium(navegador):
    scraper, sesion, _ = crear_scraper(respuesta('https://www.amazon.es/s?k=x', HTML_CON_PRODUCTOS), navegador)
    scraper.extraer('https://www.amazon.es/s?k=portatil')
    assert sesion.peticiones == []
    assert scraper.ultimo_metodo == 'selenium'


def test_modo_estatico_nunca_abre_el_navegador(navegador):
    url = 'https://spa.test/'
    scraper, _, aperturas = crear_scraper(respuesta(url, HTML_SIN_PRODUCTOS), navegador, modo='estatico')
    datos, _ = scraper.extraer(url)
    assert datos == []
    assert aperturas == []


def test_modo_selenium_no_hace_peticion_http(navegador):
    scraper, sesion, _ = crear_scraper(respuesta('https://t.test/', HTML_CON_PRODUCTOS), navegador, modo='selenium')
    scraper.extraer('https://t.test/')
    assert sesion.peticiones == []
    assert scraper.ultimo_metodo == 'selenium'


def test_modo_no_valido():
    with pytest.raises(ValueError):
        Scraper(modo='turbo', session=SesionFalsa(None))


def test_html_sin_charset_se_decodifica_bien(navegador):
    url = 'https://tienda.test/'
    r = respuesta(url, HTML_CON_PRODUCTOS, tipo='text/html')  # sin charset: requests asumiría ISO-8859-1
    scraper, _, _ = crear_scraper(r, navegador)
    datos, _ = scraper.extraer(url)
    assert datos[0]['titulo'] == 'Cafetera eléctrica'


def test_el_navegador_se_abre_una_vez_y_se_cierra(navegador):
    scraper, sesion, aperturas = crear_scraper(respuesta('https://spa.test/', HTML_SIN_PRODUCTOS), navegador)
    with scraper:
        scraper.extraer('https://spa.test/1')
        scraper.extraer('https://spa.test/2')
    assert aperturas == [True]
    assert navegador.cerrado
    assert sesion.cerrada


def test_cerrar_sin_haber_abierto_el_navegador(navegador):
    scraper, sesion, aperturas = crear_scraper(respuesta('https://t.test/', HTML_CON_PRODUCTOS), navegador)
    scraper.close()
    assert aperturas == []
    assert sesion.cerrada


def test_scrapear_pagina_universal_guarda_archivos(navegador, salida_temporal):
    url = 'https://tienda.test/'
    scraper, _, _ = crear_scraper(respuesta(url, HTML_CON_PRODUCTOS), navegador)

    datos = scraper.scrapear_pagina_universal(url, 'tienda_test')

    assert len(datos) == 2
    assert (salida_temporal / 'tienda_test.html').exists()
    assert (salida_temporal / 'tienda_test.csv').exists()
    exportado = json.loads((salida_temporal / 'tienda_test.json').read_text(encoding='utf-8'))
    assert exportado[0]['titulo'] == 'Cafetera eléctrica'
