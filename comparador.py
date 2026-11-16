"""
Comparador de precios entre dos listas de productos (normalmente de dos sitios).

Empareja productos por similitud de título y compara sus precios.
"""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher

from colorama import Fore

from precios import extraer_moneda, extraer_precio_numerico, formatear_precio, parsear_precio


class ComparadorPrecios:
    """Compara precios de productos entre diferentes sitios."""

    # Se mantienen como métodos de la clase por compatibilidad; la lógica está en precios.py
    extraer_precio_numerico = staticmethod(extraer_precio_numerico)
    extraer_moneda = staticmethod(extraer_moneda)

    @staticmethod
    def limpiar_titulo(titulo) -> str:
        """Normaliza el título para comparación: minúsculas, sin signos de puntuación."""
        if not titulo:
            return ''
        titulo = re.sub(r'[^\w\s]', ' ', str(titulo).lower())
        return ' '.join(titulo.split())

    @staticmethod
    def similitud_titulos(titulo1, titulo2) -> float:
        """Calcula la similitud entre dos títulos (0-1)."""
        return ComparadorPrecios._similitud(
            ComparadorPrecios.limpiar_titulo(titulo1),
            ComparadorPrecios.limpiar_titulo(titulo2),
        )

    @staticmethod
    def _similitud(t1: str, t2: str, minimo: float = 0.0) -> float:
        """Similitud entre títulos ya limpios. Devuelve 0 en cuanto se sabe que no llega a `minimo`."""
        if not t1 or not t2:
            return 0.0
        matcher = SequenceMatcher(None, t1, t2)
        # real_quick_ratio y quick_ratio son cotas superiores baratas de ratio()
        if matcher.real_quick_ratio() < minimo or matcher.quick_ratio() < minimo:
            return 0.0
        return matcher.ratio()

    @staticmethod
    def comparar_listas(productos1, productos2, umbral_similitud=0.7) -> list[dict]:
        """
        Compara dos listas de productos y encuentra coincidencias.

        Para cada producto de la primera lista se busca el más parecido de la
        segunda con similitud >= umbral_similitud. Los productos sin título no
        se emparejan.

        Returns:
            Lista de coincidencias con la comparación de precios. Si los dos
            precios tienen monedas distintas no se calcula la diferencia.
        """
        if not 0 <= umbral_similitud <= 1:
            raise ValueError('umbral_similitud debe estar entre 0 y 1')

        limpiar = ComparadorPrecios.limpiar_titulo
        candidatos = [
            (p2, limpiar(p2.get('titulo')))
            for p2 in productos2
            if p2.get('titulo') not in (None, '', 'N/A')
        ]

        coincidencias = []
        for p1 in productos1:
            if p1.get('titulo') in (None, '', 'N/A'):
                continue
            t1 = limpiar(p1['titulo'])

            mejor_match, mejor_similitud = None, 0.0
            for p2, t2 in candidatos:
                similitud = ComparadorPrecios._similitud(t1, t2, umbral_similitud)
                if similitud > mejor_similitud and similitud >= umbral_similitud:
                    mejor_match, mejor_similitud = p2, similitud

            if mejor_match is None:
                continue

            precio1, moneda1 = parsear_precio(p1.get('precio'))
            precio2, moneda2 = parsear_precio(mejor_match.get('precio'))
            diferencia = porcentaje = mas_barato = None

            mismas_monedas = moneda1 == moneda2 or moneda1 is None or moneda2 is None
            if precio1 is not None and precio2 is not None and mismas_monedas:
                diferencia = abs(precio1 - precio2)
                menor = min(precio1, precio2)
                porcentaje = (diferencia / menor) * 100 if menor > 0 else None
                if precio1 < precio2:
                    mas_barato = 'sitio1'
                elif precio2 < precio1:
                    mas_barato = 'sitio2'
                else:
                    mas_barato = 'igual'

            coincidencias.append({
                'producto1': p1,
                'producto2': mejor_match,
                'similitud': mejor_similitud,
                'precio1': precio1,
                'precio2': precio2,
                'moneda1': moneda1,
                'moneda2': moneda2,
                'diferencia': diferencia,
                'porcentaje_diferencia': porcentaje,
                'mas_barato': mas_barato,
            })

        return coincidencias

    @staticmethod
    def mostrar_comparacion(coincidencias, nombre_sitio1='Sitio 1', nombre_sitio2='Sitio 2'):
        """Muestra la comparación de precios por consola."""
        if not coincidencias:
            print(f"\n{Fore.YELLOW}⚠️  No se encontraron productos coincidentes\n")
            return

        print(f"\n{Fore.CYAN}{'=' * 90}")
        print(f"{Fore.YELLOW}💰 COMPARACIÓN DE PRECIOS: {nombre_sitio1} vs {nombre_sitio2}")
        print(f"{Fore.CYAN}{'=' * 90}\n")

        ahorros = defaultdict(float)  # por moneda
        mas_baratos_sitio1 = mas_baratos_sitio2 = 0

        for i, match in enumerate(coincidencias, 1):
            titulo = str(match['producto1'].get('titulo', 'N/A'))[:60]
            print(f"{Fore.WHITE}{i}. {titulo}...")

            if match['mas_barato'] is None:
                # Sin precio numérico o con monedas distintas: se muestra el texto original
                print(f"   {Fore.CYAN}{nombre_sitio1}: {Fore.WHITE}{match['producto1'].get('precio', 'N/A')}")
                print(f"   {Fore.CYAN}{nombre_sitio2}: {Fore.WHITE}{match['producto2'].get('precio', 'N/A')}")
                if match['precio1'] is not None and match['precio2'] is not None:
                    print(f"   {Fore.YELLOW}Monedas distintas, no se comparan")
            else:
                moneda = match['moneda1'] or match['moneda2']
                texto1 = formatear_precio(match['precio1'], moneda)
                texto2 = formatear_precio(match['precio2'], moneda)

                if match['mas_barato'] == 'sitio1':
                    print(f"   {Fore.CYAN}{nombre_sitio1}: {Fore.GREEN}{texto1} ✓ (más barato)")
                    print(f"   {Fore.CYAN}{nombre_sitio2}: {Fore.WHITE}{texto2}")
                    mas_baratos_sitio1 += 1
                elif match['mas_barato'] == 'sitio2':
                    print(f"   {Fore.CYAN}{nombre_sitio1}: {Fore.WHITE}{texto1}")
                    print(f"   {Fore.CYAN}{nombre_sitio2}: {Fore.GREEN}{texto2} ✓ (más barato)")
                    mas_baratos_sitio2 += 1
                else:
                    print(f"   {Fore.CYAN}{nombre_sitio1}: {Fore.WHITE}{texto1}")
                    print(f"   {Fore.CYAN}{nombre_sitio2}: {Fore.WHITE}{texto2} (mismo precio)")

                ahorros[moneda] += match['diferencia']
                porcentaje = match['porcentaje_diferencia']
                detalle = f" ({porcentaje:.1f}%)" if porcentaje is not None else ''
                print(f"   {Fore.YELLOW}💰 Diferencia: {formatear_precio(match['diferencia'], moneda)}{detalle}")

            print(f"   {Fore.MAGENTA}📊 Similitud: {match['similitud'] * 100:.0f}%\n")

        print(f"{Fore.GREEN}{'=' * 90}")
        print(f"{Fore.GREEN}📊 RESUMEN")
        print(f"{Fore.GREEN}{'=' * 90}")
        print(f"{Fore.WHITE}🔍 Productos comparados: {len(coincidencias)}")
        print(f"{Fore.GREEN}✓ {nombre_sitio1} más barato: {mas_baratos_sitio1} productos")
        print(f"{Fore.GREEN}✓ {nombre_sitio2} más barato: {mas_baratos_sitio2} productos")
        for moneda, ahorro in ahorros.items():
            if ahorro > 0:
                print(f"{Fore.YELLOW}💰 Ahorro potencial comprando lo más barato: {formatear_precio(ahorro, moneda)}")
        print()


