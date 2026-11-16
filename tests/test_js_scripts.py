import shutil
import subprocess


import pytest

from js_scripts import EXTRACTORES_POR_SITIO, codigo_fuente, extractor_para_url, script_para

def test_todas_las_funciones_existen_en_scripts_js():
    codigo = codigo_fuente()
    exportadas = codigo[codigo.index('const WebScraperJS'):]
    for funcion in [f for _, f in EXTRACTORES_POR_SITIO] + ['removerOverlays']:
        assert f'function {funcion}(' in codigo
        assert funcion in exportadas


@pytest.mark.parametrize('url, esperado', [
    ('https://www.amazon.es/s?k=portatil', 'extraerAmazon'),
    ('https://www.pccomponentes.com/portatiles', 'extraerPcComponentes'),
    ('https://www.ebay.es/sch/i.html', 'extraerEbay'),
    ('https://es.aliexpress.com/w/x.html', 'extraerAliExpress'),
    ('https://miblog.wordpress.com/', 'extraerWordPress'),
    ('https://tienda.test/?q=amazon', None),  # solo cuenta el dominio
    ('https://books.toscrape.com/', None),
])
def test_extractor_para_url(url, esperado):
    assert extractor_para_url(url) == esperado


def test_script_para_rechaza_nombres_no_validos():
    with pytest.raises(ValueError):
        script_para('alert(1); x')


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js no está instalado')
def test_scripts_js_es_javascript_valido(tmp_path):
    # Selenium envuelve el código en una función; aquí se hace lo mismo para comprobar la sintaxis
    archivo = tmp_path / 'comprobacion.js'
    archivo.write_text(f"(function () {{\n{script_para('extraerAmazon')}\n}});\n", encoding='utf-8')
    resultado = subprocess.run(['node', '--check', str(archivo)], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
