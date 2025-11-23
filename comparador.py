"""
Módulo comparador de precios entre diferentes sitios
"""
from colorama import Fore, Style
from difflib import SequenceMatcher
import re

class ComparadorPrecios:
    """Compara precios de productos entre diferentes sitios"""
    
    @staticmethod
    def limpiar_titulo(titulo):
        """Normaliza el título para comparación"""
        # Convertir a minúsculas
        titulo = titulo.lower()
        # Eliminar caracteres especiales
        titulo = re.sub(r'[^\w\s]', ' ', titulo)
        # Eliminar espacios múltiples
        titulo = ' '.join(titulo.split())
        return titulo
    
    @staticmethod
    def extraer_precio_numerico(precio_str):
        """Extrae el valor numérico del precio"""
        if not precio_str or precio_str == 'N/A':
            return None
        
        # Buscar números con decimales
        match = re.search(r'(\d+[.,]?\d*)', precio_str.replace(',', '.'))
        if match:
            try:
                return float(match.group(1))
            except:
                return None
        return None
    
    @staticmethod
    def similitud_titulos(titulo1, titulo2):
        """Calcula la similitud entre dos títulos (0-1)"""
        t1 = ComparadorPrecios.limpiar_titulo(titulo1)
        t2 = ComparadorPrecios.limpiar_titulo(titulo2)
        return SequenceMatcher(None, t1, t2).ratio()
    
    @staticmethod
    def comparar_listas(productos1, productos2, umbral_similitud=0.7):
        """
        Compara dos listas de productos y encuentra coincidencias
        
        Args:
            productos1: Lista de productos del sitio 1
            productos2: Lista de productos del sitio 2
            umbral_similitud: Similitud mínima para considerar match (0-1)
        
        Returns:
            Lista de coincidencias con comparación de precios
        """
        coincidencias = []
        
        for p1 in productos1:
            mejor_match = None
            mejor_similitud = 0
            
            for p2 in productos2:
                similitud = ComparadorPrecios.similitud_titulos(
                    p1.get('titulo', ''),
                    p2.get('titulo', '')
                )
                
                if similitud > mejor_similitud and similitud >= umbral_similitud:
                    mejor_similitud = similitud
                    mejor_match = p2
            
            if mejor_match:
                precio1 = ComparadorPrecios.extraer_precio_numerico(p1.get('precio', 'N/A'))
                precio2 = ComparadorPrecios.extraer_precio_numerico(mejor_match.get('precio', 'N/A'))
                
                diferencia = None
                porcentaje = None
                mas_barato = None
                
                if precio1 and precio2:
                    diferencia = abs(precio1 - precio2)
                    porcentaje = (diferencia / min(precio1, precio2)) * 100
                    mas_barato = 'sitio1' if precio1 < precio2 else 'sitio2'
                
                coincidencias.append({
                    'producto1': p1,
                    'producto2': mejor_match,
                    'similitud': mejor_similitud,
                    'precio1': precio1,
                    'precio2': precio2,
                    'diferencia': diferencia,
                    'porcentaje_diferencia': porcentaje,
                    'mas_barato': mas_barato
                })
        
        return coincidencias
    
    @staticmethod
    def mostrar_comparacion(coincidencias, nombre_sitio1='Sitio 1', nombre_sitio2='Sitio 2'):
        """Muestra la comparación de precios de forma visual"""
        if not coincidencias:
            print(f"\n{Fore.YELLOW}⚠️  No se encontraron productos coincidentes\n")
            return
        
        print(f"\n{Fore.CYAN}{'='*90}")
        print(f"{Fore.YELLOW}💰 COMPARACIÓN DE PRECIOS: {nombre_sitio1} vs {nombre_sitio2}")
        print(f"{Fore.CYAN}{'='*90}\n")
        
        ahorros_totales = 0
        productos_mas_baratos_sitio1 = 0
        productos_mas_baratos_sitio2 = 0
        
        for i, match in enumerate(coincidencias, 1):
            titulo = match['producto1']['titulo'][:60]
            precio1 = match['precio1']
            precio2 = match['precio2']
            
            print(f"{Fore.WHITE}{i}. {titulo}...")
            print(f"   {Fore.CYAN}{nombre_sitio1}: ", end='')
            
            if precio1 and precio2:
                if match['mas_barato'] == 'sitio1':
                    print(f"{Fore.GREEN}€{precio1:.2f} ✓ (más barato)")
                    productos_mas_baratos_sitio1 += 1
                    ahorros_totales += (precio2 - precio1)
                else:
                    print(f"{Fore.WHITE}€{precio1:.2f}")
                
                print(f"   {Fore.CYAN}{nombre_sitio2}: ", end='')
                
                if match['mas_barato'] == 'sitio2':
                    print(f"{Fore.GREEN}€{precio2:.2f} ✓ (más barato)")
                    productos_mas_baratos_sitio2 += 1
                    ahorros_totales += (precio1 - precio2)
                else:
                    print(f"{Fore.WHITE}€{precio2:.2f}")
                
                diferencia = match['diferencia']
                porcentaje = match['porcentaje_diferencia']
                print(f"   {Fore.YELLOW}💰 Diferencia: €{diferencia:.2f} ({porcentaje:.1f}%)")
            else:
                print(f"{Fore.WHITE}{match['producto1'].get('precio', 'N/A')}")
                print(f"   {Fore.CYAN}{nombre_sitio2}: {Fore.WHITE}{match['producto2'].get('precio', 'N/A')}")
            
            print(f"   {Fore.MAGENTA}📊 Similitud: {match['similitud']*100:.0f}%\n")
        
        # Resumen
        print(f"{Fore.GREEN}{'='*90}")
        print(f"{Fore.GREEN}📊 RESUMEN")
        print(f"{Fore.GREEN}{'='*90}")
        print(f"{Fore.WHITE}🔍 Productos comparados: {len(coincidencias)}")
        print(f"{Fore.GREEN}✓ {nombre_sitio1} más barato: {productos_mas_baratos_sitio1} productos")
        print(f"{Fore.GREEN}✓ {nombre_sitio2} más barato: {productos_mas_baratos_sitio2} productos")
        if ahorros_totales > 0:
            print(f"{Fore.YELLOW}💰 Ahorro potencial comprando lo más barato: €{ahorros_totales:.2f}\n")
        else:
            print()

