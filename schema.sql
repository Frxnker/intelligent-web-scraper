-- Esquema de la base de datos SQLite del scraper (output/scraper.db).
--
-- database.py ejecuta este archivo al abrir la base de datos, así que es la
-- única definición de las tablas. Versión del esquema: 1 (PRAGMA user_version).
-- Si cambias algo aquí, sube SCHEMA_VERSION en database.py y añade la migración.

-- Productos scrapeados. Un producto con enlace se identifica por su enlace
-- (sin enlace, por título y sitio). Al volver a scrapearlo se actualiza la fila.
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    precio REAL,              -- importe numérico (NULL si no se pudo interpretar)
    moneda TEXT,              -- código ISO: EUR, USD, GBP, JPY (NULL si no aparece)
    precio_texto TEXT,        -- texto original del precio tal como venía en la página
    descripcion TEXT,
    enlace TEXT UNIQUE,       -- NULL si el producto no tiene enlace
    imagen TEXT,
    sitio TEXT,
    categoria TEXT,
    fecha_scraping TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- última vez que se vio (UTC)
);

CREATE INDEX IF NOT EXISTS idx_productos_sitio ON productos(sitio);
CREATE INDEX IF NOT EXISTS idx_productos_fecha ON productos(fecha_scraping);

-- Cada vez que se guarda un producto con precio se añade una fila aquí.
CREATE TABLE IF NOT EXISTS historial_precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    precio REAL,
    moneda TEXT,
    precio_texto TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_historial_producto ON historial_precios(producto_id, fecha);

-- Registro de cada ejecución de scraping.
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    sitio TEXT,
    total_items INTEGER,
    estado TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duracion_segundos REAL
);
