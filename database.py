"""
Módulo de gestión de base de datos SQLite para el scraper
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style

class ScraperDB:
    """Gestor de base de datos para almacenar resultados de scraping"""
    
    def __init__(self, db_path='output/scraper.db'):
        """Inicializa la conexión a la base de datos"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.crear_tablas()
    
    def crear_tablas(self):
        """Crea las tablas necesarias si no existen"""
        # Tabla de productos
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                precio TEXT,
                descripcion TEXT,
                enlace TEXT UNIQUE,
                imagen TEXT,
                sitio TEXT,
                categoria TEXT,
                fecha_scraping TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de historial de precios
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial_precios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                precio TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
        ''')
        
        # Tabla de scraping jobs
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                sitio TEXT,
                total_items INTEGER,
                estado TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duracion_segundos REAL
            )
        ''')
        
        self.conn.commit()
    
    def insertar_producto(self, producto, sitio=''):
        """Inserta o actualiza un producto en la base de datos"""
        try:
            # Intentar insertar
            self.cursor.execute('''
                INSERT OR IGNORE INTO productos (titulo, precio, descripcion, enlace, imagen, sitio)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                producto.get('titulo', 'N/A'),
                producto.get('precio', 'N/A'),
                producto.get('descripcion', 'N/A'),
                producto.get('enlace', 'N/A'),
                producto.get('imagen', 'N/A'),
                sitio
            ))
            
            # Si existe, obtener ID y actualizar historial
            if producto.get('enlace') and producto.get('enlace') != 'N/A':
                self.cursor.execute('SELECT id FROM productos WHERE enlace = ?', (producto['enlace'],))
                result = self.cursor.fetchone()
                if result:
                    producto_id = result[0]
                    # Agregar al historial de precios si tiene precio
                    if producto.get('precio') and producto.get('precio') != 'N/A':
                        self.cursor.execute('''
                            INSERT INTO historial_precios (producto_id, precio)
                            VALUES (?, ?)
                        ''', (producto_id, producto['precio']))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"{Fore.RED}Error al insertar producto: {e}{Style.RESET_ALL}")
            return False
    
    def insertar_productos_bulk(self, productos, sitio=''):
        """Inserta múltiples productos de una vez"""
        contador = 0
        for producto in productos:
            if self.insertar_producto(producto, sitio):
                contador += 1
        return contador
    
    def registrar_job(self, url, sitio, total_items, estado='completado', duracion=0):
        """Registra un trabajo de scraping"""
        self.cursor.execute('''
            INSERT INTO scraping_jobs (url, sitio, total_items, estado, duracion_segundos)
            VALUES (?, ?, ?, ?, ?)
        ''', (url, sitio, total_items, estado, duracion))
        self.conn.commit()
    
    def obtener_productos(self, sitio=None, limite=50):
        """Obtiene productos de la base de datos"""
        if sitio:
            self.cursor.execute('''
                SELECT * FROM productos WHERE sitio = ? ORDER BY fecha_scraping DESC LIMIT ?
            ''', (sitio, limite))
        else:
            self.cursor.execute('''
                SELECT * FROM productos ORDER BY fecha_scraping DESC LIMIT ?
            ''', (limite,))
        
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
    
    def obtener_historial_precios(self, producto_id):
        """Obtiene el historial de precios de un producto"""
        self.cursor.execute('''
            SELECT precio, fecha FROM historial_precios 
            WHERE producto_id = ? 
            ORDER BY fecha DESC
        ''', (producto_id,))
        return self.cursor.fetchall()
    
    def buscar_productos(self, query):
        """Busca productos por título"""
        self.cursor.execute('''
            SELECT * FROM productos 
            WHERE titulo LIKE ? 
            ORDER BY fecha_scraping DESC 
            LIMIT 50
        ''', (f'%{query}%',))
        
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
    
    def obtener_estadisticas(self):
        """Obtiene estadísticas generales"""
        stats = {}
        
        # Total de productos
        self.cursor.execute('SELECT COUNT(*) FROM productos')
        stats['total_productos'] = self.cursor.fetchone()[0]
        
        # Total de jobs
        self.cursor.execute('SELECT COUNT(*) FROM scraping_jobs')
        stats['total_jobs'] = self.cursor.fetchone()[0]
        
        # Productos por sitio
        self.cursor.execute('''
            SELECT sitio, COUNT(*) as count 
            FROM productos 
            GROUP BY sitio 
            ORDER BY count DESC
        ''')
        stats['por_sitio'] = dict(self.cursor.fetchall())
        
        return stats
    
    def limpiar_datos_antiguos(self, dias=30):
        """Elimina datos más antiguos de X días"""
        self.cursor.execute('''
            DELETE FROM productos 
            WHERE fecha_scraping < datetime('now', '-' || ? || ' days')
        ''', (dias,))
        
        eliminados = self.cursor.rowcount
        self.conn.commit()
        return eliminados
    
    def cerrar(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar()
