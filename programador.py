"""
Programación de tareas de scraping periódicas.

Las tareas se guardan en output/tareas_programadas.json y se ejecutan en un
hilo en segundo plano mientras el programa está abierto.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path

import schedule
from colorama import Fore

from config import TAREAS_PATH
from utils import nombre_desde_url, truncar


class Programador:
    """Gestiona la programación de tareas de scraping."""

    def __init__(self, config_file=TAREAS_PATH):
        self.tareas = []
        self.activo = False
        self.thread = None
        self.config_file = Path(config_file)
        # Planificador propio en lugar del global de `schedule`
        self._scheduler = schedule.Scheduler()

    def agregar_tarea(self, url, nombre, intervalo_minutos=60, max_paginas=1) -> bool:
        """
        Agrega una tarea programada.

        Args:
            url: URL a scrapear.
            nombre: nombre identificador de la tarea (único).
            intervalo_minutos: intervalo en minutos (60 = cada hora).
            max_paginas: número de páginas a scrapear.

        Returns:
            True si se agregó, False si ya existía una tarea con ese nombre.
        """
        if intervalo_minutos < 1:
            raise ValueError('El intervalo debe ser de al menos 1 minuto')
        if max_paginas < 1:
            raise ValueError('Hay que scrapear al menos 1 página')
        if any(t['nombre'] == nombre for t in self.tareas):
            print(f"{Fore.YELLOW}⚠️  Ya existe una tarea llamada '{nombre}'")
            return False

        self.tareas.append({
            'url': url,
            'nombre': nombre,
            'intervalo': intervalo_minutos,
            'max_paginas': max_paginas,
            'ultima_ejecucion': None,
            'total_ejecuciones': 0,
        })
        self.guardar_tareas()
        print(f"{Fore.GREEN}✅ Tarea agregada: {nombre} (cada {intervalo_minutos} minutos)")
        return True

    def eliminar_tarea(self, nombre) -> bool:
        """Elimina una tarea por nombre. Devuelve True si existía."""
        restantes = [t for t in self.tareas if t['nombre'] != nombre]
        if len(restantes) == len(self.tareas):
            print(f"{Fore.YELLOW}⚠️  No existe ninguna tarea llamada '{nombre}'")
            return False
        self.tareas = restantes
        self.guardar_tareas()
        print(f"{Fore.YELLOW}🗑️  Tarea eliminada: {nombre}")
        return True

    def listar_tareas(self):
        """Lista todas las tareas programadas."""
        if not self.tareas:
            print(f"{Fore.YELLOW}📋 No hay tareas programadas\n")
            return

        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.YELLOW}📋 TAREAS PROGRAMADAS")
        print(f"{Fore.CYAN}{'=' * 70}\n")

        for i, tarea in enumerate(self.tareas, 1):
            print(f"{Fore.WHITE}{i}. {tarea['nombre']}")
            print(f"   🔗 URL: {truncar(tarea['url'], 60)}")
            print(f"   ⏰ Intervalo: {tarea['intervalo']} minutos")
            print(f"   📄 Páginas: {tarea['max_paginas']}")
            print(f"   📊 Ejecuciones: {tarea['total_ejecuciones']}")
            if tarea['ultima_ejecucion']:
                print(f"   🕐 Última: {tarea['ultima_ejecucion']}")
            print()

    def ejecutar_tarea(self, tarea, scraper_class):
        """Ejecuta una tarea de scraping y guarda los resultados en la base de datos."""
        from database import ScraperDB
        from paginacion import scrapear_con_paginacion

        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.YELLOW}⏰ EJECUTANDO TAREA PROGRAMADA")
        print(f"{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.WHITE}📝 Nombre: {tarea['nombre']}")
        print(f"{Fore.WHITE}🔗 URL: {tarea['url']}")
        print(f"{Fore.WHITE}🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        inicio = time.time()
        try:
            with scraper_class(headless=True) as scraper:
                if tarea['max_paginas'] > 1:
                    datos = scrapear_con_paginacion(scraper, tarea['url'], tarea['max_paginas'])
                else:
                    datos = scraper.scrapear_pagina_universal(tarea['url'], nombre_desde_url(tarea['url']))

            if datos:
                with ScraperDB() as db:
                    guardados = db.insertar_productos_bulk(datos, tarea['nombre'])
                    db.registrar_job(tarea['url'], tarea['nombre'], len(datos), duracion=time.time() - inicio)
                print(f"{Fore.GREEN}✅ Guardados {guardados} productos en la base de datos\n")

            tarea['ultima_ejecucion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tarea['total_ejecuciones'] += 1
            self.guardar_tareas()
        except Exception as e:  # noqa: BLE001 - un fallo no debe parar el hilo del programador
            print(f"{Fore.RED}❌ Error ejecutando la tarea '{tarea['nombre']}': {e}\n")

    def programar_tareas(self, scraper_class):
        """Programa todas las tareas en el planificador."""
        self._scheduler.clear()
        for tarea in self.tareas:
            self._scheduler.every(int(tarea['intervalo'])).minutes.do(self.ejecutar_tarea, tarea, scraper_class)

    def iniciar(self, scraper_class):
        """Inicia el programador en un hilo separado."""
        if self.activo:
            print(f"{Fore.YELLOW}⚠️  El programador ya está activo")
            return

        self.activo = True
        self.programar_tareas(scraper_class)

        def run_scheduler():
            print(f"\n{Fore.GREEN}{'=' * 70}")
            print(f"{Fore.GREEN}✅ PROGRAMADOR INICIADO")
            print(f"{Fore.GREEN}{'=' * 70}")
            print(f"{Fore.WHITE}📋 Tareas activas: {len(self.tareas)}")
            print(f"{Fore.CYAN}💡 Presiona Enter para detener\n")

            while self.activo:
                self._scheduler.run_pending()
                time.sleep(1)

        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()

    def detener(self):
        """Detiene el programador (una tarea que ya esté en marcha termina antes de parar)."""
        self.activo = False
        self._scheduler.clear()
        print(f"\n{Fore.YELLOW}⏸️  Programador detenido")

    def guardar_tareas(self):
        """Guarda las tareas en el archivo JSON."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.tareas, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"{Fore.RED}✗ No se pudieron guardar las tareas en {self.config_file}: {e}")

    def cargar_tareas(self):
        """Carga las tareas desde el archivo JSON."""
        if not self.config_file.exists():
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                tareas = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"{Fore.RED}✗ Error cargando tareas de {self.config_file}: {e}")
            self.tareas = []
            return
        if not isinstance(tareas, list):
            print(f"{Fore.RED}✗ {self.config_file} no contiene una lista de tareas; se ignora")
            self.tareas = []
            return
        self.tareas = tareas
        print(f"{Fore.GREEN}✅ Cargadas {len(self.tareas)} tareas guardadas")
