# -*- mode: python ; coding: utf-8 -*-
#
# Genera un único ejecutable con la interfaz web (lo mismo que `python servidor.py`):
#
#     pip install -r requirements-dev.txt
#     pyinstaller --noconfirm --clean intelligent-web-scraper.spec
#
# Resultado: dist/IntelligentWebScraper.exe (en Linux/macOS, dist/IntelligentWebScraper).
# Al ejecutarlo crea la carpeta output/ (base de datos, CSV, JSON, tareas) junto al
# ejecutable, no en el directorio actual. Los recursos (interfaz web, schema.sql,
# scripts.js) van dentro del ejecutable; config.py los busca en sys._MEIPASS.
#
# Chrome no se incluye: tiene que estar instalado en el equipo para las páginas
# que necesitan navegador. Selenium Manager (incluido) descarga el chromedriver.

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

raiz = SPECPATH  # carpeta de este .spec (la raíz del proyecto)

datas = [
    (os.path.join(raiz, 'web', 'static'), os.path.join('web', 'static')),
    (os.path.join(raiz, 'schema.sql'), '.'),
    (os.path.join(raiz, 'scripts.js'), '.'),
]
# Selenium necesita sus archivos .js internos y el binario selenium-manager
datas += collect_data_files('selenium')

# Uvicorn elige protocolos y bucles de eventos con imports dinámicos, y las
# versiones recientes de Selenium cargan sus submódulos de forma diferida
hiddenimports = collect_submodules('uvicorn') + collect_submodules('selenium')

a = Analysis(
    [os.path.join(raiz, 'servidor.py')],
    pathex=[raiz],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'PyInstaller'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='IntelligentWebScraper',
    debug=False,
    strip=False,
    upx=False,
    console=True,  # la ventana de consola muestra el registro y permite parar con Ctrl+C
)
