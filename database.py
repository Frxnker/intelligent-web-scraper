"""
Base de datos SQLite para guardar los resultados del scraping.

Las tablas se definen en schema.sql. Al abrir una base de datos creada por la
versión anterior del proyecto (precio guardado como TEXT y sin columna de
moneda) se migra automáticamente conservando los datos.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from colorama import Fore, Style

from config import DB_PATH
from precios import parsear_precio

SCHEMA_PATH = Path(__file__).resolve().parent / 'schema.sql'
SCHEMA_VERSION = 1


def _sentencias_sql(script: str) -> list[str]:
    """Divide un script SQL en sentencias completas (los comentarios sueltos se descartan)."""
    sentencias, actual = [], ''
    for linea in script.splitlines(keepends=True):
        actual += linea
        if sqlite3.complete_statement(actual):
            sentencias.append(actual.strip())
            actual = ''
    return sentencias


def _texto_o_none(valor) -> str | None:
    """Normaliza un campo de texto: vacío o 'N/A' se guardan como NULL."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return None if not texto or texto == 'N/A' else texto


class ScraperDB:
    """Gestor de base de datos para almacenar resultados de scraping."""

    def __init__(self, db_path=DB_PATH):
        """Abre (o crea) la base de datos y deja el esquema al día."""
        self.db_path = db_path
        if str(db_path) != ':memory:':
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        try:
            self.crear_tablas()
            # Tiene que activarse fuera de una transacción y después de migrar
            self.conn.execute('PRAGMA foreign_keys = ON')
        except sqlite3.Error:
            self.conn.close()
            raise

    # ------------------------------------------------------------------
    # Esquema y migración
    # ------------------------------------------------------------------

    def _ejecutar_schema(self):
        script = SCHEMA_PATH.read_text(encoding='utf-8')
        for sentencia in _sentencias_sql(script):
            self.conn.execute(sentencia)

    def _columnas(self, tabla: str) -> set[str]:
        return {fila['name'] for fila in self.conn.execute(f'PRAGMA table_info({tabla})')}

    def _necesita_migracion(self) -> bool:
        for tabla in ('productos', 'historial_precios'):
            columnas = self._columnas(tabla)
            if columnas and 'moneda' not in columnas:
                return True
        return False

    def crear_tablas(self):
        """Crea las tablas si no existen y migra el formato antiguo si hace falta."""
        if self._necesita_migracion():
            self._migrar_esquema_v0()
            return
        self._ejecutar_schema()
        version = self.conn.execute('PRAGMA user_version').fetchone()[0]
        if version < SCHEMA_VERSION:
            self.conn.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
        self.conn.commit()

    def _migrar_esquema_v0(self):
        """
        Migra las tablas de la versión anterior (precio TEXT) al esquema actual.

        Se hace en una única transacción: se renombran las tablas antiguas, se
        crean las nuevas desde schema.sql, se copian los datos interpretando
        los precios y se borran las antiguas. Si algo falla no se toca nada.
        """
        print(f"{Fore.YELLOW}Actualizando {self.db_path} al nuevo formato de precios...{Style.RESET_ALL}")
        conn = self.conn
        conn.execute('BEGIN')
        try:
            antiguas = [t for t in ('productos', 'historial_precios') if self._columnas(t)]
            for tabla in antiguas:
                conn.execute(f'ALTER TABLE {tabla} RENAME TO {tabla}_v0')
            self._ejecutar_schema()

            productos = 0
            if 'productos' in antiguas:
                for fila in conn.execute('SELECT * FROM productos_v0').fetchall():
                    fila = dict(fila)
                    texto = _texto_o_none(fila.get('precio'))
                    valor, moneda = parsear_precio(texto)
                    conn.execute(
                        '''INSERT INTO productos (id, titulo, precio, moneda, precio_texto, descripcion,
                                                  enlace, imagen, sitio, categoria, fecha_scraping)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))''',
                        (
                            fila.get('id'),
                            _texto_o_none(fila.get('titulo')) or 'N/A',
                            valor,
                            moneda,
                            texto,
                            _texto_o_none(fila.get('descripcion')),
                            _texto_o_none(fila.get('enlace')),
                            _texto_o_none(fila.get('imagen')),
                            fila.get('sitio'),
                            fila.get('categoria'),
                            fila.get('fecha_scraping'),
                        ),
                    )
                    productos += 1

            historial = descartados = 0
            if 'historial_precios' in antiguas:
                total = conn.execute('SELECT COUNT(*) FROM historial_precios_v0').fetchone()[0]
                # Las filas huérfanas (de productos ya borrados) no se copian
                filas = conn.execute(
                    'SELECT * FROM historial_precios_v0 WHERE producto_id IN (SELECT id FROM productos)'
                ).fetchall()
                for fila in filas:
                    fila = dict(fila)
                    texto = _texto_o_none(fila.get('precio'))
                    valor, moneda = parsear_precio(texto)
                    conn.execute(
                        '''INSERT INTO historial_precios (id, producto_id, precio, moneda, precio_texto, fecha)
                           VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))''',
                        (fila.get('id'), fila.get('producto_id'), valor, moneda, texto, fila.get('fecha')),
                    )
                historial = len(filas)
                descartados = total - historial

            for tabla in reversed(antiguas):
                conn.execute(f'DROP TABLE {tabla}_v0')
            # Por si algún índice con el mismo nombre se fue con las tablas antiguas
            self._ejecutar_schema()
            conn.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise

        print(f"{Fore.GREEN}✓ Migración completada: {productos} productos, "
              f"{historial} registros de historial{Style.RESET_ALL}")
        if descartados:
            print(f"{Fore.YELLOW}⚠️  Se descartaron {descartados} registros de historial "
                  f"de productos que ya no existían{Style.RESET_ALL}")

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def _guardar_producto(self, producto: dict, sitio) -> int:
        """Inserta o actualiza un producto y registra su precio. No hace commit."""
        precio_texto = _texto_o_none(producto.get('precio'))
        valor, moneda = parsear_precio(precio_texto)
        campos = {
            'titulo': _texto_o_none(producto.get('titulo')) or 'N/A',
            'precio': valor,
            'moneda': moneda,
            'precio_texto': precio_texto,
            'descripcion': _texto_o_none(producto.get('descripcion')),
            'enlace': _texto_o_none(producto.get('enlace')),
            'imagen': _texto_o_none(producto.get('imagen')),
            'sitio': sitio,
            'categoria': _texto_o_none(producto.get('categoria')),
        }

        if campos['enlace']:
            existente = self.conn.execute(
                'SELECT id FROM productos WHERE enlace = :enlace', campos
            ).fetchone()
        else:
            # Sin enlace no hay identificador fiable: se usa título + sitio
            existente = self.conn.execute(
                'SELECT id FROM productos WHERE enlace IS NULL AND titulo = :titulo AND sitio IS :sitio',
                campos,
            ).fetchone()

        if existente:
            producto_id = existente['id']
            self.conn.execute(
                '''UPDATE productos
                   SET titulo = :titulo, precio = :precio, moneda = :moneda,
                       precio_texto = :precio_texto, descripcion = :descripcion,
                       imagen = :imagen, sitio = :sitio,
                       categoria = COALESCE(:categoria, categoria),
                       fecha_scraping = CURRENT_TIMESTAMP
                   WHERE id = :id''',
                {**campos, 'id': producto_id},
            )
        else:
            cursor = self.conn.execute(
                '''INSERT INTO productos (titulo, precio, moneda, precio_texto, descripcion,
                                          enlace, imagen, sitio, categoria)
                   VALUES (:titulo, :precio, :moneda, :precio_texto, :descripcion,
                           :enlace, :imagen, :sitio, :categoria)''',
                campos,
            )
            producto_id = cursor.lastrowid

        if valor is not None:
            self.conn.execute(
                '''INSERT INTO historial_precios (producto_id, precio, moneda, precio_texto)
                   VALUES (?, ?, ?, ?)''',
                (producto_id, valor, moneda, precio_texto),
            )
        return producto_id

    def _guardar_con_aviso(self, producto: dict, sitio) -> bool:
        try:
            self._guardar_producto(producto, sitio)
            return True
        except sqlite3.Error as e:
            print(f"{Fore.RED}Error al guardar el producto {producto.get('titulo', '')!r}: {e}{Style.RESET_ALL}")
            return False

    def insertar_producto(self, producto: dict, sitio='') -> bool:
        """Inserta o actualiza un producto. Devuelve True si se guardó."""
        guardado = self._guardar_con_aviso(producto, sitio)
        self.conn.commit()
        return guardado

    def insertar_productos_bulk(self, productos, sitio='') -> int:
        """Inserta o actualiza varios productos en una sola transacción. Devuelve cuántos se guardaron."""
        guardados = sum(1 for producto in productos if self._guardar_con_aviso(producto, sitio))
        self.conn.commit()
        return guardados

    def registrar_job(self, url, sitio, total_items, estado='completado', duracion=0):
        """Registra un trabajo de scraping."""
        self.conn.execute(
            '''INSERT INTO scraping_jobs (url, sitio, total_items, estado, duracion_segundos)
               VALUES (?, ?, ?, ?, ?)''',
            (url, sitio, total_items, estado, duracion),
        )
        self.conn.commit()

    def limpiar_datos_antiguos(self, dias=30) -> int:
        """Elimina los productos que no se han visto en los últimos `dias` días (y su historial)."""
        dias = int(dias)
        if dias < 0:
            raise ValueError('dias no puede ser negativo')
        cursor = self.conn.execute(
            "DELETE FROM productos WHERE fecha_scraping < datetime('now', ?)",
            (f'-{dias} days',),
        )
        self.conn.commit()
        return cursor.rowcount

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_limite(limite) -> int:
        limite = int(limite)
        if limite < 1:
            raise ValueError('limite debe ser mayor que 0')
        return limite

    def obtener_productos(self, sitio=None, limite=50) -> list[dict]:
        """Obtiene los productos más recientes, opcionalmente filtrados por sitio."""
        limite = self._validar_limite(limite)
        if sitio:
            filas = self.conn.execute(
                'SELECT * FROM productos WHERE sitio = ? ORDER BY fecha_scraping DESC, id DESC LIMIT ?',
                (sitio, limite),
            )
        else:
            filas = self.conn.execute(
                'SELECT * FROM productos ORDER BY fecha_scraping DESC, id DESC LIMIT ?',
                (limite,),
            )
        return [dict(fila) for fila in filas]

    def obtener_historial_precios(self, producto_id) -> list[dict]:
        """Obtiene el historial de precios de un producto, del más reciente al más antiguo."""
        filas = self.conn.execute(
            '''SELECT precio, moneda, precio_texto, fecha FROM historial_precios
               WHERE producto_id = ?
               ORDER BY fecha DESC, id DESC''',
            (producto_id,),
        )
        return [dict(fila) for fila in filas]

    def buscar_productos(self, query, limite=50) -> list[dict]:
        """Busca productos cuyo título contenga `query` (sin distinguir mayúsculas en ASCII)."""
        limite = self._validar_limite(limite)
        patron = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        filas = self.conn.execute(
            r'''SELECT * FROM productos
                WHERE titulo LIKE ? ESCAPE '\'
                ORDER BY fecha_scraping DESC, id DESC
                LIMIT ?''',
            (f'%{patron}%', limite),
        )
        return [dict(fila) for fila in filas]

    def obtener_estadisticas(self) -> dict:
        """Obtiene estadísticas generales."""
        total_productos = self.conn.execute('SELECT COUNT(*) FROM productos').fetchone()[0]
        total_jobs = self.conn.execute('SELECT COUNT(*) FROM scraping_jobs').fetchone()[0]
        filas = self.conn.execute(
            'SELECT sitio, COUNT(*) AS total FROM productos GROUP BY sitio ORDER BY total DESC'
        )
        return {
            'total_productos': total_productos,
            'total_jobs': total_jobs,
            'por_sitio': {fila['sitio']: fila['total'] for fila in filas},
        }

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def cerrar(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self.conn:
            self.conn.rollback()
        self.cerrar()
