import pytest

from comparador import ComparadorPrecios
from precios import (
    buscar_precio_en_texto,
    extraer_moneda,
    extraer_precio_numerico,
    formatear_precio,
    parsear_precio,
)


@pytest.mark.parametrize('texto, valor, moneda', [
    # Formato español: punto de miles, coma decimal
    ('1.299,99 €', 1299.99, 'EUR'),
    ('1.299,99€', 1299.99, 'EUR'),
    ('€1.299,99', 1299.99, 'EUR'),
    ('€ 1.299,99', 1299.99, 'EUR'),
    ('1.299.999,50 €', 1299999.50, 'EUR'),
    ('0,99 €', 0.99, 'EUR'),
    ('12,5', 12.5, None),
    ('1.299', 1299.0, None),  # un solo separador seguido de 3 cifras = miles
    ('1.000.000', 1000000.0, None),
    # Formato inglés: coma de miles, punto decimal
    ('1,299.99', 1299.99, None),
    ('$1,299.99', 1299.99, 'USD'),
    ('$ 1,299.99', 1299.99, 'USD'),
    ('1,299.99 $', 1299.99, 'USD'),
    ('1,299,999.50', 1299999.50, None),
    ('12.50', 12.5, None),
    ('£12.50', 12.5, 'GBP'),
    ('12.50 £', 12.5, 'GBP'),
    ('¥1,000', 1000.0, 'JPY'),
    ('1000 ¥', 1000.0, 'JPY'),
    # Sin decimales
    ('1299', 1299.0, None),
    ('1299 €', 1299.0, 'EUR'),
    ('€1299', 1299.0, 'EUR'),
    ('$5', 5.0, 'USD'),
    # Espacios (normales, duros y estrechos) alrededor y como separador de miles
    ('  1.299,99  €  ', 1299.99, 'EUR'),
    ('1 299,99 €', 1299.99, 'EUR'),
    ('1 299,99 €', 1299.99, 'EUR'),
    ('1 299,99 €', 1299.99, 'EUR'),
    ('$ 1,299.99', 1299.99, 'USD'),
    # Códigos ISO
    ('EUR 1.299,99', 1299.99, 'EUR'),
    ('1.299,99 eur', 1299.99, 'EUR'),
    ('USD 10', 10.0, 'USD'),
    ('GBP12.50', 12.5, 'GBP'),
    ('1,000 JPY', 1000.0, 'JPY'),
    # Texto alrededor
    ('Desde 19,99 €', 19.99, 'EUR'),
    ('-20% 1.299,99 €', 1299.99, 'EUR'),
    ('3 x 19,99€', 19.99, 'EUR'),
    ('Ahorra 15% hoy: 85,00', 85.0, None),
    ('Precio: 12,50.', 12.5, None),
])
def test_parsear_precio(texto, valor, moneda):
    resultado_valor, resultado_moneda = parsear_precio(texto)
    assert resultado_valor == pytest.approx(valor)
    assert isinstance(resultado_valor, float)
    assert resultado_moneda == moneda


@pytest.mark.parametrize('texto', [None, '', '   ', 'N/A', 'n/a', 'Gratis', '€', '20%', True])
def test_parsear_precio_sin_numero(texto):
    assert parsear_precio(texto) == (None, None)


def test_parsear_precio_acepta_numeros():
    assert parsear_precio(1299) == (1299.0, None)
    assert parsear_precio(12.5) == (12.5, None)
    assert parsear_precio(float('nan')) == (None, None)


def test_caso_del_bug_original():
    # Antes "1.299,99 €" se convertía en 1.299
    assert extraer_precio_numerico('1.299,99 €') == pytest.approx(1299.99)
    assert ComparadorPrecios.extraer_precio_numerico('1.299,99 €') == pytest.approx(1299.99)


def test_extraer_precio_numerico_y_moneda():
    assert extraer_precio_numerico('£12.50') == pytest.approx(12.5)
    assert extraer_precio_numerico('sin precio') is None
    assert extraer_moneda('£12.50') == 'GBP'
    assert extraer_moneda('1299') is None
    assert ComparadorPrecios.extraer_moneda('$3') == 'USD'


def test_buscar_precio_en_texto():
    assert buscar_precio_en_texto('Portátil Lenovo 16GB 1.299,99 € envío gratis') == '1.299,99 €'
    assert buscar_precio_en_texto('Oferta: $1,299.99!') == '$1,299.99'
    assert buscar_precio_en_texto('Sin precio, solo 3 unidades') is None
    assert buscar_precio_en_texto('') is None


def test_formatear_precio():
    assert formatear_precio(1299.99, 'EUR') == '1299.99 €'
    assert formatear_precio(5, 'USD') == '5.00 $'
    assert formatear_precio(10, None) == '10.00'
    assert formatear_precio(10, 'CHF') == '10.00 CHF'
    assert formatear_precio(None, None, 'Consultar') == 'Consultar'
    assert formatear_precio(None) == 'N/A'
