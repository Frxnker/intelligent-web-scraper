import pytest


from programador import Programador

def test_programador_guarda_y_carga_tareas(tmp_path):
    archivo = tmp_path / 'tareas.json'
    prog = Programador(archivo)
    assert prog.agregar_tarea('https://t.test/', 'precios', 30, 2)
    assert not prog.agregar_tarea('https://t.test/otra', 'precios')  # nombre repetido

    otro = Programador(archivo)
    otro.cargar_tareas()
    assert [(t['nombre'], t['intervalo'], t['max_paginas']) for t in otro.tareas] == [('precios', 30, 2)]

    assert not otro.eliminar_tarea('no-existe')
    assert otro.eliminar_tarea('precios')
    assert otro.tareas == []


def test_programador_valida_el_intervalo(tmp_path):
    with pytest.raises(ValueError):
        Programador(tmp_path / 't.json').agregar_tarea('https://t.test/', 'x', 0)


def test_programador_ignora_un_json_corrupto(tmp_path):
    archivo = tmp_path / 'tareas.json'
    archivo.write_text('{no es json', encoding='utf-8')
    prog = Programador(archivo)
    prog.cargar_tareas()
    assert prog.tareas == []
