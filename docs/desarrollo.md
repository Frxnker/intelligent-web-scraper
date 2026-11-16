# Desarrollo

[Volver al README](../README.md)

## Estructura del proyecto

```
intelligent-web-scraper/
├── main.py               Menú de consola
├── servidor.py           Arranque de la interfaz web
├── web/
│   ├── app.py            API (FastAPI) y archivos estáticos
│   ├── esquemas.py       Validación de las entradas (Pydantic)
│   ├── jobs.py           Trabajos en segundo plano
│   └── static/           index.html, styles.css, app.js
├── servicios.py          Scrapear y guardar (lo comparten consola, web y programador)
├── scraper.py            Estrategia: sin navegador primero, Selenium si hace falta
├── scraper_selenium.py   Navegador Chrome: carga, esperas, scroll, scripts JS
├── extractor.py          Extracción genérica con BeautifulSoup
├── scripts.js            JavaScript que se ejecuta en el navegador (scripts por sitio)
├── js_scripts.py         Carga scripts.js y elige el script según el dominio
├── precios.py            Interpretación de precios y monedas
├── database.py           Acceso a SQLite y migración del formato antiguo
├── schema.sql            Definición de las tablas
├── comparador.py         Comparación de precios entre dos sitios
├── paginacion.py         Scraping de varias páginas
├── programador.py        Tareas programadas
├── utils.py              Exportación a CSV/JSON y validación de URLs
├── config.py             Configuración
├── requirements.txt      Dependencias
├── requirements-dev.txt  Dependencias para tests y para generar el .exe
├── intelligent-web-scraper.spec   Configuración de PyInstaller
├── pytest.ini
├── LICENSE
├── docs/                 Documentación (img/ tiene las capturas)
├── tests/                Tests
└── output/               Resultados (no se sube al repositorio)
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

Los tests no acceden a internet ni necesitan Chrome: usan HTML de ejemplo, una
sesión HTTP y un navegador simulados, y bases de datos temporales. Cubren el
parseo de precios, la extracción, la base de datos (incluida la migración), el
comparador, la paginación, el programador, la estrategia sin navegador y
Selenium, y la API, que se prueba con el `TestClient` de FastAPI y un scraper
falso. Si Node.js está instalado, también se comprueba que `scripts.js` es
JavaScript válido.

`requirements-dev.txt` añade `pytest`, `httpx` (para el `TestClient`) y
`pyinstaller` (para [generar el .exe](interfaz-web.md#generar-el-ejecutable-exe)).

## Versiones de Python

Probado con Python 3.13.
