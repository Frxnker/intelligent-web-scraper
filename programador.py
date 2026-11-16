"""
Programación de tareas de scraping periódicas.

Las tareas se guardan en output/tareas_programadas.json y se ejecutan en un
hilo en segundo plano mientras el programa (menú de consola o servidor web)
está abierto. Se pueden añadir y eliminar tareas con el programador en marcha:
el hilo vuelve a programarlas en su siguiente ciclo.
"""

from __future__ import annotations

import copy
import json
import threading
from datetime import datetime
from pathlib import Path

import schedule
from colorama import Fore

from config import TAREAS_PATH
from utils import truncar


class Programador:
    """Gestiona la programación de tareas de scraping."""

    def __init__(self, config_file=TAREAS_PATH, db_path=None):
        """
        Args:
            config_file: archivo JSON donde se guardan las tareas.
            db_path: base de datos donde se guardan los resultados (por defecto config.DB_PATH).
        """
        self.tareas = []
        self.activo = False
        self.thread = None
        self.config_file = Path(config_file)
        self.db_path = db_path
        # Planificador propio en lugar del global de `schedule`. Solo lo usa el hilo
        # del programador una vez arrancado; el resto de hilos le piden reprogramar.
        self._scheduler = schedule.Scheduler()
        self._trabajos = {}  # nombre de la tarea -> schedule.Job
        self._lock = threading.RLock()  # protege self.tareas, self._trabajos y el JSON
        self._reprogramar = threading.Event()
        self._parar = threading.Event()
        self._scraper_class = None

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

        with self._lock:
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
        self._reprogramar.set()
        print(f"{Fore.GREEN}✅ Tarea agregada: {nombre} (cada {intervalo_minutos} minutos)")
        return True

    def eliminar_tarea(self, nombre) -> bool:
        """Elimina una tarea por nombre. Devuelve True si existía."""
        with self._lock:
            restantes = [t for t in self.tareas if t['nombre'] != nombre]
            if len(restantes) == len(self.tareas):
                print(f"{Fore.YELLOW}⚠️  No existe ninguna tarea llamada '{nombre}'")
                return False
            self.tareas = restantes
            self.guardar_tareas()
        self._reprogramar.set()
        print(f"{Fore.YELLOW}🗑️  Tarea eliminada: {nombre}")
        return True

    def obtener_tareas(self) -> list[dict]:
        """Copia de las tareas con la fecha de su próxima ejecución (si el programador está activo)."""
        with self._lock:
            tareas = copy.deepcopy(self.tareas)
            trabajos = dict(self._trabajos)
        for tarea in tareas:
            trabajo = trabajos.get(tarea['nombre'])
            proxima = getattr(trabajo, 'next_run', None) if self.activo else None
            tarea['proxima_ejecucion'] = proxima.strftime('%Y-%m-%d %H:%M:%S') if proxima else None
        return tareas

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
        from servicios import scrapear_y_guardar

        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.YELLOW}⏰ EJECUTANDO TAREA PROGRAMADA")
        print(f"{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.WHITE}📝 Nombre: {tarea['nombre']}")
        print(f"{Fore.WHITE}🔗 URL: {tarea['url']}")
        print(f"{Fore.WHITE}🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        try:
            resultado = scrapear_y_guardar(tarea['url'], tarea['max_paginas'], scraper_class=scraper_class,
                                           sitio=tarea['nombre'], db_path=self.db_path)
            if resultado.datos:
                print(f"{Fore.GREEN}✅ Guardados {resultado.guardados} productos en la base de datos\n")

            with self._lock:
                tarea['ultima_ejecucion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                tarea['total_ejecuciones'] += 1
                self.guardar_tareas()
        except Exception as e:  # noqa: BLE001 - un fallo no debe parar el hilo del programador
            print(f"{Fore.RED}❌ Error ejecutando la tarea '{tarea['nombre']}': {e}\n")

    def programar_tareas(self, scraper_class):
        """Programa todas las tareas en el planificador."""
        self._reprogramar.clear()
        with self._lock:
            self._scheduler.clear()
            self._trabajos = {
                tarea['nombre']: self._scheduler.every(int(tarea['intervalo'])).minutes.do(
                    self.ejecutar_tarea, tarea, scraper_class
                )
                for tarea in self.tareas
            }

    def iniciar(self, scraper_class):
        """Inicia el programador en un hilo separado."""
        if self.activo:
            print(f"{Fore.YELLOW}⚠️  El programador ya está activo")
            return

        self.activo = True
        self._parar.clear()
        self._scraper_class = scraper_class
        self.programar_tareas(scraper_class)

        def run_scheduler():
            print(f"\n{Fore.GREEN}{'=' * 70}")
            print(f"{Fore.GREEN}✅ PROGRAMADOR INICIADO")
            print(f"{Fore.GREEN}{'=' * 70}")
            print(f"{Fore.WHITE}📋 Tareas activas: {len(self.tareas)}\n")

            while self.activo:
                if self._reprogramar.is_set():
                    self.programar_tareas(self._scraper_class)
                self._scheduler.run_pending()
                self._parar.wait(1)

        self.thread = threading.Thread(target=run_scheduler, name='programador', daemon=True)
        self.thread.start()

    def detener(self, esperar=False):
        """
        Detiene el programador.

        Una tarea que ya esté en marcha termina antes de parar. Con esperar=True
        se bloquea hasta que el hilo acaba (así su navegador se cierra seguro).
        """
        self.activo = False
        self._parar.set()
        if esperar and self.thread is not None:
            self.thread.join()
        with self._lock:
            self._scheduler.clear()
            self._trabajos = {}
        print(f"\n{Fore.YELLOW}⏸️  Programador detenido")

    def guardar_tareas(self):
        """Guarda las tareas en el archivo JSON."""
        with self._lock:
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
        with self._lock:
            self.tareas = tareas
        print(f"{Fore.GREEN}✅ Cargadas {len(self.tareas)} tareas guardadas")
