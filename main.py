"""
Menú avanzado con todas las funcionalidades:
- Paginación
- Base de datos
- Comparador de precios
- Programación de tareas
"""

from colorama import Fore, Style, init
import sys
from urllib.parse import urlparse

# Inicializar colorama
init(autoreset=True)

def print_banner():
    """Banner principal"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}                    🚀 WEB SCRAPER UNIVERSAL AVANZADO 🚀")
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.WHITE}       Con paginación, base de datos, comparador y automatización")
    print(f"{Fore.CYAN}{'='*80}\n")

def menu_principal():
    """Menú principal con todas las opciones"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}                           MENÚ PRINCIPAL")
    print(f"{Fore.CYAN}{'='*80}\n")
    
    print(f"{Fore.GREEN}📌 SCRAPING BÁSICO:")
    print(f"{Fore.WHITE}  1. 🌐 Scrapear URL (una página)")
    print(f"{Fore.WHITE}  2. 📄 Scrapear con paginación (múltiples páginas)")
    
    print(f"\n{Fore.GREEN}📌 COMPARACIÓN:")
    print(f"{Fore.WHITE}  3. 💰 Comparar precios entre dos sitios")
    
    print(f"\n{Fore.GREEN}📌 BASE DE DATOS:")
    print(f"{Fore.WHITE}  4. 💾 Ver productos guardados")
    print(f"{Fore.WHITE}  5. 🔍 Buscar productos")
    print(f"{Fore.WHITE}  6. 📈 Ver estadísticas")
    print(f"{Fore.WHITE}  7. 🗑️  Limpiar datos antiguos")
    
    print(f"\n{Fore.GREEN}📌 AUTOMATIZACIÓN:")
    print(f"{Fore.WHITE}  8. ⏰ Crear tarea programada")
    print(f"{Fore.WHITE}  9. 📋 Ver tareas programadas")
    print(f"{Fore.WHITE}  10. ▶️  Iniciar programador")
    print(f"{Fore.WHITE}  11. 🗑️  Eliminar tarea")
    
    print(f"\n{Fore.WHITE}  12. ❌ Salir")
    print(f"{Fore.CYAN}{'='*80}\n")

def scrapear_simple():
    """Opción 1: Scraping simple de una página"""
    from scraper_selenium import SeleniumScraper
    from database import ScraperDB
    import time
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}🌐 SCRAPING SIMPLE")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    url = input(f"{Fore.GREEN}Ingresa la URL: {Style.RESET_ALL}").strip()
    if not url:
        return
    
    if not url.startswith('http'):
        url = 'https://' + url
    
    inicio = time.time()
    scraper = SeleniumScraper(headless=True)
    
    domain = urlparse(url).netloc.replace('www.', '').replace('.', '_')
    datos = scraper.scrapear_pagina_universal(url, domain)
    scraper.close()
    
    if datos:
        with ScraperDB() as db:
            guardados = db.insertar_productos_bulk(datos, domain)
            duracion = time.time() - inicio
            db.registrar_job(url, domain, len(datos), duracion=duracion)
            print(f"{Fore.GREEN}✅ {guardados} productos guardados en la base de datos\n")

def scrapear_paginacion():
    """Opción 2: Scraping con paginación"""
    from scraper_selenium import SeleniumScraper
    from paginacion import scrapear_con_paginacion
    from database import ScraperDB
    import time
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}📄 SCRAPING CON PAGINACIÓN")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    url = input(f"{Fore.GREEN}Ingresa la URL base: {Style.RESET_ALL}").strip()
    if not url:
        return
    
    if not url.startswith('http'):
        url = 'https://' + url
    
    try:
        max_pag = int(input(f"{Fore.GREEN}¿Cuántas páginas scrapear? (1-10): {Style.RESET_ALL}"))
        max_pag = max(1, min(max_pag, 10))
    except:
        max_pag = 3
    
    inicio = time.time()
    scraper = SeleniumScraper(headless=True)
    datos = scrapear_con_paginacion(scraper, url, max_pag)
    scraper.close()
    
    if datos:
        with ScraperDB() as db:
            domain = urlparse(url).netloc.replace('www.', '').replace('.', '_')
            guardados = db.insertar_productos_bulk(datos, domain)
            duracion = time.time() - inicio
            db.registrar_job(url, domain, len(datos), duracion=duracion)
            print(f"{Fore.GREEN}✅ {guardados} productos guardados en la base de datos\n")

