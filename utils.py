"""
Funciones auxiliares para el web scraper
"""

import csv
import json
import os
from typing import List, Dict
from datetime import datetime
from config import OUTPUT_DIR
from colorama import Fore, Style


def ensure_output_dir():
    """Crea el directorio de salida si no existe"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"{Fore.GREEN}✓ Directorio creado: {OUTPUT_DIR}")


def export_to_csv(data: List[Dict], filename: str):
    """
    Exporta datos a un archivo CSV
    
    Args:
        data: Lista de diccionarios con los datos
        filename: Nombre del archivo de salida
    """
    ensure_output_dir()
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not data:
        print(f"{Fore.YELLOW}⚠ No hay datos para exportar")
        return
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        print(f"{Fore.GREEN}✓ Datos exportados a: {filepath}")
        print(f"{Fore.CYAN}📊 Total de registros: {len(data)}")
    except Exception as e:
        print(f"{Fore.RED}✗ Error al exportar CSV: {str(e)}")


def export_to_json(data: List[Dict], filename: str):
    """
    Exporta datos a un archivo JSON
    
    Args:
        data: Lista de diccionarios con los datos
        filename: Nombre del archivo de salida
    """
    ensure_output_dir()
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not data:
        print(f"{Fore.YELLOW}⚠ No hay datos para exportar")
        return
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"{Fore.GREEN}✓ Datos exportados a: {filepath}")
        print(f"{Fore.CYAN}📊 Total de registros: {len(data)}")
    except Exception as e:
        print(f"{Fore.RED}✗ Error al exportar JSON: {str(e)}")


def generate_filename(prefix: str, extension: str = 'csv') -> str:
    """
    Genera un nombre de archivo con timestamp
    
    Args:
        prefix: Prefijo del nombre del archivo
        extension: Extensión del archivo
        
    Returns:
        Nombre del archivo generado
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{prefix}_{timestamp}.{extension}"


def print_data_summary(data: List[Dict]):
    """
    Imprime un resumen de los datos scrapeados
    
    Args:
        data: Lista de diccionarios con los datos
    """
    if not data:
        print(f"{Fore.YELLOW}⚠ No hay datos para mostrar")
        return
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}📊 RESUMEN DE DATOS")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.WHITE}Total de registros: {Fore.GREEN}{len(data)}")
    print(f"{Fore.WHITE}Campos disponibles: {Fore.GREEN}{', '.join(data[0].keys())}")
    
    print(f"\n{Fore.CYAN}🔍 Primeros 3 registros:")
    print(f"{Fore.CYAN}{'-'*60}")
    
    for i, item in enumerate(data[:3], 1):
        print(f"{Fore.YELLOW}Registro {i}:")
        for key, value in item.items():
            # Truncar valores largos
            display_value = str(value)[:100] + '...' if len(str(value)) > 100 else value
            print(f"  {Fore.WHITE}{key}: {Fore.GREEN}{display_value}")
        print()
    
    print(f"{Fore.CYAN}{'='*60}\n")


def clean_text(text: str) -> str:
    """
    Limpia un texto eliminando espacios extras y caracteres especiales
    
    Args:
        text: Texto a limpiar
        
    Returns:
        Texto limpio
    """
    if not text:
        return ''
    
    # Eliminar espacios extras
    text = ' '.join(text.split())
    
    # Eliminar caracteres especiales comunes
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    return text.strip()


def validate_url(url: str) -> bool:
    """
    Valida si una URL tiene un formato correcto
    
    Args:
        url: URL a validar
        
    Returns:
        True si la URL es válida, False en caso contrario
    """
    if not url:
        return False
    
    return url.startswith('http://') or url.startswith('https://')


def print_banner():
    """Imprime un banner de bienvenida"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║              🌐  WEB SCRAPER PROJECT  🌐                 ║
║                                                          ║
║            Powered by BeautifulSoup & Requests           ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """
    print(banner)
