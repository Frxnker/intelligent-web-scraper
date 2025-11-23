// ============================================================================
// WEB SCRAPER - JAVASCRIPT SCRIPTS
// Colección de scripts JavaScript para extracción optimizada de datos
// ============================================================================

// ----------------------------------------------------------------------------
// SCRIPTS GENÉRICOS DE UTILIDAD
// ----------------------------------------------------------------------------

/**
 * Detecta cuando la página ha cargado completamente
 * Incluye soporte para jQuery y AJAX
 */
function detectarCargaCompleta() {
    return new Promise((resolve) => {
        if (document.readyState === 'complete') {
            if (typeof jQuery !== 'undefined' && jQuery.active > 0) {
                setTimeout(() => resolve(true), 500);
            } else {
                resolve(true);
            }
        } else {
            window.addEventListener('load', () => {
                setTimeout(() => resolve(true), 500);
            });
        }
    });
}

/**
 * Scroll automático hasta el final de la página
 * Útil para cargar contenido lazy-loaded
 */
async function scrollInfinito() {
    let alturaAnterior = 0;
    let intentos = 0;
    const maxIntentos = 5;

    while (intentos < maxIntentos) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const alturaActual = document.body.scrollHeight;
        if (alturaActual === alturaAnterior) {
            intentos++;
        } else {
            intentos = 0;
            alturaAnterior = alturaActual;
        }
    }
    
    window.scrollTo(0, 0);
    return true;
}

/**
 * Cuenta elementos en la página
 */
function contarElementos() {
    return {
        enlaces: document.querySelectorAll('a').length,
        imagenes: document.querySelectorAll('img').length,
        productos: document.querySelectorAll('[class*="product"], [class*="item"]').length,
        articulos: document.querySelectorAll('article').length,
        parrafos: document.querySelectorAll('p').length
    };
}

/**
 * Remueve overlays, popups y modales
 */
function removerOverlays() {
    const selectores = [
        '[class*="modal"]',
        '[class*="popup"]',
        '[class*="overlay"]',
        '[class*="cookie"]',
        '[class*="newsletter"]',
        '[id*="modal"]',
        '[id*="popup"]'
    ];
    
    selectores.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            if (el && (el.style.position === 'fixed' || el.style.position === 'absolute')) {
                el.remove();
            }
        });
    });
    
    document.body.style.overflow = 'auto';
    return true;
}

/**
 * Obtiene metadata de la página
 */
function obtenerMetadata() {
    return {
        titulo: document.title,
        url: window.location.href,
        dominio: window.location.hostname,
        descripcion: document.querySelector('meta[name="description"]')?.content || '',
        idioma: document.documentElement.lang || 'unknown',
        charset: document.characterSet,
        generador: document.querySelector('meta[name="generator"]')?.content || 'unknown'
    };
}

// ----------------------------------------------------------------------------
// SCRIPTS ESPECÍFICOS POR SITIO E-COMMERCE
// ----------------------------------------------------------------------------

/**
 * Extracción para PcComponentes
 */
function extraerPcComponentes() {
    const productos = [];
    const elementos = document.querySelectorAll('[data-product-name], .tarjeta-articulo, [class*="product"]');
    
    elementos.forEach(el => {
        const nombre = el.getAttribute('data-product-name') || 
                      el.querySelector('[class*="name"], h3, h4')?.textContent.trim();
        const precio = el.getAttribute('data-product-price') || 
                      el.querySelector('[class*="price"]')?.textContent.trim();
        const url = el.querySelector('a')?.href;
        const imagen = el.querySelector('img')?.src;
        
        if (nombre && precio) {
            productos.push({ nombre, precio, url, imagen });
        }
    });
    
    return productos;
}

/**
 * Extracción para Amazon
 */