def comparar_sitios(url1, url2, scraper_class, nombre_sitio1='Sitio 1', nombre_sitio2='Sitio 2', umbral=0.6):
    """
    Scrapea dos URLs y compara sus productos.

    Args:
        url1, url2: URLs de los listados a comparar.
        scraper_class: clase del scraper (Scraper o SeleniumScraper).
        nombre_sitio1, nombre_sitio2: nombres para mostrar.
        umbral: similitud mínima de títulos (0-1).
    """
    print(f"\n{Fore.CYAN}{'=' * 70}")
    print(f"{Fore.YELLOW}🔍 SCRAPEANDO SITIOS PARA COMPARAR")
    print(f"{Fore.CYAN}{'=' * 70}\n")

    # Un único scraper para los dos sitios: si hace falta Chrome, se abre una sola vez
    with scraper_class(headless=True) as scraper:
        print(f"{Fore.WHITE}📍 Scrapeando {nombre_sitio1}...")
        productos1 = scraper.scrapear_pagina_universal(url1, 'temp_sitio1')
        print(f"{Fore.GREEN}✅ {len(productos1)} productos encontrados\n")

        print(f"{Fore.WHITE}📍 Scrapeando {nombre_sitio2}...")
        productos2 = scraper.scrapear_pagina_universal(url2, 'temp_sitio2')
        print(f"{Fore.GREEN}✅ {len(productos2)} productos encontrados\n")

    print(f"{Fore.CYAN}🔄 Comparando productos...\n")
    coincidencias = ComparadorPrecios.comparar_listas(productos1, productos2, umbral)
    ComparadorPrecios.mostrar_comparacion(coincidencias, nombre_sitio1, nombre_sitio2)
    return coincidencias
