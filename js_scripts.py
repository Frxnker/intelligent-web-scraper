"""
📜 SCRIPTS JAVASCRIPT PERSONALIZADOS
Scripts optimizados para sitios específicos
"""

class JavaScriptScripts:
    """
    Colección de scripts JavaScript para diferentes sitios web
    """
    
    # ═══════════════════════════════════════════════════════════════
    # SCRIPTS GENÉRICOS
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def detectar_carga_completa():
        """Detecta cuando la página terminó de cargar completamente"""
        return """
        return new Promise((resolve) => {
            // Esperar a document.readyState
            if (document.readyState === 'complete') {
                // Esperar jQuery si existe
                if (typeof jQuery !== 'undefined') {
                    const checkJQuery = setInterval(() => {
                        if (jQuery.active === 0) {
                            clearInterval(checkJQuery);
                            resolve(true);
                        }
                    }, 100);
                } else {
                    resolve(true);
                }
            } else {
                window.addEventListener('load', () => resolve(true));
            }
        });
        """
    
    @staticmethod
    def scroll_infinito():
        """Hace scroll hasta cargar todo el contenido (para páginas infinitas)"""
        return """
        async function scrollHastaFinal() {
            let alturaAnterior = 0;
            let intentosSinCambio = 0;
            const maxIntentos = 5;
            
            while (intentosSinCambio < maxIntentos) {
                // Scroll hasta el final
                window.scrollTo(0, document.body.scrollHeight);
                
                // Esperar a que cargue nuevo contenido
                await new Promise(resolve => setTimeout(resolve, 1500));
                
                const alturaActual = document.body.scrollHeight;
                
                if (alturaActual === alturaAnterior) {
                    intentosSinCambio++;
                } else {
                    intentosSinCambio = 0;
                }
                
                alturaAnterior = alturaActual;
            }
            
            // Volver arriba
            window.scrollTo(0, 0);
            return true;
        }
        
        return scrollHastaFinal();
        """
    
    @staticmethod
    def contar_elementos():
        """Cuenta elementos comunes en la página"""
        return """
        return {
            links: document.querySelectorAll('a').length,
            imagenes: document.querySelectorAll('img').length,
            productos: document.querySelectorAll('[class*="product" i], [data-asin], [data-product-name]').length,
            articulos: document.querySelectorAll('article').length,
            parrafos: document.querySelectorAll('p').length
        };
        """
    
    # ═══════════════════════════════════════════════════════════════
    # SCRIPTS ESPECÍFICOS POR SITIO
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def pccomponentes():
        """Script optimizado para PcComponentes"""
        return """
        const productos = document.querySelectorAll('[data-product-name]');
        const datos = [];
        
        productos.forEach((prod, i) => {
            const titulo = prod.dataset.productName || prod.querySelector('h3, h2')?.textContent.trim();
            const precio = prod.dataset.productPrice || prod.querySelector('[class*="precio" i]')?.textContent.trim();
            const imagen = prod.querySelector('img')?.src || prod.querySelector('img')?.dataset.src;
            const enlace = prod.href || prod.querySelector('a')?.href;
            
            if (titulo) {
                datos.push({
                    numero: i + 1,
                    titulo: titulo,
                    precio: precio || 'N/A',
                    enlace: enlace || 'N/A',
                    imagen: imagen || 'N/A',
                    descripcion: 'N/A'
                });
            }
        });
        
        return datos;
        """
    
    @staticmethod
    def amazon():
        """Script optimizado para Amazon"""
        return """
        const productos = document.querySelectorAll('[data-asin]:not([data-asin=""])');
        const datos = [];
        
        productos.forEach((prod, i) => {
            const titulo = prod.querySelector('h2')?.textContent.trim() || 
                          prod.querySelector('.a-text-normal')?.textContent.trim();
            
            const precioEntero = prod.querySelector('.a-price-whole')?.textContent.trim();
            const precioDecimal = prod.querySelector('.a-price-fraction')?.textContent.trim();
            const precio = precioEntero ? `${precioEntero}${precioDecimal || ''}€` : 'N/A';
            
            const imagen = prod.querySelector('img')?.src;
            const enlace = prod.querySelector('h2 a')?.href || prod.querySelector('a.a-link-normal')?.href;
            
            if (titulo && titulo.length > 3) {
                datos.push({
                    numero: i + 1,
                    titulo: titulo,
                    precio: precio,
                    enlace: enlace || 'N/A',
                    imagen: imagen || 'N/A',
                    descripcion: 'N/A'
                });
            }
        });
        
        return datos;
        """
    
    @staticmethod
    def ebay():
        """Script optimizado para eBay"""
        return """
        const productos = document.querySelectorAll('.s-item, .lvresult');
        const datos = [];
        
        productos.forEach((prod, i) => {
            const titulo = prod.querySelector('.s-item__title, h3')?.textContent.trim();
            const precio = prod.querySelector('.s-item__price, .lvprice')?.textContent.trim();
            const imagen = prod.querySelector('img')?.src;
            const enlace = prod.querySelector('.s-item__link, a')?.href;
            
            if (titulo && titulo !== 'Shop on eBay') {
                datos.push({
                    numero: i + 1,
                    titulo: titulo,
                    precio: precio || 'N/A',
                    enlace: enlace || 'N/A',
                    imagen: imagen || 'N/A',
                    descripcion: 'N/A'
                });
            }
        });
        
        return datos;
        """
    
    @staticmethod
    def aliexpress():
        """Script optimizado para AliExpress"""
        return """
        const productos = document.querySelectorAll('[data-product-id], .product-item, .list-item');
        const datos = [];
        
        productos.forEach((prod, i) => {
            const titulo = prod.querySelector('h1, h2, h3, .product-title')?.textContent.trim();
            const precio = prod.querySelector('[class*="price" i]')?.textContent.trim();
            const imagen = prod.querySelector('img')?.src || prod.querySelector('img')?.dataset.src;
            const enlace = prod.querySelector('a')?.href;
            
            if (titulo) {
                datos.push({
                    numero: i + 1,
                    titulo: titulo,
                    precio: precio || 'N/A',
                    enlace: enlace || 'N/A',
                    imagen: imagen || 'N/A',
                    descripcion: 'N/A'
                });
            }
        });
        
        return datos;
        """
    
    @staticmethod
    def wordpress_blog():
        """Script optimizado para blogs WordPress"""
        return """
        const articulos = document.querySelectorAll('article, .post, .entry');
        const datos = [];
        
        articulos.forEach((art, i) => {
            const titulo = art.querySelector('h2, h1, .entry-title')?.textContent.trim();
            const descripcion = art.querySelector('.entry-summary, .excerpt, p')?.textContent.trim().substring(0, 150);
            const enlace = art.querySelector('a[rel="bookmark"], .entry-title a')?.href;
            const imagen = art.querySelector('img')?.src;
            
            if (titulo) {
                datos.push({
                    numero: i + 1,
                    titulo: titulo,
                    descripcion: descripcion || 'N/A',
                    enlace: enlace || 'N/A',
                    imagen: imagen || 'N/A',
                    precio: 'N/A'
                });
            }
        });
        
        return datos;
        """
    
    # ═══════════════════════════════════════════════════════════════
    # SCRIPTS DE UTILIDAD
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def detectar_tipo_sitio():
        """Detecta qué tipo de sitio es (e-commerce, blog, etc.)"""
        return """
        const tipos = [];
        
        // Detectar e-commerce
        if (document.querySelector('[data-product-name], [data-asin], [class*="product" i]')) {
            tipos.push('ecommerce');
        }
        
        // Detectar blog
        if (document.querySelector('article, .post, .entry')) {
            tipos.push('blog');
        }
        
        // Detectar noticias
        if (document.querySelector('.news, .article, [class*="noticia" i]')) {
            tipos.push('noticias');
        }
        
        // Detectar foro
        if (document.querySelector('.forum, .thread, [class*="topic" i]')) {
            tipos.push('foro');
        }
        
        return tipos.length > 0 ? tipos : ['generico'];
        """
    
    @staticmethod
    def obtener_metadata():
        """Extrae metadata útil de la página"""
        return """
        return {
            titulo: document.title,
            url: window.location.href,
            dominio: window.location.hostname,
            descripcion: document.querySelector('meta[name="description"]')?.content || '',
            idioma: document.documentElement.lang || 'desconocido',
            charset: document.characterSet,
            generador: document.querySelector('meta[name="generator"]')?.content || 'desconocido'
        };
        """
    
    @staticmethod
    def remover_overlays():
        """Remueve popups, cookies, newsletters molestos"""
        return """
        // Selectores comunes de overlays
        const selectores = [
            '.modal', '.popup', '.overlay',
            '[class*="cookie" i]', '[id*="cookie" i]',
            '[class*="newsletter" i]', '[id*="newsletter" i]',
            '.gdpr', '#gdpr',
            '[class*="consent" i]'
        ];
        
        let removidos = 0;
        selectores.forEach(selector => {
            document.querySelectorAll(selector).forEach(elem => {
                // Solo remover si está visible y cubre contenido
                const style = window.getComputedStyle(elem);
                if (style.position === 'fixed' || style.position === 'absolute') {
                    elem.remove();
                    removidos++;
                }
            });
        });
        
        // Habilitar scroll si estaba bloqueado
        document.body.style.overflow = 'auto';
        
        return removidos;
        """
    
    @staticmethod
    def obtener_script_para_sitio(url):
        """
        Devuelve el script JavaScript optimizado según la URL
        
        Args:
            url: URL del sitio
            
        Returns:
            str: Script JavaScript o None
        """
        url_lower = url.lower()
        
        if 'pccomponentes' in url_lower:
            return JavaScriptScripts.pccomponentes()
        elif 'amazon' in url_lower:
            return JavaScriptScripts.amazon()
        elif 'ebay' in url_lower:
            return JavaScriptScripts.ebay()
        elif 'aliexpress' in url_lower:
            return JavaScriptScripts.aliexpress()
        elif 'wordpress' in url_lower or '/wp-content/' in url_lower:
            return JavaScriptScripts.wordpress_blog()
        else:
            return None  # Usar extracción genérica


# ═══════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("📜 Scripts JavaScript disponibles:")
    print("\n🔧 Genéricos:")
    print("  - detectar_carga_completa()")
    print("  - scroll_infinito()")
    print("  - contar_elementos()")
    print("  - detectar_tipo_sitio()")
    print("  - obtener_metadata()")
    print("  - remover_overlays()")
    print("\n🛒 E-commerce:")
    print("  - pccomponentes()")
    print("  - amazon()")
    print("  - ebay()")
    print("  - aliexpress()")
    print("\n📰 Contenido:")
    print("  - wordpress_blog()")
    print("\n💡 Uso:")
    print("  script = JavaScriptScripts.obtener_script_para_sitio(url)")
    print("  datos = driver.execute_script(script)")
