"""
Menú avanzado con todas las funcionalidades:
- Paginación
- Base de datos
- Comparador de precios
- Programación de tareas
"""

import sys

from colorama import Fore, Style, init

from utils import normalizar_url

# Inicializar colorama
init(autoreset=True)


def pedir_url(mensaje):
    """Pide una URL. Devuelve None si se deja vacía o no es válida."""
    texto = input(f"{Fore.GREEN}{mensaje}{Style.RESET_ALL}").strip()
    if not texto:
        return None
    url = normalizar_url(texto)
    if url is None:
        print(f"{Fore.RED}✗ URL no válida: {texto}")
    return url


def pedir_numero(mensaje, por_defecto, minimo=None, maximo=None, tipo=int):
    """
    Pide un número. Si se deja vacío devuelve el valor por defecto; si no es
    un número válido avisa y usa el valor por defecto; si está fuera de rango
    lo ajusta al límite más cercano.
    """
    texto = input(f"{Fore.GREEN}{mensaje}{Style.RESET_ALL}").strip()
    if not texto:
        return por_defecto
    try:
        valor = tipo(texto.replace(',', '.') if tipo is float else texto)
    except ValueError:
        print(f"{Fore.YELLOW}⚠️  '{texto}' no es un número válido, se usa {por_defecto}")
        return por_defecto
    ajustado = valor
    if minimo is not None:
        ajustado = max(minimo, ajustado)
    if maximo is not None:
        ajustado = min(maximo, ajustado)
    if ajustado != valor:
        print(f"{Fore.YELLOW}⚠️  Valor fuera de rango, se usa {ajustado}")
    return ajustado


def mostrar_producto(p, truncar_titulo=True):
    """Imprime un producto guardado en la base de datos."""
    from precios import formatear_precio

    titulo = p['titulo'][:60] if truncar_titulo else p['titulo']
    print(f"{Fore.WHITE}{p['id']}. {titulo}")
    print(f"   💰 {formatear_precio(p['precio'], p['moneda'], p['precio_texto'])}")
    print(f"   🏪 Sitio: {p['sitio']}")
    print(f"   📅 {p['fecha_scraping']}\n")


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
    from servicios import scrapear_y_guardar

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}🌐 SCRAPING SIMPLE")
    print(f"{Fore.CYAN}{'='*70}\n")

    url = pedir_url("Ingresa la URL: ")
    if not url:
        return

    resultado = scrapear_y_guardar(url, 1)
    if resultado.datos:
        print(f"{Fore.GREEN}✅ {resultado.guardados} productos guardados en la base de datos\n")


def scrapear_paginacion():
    """Opción 2: Scraping con paginación"""
    from servicios import scrapear_y_guardar

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}📄 SCRAPING CON PAGINACIÓN")
    print(f"{Fore.CYAN}{'='*70}\n")

    url = pedir_url("Ingresa la URL base: ")
    if not url:
        return

    max_pag = pedir_numero("¿Cuántas páginas scrapear? (1-10): ", 3, minimo=1, maximo=10)

    resultado = scrapear_y_guardar(url, max_pag)
    if resultado.datos:
        print(f"{Fore.GREEN}✅ {resultado.guardados} productos guardados en la base de datos\n")

def comparar_precios():
    """Opción 3: Comparar precios entre sitios"""
    from scraper import Scraper
    from comparador import comparar_sitios
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}💰 COMPARADOR DE PRECIOS")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    print(f"{Fore.WHITE}Ejemplos:")
    print(f"{Fore.CYAN}  - PcComponentes vs Amazon (portátiles)")
    print(f"{Fore.CYAN}  - Diferentes categorías del mismo sitio\n")
    
    url1 = pedir_url("URL del primer sitio: ")
    if not url1:
        return

    url2 = pedir_url("URL del segundo sitio: ")
    if not url2:
        return
    
    nombre1 = input(f"{Fore.GREEN}Nombre del sitio 1 (ej: PcComponentes): {Style.RESET_ALL}").strip() or "Sitio 1"
    nombre2 = input(f"{Fore.GREEN}Nombre del sitio 2 (ej: Amazon): {Style.RESET_ALL}").strip() or "Sitio 2"
    
    umbral = pedir_numero("Umbral de similitud (0.5-1.0, default 0.6): ", 0.6, minimo=0.5, maximo=1.0, tipo=float)

    comparar_sitios(url1, url2, Scraper, nombre1, nombre2, umbral)

def ver_productos():
    """Opción 4: Ver productos guardados"""
    from database import ScraperDB
    
    with ScraperDB() as db:
        sitio = input(f"{Fore.GREEN}Filtrar por sitio (Enter para todos): {Style.RESET_ALL}").strip() or None
        limite = pedir_numero("Cantidad a mostrar (default 20): ", 20, minimo=1)
        
        productos = db.obtener_productos(sitio, limite)
        
        if not productos:
            print(f"\n{Fore.YELLOW}⚠️  No hay productos guardados\n")
            return
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}💾 PRODUCTOS GUARDADOS")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        for p in productos:
            mostrar_producto(p)

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
            mostrar_producto(p, truncar_titulo=False)

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
    
    dias = pedir_numero("Eliminar datos más antiguos de cuántos días? (default 30): ", 30, minimo=0)
    
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
    
    url = pedir_url("URL a scrapear: ")
    if not url:
        return

    intervalo = pedir_numero("Intervalo en minutos (default 60): ", 60, minimo=1)
    paginas = pedir_numero("Páginas a scrapear (default 1): ", 1, minimo=1)
    
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
    from scraper import Scraper
    
    prog = Programador()
    prog.cargar_tareas()
    
    if not prog.tareas:
        print(f"\n{Fore.YELLOW}⚠️  No hay tareas programadas. Crea una primero (opción 8)\n")
        return
    
    prog.iniciar(Scraper)
    
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
