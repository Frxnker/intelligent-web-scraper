# Web Scraper Universal

Un potente web scraper en Python con **soporte universal** para cualquier sitio web. Funciona con BeautifulSoup para sitios simples y Selenium para sitios con JavaScript o protección anti-bot.

## 🌟 Características

### 🎯 **Core Features**
- 🌐 **Universal**: Funciona con cualquier página web (e-commerce, noticias, blogs)
- 🤖 **Anti-bloqueo**: Usa Selenium automáticamente cuando detecta restricciones
- 📊 **Múltiples formatos**: Exporta a CSV, JSON y HTML
- 🎯 **Detección inteligente**: Encuentra productos/artículos automáticamente
- 💰 **Multi-moneda**: Detecta €, $, £, ¥
- 🖼️ **Lazy-loading**: Extrae imágenes con carga diferida

### ⚡ **Optimizaciones con JavaScript** (NUEVO)
- 🚀 **3-5x más rápido** que BeautifulSoup puro
- 🎯 **Scripts específicos** para sitios conocidos (Amazon, PcComponentes, eBay)
- 🧠 **Espera inteligente**: Detecta cuando la página terminó de cargar
- 🔄 **Scroll automático**: Carga todo el contenido lazy-load hasta el final
- 🧹 **Remover popups**: Elimina cookies, newsletters automáticamente
- 📊 **Extracción directa con JS**: Acceso nativo al DOM del navegador

### 🔥 **Características Avanzadas**
- 💾 **Base de datos SQLite**: Almacenamiento persistente + historial de precios
- 📄 **Paginación automática**: Scraping de múltiples páginas con detección inteligente
- 💰 **Comparador de precios**: Encuentra mejores ofertas entre sitios con algoritmo fuzzy
- ⏰ **Programador de tareas**: Scraping automático recurrente (minutos/horas/días)
- 📈 **Estadísticas**: Análisis de datos scrapeados por sitio y categoría
- ⚡ **Rápido**: Optimizado con JavaScript (2-4 segundos por página)

## ✅ Sitios Compatibles

### E-commerce
- **PcComponentes** - Tecnología española
- **Amazon** - E-commerce internacional  
- **eBay** - Subastas y productos
- **AliExpress** - Importación
- Cualquier tienda online

### Noticias y Blogs  
- **WordPress** - Blogs y contenido
- Sitios de noticias
- Cualquier blog HTML5

### Detecta automáticamente
- `data-product-name`, `data-asin` (atributos e-commerce)
- `<article>`, `<div class="post">` (noticias/blogs)
- Precios en múltiples monedas
- Imágenes con `srcset`, `data-src`

## Instalación

1. Clona el repositorio o descarga los archivos
2. Crea un entorno virtual (opcional pero recomendado):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # En Windows
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Uso Rápido

### Uso Simple
```bash
# 1. Activa el entorno virtual
.venv\Scripts\activate

# 2. Ejecuta el scraper
python main.py
```

**Funcionalidades incluidas:**
- ✅ Scraping simple y con paginación (JavaScript optimizado)
- ✅ Comparador de precios entre sitios
- ✅ Base de datos SQLite automática
- ✅ Búsqueda y estadísticas
- ✅ Programación de tareas (scraping automático cada X minutos/horas)
- ✅ Extracción 3-5x más rápida con JavaScript nativo

### Ejemplos rápidos:

**1. Scrapear con paginación (5 páginas):**
```bash
python main.py
# Opción 2 → URL → 5 páginas
```

**2. Comparar precios PcComponentes vs Amazon:**
```bash
python main_avanzado.py
# Opción 3 → URL1 → URL2 → Comparar
```

**3. Programar scraping automático cada hora:**
```bash
python main_avanzado.py
# Opción 8 → Crear tarea → 60 minutos
# Opción 10 → Iniciar programador
```

Los datos se guardan en:
- `output/scraper.db` - Base de datos SQLite
- `output/nombre_pagina.csv` - Tabla para Excel
- `output/nombre_pagina.json` - Datos estructurados

## 📂 Estructura del Proyecto

```
webscraper/
├── main.py                  # Menú completo con TODAS las funcionalidades ⭐
├── scraper_selenium.py     # Scraper avanzado (Selenium + JavaScript)
├── js_scripts.py           # Scripts JavaScript personalizados 📜
├── database.py             # Gestión de base de datos SQLite
├── paginacion.py           # Scraping de múltiples páginas
├── comparador.py           # Comparador de precios
├── programador.py          # Automatización de tareas
├── utils.py                # Funciones auxiliares
├── config.py               # Configuración
├── requirements.txt        # Dependencias
├── README.md               # Esta guía
├── JAVASCRIPT_MEJORAS.md   # Guía completa de JavaScript 📖
├── GUIA_AVANZADA.md        # Guía de características avanzadas
├── COMPLETADO.md           # Resumen del proyecto
├── output/                 # Directorio de salida
│   ├── scraper.db          # Base de datos SQLite
│   ├── *.csv               # Archivos CSV
│   ├── *.json              # Archivos JSON
│   └── *.html              # HTML guardado
└── .venv/                  # Entorno virtual
```

## Configuración

Puedes modificar la configuración en `config.py`:

- `USER_AGENT`: User agent para las peticiones HTTP
- `TIMEOUT`: Timeout para las peticiones
- `MAX_RETRIES`: Número máximo de reintentos
- `OUTPUT_DIR`: Directorio para guardar resultados

## Ejemplos

### Ejemplo 1: Scrapear títulos de artículos

```python
scraper = WebScraper()
soup = scraper.get_soup("https://ejemplo.com/blog")
titles = soup.find_all('h2', class_='article-title')
for title in titles:
    print(title.text)
```

### Ejemplo 2: Exportar a CSV

```python
from utils import export_to_csv

data = [
    {'titulo': 'Artículo 1', 'fecha': '2025-01-01'},
    {'titulo': 'Artículo 2', 'fecha': '2025-01-02'}
]
export_to_csv(data, 'articulos.csv')
```

## Notas

- Respeta las políticas de scraping de cada sitio web
- Verifica el archivo `robots.txt` antes de scrapear
- No hagas demasiadas peticiones en poco tiempo
- Considera usar delays entre peticiones

## Licencia

MIT License
