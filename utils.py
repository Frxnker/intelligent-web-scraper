"""
Funciones auxiliares: exportación de resultados y validación de URLs.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from colorama import Fore

import config


def ensure_output_dir() -> Path:
    """Crea el directorio de salida si no existe y lo devuelve."""
    salida = Path(config.OUTPUT_DIR)
    salida.mkdir(parents=True, exist_ok=True)
    return salida


def _campos(data: list[dict]) -> list[str]:
    """Une las claves de todos los registros conservando el orden de aparición."""
    campos: dict[str, None] = {}
    for fila in data:
        campos.update(dict.fromkeys(fila))
    return list(campos)


def escribir_csv(data: list[dict], destino, valor_vacio: str = 'N/A', campos: list[str] | None = None):
    """
    Escribe una lista de diccionarios como CSV en un archivo abierto (o io.StringIO).

    Las columnas son `campos` o, si no se indican, la unión de las claves de los registros.
    """
    writer = csv.DictWriter(destino, fieldnames=campos or _campos(data), restval=valor_vacio)
    writer.writeheader()
    writer.writerows(data)


def export_to_csv(data: list[dict], filename: str) -> Path | None:
    """Exporta una lista de diccionarios a output/<filename>. Devuelve la ruta o None."""
    if not data:
        print(f"{Fore.YELLOW}⚠ No hay datos para exportar")
        return None

    filepath = ensure_output_dir() / filename
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            escribir_csv(data, f)
    except OSError as e:
        print(f"{Fore.RED}✗ Error al exportar CSV a {filepath}: {e}")
        return None

    print(f"{Fore.GREEN}✓ Datos exportados a: {filepath}")
    return filepath


def export_to_json(data: list[dict], filename: str) -> Path | None:
    """Exporta una lista de diccionarios a output/<filename>. Devuelve la ruta o None."""
    if not data:
        print(f"{Fore.YELLOW}⚠ No hay datos para exportar")
        return None

    filepath = ensure_output_dir() / filename
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (OSError, TypeError) as e:
        print(f"{Fore.RED}✗ Error al exportar JSON a {filepath}: {e}")
        return None

    print(f"{Fore.GREEN}✓ Datos exportados a: {filepath}")
    return filepath


def guardar_html(html: str, filename: str) -> Path | None:
    """Guarda el HTML de la página en output/<filename> para poder revisarlo."""
    filepath = ensure_output_dir() / filename
    try:
        filepath.write_text(html, encoding='utf-8')
    except OSError as e:
        print(f"{Fore.RED}✗ Error al guardar el HTML en {filepath}: {e}")
        return None
    print(f"{Fore.GREEN}✓ HTML guardado en: {filepath}")
    return filepath


def guardar_resultados(datos: list[dict], nombre_base: str, html: str | None = None):
    """Guarda el HTML (si lo hay) y exporta los datos a CSV y JSON."""
    if html:
        guardar_html(html, f"{nombre_base}.html")
    if datos:
        export_to_csv(datos, f"{nombre_base}.csv")
        export_to_json(datos, f"{nombre_base}.json")
        print(f"{Fore.CYAN}📊 Total de registros: {len(datos)}\n")


def mostrar_muestra(datos: list[dict], cantidad: int = 5):
    """Muestra los primeros elementos extraídos."""
    for dato in datos[:cantidad]:
        print(f"{Fore.YELLOW}Elemento #{dato.get('numero', '?')}")
        print(f"{Fore.WHITE}  📝 {str(dato.get('titulo', 'N/A'))[:65]}")
        if dato.get('precio', 'N/A') != 'N/A':
            print(f"{Fore.GREEN}  💰 {dato['precio']}")
        print()
    if len(datos) > cantidad:
        print(f"{Fore.CYAN}... y {len(datos) - cantidad} elementos más\n")


def guardar_y_mostrar(datos: list[dict], nombre_base: str, html: str | None = None):
    """Guarda los resultados de una página y muestra una muestra por consola."""
    guardar_resultados(datos, nombre_base, html)
    if datos:
        mostrar_muestra(datos)
        return
    print(f"{Fore.YELLOW}⚠️  No se encontraron elementos estructurados")
    if html:
        print(f"{Fore.CYAN}💡 Revisa output/{nombre_base}.html para ver la estructura de la página\n")


def normalizar_url(texto: str) -> str | None:
    """
    Valida una URL introducida por el usuario.

    Añade https:// si no lleva esquema. Devuelve None si no es una URL
    http(s) con dominio.
    """
    texto = (texto or '').strip()
    if not texto:
        return None
    if '://' not in texto:
        texto = 'https://' + texto
    try:
        partes = urlparse(texto)
        hostname = partes.hostname
        partes.port  # noqa: B018 - lanza ValueError si el puerto no es válido ("javascript:alert(1)")
    except ValueError:  # p. ej. "https://[::1" (IPv6 mal cerrada)
        return None
    if partes.scheme not in ('http', 'https') or not hostname or ' ' in partes.netloc:
        return None
    return texto


def nombre_desde_url(url: str) -> str:
    """Nombre seguro para archivos a partir del dominio: 'www.amazon.es' -> 'amazon_es'."""
    netloc = urlparse(url).netloc.rsplit('@', 1)[-1]  # sin usuario:contraseña
    dominio = netloc.lower().removeprefix('www.')
    nombre = re.sub(r'[^a-z0-9_-]+', '_', dominio).strip('_')
    return nombre or 'pagina'


def truncar(texto: str, longitud: int) -> str:
    """Recorta un texto añadiendo '...' solo si hace falta."""
    texto = str(texto)
    return texto if len(texto) <= longitud else texto[:longitud] + '...'