function extraerAmazon() {
    const productos = [];
    const elementos = document.querySelectorAll('[data-asin], [data-component-type="s-search-result"]');
    
    elementos.forEach(el => {
        const nombre = el.querySelector('h2, .a-text-normal')?.textContent.trim();
        const precioEntero = el.querySelector('.a-price-whole')?.textContent.trim();
        const precioDecimal = el.querySelector('.a-price-fraction')?.textContent.trim();
        const precio = precioEntero && precioDecimal ? `${precioEntero}${precioDecimal}` : null;
        const url = el.querySelector('h2 a, .a-link-normal')?.href;
        const imagen = el.querySelector('img')?.src;
        
        if (nombre && precio) {
            productos.push({ nombre, precio, url, imagen });
        }
    });
    
    return productos;
}

/**
 * Extracción para eBay
 */
function extraerEbay() {
    const productos = [];
    const elementos = document.querySelectorAll('.s-item, .lvresult');
    
    elementos.forEach(el => {
        const nombre = el.querySelector('.s-item__title, h3')?.textContent.trim();
        const precio = el.querySelector('.s-item__price, .lvprice')?.textContent.trim();
        const url = el.querySelector('a')?.href;
        const imagen = el.querySelector('img')?.src;
        
        if (nombre && precio && !nombre.includes('Shop on eBay')) {
            productos.push({ nombre, precio, url, imagen });
        }
    });
    
    return productos;
}

/**
 * Extracción para AliExpress
 */
function extraerAliExpress() {
    const productos = [];
    const elementos = document.querySelectorAll('[data-product-id], .product-item, [class*="list--item"]');
    
    elementos.forEach(el => {
        const nombre = el.querySelector('[class*="title"], h1, h2, h3')?.textContent.trim();
        const precio = el.querySelector('[class*="price"]')?.textContent.trim();
        const url = el.querySelector('a')?.href;
        const imagen = el.querySelector('img')?.src;
        
        if (nombre && precio) {
            productos.push({ nombre, precio, url, imagen });
        }
    });
    
    return productos;
}

/**
 * Extracción para blogs WordPress
 */
function extraerWordPressBlog() {
    const articulos = [];
    const elementos = document.querySelectorAll('article, .post, .entry');
    
    elementos.forEach(el => {
        const titulo = el.querySelector('h1, h2, .entry-title')?.textContent.trim();
        const extracto = el.querySelector('.entry-summary, .excerpt, p')?.textContent.trim();
        const url = el.querySelector('a')?.href;
        const fecha = el.querySelector('time, .published')?.textContent.trim();
        const autor = el.querySelector('.author, .by-author')?.textContent.trim();
        
        if (titulo) {
            articulos.push({ titulo, extracto, url, fecha, autor });
        }
    });
    
    return articulos;
}

// ----------------------------------------------------------------------------
// DETECCIÓN AUTOMÁTICA DE TIPO DE SITIO
// ----------------------------------------------------------------------------

/**
 * Detecta el tipo de sitio web
 */
function detectarTipoSitio() {
    const url = window.location.hostname.toLowerCase();
    const contenido = document.body.innerHTML.toLowerCase();
    
    // E-commerce
    if (url.includes('amazon') || contenido.includes('add to cart') || 
        contenido.includes('añadir al carrito') || document.querySelector('[class*="cart"]')) {
        return 'ecommerce';
    }
    
    // Blog
    if (document.querySelectorAll('article').length > 2 || 
        contenido.includes('wordpress') || document.querySelector('.wp-')) {
        return 'blog';
    }
    
    // Noticias
    if (url.includes('news') || url.includes('noticia') || 
        document.querySelectorAll('article').length > 5) {
        return 'noticias';
    }
    
    // Foro
    if (url.includes('forum') || url.includes('foro') || 
        document.querySelector('[class*="thread"], [class*="topic"]')) {
        return 'foro';
    }
    
    return 'general';
}

// ----------------------------------------------------------------------------
// EXPORTAR PARA USO EN PYTHON
// ----------------------------------------------------------------------------

// Este objeto se puede acceder desde Python usando execute_script
window.WebScraperJS = {
    detectarCargaCompleta,
    scrollInfinito,
    contarElementos,
    removerOverlays,
    obtenerMetadata,
    extraerPcComponentes,
    extraerAmazon,
    extraerEbay,
    extraerAliExpress,
    extraerWordPressBlog,
    detectarTipoSitio
};
