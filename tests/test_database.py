import sqlite3

import pytest

from database import SCHEMA_PATH, SCHEMA_VERSION, ScraperDB


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / 'scraper.db'


@pytest.fixture
def db(db_path):
    with ScraperDB(db_path) as base:
        yield base


def producto(titulo='Portátil Lenovo', precio='1.299,99 €', enlace='https://tienda.test/p/1', **extra):
    return {'titulo': titulo, 'precio': precio, 'enlace': enlace,
            'descripcion': 'N/A', 'imagen': 'N/A', **extra}


def columnas(conn, tabla):
    return {fila[1]: fila[2] for fila in conn.execute(f'PRAGMA table_info({tabla})')}


# ---------------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------------

def test_el_esquema_coincide_con_schema_sql(db_path, tmp_path):
    ScraperDB(db_path).cerrar()

    referencia = sqlite3.connect(tmp_path / 'referencia.db')
    referencia.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
    creada = sqlite3.connect(db_path)

    consulta = "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    assert creada.execute(consulta).fetchall() == referencia.execute(consulta).fetchall()
    assert creada.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION
    referencia.close()
    creada.close()


def test_precio_es_real_y_moneda_columna_aparte(db):
    for tabla in ('productos', 'historial_precios'):
        tipos = columnas(db.conn, tabla)
        assert tipos['precio'] == 'REAL'
        assert tipos['moneda'] == 'TEXT'
        assert tipos['precio_texto'] == 'TEXT'


def test_claves_foraneas_activadas(db):
    assert db.conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Inserción
# ---------------------------------------------------------------------------

def test_insertar_producto_guarda_precio_numerico_moneda_y_texto(db):
    assert db.insertar_producto(producto(), 'tienda')

    [guardado] = db.obtener_productos()
    assert guardado['precio'] == pytest.approx(1299.99)
    assert guardado['moneda'] == 'EUR'
    assert guardado['precio_texto'] == '1.299,99 €'
    assert guardado['descripcion'] is None  # 'N/A' se guarda como NULL
    assert guardado['sitio'] == 'tienda'

    [historial] = db.obtener_historial_precios(guardado['id'])
    assert historial['precio'] == pytest.approx(1299.99)
    assert historial['moneda'] == 'EUR'
    assert historial['precio_texto'] == '1.299,99 €'


def test_mismo_enlace_actualiza_y_amplia_historial(db):
    db.insertar_producto(producto(precio='1.299,99 €'), 'tienda')
    db.insertar_producto(producto(titulo='Portátil Lenovo (rebajado)', precio='1.199,00 €'), 'tienda')

    [guardado] = db.obtener_productos()
    assert guardado['titulo'] == 'Portátil Lenovo (rebajado)'
    assert guardado['precio'] == pytest.approx(1199.0)

    historial = db.obtener_historial_precios(guardado['id'])
    assert [h['precio'] for h in historial] == pytest.approx([1199.0, 1299.99])


def test_productos_sin_enlace(db):
    # Antes solo se podía guardar uno (enlace 'N/A' + UNIQUE + INSERT OR IGNORE)
    db.insertar_producto(producto(titulo='Producto A', enlace='N/A'), 'tienda')
    db.insertar_producto(producto(titulo='Producto B', enlace='N/A'), 'tienda')
    # Mismo título y sitio sin enlace: se actualiza en lugar de duplicarse
    db.insertar_producto(producto(titulo='Producto A', enlace='N/A', precio='10 €'), 'tienda')

    productos = {p['titulo']: p for p in db.obtener_productos()}
    assert set(productos) == {'Producto A', 'Producto B'}
    assert productos['Producto A']['enlace'] is None
    assert productos['Producto A']['precio'] == pytest.approx(10.0)


def test_producto_sin_precio_no_genera_historial(db):
    db.insertar_producto(producto(precio='N/A'))
    [guardado] = db.obtener_productos()
    assert guardado['precio'] is None
    assert guardado['moneda'] is None
    assert guardado['precio_texto'] is None
    assert db.obtener_historial_precios(guardado['id']) == []