def comparar_sitios(url1, url2, scraper_class, nombre_sitio1='Sitio 1', nombre_sitio2='Sitio 2', umbral=0.6):
    """
    Función auxiliar para comparar dos sitios completos
    
    Args:
        url1: URL del primer sitio
        url2: URL del segundo sitio
        scraper_class: Clase del scraper a usar
        nombre_sitio1: Nombre del primer sitio
        nombre_sitio2: Nombre del segundo sitio
        umbral: Umbral de similitud mínimo
    """
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}🔍 SCRAPEANDO SITIOS PARA COMPARAR")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    # Scrapear sitio 1
    print(f"{Fore.WHITE}📍 Scrapeando {nombre_sitio1}...")
    scraper1 = scraper_class(headless=True)
    productos1 = scraper1.scrapear_pagina_universal(url1, 'temp_sitio1')
    scraper1.close()
    print(f"{Fore.GREEN}✅ {len(productos1)} productos encontrados\n")
    
    # Scrapear sitio 2
    print(f"{Fore.WHITE}📍 Scrapeando {nombre_sitio2}...")
    scraper2 = scraper_class(headless=True)
    productos2 = scraper2.scrapear_pagina_universal(url2, 'temp_sitio2')
    scraper2.close()
    print(f"{Fore.GREEN}✅ {len(productos2)} productos encontrados\n")
    
    # Comparar
    print(f"{Fore.CYAN}🔄 Comparando productos...\n")
    comparador = ComparadorPrecios()
    coincidencias = comparador.comparar_listas(productos1, productos2, umbral)
    
    # Mostrar resultados
    comparador.mostrar_comparacion(coincidencias, nombre_sitio1, nombre_sitio2)
    
    return coincidencias
