"""
Ejecución en segundo plano de los trabajos largos de la API (scraping y comparación).

Cada trabajo (job) corre en un hilo de un ThreadPoolExecutor con un número
máximo de trabajos simultáneos; el resto esperan en estado 'pendiente'. El
estado se guarda en memoria, así que se pierde al reiniciar el servidor (el
registro permanente de cada ejecución está en la tabla scraping_jobs).
"""

import threading
import traceback
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from servicios import OperacionCancelada

ESTADOS_FINALES = ('terminado', 'error')


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _mensaje(error: Exception) -> str:
    """Primera línea del mensaje de la excepción (las de Selenium traen el stacktrace detrás)."""
    texto = str(error).strip()
    return texto.splitlines()[0] if texto else type(error).__name__


class Job:
    """Estado de un trabajo. Lo actualiza su hilo y lo leen las peticiones a la API."""

    def __init__(self, tipo: str, unidad: str):
        self.id = uuid.uuid4().hex
        self.tipo = tipo
        self.unidad = unidad  # 'Página' o 'Sitio', para el texto del progreso
        self.estado = 'pendiente'
        self.actual = 0
        self.total = 0
        self.productos = 0
        self.error = None
        self.resultado = None
        self.creado = _ahora()
        self.iniciado = None
        self.terminado = None
        self._cancelado = threading.Event()
        self._lock = threading.Lock()

    def avanzar(self, actual: int, total: int):
        """
        Función de progreso que se pasa a servicios/paginación/comparador.

        Se llama antes de cada página; si el job se ha cancelado, interrumpe el trabajo.
        """
        if self._cancelado.is_set():
            raise OperacionCancelada('Cancelado: el servidor se está cerrando')
        with self._lock:
            self.actual, self.total = actual, total

    def cancelar(self):
        self._cancelado.set()

    @property
    def cancelado(self) -> bool:
        return self._cancelado.is_set()

    def actualizar(self, **campos):
        with self._lock:
            for nombre, valor in campos.items():
                setattr(self, nombre, valor)

    def a_dict(self) -> dict:
        with self._lock:
            if self.total:
                texto = f'{self.unidad} {self.actual} de {self.total}'
            else:
                texto = 'En cola' if self.estado == 'pendiente' else ''
            return {
                'id': self.id,
                'tipo': self.tipo,
                'estado': self.estado,
                'progreso': {'actual': self.actual, 'total': self.total, 'texto': texto},
                'productos': self.productos,
                'error': self.error,
                'resultado': self.resultado if self.estado == 'terminado' else None,
                'creado': self.creado,
                'iniciado': self.iniciado,
                'terminado': self.terminado,
            }


class GestorJobs:
    """Lanza trabajos en segundo plano y guarda su estado (los últimos `max_guardados`)."""

    def __init__(self, max_simultaneos: int = 2, max_guardados: int = 200):
        self._jobs = OrderedDict()
        self._lock = threading.Lock()
        self._max_guardados = max_guardados
        self._executor = ThreadPoolExecutor(max_workers=max_simultaneos, thread_name_prefix='job')
        self._cerrado = False

    def lanzar(self, tipo: str, unidad: str, funcion, *args) -> Job:
        """
        Crea un job y lo pone en cola.

        `funcion(job, *args)` hace el trabajo, usa `job.avanzar` como función de
        progreso y devuelve (número de productos, resultado serializable a JSON).
        """
        job = Job(tipo, unidad)
        with self._lock:
            if self._cerrado:
                raise RuntimeError('El servidor se está cerrando')
            self._jobs[job.id] = job
            self._purgar()
        self._executor.submit(self._ejecutar, job, funcion, args)
        return job

    def obtener(self, job_id: str):
        with self._lock:
            return self._jobs.get(job_id)

    def _purgar(self):
        """Olvida los jobs terminados más antiguos cuando hay demasiados."""
        while len(self._jobs) > self._max_guardados:
            antiguo = next((id_ for id_, job in self._jobs.items() if job.estado in ESTADOS_FINALES), None)
            if antiguo is None:
                return
            del self._jobs[antiguo]

    def _ejecutar(self, job: Job, funcion, args):
        if job.cancelado:
            job.actualizar(estado='error', error='Cancelado: el servidor se está cerrando', terminado=_ahora())
            return
        job.actualizar(estado='en_curso', iniciado=_ahora())
        try:
            productos, resultado = funcion(job, *args)
        except OperacionCancelada as e:
            job.actualizar(estado='error', error=str(e), terminado=_ahora())
        except Exception as e:  # noqa: BLE001 - el error se guarda en el job para mostrarlo en la web
            if self._cerrado:
                # Al pulsar Ctrl+C la consola también cierra chromedriver: no es un fallo real
                print(f'Job {job.id[:8]} interrumpido al cerrar el servidor: {_mensaje(e)}')
            else:
                traceback.print_exc()
            job.actualizar(estado='error', error=_mensaje(e), terminado=_ahora())
        else:
            job.actualizar(estado='terminado', productos=productos, resultado=resultado, terminado=_ahora())

    def apagar(self):
        """
        Cancela los jobs pendientes, pide a los que están en curso que paren en la
        siguiente página y espera a que terminen (así sus navegadores se cierran).
        """
        with self._lock:
            self._cerrado = True
            jobs = list(self._jobs.values())
        for job in jobs:
            job.cancelar()
        self._executor.shutdown(wait=True, cancel_futures=True)
        for job in jobs:
            if job.estado == 'pendiente':
                job.actualizar(estado='error', error='Cancelado: el servidor se cerró', terminado=_ahora())
