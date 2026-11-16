"""
Parseo de precios escritos como texto libre.

Formatos admitidos:
    "1.299,99 €"   formato español (punto de miles, coma decimal)
    "$1,299.99"    formato inglés (coma de miles, punto decimal)
    "1299", "12,5", "1 299,99 €" (espacio o espacio duro como separador de miles)
    Símbolo delante o detrás, con o sin espacio: €, $, £, ¥
    Códigos ISO delante o detrás: EUR, USD, GBP, JPY

Regla para un único separador ("1.299" o "12,50"): si va seguido de exactamente
tres dígitos se considera separador de miles; en otro caso, decimal. Por eso
"1.299" se interpreta como 1299 y no como 1,299.
"""

from __future__ import annotations

import math
import re

SIMBOLOS_MONEDA = {'€': 'EUR', '$': 'USD', '£': 'GBP', '¥': 'JPY'}
CODIGOS_MONEDA = ('EUR', 'USD', 'GBP', 'JPY')
SIMBOLO_POR_CODIGO = {codigo: simbolo for simbolo, codigo in SIMBOLOS_MONEDA.items()}

_MONEDA = r"[€$£¥]|(?<![A-Za-z])(?:" + "|".join(CODIGOS_MONEDA) + r")(?![A-Za-z])"
# Un número es, o bien grupos de tres cifras separados por espacios
# ("1 299,99"), o bien cifras separadas por puntos o comas ("1.299,99").
_NUMERO = r"(?<!\d)(?:\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)*)"

_RE_PRECIO_CON_MONEDA = re.compile(
    rf"(?P<m1>{_MONEDA})\s*(?P<n1>{_NUMERO})|(?P<n2>{_NUMERO})\s*(?P<m2>{_MONEDA})",
    re.IGNORECASE,
)
# Número suelto que no sea un porcentaje ("-20%") ni parte de otro número
_RE_NUMERO = re.compile(rf"(?P<n>{_NUMERO})(?!\d|[.,]\d|\s*%)")
_RE_MONEDA = re.compile(_MONEDA, re.IGNORECASE)
_RE_ESPACIOS = re.compile(r"[\s  ]")


def _codigo_moneda(marca: str | None) -> str | None:
    if not marca:
        return None
    return SIMBOLOS_MONEDA.get(marca, marca.upper())


def _numero_a_float(numero: str) -> float | None:
    """Convierte "1.299,99", "1,299.99", "1 299" ... a float."""
    texto = _RE_ESPACIOS.sub('', numero)
    ultimo_punto = texto.rfind('.')
    ultima_coma = texto.rfind(',')

    if ultimo_punto != -1 and ultima_coma != -1:
        # Hay los dos separadores: el que aparece el último es el decimal
        decimal, miles = ('.', ',') if ultimo_punto > ultima_coma else (',', '.')
        texto = texto.replace(miles, '').replace(decimal, '.')
    elif ultimo_punto != -1 or ultima_coma != -1:
        separador = '.' if ultimo_punto != -1 else ','
        partes = texto.split(separador)
        es_miles = len(partes) > 2 or (len(partes[1]) == 3 and partes[0] != '0')
        texto = ''.join(partes) if es_miles else f"{partes[0]}.{partes[1]}"

    try:
        return float(texto)
    except ValueError:
        return None


def parsear_precio(texto) -> tuple[float | None, str | None]:
    """
    Extrae el importe y la moneda de un texto.

    Returns:
        (valor, moneda): valor es float o None si no hay un número reconocible;
        moneda es un código ISO ('EUR', 'USD', 'GBP', 'JPY') o None si no aparece.
    """
    if texto is None or isinstance(texto, bool):
        return None, None
    if isinstance(texto, (int, float)):
        return (float(texto) if math.isfinite(texto) else None), None

    texto = str(texto).strip()
    if not texto or texto.upper() == 'N/A':
        return None, None

    # Preferimos el número pegado a un símbolo de moneda: en "-20% 1.299,99 €"
    # el precio es 1.299,99 y no 20.
    coincidencia = _RE_PRECIO_CON_MONEDA.search(texto)
    if coincidencia:
        numero = coincidencia.group('n1') or coincidencia.group('n2')
        moneda = coincidencia.group('m1') or coincidencia.group('m2')
        return _numero_a_float(numero), _codigo_moneda(moneda)

    coincidencia = _RE_NUMERO.search(texto)
    if not coincidencia:
        return None, None
    moneda = _RE_MONEDA.search(texto)
    return _numero_a_float(coincidencia.group('n')), _codigo_moneda(moneda.group(0) if moneda else None)


def extraer_precio_numerico(texto) -> float | None:
    """Devuelve el importe como float, o None si no se puede interpretar."""
    return parsear_precio(texto)[0]


def extraer_moneda(texto) -> str | None:
    """Devuelve el código ISO de la moneda del precio, o None."""
    return parsear_precio(texto)[1]


def buscar_precio_en_texto(texto: str) -> str | None:
    """Devuelve el fragmento de texto que parece un precio con moneda ("1.299,99 €")."""
    if not texto:
        return None
    coincidencia = _RE_PRECIO_CON_MONEDA.search(texto)
    return coincidencia.group(0).strip() if coincidencia else None


def formatear_precio(valor: float | None, moneda: str | None = None, texto_original: str | None = None) -> str:
    """Formatea un precio para mostrarlo por consola."""
    if valor is None:
        return texto_original or 'N/A'
    simbolo = SIMBOLO_POR_CODIGO.get(moneda, moneda) if moneda else ''
    return f"{valor:.2f} {simbolo}".strip()
