"""
API de la interfaz web y servidor de los archivos estáticos.

Se crea con crear_app(); servidor.py la arranca con Uvicorn. Toda la lógica
(scraping, base de datos, comparación, tareas) está en los módulos del
proyecto; aquí solo se validan las entradas y se lanzan los trabajos largos en
segundo plano.
"""

import asyncio
import io
import json
import math
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

import config
from comparador import ComparadorPrecios, comparar_sitios
from database import ScraperDB
from programador import Programador
from servicios import scrapear_y_guardar
from utils import escribir_csv
from web.esquemas import (
    ConsultaExportar,
    ConsultaProductos,
    FiltrosProductos,
    SolicitudComparar,
    SolicitudScrape,
    SolicitudTarea,
)
from web.jobs import GestorJobs

STATIC_DIR = config.RECURSOS_DIR / 'web' / 'static'
HOSTS_LOCALES = ['127.0.0.1', 'localhost']
MUESTRA_RESULTADO = 20  # productos que se devuelven en el resultado de un scraping
ULTIMOS_JOBS = 10

# Mensajes de validación en español, por tipo de error de Pydantic
MENSAJES_VALIDACION = {
    'missing': 'Campo obligatorio',
    'extra_forbidden': 'Campo no permitido',
    'greater_than_equal': 'Debe ser mayor o igual que {ge}',
    'less_than_equal': 'Debe ser menor o igual que {le}',
    'greater_than': 'Debe ser mayor que {gt}',
    'less_than': 'Debe ser menor que {lt}',
    'int_parsing': 'Debe ser un número entero',
    'int_from_float': 'Debe ser un número entero',
    'int_type': 'Debe ser un número entero',
    'float_parsing': 'Debe ser un número',
    'float_type': 'Debe ser un número',
    'string_type': 'Debe ser un texto',
    'string_too_long': 'Debe tener como máximo {max_length} caracteres',
    'literal_error': 'Debe ser uno de estos valores: {expected}',
    'json_invalid': 'El cuerpo de la petición no es un JSON válido',
    'model_attributes_type': 'El cuerpo de la petición debe ser un objeto JSON',
    'dict_type': 'El cuerpo de la petición debe ser un objeto JSON',
}