def comparar_precios():
    """Opción 3: Comparar precios entre sitios"""
    from scraper_selenium import SeleniumScraper
    from comparador import comparar_sitios
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}💰 COMPARADOR DE PRECIOS")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    print(f"{Fore.WHITE}Ejemplos:")
    print(f"{Fore.CYAN}  - PcComponentes vs Amazon (portátiles)")
    print(f"{Fore.CYAN}  - Diferentes categorías del mismo sitio\n")
    
    url1 = input(f"{Fore.GREEN}URL del primer sitio: {Style.RESET_ALL}").strip()
    if not url1:
        return
    if not url1.startswith('http'):
        url1 = 'https://' + url1
    
    url2 = input(f"{Fore.GREEN}URL del segundo sitio: {Style.RESET_ALL}").strip()
    if not url2:
        return
    if not url2.startswith('http'):
        url2 = 'https://' + url2
    
    nombre1 = input(f"{Fore.GREEN}Nombre del sitio 1 (ej: PcComponentes): {Style.RESET_ALL}").strip() or "Sitio 1"
    nombre2 = input(f"{Fore.GREEN}Nombre del sitio 2 (ej: Amazon): {Style.RESET_ALL}").strip() or "Sitio 2"
    
    try:
        umbral = float(input(f"{Fore.GREEN}Umbral de similitud (0.5-1.0, default 0.6): {Style.RESET_ALL}") or "0.6")
        umbral = max(0.5, min(umbral, 1.0))
    except:
        umbral = 0.6
    
    comparar_sitios(url1, url2, SeleniumScraper, nombre1, nombre2, umbral)

def ver_productos():
    """Opción 4: Ver productos guardados"""
    from database import ScraperDB
    
    with ScraperDB() as db:
        sitio = input(f"{Fore.GREEN}Filtrar por sitio (Enter para todos): {Style.RESET_ALL}").strip() or None
        try:
            limite = int(input(f"{Fore.GREEN}Cantidad a mostrar (default 20): {Style.RESET_ALL}") or "20")
        except:
            limite = 20
        
        productos = db.obtener_productos(sitio, limite)
        
        if not productos:
            print(f"\n{Fore.YELLOW}⚠️  No hay productos guardados\n")
            return
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}💾 PRODUCTOS GUARDADOS")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        for p in productos:
            print(f"{Fore.WHITE}{p['id']}. {p['titulo'][:60]}")
            print(f"   💰 {p['precio']}")
            print(f"   🏪 Sitio: {p['sitio']}")
            print(f"   📅 {p['fecha_scraping']}\n")

def buscar_productos():
    """Opción 5: Buscar productos"""
    from database import ScraperDB
    
    query = input(f"{Fore.GREEN}Buscar producto: {Style.RESET_ALL}").strip()
    if not query:
        return
    
    with ScraperDB() as db:
        productos = db.buscar_productos(query)
        
        if not productos:
            print(f"\n{Fore.YELLOW}⚠️  No se encontraron productos con '{query}'\n")
            return
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}🔍 RESULTADOS DE BÚSQUEDA: '{query}'")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        for p in productos:
            print(f"{Fore.WHITE}{p['id']}. {p['titulo']}")
            print(f"   💰 {p['precio']}")
            print(f"   🏪 Sitio: {p['sitio']}")
            print(f"   📅 {p['fecha_scraping']}\n")

def ver_estadisticas():
    """Opción 6: Ver estadísticas"""
    from database import ScraperDB
    
    with ScraperDB() as db:
        stats = db.obtener_estadisticas()
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}📈 ESTADÍSTICAS")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        print(f"{Fore.WHITE}📦 Total de productos: {Fore.GREEN}{stats['total_productos']}")
        print(f"{Fore.WHITE}🔄 Total de scraping jobs: {Fore.GREEN}{stats['total_jobs']}\n")
        
        if stats['por_sitio']:
            print(f"{Fore.CYAN}📊 Productos por sitio:")
            for sitio, count in stats['por_sitio'].items():
                print(f"{Fore.WHITE}  {sitio}: {Fore.GREEN}{count}")
        print()

