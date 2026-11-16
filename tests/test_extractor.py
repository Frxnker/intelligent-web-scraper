from extractor import CAMPOS, extraer_productos_html, normalizar_items

URL = 'https://tienda.test/categoria/portatiles?page=1'

LISTADO_TIENDA = '''
<html><body>
  <nav><ul><li class="nav-item"><a href="/">Inicio</a></li></ul></nav>
  <div class="product-card">
    <a href="/p/legion-5"><img src="data:image/gif;base64,R0lGOD" data-src="/img/legion.jpg"></a>
    <h2>Lenovo Legion 5</h2>
    <p>Portátil gaming con Ryzen 7 y RTX 3060.</p>
    <span class="price">1.299,99&nbsp;€</span>
  </div>
  <div class="product-card">
    <a href="https://otra.test/p/2"><img src="https://cdn.test/2.jpg"></a>
    <h2>ASUS TUF A15</h2>
    <span class="product-price">999 €</span>
  </div>
</body></html>
'''


def test_listado_de_tienda():
    datos = extraer_productos_html(LISTADO_TIENDA, URL)

    assert [d['titulo'] for d in datos] == ['Lenovo Legion 5', 'ASUS TUF A15']
    primero = datos[0]
    assert list(primero) == list(CAMPOS)
    assert primero['numero'] == 1
    assert primero['precio'] == '1.299,99 €'
    assert primero['descripcion'] == 'Portátil gaming con Ryzen 7 y RTX 3060.'
    assert primero['enlace'] == 'https://tienda.test/p/legion-5'  # relativo -> absoluto
    assert primero['imagen'] == 'https://tienda.test/img/legion.jpg'  # ignora el placeholder data:
    assert datos[1]['enlace'] == 'https://otra.test/p/2'
    assert datos[1]['descripcion'] == 'N/A'


def test_atributos_data_de_producto():
    html = '''
    <a data-product-name="Monitor LG 27GL850" data-product-price="349.90" href="/monitor-lg">
      <img srcset="/img/lg-300.jpg 300w, /img/lg-600.jpg 600w">
    </a>
    <a data-product-name="Teclado Keychron K2" data-product-price="89" href="/keychron"></a>
    '''
    datos = extraer_productos_html(html, 'https://tienda.test/')
    assert datos[0]['titulo'] == 'Monitor LG 27GL850'
    assert datos[0]['precio'] == '349.90'
    assert datos[0]['enlace'] == 'https://tienda.test/monitor-lg'
    assert datos[0]['imagen'] == 'https://tienda.test/img/lg-300.jpg'
    assert datos[1]['precio'] == '89'


def test_precio_buscado_en_el_texto():
    html = '''
    <article><h3>Libro de Python</h3><div>Solo hoy por $24.99 con envío</div></article>
    <article><h3>Libro de SQL</h3><div>Sin precio</div></article>
    '''
    datos = extraer_productos_html(html)
    assert datos[0]['precio'] == '$24.99'
    assert datos[1]['precio'] == 'N/A'


def test_blog_con_articulos():
    texto_largo = 'Lorem ipsum ' * 30
    html = f'''
    <article><h2><a href="/post-1">Primer artículo</a></h2><p>{texto_largo}</p></article>
    <article><h2><a href="/post-2">Segundo artículo</a></h2><p>Resumen corto</p></article>
    '''
    datos = extraer_productos_html(html, 'https://blog.test/')
    assert [d['titulo'] for d in datos] == ['Primer artículo', 'Segundo artículo']
    assert len(datos[0]['descripcion']) == 100
    assert datos[1]['enlace'] == 'https://blog.test/post-2'


def test_si_un_selector_solo_tiene_contenedores_vacios_se_prueba_el_siguiente():
    html = '''
    <div class="card"></div><div class="card"><span></span></div>
    <div class="item"><h3>Producto real</h3><span class="price">10 €</span></div>
    '''
    datos = extraer_productos_html(html)
    assert [d['titulo'] for d in datos] == ['Producto real']


def test_pagina_sin_estructura():
    assert extraer_productos_html('<html><body><p>Hola</p><a href="/x">x</a></body></html>') == []
    assert extraer_productos_html('') == []


def test_limite_de_elementos():
    html = ''.join(f'<article><h2>Artículo número {i}</h2></article>' for i in range(30))
    assert len(extraer_productos_html(html, max_items=10)) == 10


def test_acepta_bytes():
    html = '<meta charset="utf-8"><article><h2>Cafetera eléctrica</h2></article>'.encode('utf-8')
    assert extraer_productos_html(html)[0]['titulo'] == 'Cafetera eléctrica'


def test_normalizar_items():
    items = [
        {'titulo': '  Uno  ', 'precio': '1 €', 'enlace': None},
        {'titulo': 'Uno', 'precio': '1 €'},  # duplicado exacto tras normalizar
        {'titulo': 'Dos', 'precio': '', 'extra': 'se ignora'},
    ]
    assert normalizar_items(items) == [
        {'numero': 1, 'titulo': 'Uno', 'precio': '1 €', 'descripcion': 'N/A', 'enlace': 'N/A', 'imagen': 'N/A'},
        {'numero': 2, 'titulo': 'Dos', 'precio': 'N/A', 'descripcion': 'N/A', 'enlace': 'N/A', 'imagen': 'N/A'},
    ]
    assert normalizar_items(None) == []