def test_precio_no_interpretable_conserva_el_texto(db):
    db.insertar_producto(producto(precio='Consultar'))
    [guardado] = db.obtener_productos()
    assert guardado['precio'] is None
    assert guardado['precio_texto'] == 'Consultar'


def test_insertar_productos_bulk(db):
    productos = [
        producto(titulo='Uno', enlace='https://t.test/1', precio='$10.50'),
        producto(titulo='Dos', enlace='https://t.test/2', precio='£3'),
        producto(titulo='Tres', enlace='https://t.test/3', precio='N/A'),
    ]
    assert db.insertar_productos_bulk(productos, 'tienda') == 3

    por_titulo = {p['titulo']: p for p in db.obtener_productos()}
    assert (por_titulo['Uno']['precio'], por_titulo['Uno']['moneda']) == (10.5, 'USD')
    assert (por_titulo['Dos']['precio'], por_titulo['Dos']['moneda']) == (3.0, 'GBP')


def test_titulo_vacio_se_guarda_como_na(db):
    db.insertar_producto({'precio': '5 €', 'enlace': 'https://t.test/x'})
    assert db.obtener_productos()[0]['titulo'] == 'N/A'


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def test_obtener_productos_filtra_por_sitio_y_limita(db):
    db.insertar_productos_bulk([producto(titulo=f'A{i}', enlace=f'https://a.test/{i}') for i in range(5)], 'a')
    db.insertar_productos_bulk([producto(titulo='B', enlace='https://b.test/1')], 'b')

    assert len(db.obtener_productos()) == 6
    assert len(db.obtener_productos(limite=2)) == 2
    assert [p['titulo'] for p in db.obtener_productos('b')] == ['B']
    with pytest.raises(ValueError):
        db.obtener_productos(limite=0)


def test_buscar_productos_escapa_comodines(db):
    db.insertar_productos_bulk([
        producto(titulo='Cargador 100% original', enlace='https://t.test/1'),
        producto(titulo='Cargador 1000 W', enlace='https://t.test/2'),
        producto(titulo='Cable_USB', enlace='https://t.test/3'),
        producto(titulo='Cable-USB', enlace='https://t.test/4'),
    ])
    assert [p['titulo'] for p in db.buscar_productos('100%')] == ['Cargador 100% original']
    assert [p['titulo'] for p in db.buscar_productos('cable_')] == ['Cable_USB']
    assert len(db.buscar_productos('cargador')) == 2


def test_estadisticas_y_jobs(db):
    db.insertar_productos_bulk([producto(titulo='A', enlace='https://a.test/1'),
                                producto(titulo='B', enlace='https://a.test/2')], 'a')
    db.insertar_producto(producto(titulo='C', enlace='https://b.test/1'), 'b')
    db.registrar_job('https://a.test', 'a', 2, duracion=1.5)

    stats = db.obtener_estadisticas()
    assert stats == {'total_productos': 3, 'total_jobs': 1, 'por_sitio': {'a': 2, 'b': 1}}
    job = db.conn.execute('SELECT * FROM scraping_jobs').fetchone()
    assert (job['url'], job['estado'], job['duracion_segundos']) == ('https://a.test', 'completado', 1.5)


def test_limpiar_datos_antiguos_borra_tambien_el_historial(db):
    db.insertar_producto(producto(titulo='Viejo', enlace='https://t.test/viejo'))
    db.insertar_producto(producto(titulo='Nuevo', enlace='https://t.test/nuevo'))
    db.conn.execute("UPDATE productos SET fecha_scraping = datetime('now', '-40 days') WHERE titulo = 'Viejo'")
    db.conn.commit()

    assert db.limpiar_datos_antiguos(30) == 1
    assert [p['titulo'] for p in db.obtener_productos()] == ['Nuevo']
    huerfanos = db.conn.execute(
        'SELECT COUNT(*) FROM historial_precios WHERE producto_id NOT IN (SELECT id FROM productos)'
    ).fetchone()[0]
    assert huerfanos == 0
    with pytest.raises(ValueError):
        db.limpiar_datos_antiguos(-1)


