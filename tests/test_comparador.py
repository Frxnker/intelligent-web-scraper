import pytest

from comparador import ComparadorPrecios, comparar_sitios


def producto(titulo, precio='N/A', enlace='N/A'):
    return {'titulo': titulo, 'precio': precio, 'enlace': enlace}


# ---------------------------------------------------------------------------
# Similitud de títulos
# ---------------------------------------------------------------------------

def test_limpiar_titulo():
    assert ComparadorPrecios.limpiar_titulo('  Portátil LENOVO  Legion-5, 16GB!  ') == 'portátil lenovo legion 5 16gb'
    assert ComparadorPrecios.limpiar_titulo(None) == ''


def test_titulos_identicos():
    assert ComparadorPrecios.similitud_titulos('Lenovo Legion 5', 'Lenovo Legion 5') == 1.0


def test_similitud_ignora_mayusculas_y_puntuacion():
    assert ComparadorPrecios.similitud_titulos('Portátil Lenovo Legion-5', 'portátil lenovo, legion 5') == 1.0


def test_titulos_parecidos_superan_el_umbral():
    similitud = ComparadorPrecios.similitud_titulos(
        'Lenovo Legion 5 15ACH6H Ryzen 7 16GB',
        'Lenovo Legion 5 15ACH6 Ryzen 7 16 GB RAM',
    )
    assert similitud > 0.8


def test_titulos_distintos_quedan_por_debajo():
    similitud = ComparadorPrecios.similitud_titulos('Lenovo Legion 5', 'Cafetera Nespresso Vertuo')
    assert similitud < 0.5


@pytest.mark.parametrize('t1, t2', [('', ''), (None, 'Algo'), ('Algo', ''), ('!!!', '???')])
def test_titulos_vacios_no_se_parecen(t1, t2):
    assert ComparadorPrecios.similitud_titulos(t1, t2) == 0.0


def test_similitud_en_rango():
    for t1, t2 in [('abc', 'abd'), ('Monitor 27"', 'Monitor 24"'), ('a', 'b')]:
        assert 0.0 <= ComparadorPrecios.similitud_titulos(t1, t2) <= 1.0


# ---------------------------------------------------------------------------
# Comparación de listas
# ---------------------------------------------------------------------------

def test_comparar_listas_empareja_y_compara_precios_en_distintos_formatos():
    sitio1 = [producto('Lenovo Legion 5 Ryzen 7', '1.299,99 €'), producto('Cafetera Nespresso', '99 €')]
    sitio2 = [producto('Cafetera Nespresso Vertuo', '89,50 €'), producto('LENOVO Legion 5 - Ryzen 7', '1,199.99 €')]

    coincidencias = ComparadorPrecios.comparar_listas(sitio1, sitio2, 0.6)

    assert len(coincidencias) == 2
    legion, cafetera = coincidencias
    assert legion['producto2'] is sitio2[1]
    assert legion['precio1'] == pytest.approx(1299.99)
    assert legion['precio2'] == pytest.approx(1199.99)
    assert legion['diferencia'] == pytest.approx(100.0)
    assert legion['porcentaje_diferencia'] == pytest.approx(100 / 1199.99 * 100)
    assert legion['mas_barato'] == 'sitio2'
    assert legion['moneda1'] == legion['moneda2'] == 'EUR'
    assert cafetera['producto2'] is sitio2[0]
    assert cafetera['mas_barato'] == 'sitio2'


def test_precios_iguales():
    coincidencias = ComparadorPrecios.comparar_listas([producto('Ratón Logitech', '20 €')],
                                                      [producto('Ratón Logitech', '20,00€')])
    assert coincidencias[0]['mas_barato'] == 'igual'
    assert coincidencias[0]['diferencia'] == 0


def test_monedas_distintas_no_se_comparan():
    coincidencias = ComparadorPrecios.comparar_listas([producto('Teclado mecánico', '50 €')],
                                                      [producto('Teclado mecánico', '$50')])
    assert len(coincidencias) == 1
    assert coincidencias[0]['diferencia'] is None
    assert coincidencias[0]['mas_barato'] is None


def test_precio_cero_no_divide_por_cero():
    coincidencias = ComparadorPrecios.comparar_listas([producto('Juego gratis', '0 €')],
                                                      [producto('Juego gratis', '5 €')])
    assert coincidencias[0]['mas_barato'] == 'sitio1'
    assert coincidencias[0]['porcentaje_diferencia'] is None


def test_sin_coincidencias_por_debajo_del_umbral():
    assert ComparadorPrecios.comparar_listas([producto('Lenovo Legion 5')], [producto('Cafetera')], 0.7) == []


def test_productos_sin_titulo_no_se_emparejan():
    assert ComparadorPrecios.comparar_listas([producto('N/A', '10 €')], [producto('N/A', '12 €')]) == []


def test_umbral_no_valido():
    with pytest.raises(ValueError):
        ComparadorPrecios.comparar_listas([], [], 1.5)


def test_mostrar_comparacion(capsys):
    coincidencias = ComparadorPrecios.comparar_listas(
        [producto('Monitor LG 27', '199,99 €'), producto('Teclado mecánico', '50 €')],
        [producto('Monitor LG 27', '219,99 €'), producto('Teclado mecánico', '$50')],
    )
    ComparadorPrecios.mostrar_comparacion(coincidencias, 'Tienda A', 'Tienda B')
    salida = capsys.readouterr().out
    assert '199.99 €' in salida
    assert 'Diferencia: 20.00 €' in salida
    assert 'Monedas distintas' in salida


class ScraperFalso:
    """Imita la interfaz de Scraper sin acceder a la red."""

    instancias = []

    def __init__(self, headless=True):
        self.cerrado = False
        ScraperFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cerrado = True

    def scrapear_pagina_universal(self, url, nombre):
        if 'tienda-a' in url:
            return [producto('Auriculares Sony WH-1000XM5', '379,00 €')]
        return [producto('Sony WH-1000XM5 Auriculares', '349,00 €')]


def test_comparar_sitios_usa_un_solo_scraper_y_lo_cierra():
    ScraperFalso.instancias = []
    coincidencias = comparar_sitios('https://tienda-a.test/', 'https://tienda-b.test/', ScraperFalso, umbral=0.5)
    assert len(ScraperFalso.instancias) == 1
    assert ScraperFalso.instancias[0].cerrado
    assert coincidencias[0]['mas_barato'] == 'sitio2'
