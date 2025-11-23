"""
Módulo de programación de tareas para scraping automático
"""
import schedule
import time
from datetime import datetime
from colorama import Fore, Style
import threading
import json
from pathlib import Path

class Programador:
    """Gestiona la programación de tareas de scraping"""
    
    def __init__(self):
        self.tareas = []
        self.activo = False
        self.thread = None
        self.config_file = 'output/tareas_programadas.json'
    
    def agregar_tarea(self, url, nombre, intervalo_minutos=60, max_paginas=1):
        """
        Agrega una tarea programada
        
        Args:
            url: URL a scrapear
            nombre: Nombre identificador de la tarea
            intervalo_minutos: Intervalo en minutos (60 = cada hora)
            max_paginas: Número de páginas a scrapear
        """
        tarea = {
            'url': url,
            'nombre': nombre,
            'intervalo': intervalo_minutos,
            'max_paginas': max_paginas,
            'ultima_ejecucion': None,
            'total_ejecuciones': 0
        }
        
        self.tareas.append(tarea)
        self.guardar_tareas()
        print(f"{Fore.GREEN}✅ Tarea agregada: {nombre} (cada {intervalo_minutos} minutos)")
    
    def eliminar_tarea(self, nombre):
        """Elimina una tarea por nombre"""
        self.tareas = [t for t in self.tareas if t['nombre'] != nombre]
        self.guardar_tareas()
        print(f"{Fore.YELLOW}🗑️  Tarea eliminada: {nombre}")
    
    def listar_tareas(self):
        """Lista todas las tareas programadas"""
        if not self.tareas:
            print(f"{Fore.YELLOW}📋 No hay tareas programadas\n")
            return
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}📋 TAREAS PROGRAMADAS")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        for i, tarea in enumerate(self.tareas, 1):
            print(f"{Fore.WHITE}{i}. {tarea['nombre']}")
            print(f"   🔗 URL: {tarea['url'][:60]}...")
            print(f"   ⏰ Intervalo: {tarea['intervalo']} minutos")
            print(f"   📄 Páginas: {tarea['max_paginas']}")
            print(f"   📊 Ejecuciones: {tarea['total_ejecuciones']}")
            if tarea['ultima_ejecucion']:
                print(f"   🕐 Última: {tarea['ultima_ejecucion']}")
            print()
    
    def ejecutar_tarea(self, tarea, scraper_class):
        """Ejecuta una tarea de scraping"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}⏰ EJECUTANDO TAREA PROGRAMADA")
        print(f"{Fore.CYAN}{'='*70}")
        print(f"{Fore.WHITE}📝 Nombre: {tarea['nombre']}")
        print(f"{Fore.WHITE}🔗 URL: {tarea['url']}")
        print(f"{Fore.WHITE}🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            # Importar módulos necesarios
            from database import ScraperDB
            from paginacion import scrapear_con_paginacion
            
            # Crear scraper
            scraper = scraper_class(headless=True)
            
            # Scrapear con paginación
            if tarea['max_paginas'] > 1:
                datos = scrapear_con_paginacion(scraper, tarea['url'], tarea['max_paginas'])
            else:
                from urllib.parse import urlparse
                domain = urlparse(tarea['url']).netloc.replace('www.', '').replace('.', '_')
                datos = scraper.scrapear_pagina_universal(tarea['url'], domain)
            
            # Guardar en base de datos
            if datos:
                with ScraperDB() as db:
                    guardados = db.insertar_productos_bulk(datos, tarea['nombre'])
                    db.registrar_job(tarea['url'], tarea['nombre'], len(datos))
                    print(f"{Fore.GREEN}✅ Guardados {guardados} productos en la base de datos\n")
            
            # Actualizar tarea
            tarea['ultima_ejecucion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tarea['total_ejecuciones'] += 1
            self.guardar_tareas()
            
            scraper.close()
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error ejecutando tarea: {str(e)}\n")
    
    def programar_tareas(self, scraper_class):
        """Programa todas las tareas en el scheduler"""
        schedule.clear()
        
        for tarea in self.tareas:
            intervalo = tarea['intervalo']
            
            # Programar según el intervalo
            if intervalo < 60:
                schedule.every(intervalo).minutes.do(
                    lambda t=tarea: self.ejecutar_tarea(t, scraper_class)
                )
            elif intervalo == 60:
                schedule.every().hour.do(
                    lambda t=tarea: self.ejecutar_tarea(t, scraper_class)
                )
            elif intervalo == 1440:  # 24 horas
                schedule.every().day.do(
                    lambda t=tarea: self.ejecutar_tarea(t, scraper_class)
                )
            else:
                schedule.every(intervalo).minutes.do(
                    lambda t=tarea: self.ejecutar_tarea(t, scraper_class)
                )
    
    def iniciar(self, scraper_class):
        """Inicia el programador en un thread separado"""
        if self.activo:
            print(f"{Fore.YELLOW}⚠️  El programador ya está activo")
            return
        
        self.activo = True
        self.programar_tareas(scraper_class)
        
        def run_scheduler():
            print(f"\n{Fore.GREEN}{'='*70}")
            print(f"{Fore.GREEN}✅ PROGRAMADOR INICIADO")
            print(f"{Fore.GREEN}{'='*70}")
            print(f"{Fore.WHITE}📋 Tareas activas: {len(self.tareas)}")
            print(f"{Fore.CYAN}💡 Presiona Ctrl+C para detener\n")
            
            while self.activo:
                schedule.run_pending()
                time.sleep(1)
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
    
    def detener(self):
        """Detiene el programador"""
        self.activo = False
        schedule.clear()
        print(f"\n{Fore.YELLOW}⏸️  Programador detenido")
    
    def guardar_tareas(self):
        """Guarda las tareas en un archivo JSON"""
        Path(self.config_file).parent.mkdir(exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.tareas, f, indent=2, ensure_ascii=False)
    
    def cargar_tareas(self):
        """Carga las tareas desde el archivo JSON"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.tareas = json.load(f)
                print(f"{Fore.GREEN}✅ Cargadas {len(self.tareas)} tareas guardadas")
        except Exception as e:
            print(f"{Fore.RED}Error cargando tareas: {e}")
            self.tareas = []