def test_context_manager_cierra_la_conexion(db_path):
    with ScraperDB(db_path) as base:
        base.insertar_producto(producto())
    assert base.conn is None
    with ScraperDB(db_path) as base:
        assert len(base.obtener_productos()) == 1


# ---------------------------------------------------------------------------
# Migración desde el formato anterior (precio TEXT)
# ---------------------------------------------------------------------------

ESQUEMA_ANTIGUO = '''
CREATE TABLE productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    precio TEXT,
    descripcion TEXT,
    enlace TEXT UNIQUE,
    imagen TEXT,
    sitio TEXT,
    categoria TEXT,
    fecha_scraping TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE historial_precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER,
    precio TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);
CREATE TABLE scraping_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    sitio TEXT,
    total_items INTEGER,
    estado TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duracion_segundos REAL
);
'''


@pytest.fixture
def db_antigua(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(ESQUEMA_ANTIGUO)
    conn.executemany(
        'INSERT INTO productos (id, titulo, precio, descripcion, enlace, imagen, sitio, fecha_scraping) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [
            (3, 'Portátil', '1.299,99 €', 'N/A', 'https://t.test/1', 'N/A', 'tienda', '2025-01-01 10:00:00'),
            (7, 'Sin enlace', 'N/A', 'Algo', 'N/A', 'N/A', 'tienda', '2025-01-02 10:00:00'),
            (9, 'Libro', '$12.50', 'N/A', 'https://t.test/2', 'N/A', 'otra', '2025-01-03 10:00:00'),
        ],
    )
    conn.executemany(
        'INSERT INTO historial_precios (producto_id, precio, fecha) VALUES (?, ?, ?)',
        [
            (3, '1.399,99 €', '2024-12-01 10:00:00'),
            (3, '1.299,99 €', '2025-01-01 10:00:00'),
            (9, '$12.50', '2025-01-03 10:00:00'),
            (999, '5 €', '2024-01-01 10:00:00'),  # huérfano de un producto ya borrado
        ],
    )
    conn.execute("INSERT INTO scraping_jobs (url, sitio, total_items, estado) VALUES ('https://t.test', 'tienda', 3, 'completado')")
    conn.commit()
    conn.close()
    return db_path


def test_migracion_desde_esquema_antiguo(db_antigua):
    with ScraperDB(db_antigua) as db:
        assert columnas(db.conn, 'productos')['precio'] == 'REAL'
        assert columnas(db.conn, 'historial_precios')['precio'] == 'REAL'
        assert db.conn.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION

        productos = {p['id']: p for p in db.obtener_productos()}
        assert set(productos) == {3, 7, 9}  # se conservan los ids
        assert productos[3]['precio'] == pytest.approx(1299.99)
        assert productos[3]['moneda'] == 'EUR'
        assert productos[3]['precio_texto'] == '1.299,99 €'
        assert productos[3]['fecha_scraping'] == '2025-01-01 10:00:00'
        assert productos[7]['enlace'] is None
        assert productos[7]['precio'] is None
        assert productos[9]['moneda'] == 'USD'

        historial = db.obtener_historial_precios(3)
        assert [h['precio'] for h in historial] == pytest.approx([1299.99, 1399.99])
        total_historial = db.conn.execute('SELECT COUNT(*) FROM historial_precios').fetchone()[0]
        assert total_historial == 3  # el huérfano se descarta

        assert db.obtener_estadisticas()['total_jobs'] == 1
        tablas = {fila[0] for fila in db.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert not {'productos_v0', 'historial_precios_v0'} & tablas

        # Tras migrar, se puede seguir trabajando con normalidad
        db.insertar_producto(producto(titulo='Nuevo', enlace='https://t.test/nuevo', precio='5 €'), 'tienda')
        assert db.obtener_estadisticas()['total_productos'] == 4


def test_migracion_solo_se_hace_una_vez(db_antigua, capsys):
    ScraperDB(db_antigua).cerrar()
    assert 'Migración completada' in capsys.readouterr().out
    with ScraperDB(db_antigua) as db:
        assert len(db.obtener_productos()) == 3
    assert 'Migración' not in capsys.readouterr().out