def limpiar_datos():
    """Opción 7: Limpiar datos antiguos"""
    from database import ScraperDB
    
    try:
        dias = int(input(f"{Fore.GREEN}Eliminar datos más antiguos de cuántos días? (default 30): {Style.RESET_ALL}") or "30")
    except:
        dias = 30
    
    confirmar = input(f"{Fore.YELLOW}⚠️  ¿Estás seguro? (s/n): {Style.RESET_ALL}").strip().lower()
    if confirmar != 's':
        print(f"{Fore.CYAN}Operación cancelada")
        return
    
    with ScraperDB() as db:
        eliminados = db.limpiar_datos_antiguos(dias)
        print(f"{Fore.GREEN}✅ {eliminados} productos eliminados\n")

def crear_tarea():
    """Opción 8: Crear tarea programada"""
    from programador import Programador
    
    prog = Programador()
    prog.cargar_tareas()
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}⏰ CREAR TAREA PROGRAMADA")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    nombre = input(f"{Fore.GREEN}Nombre de la tarea: {Style.RESET_ALL}").strip()
    if not nombre:
        return
    
    url = input(f"{Fore.GREEN}URL a scrapear: {Style.RESET_ALL}").strip()
    if not url:
        return
    if not url.startswith('http'):
        url = 'https://' + url
    
    try:
        intervalo = int(input(f"{Fore.GREEN}Intervalo en minutos (default 60): {Style.RESET_ALL}") or "60")
    except:
        intervalo = 60
    
    try:
        paginas = int(input(f"{Fore.GREEN}Páginas a scrapear (default 1): {Style.RESET_ALL}") or "1")
    except:
        paginas = 1
    
    prog.agregar_tarea(url, nombre, intervalo, paginas)
    print()

def ver_tareas():
    """Opción 9: Ver tareas programadas"""
    from programador import Programador
    
    prog = Programador()
    prog.cargar_tareas()
    prog.listar_tareas()

def iniciar_programador():
    """Opción 10: Iniciar programador"""
    from programador import Programador
    from scraper_selenium import SeleniumScraper
    
    prog = Programador()
    prog.cargar_tareas()
    
    if not prog.tareas:
        print(f"\n{Fore.YELLOW}⚠️  No hay tareas programadas. Crea una primero (opción 8)\n")
        return
    
    prog.iniciar(SeleniumScraper)
    
    try:
        input(f"{Fore.CYAN}Presiona Enter para detener el programador...{Style.RESET_ALL}")
    except KeyboardInterrupt:
        pass
    
    prog.detener()

def eliminar_tarea():
    """Opción 11: Eliminar tarea"""
    from programador import Programador
    
    prog = Programador()
    prog.cargar_tareas()
    prog.listar_tareas()
    
    if not prog.tareas:
        return
    
    nombre = input(f"{Fore.GREEN}Nombre de la tarea a eliminar: {Style.RESET_ALL}").strip()
    if nombre:
        prog.eliminar_tarea(nombre)

def main():
    """Función principal"""
    print_banner()
    
    while True:
        menu_principal()
        
        try:
            opcion = input(f"{Fore.GREEN}Selecciona una opción (1-12): {Style.RESET_ALL}").strip()
            
            if opcion == '1':
                scrapear_simple()
            elif opcion == '2':
                scrapear_paginacion()
            elif opcion == '3':
                comparar_precios()
            elif opcion == '4':
                ver_productos()
            elif opcion == '5':
                buscar_productos()
            elif opcion == '6':
                ver_estadisticas()
            elif opcion == '7':
                limpiar_datos()
            elif opcion == '8':
                crear_tarea()
            elif opcion == '9':
                ver_tareas()
            elif opcion == '10':
                iniciar_programador()
            elif opcion == '11':
                eliminar_tarea()
            elif opcion == '12':
                print(f"\n{Fore.CYAN}👋 ¡Hasta luego!")
                sys.exit(0)
            else:
                print(f"{Fore.RED}✗ Opción inválida. Selecciona 1-12.")
                continue
            
            continuar = input(f"\n{Fore.GREEN}¿Continuar? (s/n): {Style.RESET_ALL}").strip().lower()
            if continuar != 's':
                print(f"\n{Fore.CYAN}👋 ¡Hasta luego!")
                break
        
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}⚠️  Operación cancelada")
            print(f"{Fore.CYAN}👋 ¡Hasta luego!")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Fore.RED}✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
