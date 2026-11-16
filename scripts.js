/*
 * Scripts que Selenium ejecuta dentro del navegador.
 *
 * Este archivo no se incluye en ninguna página. js_scripts.py lo lee entero y
 * le añade al final
 *
 *     return WebScraperJS.<funcion>.apply(null, arguments);
 *
 * para ejecutarlo con driver.execute_script(). Por eso todo lo que haya aquí
 * vive dentro de la función que crea Selenium y no ensucia la página.
 *
 * Las funciones de extracción devuelven una lista de objetos con las claves
 * titulo, precio, descripcion, enlace e imagen. La numeración y el valor
 * 'N/A' de los campos vacíos los añade Python (extractor.normalizar_items).
 */

function limpiarTexto(texto) {
    return texto ? texto.trim().replace(/\s+/g, ' ') : '';
}

function textoDe(raiz, selector) {
    const elemento = raiz.querySelector(selector);
    return elemento ? limpiarTexto(elemento.textContent) : '';
}

function enlaceDe(raiz, selector) {
    const enlace = raiz.querySelector(selector || 'a[href]');
    return enlace ? enlace.href : '';
}

function imagenDe(raiz) {
    const imagen = raiz.querySelector('img');
    if (!imagen) {
        return '';
    }
    return imagen.currentSrc || imagen.src || imagen.dataset.src || '';
}

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

/**
 * Elimina avisos de cookies, newsletters y modales que tapan el contenido.
 * Solo quita los elementos con posición fija o absoluta.
 * Devuelve cuántos elementos se han eliminado.
 */
function removerOverlays() {
    const selectores = [
        '.modal', '.popup', '.overlay',
        '[class*="cookie" i]', '[id*="cookie" i]',
        '[class*="newsletter" i]', '[id*="newsletter" i]',
        '.gdpr', '#gdpr',
        '[class*="consent" i]'
    ];

    let removidos = 0;
    selectores.forEach(selector => {
        document.querySelectorAll(selector).forEach(elemento => {
            const posicion = window.getComputedStyle(elemento).position;
            if (posicion === 'fixed' || posicion === 'absolute') {
                elemento.remove();
                removidos++;
            }
        });
    });

    // Algunos avisos bloquean el scroll de la página
    if (document.body) {
        document.body.style.overflow = 'auto';
    }
    return removidos;
}

// ---------------------------------------------------------------------------
// Extracción específica por sitio
// ---------------------------------------------------------------------------

function extraerPcComponentes() {
    const datos = [];
    document.querySelectorAll('[data-product-name]').forEach(producto => {
        const titulo = producto.dataset.productName || textoDe(producto, 'h3, h2');
        if (!titulo) {
            return;
        }
        datos.push({
            titulo: titulo,
            precio: producto.dataset.productPrice || textoDe(producto, '[class*="precio" i]'),
            descripcion: '',
            enlace: producto.href || enlaceDe(producto),
            imagen: imagenDe(producto)
        });
    });
    return datos;
}

function extraerAmazon() {
    const datos = [];
    document.querySelectorAll('[data-asin]:not([data-asin=""])').forEach(producto => {
        const titulo = textoDe(producto, 'h2') || textoDe(producto, '.a-text-normal');
        if (titulo.length <= 3) {
            return;
        }
        // .a-price-whole ya incluye el separador decimal ("1.299," o "1,299.")
        const entero = textoDe(producto, '.a-price-whole');
        const decimales = textoDe(producto, '.a-price-fraction');
        const simbolo = textoDe(producto, '.a-price-symbol');
        datos.push({
            titulo: titulo,
            precio: entero ? `${entero}${decimales}${simbolo}` : '',
            descripcion: '',
            enlace: enlaceDe(producto, 'h2 a') || enlaceDe(producto, 'a.a-link-normal'),
            imagen: imagenDe(producto)
        });
    });
    return datos;
}

function extraerEbay() {
    const datos = [];
    document.querySelectorAll('.s-item, .lvresult').forEach(producto => {
        const titulo = textoDe(producto, '.s-item__title, h3');
        if (!titulo || titulo === 'Shop on eBay') {
            return;
        }
        datos.push({
            titulo: titulo,
            precio: textoDe(producto, '.s-item__price, .lvprice'),
            descripcion: '',
            enlace: enlaceDe(producto, '.s-item__link, a[href]'),
            imagen: imagenDe(producto)
        });
    });
    return datos;
}

function extraerAliExpress() {
    const datos = [];
    document.querySelectorAll('[data-product-id], .product-item, .list-item').forEach(producto => {
        const titulo = textoDe(producto, 'h1, h2, h3, .product-title');
        if (!titulo) {
            return;
        }
        datos.push({
            titulo: titulo,
            precio: textoDe(producto, '[class*="price" i]'),
            descripcion: '',
            enlace: enlaceDe(producto),
            imagen: imagenDe(producto)
        });
    });
    return datos;
}

function extraerWordPress() {
    const datos = [];
    document.querySelectorAll('article, .post, .entry').forEach(articulo => {
        const titulo = textoDe(articulo, 'h2, h1, .entry-title');
        if (!titulo) {
            return;
        }
        datos.push({
            titulo: titulo,
            precio: '',
            descripcion: textoDe(articulo, '.entry-summary, .excerpt, p').substring(0, 150),
            enlace: enlaceDe(articulo, 'a[rel="bookmark"], .entry-title a'),
            imagen: imagenDe(articulo)
        });
    });
    return datos;
}

// Funciones que se pueden llamar desde Python (js_scripts.py)
const WebScraperJS = {
    removerOverlays,
    extraerPcComponentes,
    extraerAmazon,
    extraerEbay,
    extraerAliExpress,
    extraerWordPress
};