def _numero_legible(valor):
    """1.0 -> '1', 0.5 -> '0,5' (los límites numéricos de los mensajes, en formato español)."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).replace('.', ',')


def _detalle_validacion(error: dict) -> dict:
    """Convierte un error de Pydantic en {'campo', 'mensaje'} legible."""
    tipo = error.get('type', '')
    contexto = {clave: _numero_legible(valor) for clave, valor in (error.get('ctx') or {}).items()}
    ubicacion = [str(parte) for parte in error.get('loc', ()) if parte not in ('body', 'query', 'path')]

    if tipo == 'value_error':
        mensaje = str(contexto.get('error', error.get('msg', '')))
    elif tipo == 'string_too_short':
        minimo = (error.get('ctx') or {}).get('min_length', 1)
        mensaje = 'No puede estar vacío' if minimo == 1 else f'Debe tener al menos {minimo} caracteres'
    elif tipo == 'missing' and not ubicacion:
        mensaje = 'Falta el cuerpo de la petición'
    elif tipo in MENSAJES_VALIDACION:
        try:
            mensaje = MENSAJES_VALIDACION[tipo].format(**contexto).replace(' or ', ' o ')
        except (KeyError, IndexError):
            mensaje = error.get('msg', 'Valor no válido')
    else:
        mensaje = error.get('msg', 'Valor no válido')

    if tipo == 'json_invalid':
        ubicacion = []
    return {'campo': '.'.join(ubicacion) or None, 'mensaje': mensaje}


def _resumir_coincidencia(match: dict) -> dict:
    """Coincidencia del comparador sin los campos que la web no usa."""
    def producto(p):
        return {campo: p.get(campo) for campo in ('titulo', 'precio', 'enlace', 'imagen')}

    return {
        **{clave: valor for clave, valor in match.items() if clave not in ('producto1', 'producto2')},
        'producto1': producto(match['producto1']),
        'producto2': producto(match['producto2']),
    }


def crear_app(*, db_path=None, tareas_path=None, scraper_class=None, iniciar_programador=True,
              max_jobs_simultaneos=None, hosts_permitidos=None) -> FastAPI:
    """
    Crea la aplicación.

    Args:
        db_path: base de datos (por defecto config.DB_PATH).
        tareas_path: archivo de tareas programadas (por defecto config.TAREAS_PATH).
        scraper_class: clase del scraper (por defecto scraper.Scraper). Los tests pasan uno falso.
        iniciar_programador: arrancar el hilo del programador de tareas con el servidor.
        max_jobs_simultaneos: scrapings en paralelo (por defecto config.MAX_JOBS_SIMULTANEOS).
        hosts_permitidos: cabeceras Host aceptadas (por defecto solo 127.0.0.1 y localhost).
    """
    if scraper_class is None:
        from scraper import Scraper
        scraper_class = Scraper
    db_path = Path(db_path or config.DB_PATH)
    gestor = GestorJobs(max_jobs_simultaneos or config.MAX_JOBS_SIMULTANEOS)
    programador = Programador(tareas_path or config.TAREAS_PATH, db_path=db_path)
    programador.cargar_tareas()

    def abrir_db() -> ScraperDB:
        return ScraperDB(db_path)

    @asynccontextmanager
    async def ciclo_de_vida(app):
        abrir_db().cerrar()  # crea la base de datos o la migra antes de aceptar peticiones
        if iniciar_programador:
            programador.iniciar(scraper_class)
        try:
            yield
        finally:
            # Se espera a los trabajos en curso para que sus navegadores se cierren
            await asyncio.to_thread(gestor.apagar)
            if programador.activo:
                await asyncio.to_thread(programador.detener, True)

    app = FastAPI(
        title='Intelligent Web Scraper',
        description='API local para scrapear listados, consultar productos, comparar precios y programar tareas.',
        version='1.0.0',
        lifespan=ciclo_de_vida,
    )
    app.state.gestor = gestor
    app.state.programador = programador
    app.state.db_path = db_path
    # Evita que otras webs abiertas en el navegador usen la API mediante DNS rebinding
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts_permitidos or HOSTS_LOCALES)

    # ------------------------------------------------------------------
    # Errores: siempre {"error": "...", "detalles": [...]}
    # ------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def error_validacion(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,  # el nombre de la constante cambia entre versiones de Starlette
            content={'error': 'Datos no válidos', 'detalles': [_detalle_validacion(e) for e in exc.errors()]},
        )

    @app.exception_handler(StarletteHTTPException)
    async def error_http(request: Request, exc: StarletteHTTPException):
        traducciones = {'Not Found': 'Recurso no encontrado', 'Method Not Allowed': 'Método no permitido'}
        mensaje = traducciones.get(exc.detail, exc.detail) if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content={'error': mensaje},
                            headers=getattr(exc, 'headers', None))

    # ------------------------------------------------------------------
    # Trabajos en segundo plano
    # ------------------------------------------------------------------

    def trabajo_scrape(job, url, paginas):
        resultado = scrapear_y_guardar(url, paginas, scraper_class=scraper_class, db_path=db_path,
                                       progreso=job.avanzar)
        return len(resultado.datos), {
            'url': url,
            'sitio': resultado.sitio,
            'productos': len(resultado.datos),
            'guardados': resultado.guardados,
            'duracion': round(resultado.duracion, 1),
            'muestra': resultado.datos[:MUESTRA_RESULTADO],
        }

    def trabajo_comparar(job, solicitud: SolicitudComparar):
        nombre1 = solicitud.nombre1 or 'Sitio 1'
        nombre2 = solicitud.nombre2 or 'Sitio 2'
        coincidencias, productos1, productos2 = comparar_sitios(
            solicitud.url1, solicitud.url2, scraper_class, nombre1, nombre2, solicitud.umbral,
            progreso=job.avanzar, con_productos=True,
        )
        return len(productos1) + len(productos2), {
            'nombre1': nombre1,
            'nombre2': nombre2,
            'url1': solicitud.url1,
            'url2': solicitud.url2,
            'umbral': solicitud.umbral,
            'productos1': len(productos1),
            'productos2': len(productos2),
            'coincidencias': [_resumir_coincidencia(c) for c in coincidencias],
            'resumen': ComparadorPrecios.resumen(coincidencias),
        }

    def lanzar(tipo, unidad, funcion, *args):
        try:
            job = gestor.lanzar(tipo, unidad, funcion, *args)
        except RuntimeError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
        return {'job_id': job.id, 'estado': 'pendiente'}

    @app.post('/api/scrape', status_code=status.HTTP_202_ACCEPTED, tags=['scraping'])
    def lanzar_scrape(solicitud: SolicitudScrape):
        """Lanza el scraping de una URL (1-10 páginas) en segundo plano y devuelve el id del job."""
        return lanzar('scrape', 'Página', trabajo_scrape, solicitud.url, solicitud.paginas)

    @app.post('/api/comparar', status_code=status.HTTP_202_ACCEPTED, tags=['scraping'])
    def lanzar_comparacion(solicitud: SolicitudComparar):
        """Scrapea dos URLs y compara sus precios en segundo plano."""
        return lanzar('comparar', 'Sitio', trabajo_comparar, solicitud)

    @app.get('/api/jobs/{job_id}', tags=['scraping'])
    def estado_job(job_id: str):
        """Estado, progreso y resultado de un job."""
        job = gestor.obtener(job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'No existe ese job (los jobs se pierden al reiniciar el servidor)')
        return job.a_dict()

    # ------------------------------------------------------------------
    # Productos
    # ------------------------------------------------------------------

    def consultar(db: ScraperDB, filtros: FiltrosProductos, **paginacion):
        return db.consultar_productos(
            sitio=filtros.sitio or None,
            texto=filtros.q or None,
            precio_min=filtros.precio_min,
            precio_max=filtros.precio_max,
            orden=filtros.orden,
            descendente=filtros.direccion == 'desc',
            **paginacion,
        )

    @app.get('/api/productos', tags=['productos'])
    def listar_productos(consulta: Annotated[ConsultaProductos, Query()]):
        """Productos guardados con filtros, orden y paginación."""
        with abrir_db() as db:
            productos, total = consultar(db, consulta, limite=consulta.por_pagina,
                                         desplazamiento=(consulta.pagina - 1) * consulta.por_pagina)
        return {
            'productos': productos,
            'total': total,
            'pagina': consulta.pagina,
            'por_pagina': consulta.por_pagina,
            'paginas': max(1, math.ceil(total / consulta.por_pagina)),
        }

    @app.get('/api/productos/{producto_id}/historial', tags=['productos'])
    def historial_producto(producto_id: int):
        """Historial de precios de un producto, del más reciente al más antiguo."""
        with abrir_db() as db:
            producto = db.obtener_producto(producto_id)
            if producto is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f'No existe el producto {producto_id}')
            return {'producto': producto, 'historial': db.obtener_historial_precios(producto_id)}

    @app.get('/api/exportar', tags=['productos'])
    def exportar(consulta: Annotated[ConsultaExportar, Query()]):
        """Descarga en CSV o JSON los productos que cumplen los filtros (sin paginar)."""
        with abrir_db() as db:
            productos, _ = consultar(db, consulta, limite=None)
            columnas = db.columnas_productos()

        marca = datetime.now().strftime('%Y%m%d_%H%M%S')
        if consulta.formato == 'json':
            contenido = json.dumps(productos, ensure_ascii=False, indent=2)
            tipo = 'application/json'
        else:
            buffer = io.StringIO()
            escribir_csv(productos, buffer, valor_vacio='', campos=columnas)
            contenido = '﻿' + buffer.getvalue()  # BOM para que Excel detecte UTF-8
            tipo = 'text/csv; charset=utf-8'
        return Response(
            content=contenido,
            media_type=tipo,
            headers={'Content-Disposition': f'attachment; filename="productos_{marca}.{consulta.formato}"'},
        )

    # ------------------------------------------------------------------
    # Estadísticas
    # ------------------------------------------------------------------

    @app.get('/api/estadisticas', tags=['estadisticas'])
    def estadisticas():
        """Totales, productos por sitio, precio medio por moneda y últimas ejecuciones."""
        with abrir_db() as db:
            generales = db.obtener_estadisticas()
            return {
                'total_productos': generales['total_productos'],
                'total_jobs': generales['total_jobs'],
                'total_sitios': len(generales['por_sitio']),
                'por_sitio': [{'sitio': sitio, 'productos': total} for sitio, total in generales['por_sitio'].items()],
                'precio_medio': db.precio_medio_por_moneda(),
                'ultimos_jobs': db.obtener_ultimos_jobs(ULTIMOS_JOBS),
            }

    # ------------------------------------------------------------------
    # Tareas programadas
    # ------------------------------------------------------------------

    @app.get('/api/tareas', tags=['tareas'])
    def listar_tareas():
        """Tareas programadas y si el programador está en marcha."""
        return {'programador_activo': programador.activo, 'tareas': programador.obtener_tareas()}

    @app.post('/api/tareas', status_code=status.HTTP_201_CREATED, tags=['tareas'])
    def crear_tarea(solicitud: SolicitudTarea):
        """Crea una tarea programada. El nombre tiene que ser único."""
        if not programador.agregar_tarea(solicitud.url, solicitud.nombre, solicitud.intervalo_minutos,
                                         solicitud.max_paginas):
            raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe una tarea llamada '{solicitud.nombre}'")
        return next(t for t in programador.obtener_tareas() if t['nombre'] == solicitud.nombre)

    @app.delete('/api/tareas/{nombre:path}', tags=['tareas'])
    def eliminar_tarea(nombre: str):
        """Elimina una tarea programada por su nombre."""
        if not programador.eliminar_tarea(nombre):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe ninguna tarea llamada '{nombre}'")
        return {'eliminada': nombre}

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------

    app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

    @app.get('/', include_in_schema=False)
    def inicio():
        return FileResponse(STATIC_DIR / 'index.html')

    return app
