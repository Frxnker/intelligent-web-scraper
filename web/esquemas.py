"""Modelos Pydantic que validan las entradas de la API."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from utils import normalizar_url


def _url_valida(valor: str) -> str:
    url = normalizar_url(valor)
    if url is None:
        raise ValueError('URL no válida: usa una dirección web como https://tienda.com/categoria')
    return url


class _Cuerpo(BaseModel):
    """Base de los cuerpos JSON: quita espacios y rechaza campos desconocidos."""

    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


class SolicitudScrape(_Cuerpo):
    url: str = Field(max_length=2000, description='URL del listado. Si no lleva esquema se añade https://')
    paginas: int = Field(1, ge=1, le=10, description='Número de páginas a scrapear (1-10)')

    _validar_url = field_validator('url')(_url_valida)


class SolicitudComparar(_Cuerpo):
    url1: str = Field(max_length=2000)
    url2: str = Field(max_length=2000)
    nombre1: Optional[str] = Field(None, max_length=60, description='Nombre para mostrar del sitio 1')
    nombre2: Optional[str] = Field(None, max_length=60, description='Nombre para mostrar del sitio 2')
    umbral: float = Field(0.6, ge=0.5, le=1.0, description='Similitud mínima de títulos (0.5-1.0)')

    _validar_urls = field_validator('url1', 'url2')(_url_valida)


class SolicitudTarea(_Cuerpo):
    nombre: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=2000)
    intervalo_minutos: int = Field(60, ge=1, le=10080, description='Cada cuántos minutos (máximo una semana)')
    max_paginas: int = Field(1, ge=1, le=10)

    _validar_url = field_validator('url')(_url_valida)


class FiltrosProductos(BaseModel):
    """Filtros comunes de /api/productos y /api/exportar (parámetros de la query string)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sitio: Optional[str] = Field(None, max_length=200)
    q: Optional[str] = Field(None, max_length=200, description='Texto a buscar en el título')
    precio_min: Optional[float] = Field(None, ge=0)
    precio_max: Optional[float] = Field(None, ge=0)
    orden: Literal['fecha', 'precio', 'titulo'] = 'fecha'
    direccion: Literal['asc', 'desc'] = 'desc'

    @model_validator(mode='after')
    def _rango_de_precio(self):
        if self.precio_min is not None and self.precio_max is not None and self.precio_min > self.precio_max:
            raise ValueError('El precio mínimo no puede ser mayor que el máximo')
        return self


class ConsultaProductos(FiltrosProductos):
    pagina: int = Field(1, ge=1, le=100000)
    por_pagina: int = Field(24, ge=1, le=100)


class ConsultaExportar(FiltrosProductos):
    formato: Literal['csv', 'json'] = 'csv'
