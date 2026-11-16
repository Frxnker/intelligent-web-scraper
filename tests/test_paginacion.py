from paginacion import Paginador, scrapear_con_paginacion


def test_generar_urls_paginadas():
    assert Paginador.generar_urls_paginadas('https://t.test/lista?orden=precio', 3) == [
        'https://t.test/lista?orden=precio',
        'https://t.test/lista?orden=precio&page=2',
        'https://t.test/lista?orden=precio&page=3',
    ]


def test_generar_urls_paginadas_continua_desde_la_pagina_actual():
    assert Paginador.generar_urls_paginadas('https://t.test/?p=3', 3) == [
        'https://t.test/?p=3', 'https://t.test/?p=4', 'https://t.test/?p=5',
    ]
    assert Paginador.generar_urls_paginadas('https://t.test/', 0) == []


class ScraperPaginas:
    def __init__(self, paginas):
        self.paginas = paginas
        self.urls = []

    def scrapear_pagina_universal(self, url, nombre):
        self.urls.append(url)
        return self.paginas[len(self.urls) - 1] if len(self.urls) <= len(self.paginas) else []


def item(n):
    return {'titulo': f'Producto {n}', 'precio': '1 €', 'enlace': f'https://t.test/p/{n}'}


def test_paginacion_acumula_y_elimina_repetidos():
    scraper = ScraperPaginas([[item(1), item(2)], [item(2), item(3)], [item(4)]])
    datos = scrapear_con_paginacion(scraper, 'https://t.test/', max_paginas=3, delay=0)
    assert [d['titulo'] for d in datos] == ['Producto 1', 'Producto 2', 'Producto 3', 'Producto 4']


def test_paginacion_se_detiene_si_el_sitio_ignora_el_parametro():
    misma_pagina = [item(1), item(2)]
    scraper = ScraperPaginas([misma_pagina, misma_pagina, misma_pagina])
    datos = scrapear_con_paginacion(scraper, 'https://t.test/', max_paginas=3, delay=0)
    assert len(datos) == 2
    assert len(scraper.urls) == 2


def test_paginacion_se_detiene_sin_datos():
    scraper = ScraperPaginas([[item(1)], []])
    datos = scrapear_con_paginacion(scraper, 'https://t.test/', max_paginas=5, delay=0)
    assert len(datos) == 1
    assert len(scraper.urls) == 2
