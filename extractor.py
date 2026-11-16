"""
Extracción genérica de listados (productos, artículos...) a partir de HTML.

La usan los dos caminos del scraper:
  - el modo sin navegador (HTML descargado con requests), y
  - Selenium, sobre el HTML ya renderizado cuando no hay un script específico
    para el sitio o ese script no encuentra nada.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import MAX_ELEMENTOS, PARSER
from precios import buscar_precio_en_texto

CAMPOS = ('numero', 'titulo', 'precio', 'descripcion', 'enlace', 'imagen')

# Selectores de los contenedores de cada elemento, por orden de prioridad.
# Se usa el primero que encuentre algo.
SELECTORES_CONTENEDOR = (
    'a[data-product-name]',                               # PcComponentes
    '[data-asin].s-result-item',                          # Amazon
    '.s-item, .lvresult',                                 # eBay
    '.product-card, [class*="product-card" i]',           # e-commerce genérico
    'article',                                            # HTML5 (blogs, noticias)
    '[class*="product" i][class*="item" i]',
    'li[class*="product" i]',
    '.card, [class*="card" i]',
    'div[class*="post" i], div[class*="entry" i]',        # WordPress y similares
    'li[class*="item" i], div[class*="item" i], '
    'section[class*="product" i], section[class*="item" i]',
)

ATRIBUTOS_TITULO = ('data-product-name', 'data-title', 'data-name')
ETIQUETAS_TITULO = ('h2', 'h3', 'h1', 'h4', 'h5', 'h6')
SELECTOR_TITULO_POR_CLASE = '[class*="title" i], [class*="name" i], [class*="heading" i]'
ATRIBUTOS_PRECIO = ('data-product-price', 'data-price')
SELECTOR_PRECIO_POR_CLASE = (
    '[class*="price" i], [class*="precio" i], [class*="cost" i], [class*="amount" i]'
)
ATRIBUTOS_IMAGEN = ('src', 'data-src', 'data-lazy-src', 'data-original')
LONGITUD_MAX_DESCRIPCION = 100


def _texto(elemento) -> str:
    """Texto de un elemento con los espacios normalizados."""
    if elemento is None:
        return ''
    return ' '.join(elemento.get_text(' ').split())


def _atributo(elemento, nombre: str) -> str:
    valor = elemento.get(nombre) if elemento is not None else None
    if isinstance(valor, list):  # atributos multivaluados como class
        valor = ' '.join(valor)
    return ' '.join(str(valor).split()) if valor else ''


def _extraer_titulo(item) -> str:
    for atributo in ATRIBUTOS_TITULO:
        if valor := _atributo(item, atributo):
            return valor
    for etiqueta in ETIQUETAS_TITULO:
        texto = _texto(item.find(etiqueta))
        if len(texto) > 3:
            return texto
    if valor := _atributo(item.find('a', title=True), 'title'):
        return valor
    texto = _texto(item.select_one(SELECTOR_TITULO_POR_CLASE))
    if len(texto) > 3:
        return texto
    for atributo in ('title', 'aria-label'):
        if valor := _atributo(item, atributo):
            return valor
    return ''


def _extraer_precio(item) -> str:
    for atributo in ATRIBUTOS_PRECIO:
        if valor := _atributo(item, atributo):
            return valor
        if valor := _atributo(item.find(attrs={atributo: True}), atributo):
            return valor
    for elemento in item.select(SELECTOR_PRECIO_POR_CLASE):
        texto = _texto(elemento)
        if any(c.isdigit() for c in texto):
            return texto
    return buscar_precio_en_texto(_texto(item)) or ''


def _extraer_enlace(item, url_base: str) -> str:
    enlace = item if item.name == 'a' and item.get('href') else item.find('a', href=True)
    href = _atributo(enlace, 'href')
    if not href or href.startswith(('#', 'javascript:')):
        return ''
    return urljoin(url_base, href)


def _extraer_imagen(item, url_base: str) -> str:
    imagen = item.find('img')
    if imagen is None:
        return ''
    for atributo in ATRIBUTOS_IMAGEN:
        valor = _atributo(imagen, atributo)
        # Las imágenes con carga diferida suelen tener un "data:" de relleno en src
        if valor and not valor.startswith('data:'):
            return urljoin(url_base, valor)
    srcset = _atributo(imagen, 'srcset')
    if srcset:
        return urljoin(url_base, srcset.split(',')[0].split()[0])
    return ''


def extraer_item(item, url_base: str = '') -> dict | None:
    """Extrae los campos de un contenedor. Devuelve None si no tiene nada útil."""
    titulo = _extraer_titulo(item)
    precio = _extraer_precio(item)
    descripcion = _texto(item.find('p'))[:LONGITUD_MAX_DESCRIPCION]
    if not (titulo or precio or descripcion):
        return None
    return {
        'titulo': titulo,
        'precio': precio,
        'descripcion': descripcion,
        'enlace': _extraer_enlace(item, url_base),
        'imagen': _extraer_imagen(item, url_base),
    }


def normalizar_items(items) -> list[dict]:
    """
    Deja todos los elementos con las mismas claves, en el mismo orden, con 'N/A'
    en los campos vacíos, numerados desde 1 y sin duplicados exactos.
    """
    resultado, vistos = [], set()
    for item in items or []:
        dato = {}
        for campo in CAMPOS[1:]:
            valor = item.get(campo)
            valor = ' '.join(str(valor).split()) if valor is not None else ''
            dato[campo] = valor or 'N/A'
        clave = tuple(dato.values())
        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append({'numero': len(resultado) + 1, **dato})
    return resultado


def extraer_productos_html(html, url_base: str = '', max_items: int = MAX_ELEMENTOS) -> list[dict]:
    """
    Busca elementos repetidos (productos, artículos...) en un HTML.

    Prueba los selectores de SELECTORES_CONTENEDOR en orden y se queda con el
    primero del que se obtiene algún elemento con datos (si un selector solo
    encuentra contenedores vacíos, se pasa al siguiente).

    Args:
        html: HTML de la página (str o bytes).
        url_base: URL de la página, para convertir enlaces relativos en absolutos.
        max_items: número máximo de elementos a devolver.
    """
    soup = BeautifulSoup(html, PARSER)
    for selector in SELECTORES_CONTENEDOR:
        datos = []
        for contenedor in soup.select(selector):
            dato = extraer_item(contenedor, url_base)
            if dato:
                datos.append(dato)
                if len(datos) >= max_items:
                    break
        if datos:
            return normalizar_items(datos)
    return []
