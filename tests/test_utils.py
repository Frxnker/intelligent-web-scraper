import csv


import pytest

from utils import export_to_csv, nombre_desde_url, normalizar_url, truncar

@pytest.mark.parametrize('entrada, esperado', [
    ('https://tienda.test/a?b=1', 'https://tienda.test/a?b=1'),
    ('http://tienda.test', 'http://tienda.test'),
    ('tienda.test/categoria', 'https://tienda.test/categoria'),
    ('  www.tienda.test  ', 'https://www.tienda.test'),
    ('httpbin.org/get', 'https://httpbin.org/get'),  # antes no se le añadía el esquema
    ('localhost:8000', 'https://localhost:8000'),
    ('', None),
    ('   ', None),
    ('ftp://tienda.test', None),
    ('https://', None),
    ('https://[::1', None),
    ('no es una url', None),
])
def test_normalizar_url(entrada, esperado):
    assert normalizar_url(entrada) == esperado


@pytest.mark.parametrize('url, esperado', [
    ('https://www.amazon.es/s?k=x', 'amazon_es'),
    ('https://books.toscrape.com/', 'books_toscrape_com'),
    ('http://localhost:8000/x', 'localhost_8000'),  # ':' no es válido en nombres de archivo en Windows
    ('https://WWW.Tienda.Test', 'tienda_test'),
    ('https://usuario:clave@tienda.test/', 'tienda_test'),
])
def test_nombre_desde_url(url, esperado):
    assert nombre_desde_url(url) == esperado


def test_export_to_csv_con_claves_distintas(salida_temporal):
    ruta = export_to_csv([{'titulo': 'A', 'precio': '1 €'}, {'titulo': 'B', 'extra': 'x'}], 'prueba.csv')
    with open(ruta, encoding='utf-8', newline='') as f:
        filas = list(csv.DictReader(f))
    assert filas[1] == {'titulo': 'B', 'precio': 'N/A', 'extra': 'x'}
    assert ruta.parent == salida_temporal


def test_truncar():
    assert truncar('corto', 10) == 'corto'
    assert truncar('x' * 12, 10) == 'x' * 10 + '...'
