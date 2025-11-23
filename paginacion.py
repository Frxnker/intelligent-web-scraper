"""
Módulo de paginación automática para scrapear múltiples páginas
"""
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from colorama import Fore, Style
import time

class Paginador:
    """Gestiona la paginación automática para scrapear múltiples páginas"""
    
    @staticmethod
    def detectar_tipo_paginacion(url, soup):
        """
        Detecta el tipo de paginación del sitio
        Retorna: 'query_param', 'path', 'next_link', o None
        """
        # Buscar enlaces de "siguiente" o paginación
        next_links = soup.find_all('a', text=lambda x: x and ('siguiente' in str(x).lower() or 'next' in str(x).lower()))
        if next_links:
            return 'next_link'
        
        # Buscar parámetros de paginación en la URL
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Parámetros comunes de paginación
        page_params = ['page', 'p', 'pg', 'pagina', 'offset', 'start']
        for param in page_params:
            if param in params:
                return 'query_param'
        
        return None
    
    @staticmethod
    def generar_urls_paginadas(url_base, max_paginas=5):
        """
        Genera URLs para múltiples páginas
        """
        urls = [url_base]
        parsed = urlparse(url_base)
        params = parse_qs(parsed.query)
        
        # Detectar parámetro de página
        page_param = None
        page_params = ['page', 'p', 'pg', 'pagina']
        for param in page_params:
            if param in params:
                page_param = param
                break
        
        if not page_param:
            # Si no hay parámetro, agregar uno
            page_param = 'page'
        
        # Generar URLs
        for i in range(2, max_paginas + 1):
            params_copy = params.copy()
            params_copy[page_param] = [str(i)]
            
            nueva_query = urlencode(params_copy, doseq=True)
            nueva_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                nueva_query,
                parsed.fragment
            ))
            urls.append(nueva_url)
        
        return urls
    
    @staticmethod
    def obtener_url_siguiente(soup, url_actual):
        """
        Busca el enlace a la página siguiente en el HTML
        """
        # Buscar enlaces comunes de "siguiente"
        selectores = [
            ('a', {'class': lambda x: x and ('next' in str(x).lower() or 'siguiente' in str(x).lower())}),
            ('a', {'rel': 'next'}),
            ('a', {'aria-label': lambda x: x and 'next' in str(x).lower()}),
        ]
        
        for tag, attrs in selectores:
            link = soup.find(tag, attrs=attrs)
            if link and link.get('href'):
                href = link['href']
                # Convertir a URL absoluta si es relativa
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    return urljoin(url_actual, href)
                return href
        
        return None

def scrapear_con_paginacion(scraper, url_base, max_paginas=5, delay=2):
    """
    Scrapea múltiples páginas automáticamente
    
    Args:
        scraper: Instancia del scraper (SeleniumScraper o WebScraper)
        url_base: URL de la primera página
        max_paginas: Número máximo de páginas a scrapear
        delay: Tiempo de espera entre páginas (segundos)
    
    Returns:
        Lista con todos los datos scrapeados
    """
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}📄 SCRAPING CON PAGINACIÓN")
    print(f"{Fore.CYAN}{'='*70}\n")
    print(f"{Fore.WHITE}🔗 URL base: {url_base}")
    print(f"{Fore.WHITE}📊 Páginas máximas: {max_paginas}\n")
    
    todos_los_datos = []
    urls = Paginador.generar_urls_paginadas(url_base, max_paginas)
    
    for i, url in enumerate(urls[:max_paginas], 1):
        print(f"{Fore.CYAN}📄 Scrapeando página {i}/{min(len(urls), max_paginas)}...")
        print(f"{Fore.WHITE}   URL: {url}\n")
        
        try:
            # Scrapear la página
            if hasattr(scraper, 'scrapear_pagina_universal'):
                # Selenium scraper
                datos = scraper.scrapear_pagina_universal(url, f'pagina_{i}')
            else:
                # Basic scraper
                soup = scraper.get_soup(url)
                datos = []  # Implementar lógica básica si es necesario
            
            if datos:
                todos_los_datos.extend(datos)
                print(f"{Fore.GREEN}✅ Página {i}: {len(datos)} elementos encontrados")
                print(f"{Fore.CYAN}   Total acumulado: {len(todos_los_datos)}\n")
            else:
                print(f"{Fore.YELLOW}⚠️  Página {i}: Sin datos, deteniendo paginación\n")
                break
            
            # Esperar entre páginas para no sobrecargar el servidor
            if i < min(len(urls), max_paginas):
                print(f"{Fore.CYAN}⏳ Esperando {delay} segundos...\n")
                time.sleep(delay)
                
        except Exception as e:
            print(f"{Fore.RED}❌ Error en página {i}: {str(e)}\n")
            break
    
    print(f"{Fore.GREEN}{'='*70}")
    print(f"{Fore.GREEN}✅ PAGINACIÓN COMPLETADA")
    print(f"{Fore.GREEN}{'='*70}")
    print(f"{Fore.WHITE}📊 Total de elementos: {len(todos_los_datos)}")
    print(f"{Fore.WHITE}📄 Páginas scrapeadas: {i}/{max_paginas}\n")
    
    return todos_los_datos
