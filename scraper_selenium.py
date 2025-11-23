"""
🚀 WEB SCRAPER CON SELENIUM
Funciona con sitios que bloquean scrapers normales (como PcComponentes)
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from colorama import Fore, Style, init
from utils import export_to_csv, export_to_json
from js_scripts import JavaScriptScripts

init(autoreset=True)


class SeleniumScraper:
    """
    Scraper usando Selenium - Simula un navegador real
    """
    
    def __init__(self, headless=True):
        """
        Inicializa el navegador Chrome
        
        Args:
            headless: Si es True, el navegador se ejecuta sin ventana visible
        """
        print(f"{Fore.CYAN}🚀 Inicializando navegador Chrome...")
        
        # Configurar opciones de Chrome
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless=new')  # Modo sin ventana
            print(f"{Fore.CYAN}   Modo: Headless (sin ventana)")
        else:
            print(f"{Fore.CYAN}   Modo: Con ventana visible")
        
        # Opciones para evitar detección
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Inicializar el driver
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configurar script para evitar detección
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"{Fore.GREEN}✓ Navegador iniciado correctamente\n")
        
        except Exception as e:
            print(f"{Fore.RED}✗ Error al iniciar navegador: {str(e)}")
            raise
    
    def get_page(self, url, wait_time=3):
        """
        Carga una página web
        
        Args:
            url: URL a cargar
            wait_time: Tiempo de espera después de cargar
        """
        print(f"{Fore.CYAN}📡 Cargando: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(wait_time)  # Esperar a que cargue el JavaScript
            
            print(f"{Fore.GREEN}✓ Página cargada\n")
            return True
        
        except Exception as e:
            print(f"{Fore.RED}✗ Error al cargar página: {str(e)}\n")
            return False
    
    def esperar_carga_completa(self, timeout=10):
        """
        Espera inteligente usando JavaScript para detectar cuando la página terminó de cargar
        """
        try:
            # Esperar a que document.readyState sea 'complete'
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Esperar a que jQuery termine (si existe)
            self.driver.execute_script("""
                if (typeof jQuery != 'undefined') {
                    return jQuery.active == 0;
                }
                return true;
            """)
            
            print(f"{Fore.GREEN}✓ Página completamente cargada")
            return True
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  Timeout esperando carga completa")
            return False
    
    def scroll_automatico_hasta_final(self, pausa=1):
        """
        Hace scroll automático hasta el final de la página para cargar contenido lazy-load
        Usa JavaScript para detectar cuando no hay más contenido
        """
        print(f"{Fore.CYAN}📜 Haciendo scroll para cargar contenido...")
        
        ultima_altura = self.driver.execute_script("return document.body.scrollHeight")
        intentos = 0
        max_intentos = 10
        
        while intentos < max_intentos:
            # Scroll hasta el final
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pausa)
            
            # Calcular nueva altura
            nueva_altura = self.driver.execute_script("return document.body.scrollHeight")
            
            # Si no cambió la altura, ya llegamos al final
            if nueva_altura == ultima_altura:
                break
            
            ultima_altura = nueva_altura
            intentos += 1
        
        # Volver arriba
        self.driver.execute_script("window.scrollTo(0, 0);")
        print(f"{Fore.GREEN}✓ Scroll completado ({intentos} iteraciones)\n")
    
    def extraer_datos_con_js(self):
        """
        Extrae datos directamente con JavaScript (MÁS RÁPIDO que BeautifulSoup)
        Busca productos/artículos usando selectores comunes
        """
        script = r"""
        // Función para limpiar texto
        function limpiarTexto(texto) {
            return texto ? texto.trim().replace(/\s+/g, ' ') : '';
        }
        
        // Función para buscar precio en un elemento
        function buscarPrecio(elemento) {
            // Buscar en atributos data-*
            const dataPrice = elemento.dataset.productPrice || elemento.dataset.price;
            if (dataPrice) return dataPrice;
            
            // Buscar en clases con 'price'
            const precioElem = elemento.querySelector('[class*="price" i], [class*="precio" i], [class*="cost" i]');
            if (precioElem) return limpiarTexto(precioElem.textContent);
            
            // Buscar símbolos de moneda en el texto
            const textoCompleto = elemento.textContent;
            const matchPrecio = textoCompleto.match(/[€$£¥]\s*[\d,\.]+|[\d,\.]+\s*[€$£¥]/);
            if (matchPrecio) return matchPrecio[0];
            
            return null;
        }
        
        // Función para buscar título en un elemento
        function buscarTitulo(elemento) {
            // Atributos data-*
            if (elemento.dataset.productName) return elemento.dataset.productName;
            if (elemento.dataset.title) return elemento.dataset.title;
            if (elemento.title) return elemento.title;
            
            // Encabezados
            const h2 = elemento.querySelector('h2');
            if (h2) return limpiarTexto(h2.textContent);
            
            const h3 = elemento.querySelector('h3');
            if (h3) return limpiarTexto(h3.textContent);
            
            const h1 = elemento.querySelector('h1');
            if (h1) return limpiarTexto(h1.textContent);
            
            // Enlaces con title
            const linkConTitle = elemento.querySelector('a[title]');
            if (linkConTitle) return linkConTitle.title;
            
            // aria-label
            if (elemento.getAttribute('aria-label')) return elemento.getAttribute('aria-label');
            
            return null;
        }
        
        // Selectores a probar (orden de prioridad)
        const selectores = [
            'a[data-product-name]',  // PcComponentes
            '[data-asin].s-result-item',  // Amazon
            '.s-item',  // eBay
            '.product-card, [class*="product-card" i]',  // E-commerce genérico
            'article',  // HTML5 estándar
            '[class*="product" i][class*="item" i]',  // Genérico
            'li[class*="product" i]',  // Listas de productos
            '.card, [class*="card" i]'  // Tarjetas genéricas
        ];
        
        let elementos = [];
        
        // Probar cada selector hasta encontrar elementos
        for (const selector of selectores) {
            try {
                elementos = Array.from(document.querySelectorAll(selector));
                if (elementos.length > 0) {
                    console.log(`✓ Encontrados ${elementos.length} elementos con: ${selector}`);
                    break;
                }
            } catch (e) {
                continue;
            }
        }
        
        // Extraer datos de cada elemento
        const datos = [];
        const maxItems = Math.min(elementos.length, 50);  // Máximo 50 items
        
        for (let i = 0; i < maxItems; i++) {
            const elem = elementos[i];
            
            const titulo = buscarTitulo(elem);
            const precio = buscarPrecio(elem);
            
            // Descripción
            const parrafo = elem.querySelector('p');
            const descripcion = parrafo ? limpiarTexto(parrafo.textContent).substring(0, 100) : null;
            
            // Enlace
            const enlace = elem.querySelector('a');
            const url = enlace ? enlace.href : null;
            
            // Imagen
            const img = elem.querySelector('img');
            const imagen = img ? (img.src || img.dataset.src || img.dataset.lazySrc) : null;
            
            // Solo agregar si tiene información relevante
            if (titulo || precio) {
                datos.push({
                    numero: i + 1,
                    titulo: titulo || 'N/A',
                    precio: precio || 'N/A',
                    descripcion: descripcion || 'N/A',
                    enlace: url || 'N/A',
                    imagen: imagen || 'N/A'
                });
            }
        }
        
        return datos;
        """
        
        try:
            datos = self.driver.execute_script(script)
            print(f"{Fore.GREEN}✓ Datos extraídos con JavaScript: {len(datos)} elementos\n")
            return datos if datos else []
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  Error en extracción JS: {str(e)}")
            return []
    
    def get_soup(self):
        """
        Obtiene BeautifulSoup del HTML actual
        """
        html = self.driver.page_source
        return BeautifulSoup(html, 'lxml')
    
    def scrapear_pagina_universal(self, url, nombre_archivo='scraping_selenium'):
        """
        Scrapea cualquier página web con Selenium
        
        Args:
            url: URL completa de la página a scrapear
            nombre_archivo: Nombre base para guardar archivos
        """
        print(f"{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}🌐 SCRAPEANDO CON SELENIUM")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        print(f"{Fore.WHITE}🔗 URL: {url}\n")
        
        if not self.get_page(url, wait_time=3):
            return []
        
        # Esperar carga completa inteligente
        self.esperar_carga_completa()
        
        # Remover overlays molestos (cookies, popups, etc.)
        print(f"{Fore.CYAN}🧹 Removiendo popups molestos...")
        removidos = self.driver.execute_script(JavaScriptScripts.remover_overlays())
        if removidos > 0:
            print(f"{Fore.GREEN}✓ Removidos {removidos} overlays\n")
        
        # Hacer scroll automático hasta el final (lazy loading)
        self.scroll_automatico_hasta_final(pausa=1)
        
        # Intentar script específico para el sitio primero
        script_especifico = JavaScriptScripts.obtener_script_para_sitio(url)
        
        if script_especifico:
            print(f"{Fore.CYAN}🎯 Usando script específico para este sitio...")
            try:
                datos_especificos = self.driver.execute_script(script_especifico)
                if datos_especificos and len(datos_especificos) > 0:
                    print(f"{Fore.GREEN}✓ Script específico exitoso: {len(datos_especificos)} productos\n")
                    
                    # Guardar HTML
                    soup = self.get_soup()
                    html_file = f'output/{nombre_archivo}.html'
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(soup.prettify())
                    
                    # Exportar
                    from utils import export_to_csv, export_to_json
                    filename_csv = f"{nombre_archivo}.csv"
                    filename_json = f"{nombre_archivo}.json"
                    export_to_csv(datos_especificos, filename_csv)
                    export_to_json(datos_especificos, filename_json)
                    
                    print(f"{Fore.GREEN}✓ Datos guardados:")
                    print(f"{Fore.WHITE}  - output/{filename_csv}")
                    print(f"{Fore.WHITE}  - output/{filename_json}")
                    print(f"{Fore.WHITE}  - {html_file}\n")
                    
                    # Mostrar resultados
                    for dato in datos_especificos[:5]:
                        print(f"{Fore.YELLOW}Elemento #{dato['numero']}")
                        print(f"{Fore.WHITE}  📝 {dato['titulo'][:65]}")
                        if dato['precio'] != 'N/A':
                            print(f"{Fore.GREEN}  💰 {dato['precio']}")
                        print()
                    
                    if len(datos_especificos) > 5:
                        print(f"{Fore.CYAN}... y {len(datos_especificos) - 5} elementos más\n")
                    
                    return datos_especificos
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️  Script específico falló: {str(e)}\n")
        
        # Intentar extracción con JavaScript genérico
        print(f"{Fore.CYAN}🚀 Intentando extracción con JavaScript genérico...")
        datos_js = self.extraer_datos_con_js()
        
        if datos_js and len(datos_js) > 0:
            # Éxito con JavaScript - Guardar y retornar
            print(f"{Fore.GREEN}✓ Extracción JavaScript exitosa: {len(datos_js)} productos\n")
            
            # Guardar HTML para referencia
            soup = self.get_soup()
            html_file = f'output/{nombre_archivo}.html'
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            
            # Exportar
            from utils import export_to_csv, export_to_json
            filename_csv = f"{nombre_archivo}.csv"
            filename_json = f"{nombre_archivo}.json"
            export_to_csv(datos_js, filename_csv)
            export_to_json(datos_js, filename_json)
            
            print(f"{Fore.GREEN}✓ Datos guardados:")
            print(f"{Fore.WHITE}  - output/{filename_csv}")
            print(f"{Fore.WHITE}  - output/{filename_json}")
            print(f"{Fore.WHITE}  - {html_file}\n")
            
            # Mostrar primeros resultados
            for dato in datos_js[:5]:
                print(f"{Fore.YELLOW}Elemento #{dato['numero']}")
                print(f"{Fore.WHITE}  📝 {dato['titulo'][:65]}")
                if dato['precio'] != 'N/A':
                    print(f"{Fore.GREEN}  💰 {dato['precio']}")
                print()
            
            if len(datos_js) > 5:
                print(f"{Fore.CYAN}... y {len(datos_js) - 5} elementos más\n")
            
            return datos_js
        
        # Si JavaScript no funcionó, usar método tradicional con BeautifulSoup
        print(f"{Fore.YELLOW}⚠️  Extracción JS sin resultados, usando BeautifulSoup...\n")
        
        # Obtener el HTML
        soup = self.get_soup()
        
        # Guardar HTML para análisis
        html_file = f'output/{nombre_archivo}.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"{Fore.GREEN}✓ HTML guardado en: {html_file}\n")
        
        # Buscar elementos (intentar con selectores comunes)
        datos = []
        
        # Intentar con varios selectores comunes (orden de prioridad)
        selectores = [
            # E-commerce español
            ('a', {'data-product-name': True}),  # PcComponentes
            ('div', {'data-asin': True, 'class': lambda x: x and 's-result-item' in str(x)}),  # Amazon
            
            # E-commerce internacional
            ('div', {'class': lambda x: x and ('s-item' in str(x) or 'lvresult' in str(x))}),  # eBay
            ('div', {'class': lambda x: x and 'product-card' in str(x).lower()}),  # Genérico e-commerce
            ('li', {'class': lambda x: x and ('product' in str(x).lower() or 'item' in str(x).lower())}),  # AliExpress, otros
            
            # Noticias y blogs
            ('article', {}),  # Estándar HTML5 para artículos
            ('div', {'class': lambda x: x and ('post' in str(x).lower() or 'entry' in str(x).lower())}),  # WordPress
            
            # Genéricos
            ('div', {'class': lambda x: x and ('card' in str(x).lower() or 'item' in str(x).lower())}),
            ('section', {'class': lambda x: x and ('product' in str(x).lower() or 'item' in str(x).lower())}),
        ]
        
        items_encontrados = []
        for tag, attrs in selectores:
            if attrs:
                items = soup.find_all(tag, attrs=attrs)
            else:
                items = soup.find_all(tag)
            
            if items and len(items) > 0:
                items_encontrados = items
                print(f"{Fore.GREEN}✓ Encontrados {len(items)} elementos <{tag}>\n")
                break
        
        if not items_encontrados:
            print(f"{Fore.YELLOW}⚠️  No se encontraron elementos estructurados")
            print(f"{Fore.CYAN}💡 Revisa '{html_file}' para ver la estructura\n")
            
            # Extraer al menos los links y títulos básicos
            links = soup.find_all('a', href=True)
            print(f"{Fore.CYAN}📊 Información básica de la página:")
            print(f"{Fore.WHITE}  - Total de enlaces: {len(links)}")
            print(f"{Fore.WHITE}  - Imágenes: {len(soup.find_all('img'))}")
            print(f"{Fore.WHITE}  - Párrafos: {len(soup.find_all('p'))}\n")
            return []
        
        # Extraer información de cada elemento
        max_items = min(len(items_encontrados), 20)
        for i, item in enumerate(items_encontrados[:max_items], 1):
            try:
                # Título/Nombre (buscar en múltiples ubicaciones comunes)
                titulo = None
                titulo_elems = [
                    item.find('h2'),  # Amazon, eBay, la mayoría de e-commerce
                    item.find('h3'),  # AliExpress, algunos blogs
                    item.find('h1'),  # Páginas de detalle
                    item.find('h4'), item.find('h5'), item.find('h6'),
                    item.find('a', {'title': True}),  # Enlaces con atributo title
                    item.find('span', class_=lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower() or 'heading' in str(x).lower())),
                    item.find(class_=lambda x: x and ('product-title' in str(x).lower() or 'item-title' in str(x).lower())),  # Clases comunes
                ]
                
                for elem in titulo_elems:
                    if elem:
                        if elem.name == 'a' and 'title' in elem.attrs:
                            titulo = elem['title']
                        else:
                            titulo = elem.get_text(strip=True)
                        if titulo and len(titulo) > 3:
                            break
                
                # Si no encuentra título, buscar en atributos data-* comunes
                if not titulo:
                    title_attrs = [
                        item.get('data-product-name'),  # PcComponentes
                        item.get('data-title'),  # Genérico
                        item.get('title'),  # HTML estándar
                        item.get('data-name'),  # Algunos sitios
                        item.get('aria-label'),  # Accesibilidad
                    ]
                    for attr in title_attrs:
                        if attr and len(str(attr)) > 3:
                            titulo = attr
                            break
                
                # Precio (buscar en múltiples formatos y monedas)
                precio = None
                precio_elems = [
                    item.find(class_=lambda x: x and 'price' in str(x).lower()),
                    item.find(class_=lambda x: x and 'precio' in str(x).lower()),
                    item.find(class_=lambda x: x and 'cost' in str(x).lower()),
                    item.find('span', class_=lambda x: x and ('amount' in str(x).lower() or 'value' in str(x).lower())),
                    item.find(text=lambda x: x and ('€' in str(x) or '$' in str(x) or '£' in str(x) or '¥' in str(x))),
                ]
                
                for elem in precio_elems:
                    if elem:
                        if isinstance(elem, str):
                            precio = elem.strip()
                        else:
                            precio = elem.get_text(strip=True)
                        if precio and any(c in precio for c in ['€', '$', '£']):
                            break
                
                # Si no encuentra precio en el texto, buscar en atributos data-* comunes
                if not precio:
                    price_attr = item.get('data-product-price') or item.get('data-price') or item.find(attrs={'data-product-price': True}) or item.find(attrs={'data-price': True})
                    if price_attr:
                        if isinstance(price_attr, str):
                            precio = price_attr if any(c in price_attr for c in ['€', '$', '£', '¥']) else price_attr + '€'
                        else:
                            price_val = price_attr.get('data-product-price') or price_attr.get('data-price', '')
                            precio = price_val if any(c in price_val for c in ['€', '$', '£', '¥']) else price_val + '€'
                
                # Descripción
                descripcion = None
                desc_elem = item.find('p')
                if desc_elem:
                    descripcion = desc_elem.get_text(strip=True)[:100]
                
                # Enlace
                enlace = None
                enlace_elem = item.find('a', href=True)
                if enlace_elem:
                    enlace = enlace_elem['href']
                    if enlace and not enlace.startswith('http'):
                        # Construir URL completa
                        from urllib.parse import urljoin
                        enlace = urljoin(url, enlace)
                
                # Imagen (buscar en múltiples atributos comunes)
                imagen = None
                img_elem = item.find('img')
                if img_elem:
                    # Intentar varios atributos comunes para imágenes lazy-loaded
                    imagen = (img_elem.get('src') or 
                             img_elem.get('data-src') or 
                             img_elem.get('data-lazy-src') or
                             img_elem.get('data-original') or
                             img_elem.get('srcset', '').split(',')[0].split(' ')[0])  # Primera imagen del srcset
                
                # Solo agregar si tiene información relevante
                if titulo or precio or descripcion:
                    dato = {
                        'numero': i,
                        'titulo': titulo if titulo else 'N/A',
                        'precio': precio if precio else 'N/A',
                        'descripcion': descripcion if descripcion else 'N/A',
                        'enlace': enlace if enlace else 'N/A',
                        'imagen': imagen if imagen else 'N/A'
                    }
                    
                    datos.append(dato)
                    
                    # Mostrar
                    print(f"{Fore.YELLOW}Elemento #{i}")
                    print(f"{Fore.WHITE}  📝 {dato['titulo'][:65]}")
                    if precio:
                        print(f"{Fore.GREEN}  💰 {dato['precio']}")
                    print()
            
            except Exception as e:
                print(f"{Fore.RED}⚠️  Error procesando elemento {i}: {str(e)}")
                continue
        
        # Exportar datos si se encontraron
        if datos:
            from utils import export_to_csv, export_to_json
            
            filename_csv = f"{nombre_archivo}.csv"
            filename_json = f"{nombre_archivo}.json"
            
            export_to_csv(datos, filename_csv)
            export_to_json(datos, filename_json)
            
            print(f"{Fore.GREEN}✓ Datos guardados:")
            print(f"{Fore.WHITE}  - output/{filename_csv}")
            print(f"{Fore.WHITE}  - output/{filename_json}\n")
        
        return datos
    
    def captura_pantalla(self, filename='screenshot.png'):
        """Toma una captura de pantalla"""
        filepath = f'output/{filename}'
        self.driver.save_screenshot(filepath)
        print(f"{Fore.GREEN}✓ Captura guardada: {filepath}")
    
    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            print(f"\n{Fore.CYAN}👋 Navegador cerrado")


def ejemplo_universal():
    """Ejemplo de scraping universal con Selenium"""
    
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║       🚀 SCRAPER UNIVERSAL CON SELENIUM 🚀                   ║
║                                                              ║
║  Usa un navegador real para evitar bloqueos                 ║
║  Funciona con CUALQUIER sitio web                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """)
    
    # Crear scraper
    scraper = SeleniumScraper(headless=True)
    
    try:
        # Pedir URL
        print(f"{Fore.YELLOW}Ejemplos de URLs:")
        print(f"{Fore.WHITE}  - https://www.pccomponentes.com/")
        print(f"{Fore.WHITE}  - https://www.amazon.es/")
        print(f"{Fore.WHITE}  - https://quotes.toscrape.com/")
        print(f"{Fore.WHITE}  - https://news.ycombinator.com/\n")
        
        url = input(f"{Fore.GREEN}Ingresa la URL completa: {Style.RESET_ALL}").strip()
        
        if not url:
            url = "https://quotes.toscrape.com/"
            print(f"{Fore.CYAN}Usando URL por defecto: {url}\n")
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Generar nombre de archivo limpio
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '').replace('.', '_')
        nombre_archivo = f"{domain}_selenium"
        
        # Scrapear
        datos = scraper.scrapear_pagina_universal(url, nombre_archivo)
        
        if datos:
            print(f"\n{Fore.CYAN}{'='*70}")
            print(f"{Fore.GREEN}✅ Scraping completado!")
            print(f"{Fore.CYAN}{'='*70}\n")
            
            print(f"{Fore.WHITE}📊 Total de elementos extraídos: {Fore.GREEN}{len(datos)}")
            
            # Exportar
            filename_csv = f"{nombre_archivo}.csv"
            filename_json = f"{nombre_archivo}.json"
            
            export_to_csv(datos, filename_csv)
            export_to_json(datos, filename_json)
            
            print(f"\n{Fore.CYAN}📁 Archivos guardados en 'output/':")
            print(f"{Fore.WHITE}  - {filename_csv}")
            print(f"{Fore.WHITE}  - {filename_json}")
            print(f"{Fore.WHITE}  - {nombre_archivo}.html")
            
        else:
            print(f"\n{Fore.YELLOW}⚠️  No se encontraron datos estructurados")
            print(f"{Fore.CYAN}💡 El archivo HTML ha sido guardado. Revísalo para ver la estructura del sitio")
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Proceso interrumpido por el usuario")
    
    except Exception as e:
        print(f"\n{Fore.RED}✗ Error: {str(e)}")
    
    finally:
        scraper.close()


