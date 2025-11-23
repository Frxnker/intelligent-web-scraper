-- Schema de la base de datos SQLite para Web Scraper
-- Este archivo define la estructura de las tablas utilizadas

-- Tabla principal de productos scrapeados
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    precio REAL,
    url TEXT,
    sitio TEXT,
    fecha_scraping DATETIME DEFAULT CURRENT_TIMESTAMP,
    imagen_url TEXT,
    descripcion TEXT,
    disponibilidad TEXT,
    categoria TEXT
);

-- Índices para mejorar el rendimiento de búsquedas
CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre);
CREATE INDEX IF NOT EXISTS idx_productos_sitio ON productos(sitio);
CREATE INDEX IF NOT EXISTS idx_productos_fecha ON productos(fecha_scraping);

-- Tabla de historial de precios para tracking
CREATE TABLE IF NOT EXISTS historial_precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    precio REAL NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_historial_producto ON historial_precios(producto_id);
CREATE INDEX IF NOT EXISTS idx_historial_fecha ON historial_precios(fecha);

-- Tabla de trabajos programados
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    frecuencia TEXT NOT NULL,
    ultima_ejecucion DATETIME,
    proxima_ejecucion DATETIME,
    activo INTEGER DEFAULT 1,
    descripcion TEXT,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_activo ON scraping_jobs(activo);
CREATE INDEX IF NOT EXISTS idx_jobs_proxima ON scraping_jobs(proxima_ejecucion);