def modo_interactivo():
    """Modo interactivo con más opciones"""
    
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║       🚀 SCRAPER SELENIUM - MODO INTERACTIVO                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """)
    
    print(f"{Fore.YELLOW}🔧 Configuración:")
    modo = input(f"{Fore.WHITE}¿Ver el navegador mientras scrapea? (s/n): {Style.RESET_ALL}").strip().lower()
    headless = modo != 's'
    
    scraper = SeleniumScraper(headless=headless)
    
    try:
        while True:
            print(f"\n{Fore.CYAN}{'─'*60}")
            print(f"{Fore.YELLOW}OPCIONES:")
            print(f"{Fore.WHITE}1. 🌐 Scrapear URL")
            print(f"{Fore.WHITE}2. 🔍 Solo navegar a URL (sin scrapear)")
            print(f"{Fore.WHITE}3. 📸 Tomar captura de pantalla")
            print(f"{Fore.WHITE}4. 💾 Guardar HTML actual")
            print(f"{Fore.WHITE}5. ❌ Salir")
            print(f"{Fore.CYAN}{'─'*60}\n")
            
            opcion = input(f"{Fore.GREEN}Elige opción (1-5): {Style.RESET_ALL}").strip()
            
            if opcion == '1':
                url_input = input(f"{Fore.GREEN}URL de la página: {Style.RESET_ALL}").strip()
                if url_input:
                    if not url_input.startswith('http'):
                        url_input = 'https://' + url_input
                    from urllib.parse import urlparse
                    domain = urlparse(url_input).netloc.replace('www.', '').replace('.', '_')
                    datos = scraper.scrapear_pagina_universal(url_input, domain)
                    if datos:
                        export_to_csv(datos, f"{domain}.csv")
            
            elif opcion == '2':
                url = input(f"{Fore.GREEN}URL: {Style.RESET_ALL}").strip()
                if url:
                    scraper.get_page(url)
                    soup = scraper.get_soup()
                    print(f"{Fore.CYAN}Elementos encontrados:")
                    print(f"{Fore.WHITE}  - Links: {len(soup.find_all('a'))}")
                    print(f"{Fore.WHITE}  - Imágenes: {len(soup.find_all('img'))}")
            
            elif opcion == '3':
                nombre = input(f"{Fore.GREEN}Nombre archivo (ej: captura.png): {Style.RESET_ALL}").strip()
                scraper.captura_pantalla(nombre if nombre else 'screenshot.png')
            
            elif opcion == '4':
                soup = scraper.get_soup()
                with open('output/pagina_actual.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                print(f"{Fore.GREEN}✓ HTML guardado en: output/pagina_actual.html")
            
            elif opcion == '5':
                break
            
            else:
                print(f"{Fore.RED}❌ Opción inválida")
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Interrumpido")
    
    finally:
        scraper.close()


# ═══════════════════════════════════════════════════════════════
# EJECUCIÓN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Ejecutar ejemplo universal
    ejemplo_universal()
    
    # O ejecutar modo interactivo:
    # modo_interactivo()
