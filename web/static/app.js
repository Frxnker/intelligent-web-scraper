/* Intelligent Web Scraper - interfaz web.
 *
 * JavaScript sin frameworks. Todo lo que viene de las páginas scrapeadas
 * (títulos, enlaces, imágenes) se inserta como texto con el helper el(), nunca
 * con innerHTML, y solo se aceptan enlaces e imágenes http(s).
 */
'use strict';

// =====================================================================
// Utilidades de DOM
// =====================================================================

const $ = (selector, raiz = document) => raiz.querySelector(selector);

/** Crea un elemento. Los hijos de texto se insertan como texto, nunca como HTML. */
function el(etiqueta, atributos = {}, ...hijos) {
    const nodo = document.createElement(etiqueta);
    for (const [clave, valor] of Object.entries(atributos)) {
        if (valor === null || valor === undefined || valor === false) continue;
        if (clave === 'class') nodo.className = valor;
        else if (clave.startsWith('on') && typeof valor === 'function') nodo.addEventListener(clave.slice(2), valor);
        else nodo.setAttribute(clave, valor === true ? '' : String(valor));
    }
    for (const hijo of hijos.flat()) {
        if (hijo === null || hijo === undefined || hijo === false) continue;
        nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
    }
    return nodo;
}

function mostrar(contenedor, ...nodos) {
    contenedor.replaceChildren(...nodos.flat().filter(Boolean));
}

const ICONOS = {
    externo: ['M15 3h6v6', 'M10 14 21 3', 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6'],
    imagen: ['M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',
             'M8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z', 'm21 15-5-5L5 21'],
};

function icono(nombre, tamano = 16) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const atributos = {
        width: tamano, height: tamano, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
        'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true',
    };
    for (const [clave, valor] of Object.entries(atributos)) svg.setAttribute(clave, valor);
    for (const d of ICONOS[nombre]) {
        const trazo = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        trazo.setAttribute('d', d);
        svg.append(trazo);
    }
    return svg;
}

function debounce(funcion, espera) {
    let temporizador;
    return (...args) => {
        clearTimeout(temporizador);
        temporizador = setTimeout(() => funcion(...args), espera);
    };
}

// =====================================================================
// Formato
// =====================================================================

const NUMERO = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ENTERO = new Intl.NumberFormat('es-ES');

/** Los campos vacíos de los productos scrapeados llegan como 'N/A'. */
const valor = (texto) => (texto && texto !== 'N/A' ? texto : null);

function formatearPrecio(importe, moneda, textoOriginal) {
    if (importe === null || importe === undefined) return valor(textoOriginal) || 'Sin precio';
    if (moneda) {
        try {
            return new Intl.NumberFormat('es-ES', { style: 'currency', currency: moneda }).format(importe);
        } catch {
            return `${NUMERO.format(importe)} ${moneda}`;
        }
    }
    return NUMERO.format(importe);
}

/** Fechas de SQLite (CURRENT_TIMESTAMP, en UTC) a hora local. */
function formatearFechaUtc(texto) {
    if (!texto) return '—';
    const fecha = new Date(`${texto.replace(' ', 'T')}Z`);
    return Number.isNaN(fecha.getTime()) ? texto : fecha.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
}

/** Fechas que el servidor ya guarda en hora local (tareas programadas). */
function formatearFechaLocal(texto) {
    if (!texto) return '—';
    const fecha = new Date(texto.replace(' ', 'T'));
    return Number.isNaN(fecha.getTime()) ? texto : fecha.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
}

function formatearDuracion(segundos) {
    if (segundos === null || segundos === undefined) return '—';
    if (segundos < 1) return 'menos de 1 s';
    if (segundos < 60) return `${segundos.toLocaleString('es-ES', { maximumFractionDigits: 1 })} s`;
    return `${Math.floor(segundos / 60)} min ${Math.round(segundos % 60)} s`;
}

function formatearIntervalo(minutos) {
    if (minutos % 1440 === 0) return minutos === 1440 ? 'Cada día' : `Cada ${minutos / 1440} días`;
    if (minutos % 60 === 0) return minutos === 60 ? 'Cada hora' : `Cada ${minutos / 60} horas`;
    return `Cada ${minutos} min`;
}

/** Devuelve la URL solo si es http(s); evita enlaces javascript: y similares. */
function urlSegura(texto) {
    if (!valor(texto)) return null;
    try {
        const url = new URL(texto);
        return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
    } catch {
        return null;
    }
}

function enlaceExterno(url, texto) {
    const segura = urlSegura(url);
    if (!segura) return null;
    return el('a', {
        class: 'enlace-externo', href: segura, target: '_blank', rel: 'noopener noreferrer',
        onclick: (evento) => evento.stopPropagation(),
    }, texto, icono('externo', 14));
}

function textoConEnlace(texto, url) {
    const segura = urlSegura(url);
    const contenido = valor(texto) || 'Sin título';
    return segura ? el('a', { href: segura, target: '_blank', rel: 'noopener noreferrer' }, contenido) : contenido;
}

// =====================================================================
// API
// =====================================================================

class ErrorApi extends Error {
    constructor(mensaje, estado = 0, detalles = []) {
        super(mensaje);
        this.estado = estado;
        this.detalles = detalles;
    }
}

async function api(ruta, { json, ...opciones } = {}) {
    const init = { ...opciones, headers: { Accept: 'application/json', ...(opciones.headers || {}) } };
    if (json !== undefined) {
        init.method = init.method || 'POST';
        init.headers['Content-Type'] = 'application/json';
        init.body = JSON.stringify(json);
    }

    let respuesta;
    try {
        respuesta = await fetch(ruta, init);
    } catch {
        throw new ErrorApi('No se pudo conectar con el servidor. Comprueba que servidor.py sigue en marcha.');
    }
    const esJson = (respuesta.headers.get('Content-Type') || '').includes('application/json');
    const cuerpo = esJson ? await respuesta.json().catch(() => null) : null;
    if (!respuesta.ok) {
        throw new ErrorApi(cuerpo?.error || `Error ${respuesta.status}`, respuesta.status, cuerpo?.detalles || []);
    }
    return cuerpo;
}

const NOMBRES_CAMPOS = {
    url: 'URL', url1: 'URL del primer sitio', url2: 'URL del segundo sitio', paginas: 'Páginas',
    nombre: 'Nombre', nombre1: 'Nombre del sitio 1', nombre2: 'Nombre del sitio 2', umbral: 'Similitud',
    intervalo_minutos: 'Intervalo', max_paginas: 'Páginas', precio_min: 'Precio mínimo',
    precio_max: 'Precio máximo', q: 'Búsqueda', sitio: 'Sitio',
};

function textoError(error) {
    const detalles = (error.detalles || []).map((d) => (d.campo ? `${NOMBRES_CAMPOS[d.campo] || d.campo}: ${d.mensaje}` : d.mensaje));
    return detalles.length ? `${error.message}. ${detalles.join('. ')}.` : error.message;
}

/** Consulta un job cada segundo hasta que termina o falla. */
function seguirJob(id, { alActualizar, alTerminar, alFallar }) {
    let fallosSeguidos = 0;
    async function consultar() {
        try {
            const job = await api(`/api/jobs/${encodeURIComponent(id)}`);
            fallosSeguidos = 0;
            alActualizar(job);
            if (job.estado === 'terminado') return alTerminar(job);
            if (job.estado === 'error') return alFallar(new ErrorApi(job.error || 'Error desconocido'));
        } catch (error) {
            if (error.estado === 404) return alFallar(new ErrorApi('El trabajo ya no existe (¿se reinició el servidor?).'));
            fallosSeguidos += 1;
            if (fallosSeguidos >= 5) return alFallar(error);
        }
        setTimeout(consultar, 1000);
    }
    consultar();
}

// =====================================================================
// Componentes
// =====================================================================

function estadoCarga(texto = 'Cargando…') {
    return el('div', { class: 'estado', role: 'status' }, el('span', { class: 'spinner', 'aria-hidden': 'true' }), texto);
}

function estadoVacio(titulo, texto, accion) {
    return el('div', { class: 'estado panel' }, el('p', { class: 'estado-titulo' }, titulo), texto && el('p', {}, texto), accion);
}

function estadoError(error, reintentar) {
    return el('div', { class: 'estado estado-error', role: 'alert' },
        el('p', { class: 'estado-titulo' }, 'Algo ha fallado'),
        el('p', {}, textoError(error)),
        reintentar && el('button', { class: 'boton boton-secundario', type: 'button', onclick: reintentar }, 'Reintentar'));
}

function mensajeError(texto) {
    return el('p', { class: 'mensaje-error', role: 'alert' }, texto);
}

function tabla(cabeceras, filas, { numericas = [] } = {}) {
    return el('div', { class: 'tabla-contenedor' },
        el('table', {},
            el('thead', {}, el('tr', {}, cabeceras.map((texto, i) => el('th', { scope: 'col', class: numericas.includes(i) ? 'numero' : null }, texto)))),
            el('tbody', {}, filas)));
}

function tarjetaDato(etiqueta, dato, detalle) {
    return el('div', { class: 'tarjeta-dato' },
        el('span', { class: 'etiqueta' }, etiqueta),
        el('span', { class: 'valor' }, dato),
        detalle && el('span', { class: 'detalle' }, detalle));
}

function crearProgreso(titulo) {
    const texto = el('span', {}, 'En cola…');
    const relleno = el('div', { class: 'barra-relleno' });
    const barra = el('div', {
        class: 'barra barra-animada', role: 'progressbar', 'aria-label': titulo,
        'aria-valuemin': 0, 'aria-valuemax': 100, 'aria-valuenow': 0,
    }, relleno);
    const nodo = el('div', { class: 'panel progreso', 'aria-live': 'polite' },
        el('div', { class: 'progreso-cabecera' }, el('span', {}, titulo), texto), barra);

    function actualizar(job) {
        const { actual, total } = job.progreso;
        let porcentaje = 3;
        if (job.estado === 'terminado') porcentaje = 100;
        else if (job.estado === 'en_curso' && total) porcentaje = Math.max(5, ((actual - 0.5) / total) * 100);
        relleno.style.width = `${porcentaje}%`;
        barra.setAttribute('aria-valuenow', String(Math.round(porcentaje)));
        if (job.estado === 'pendiente') texto.textContent = 'En cola…';
        else if (job.estado === 'en_curso') texto.textContent = job.progreso.texto || 'Empezando…';
    }
    return { nodo, actualizar };
}

function imagenProducto(url) {
    const contenedor = el('div', { class: 'producto-imagen' });
    const marcador = () => contenedor.replaceChildren(icono('imagen', 32));
    const segura = urlSegura(url);
    if (!segura) {
        marcador();
        return contenedor;
    }
    const imagen = el('img', { src: segura, alt: '', loading: 'lazy', decoding: 'async', referrerpolicy: 'no-referrer' });
    imagen.addEventListener('error', marcador, { once: true });
    contenedor.append(imagen);
    return contenedor;
}

// =====================================================================
// Pestañas
// =====================================================================

const VISTAS = ['scrapear', 'productos', 'comparar', 'tareas', 'estadisticas'];
const pestanas = [...document.querySelectorAll('.pestana')];

function vistaDesdeHash() {
    const nombre = location.hash.slice(1);
    return VISTAS.includes(nombre) ? nombre : 'scrapear';
}

function activarVista(nombre) {
    for (const pestana of pestanas) {
        const activa = pestana.dataset.vista === nombre;
        pestana.setAttribute('aria-selected', String(activa));
        pestana.tabIndex = activa ? 0 : -1;
    }
    for (const vista of VISTAS) $(`#vista-${vista}`).hidden = vista !== nombre;

    if (nombre === 'productos') Productos.mostrar();
    else if (nombre === 'tareas') Tareas.cargar();
    else if (nombre === 'estadisticas') Estadisticas.cargar();
}

function irAVista(nombre) {
    if (location.hash === `#${nombre}`) activarVista(nombre);
    else location.hash = `#${nombre}`;
}

function iniciarPestanas() {
    for (const pestana of pestanas) {
        pestana.addEventListener('click', () => irAVista(pestana.dataset.vista));
        pestana.addEventListener('keydown', (evento) => {
            if (evento.key !== 'ArrowRight' && evento.key !== 'ArrowLeft') return;
            const paso = evento.key === 'ArrowRight' ? 1 : -1;
            const siguiente = pestanas[(pestanas.indexOf(pestana) + paso + pestanas.length) % pestanas.length];
            siguiente.focus();
            irAVista(siguiente.dataset.vista);
        });
    }
    window.addEventListener('hashchange', () => activarVista(vistaDesdeHash()));
}

// =====================================================================
// Scrapear
// =====================================================================

const Scrapear = {
    form: $('#form-scrape'),
    boton: $('#scrape-enviar'),
    salida: $('#scrape-estado'),

    init() {
        this.form.addEventListener('submit', (evento) => this.enviar(evento));
        // Si se recarga la página con un scraping en marcha, se sigue su progreso
        const pendiente = sessionStorage.getItem('job-scrape');
        if (pendiente) this.seguir(pendiente);
    },

    async enviar(evento) {
        evento.preventDefault();
        const url = this.form.url.value.trim();
        const paginas = Number(this.form.paginas.value);
        if (!url) return mostrar(this.salida, mensajeError('Escribe la URL del listado.'));
        if (!Number.isInteger(paginas) || paginas < 1 || paginas > 10) {
            return mostrar(this.salida, mensajeError('El número de páginas tiene que estar entre 1 y 10.'));
        }

        this.ocupado(true);
        try {
            const { job_id: id } = await api('/api/scrape', { json: { url, paginas } });
            sessionStorage.setItem('job-scrape', id);
            this.seguir(id);
        } catch (error) {
            this.ocupado(false);
            mostrar(this.salida, estadoError(error));
        }
    },

    seguir(id) {
        this.ocupado(true);
        const progreso = crearProgreso('Scrapeando');
        mostrar(this.salida, progreso.nodo);
        const terminar = (nodo) => {
            sessionStorage.removeItem('job-scrape');
            this.ocupado(false);
            mostrar(this.salida, nodo);
        };
        seguirJob(id, {
            alActualizar: (job) => progreso.actualizar(job),
            alTerminar: (job) => terminar(this.resultado(job.resultado)),
            alFallar: (error) => terminar(estadoError(error)),
        });
    },

    ocupado(activo) {
        this.boton.disabled = activo;
        this.boton.textContent = activo ? 'Scrapeando…' : 'Scrapear';
    },

    resultado(r) {
        if (!r.productos) {
            return estadoVacio('No se encontró ningún producto',
                `La página se descargó pero no se reconoció ningún listado. Revisa output/${r.sitio}.html para ver su estructura.`);
        }
        const filas = r.muestra.map((p) => el('tr', {},
            el('td', { class: 'celda-titulo' }, valor(p.titulo) || '—'),
            el('td', { class: 'numero' }, valor(p.precio) || '—'),
            el('td', {}, enlaceExterno(p.enlace, 'Abrir') || '—')));
        return el('div', { class: 'panel pila' },
            el('h2', {}, 'Scraping terminado'),
            el('p', {}, `Se encontraron ${ENTERO.format(r.productos)} productos y se guardaron ${ENTERO.format(r.guardados)} `
                + `en la base de datos como «${r.sitio}» (${formatearDuracion(r.duracion)}).`),
            el('div', { class: 'acciones' },
                el('button', { class: 'boton boton-secundario', type: 'button', onclick: () => Productos.filtrarPorSitio(r.sitio) },
                    'Ver en Productos')),
            r.productos > r.muestra.length && el('p', { class: 'texto-suave' }, `Se muestran los primeros ${r.muestra.length}.`),
            tabla(['Título', 'Precio', 'Enlace'], filas, { numericas: [1] }));
    },
};

// =====================================================================
// Productos
// =====================================================================

const FILTROS_INICIALES = { q: '', sitio: '', precio_min: '', precio_max: '', orden: 'fecha', direccion: 'desc' };

const Productos = {
    estado: { ...FILTROS_INICIALES, pagina: 1 },
    porPagina: 24,
    peticion: 0,
    salida: $('#productos-resultados'),

    init() {
        const form = $('#form-filtros');
        form.addEventListener('submit', (evento) => evento.preventDefault());
        $('#filtro-q').addEventListener('input', debounce((evento) => this.cambiar({ q: evento.target.value.trim() }), 300));
        $('#filtro-min').addEventListener('input', debounce((evento) => this.cambiar({ precio_min: evento.target.value }), 400));
        $('#filtro-max').addEventListener('input', debounce((evento) => this.cambiar({ precio_max: evento.target.value }), 400));
        $('#filtro-sitio').addEventListener('change', (evento) => this.cambiar({ sitio: evento.target.value }));
        $('#filtro-orden').addEventListener('change', (evento) => {
            const [orden, direccion] = evento.target.value.split(':');
            this.cambiar({ orden, direccion });
        });
        // El evento reset se dispara antes de vaciar los campos
        form.addEventListener('reset', () => setTimeout(() => this.cambiar({ ...FILTROS_INICIALES })));
    },

    cambiar(cambios) {
        Object.assign(this.estado, cambios, { pagina: 1 });
        this.cargar();
    },

    parametros(conPaginacion) {
        const parametros = new URLSearchParams();
        for (const clave of ['q', 'sitio', 'precio_min', 'precio_max']) {
            if (this.estado[clave] !== '') parametros.set(clave, this.estado[clave]);
        }
        parametros.set('orden', this.estado.orden);
        parametros.set('direccion', this.estado.direccion);
        if (conPaginacion) {
            parametros.set('pagina', this.estado.pagina);
            parametros.set('por_pagina', this.porPagina);
        }
        return parametros;
    },

    hayFiltros() {
        return ['q', 'sitio', 'precio_min', 'precio_max'].some((clave) => this.estado[clave] !== '');
    },

    mostrar() {
        this.cargarSitios();
        return this.cargar();
    },

    async cargarSitios() {
        const selector = $('#filtro-sitio');
        try {
            const { por_sitio: sitios } = await api('/api/estadisticas');
            const actual = this.estado.sitio;
            const opciones = sitios.filter((s) => s.sitio).map((s) => el('option', { value: s.sitio }, `${s.sitio} (${ENTERO.format(s.productos)})`));
            if (actual && !sitios.some((s) => s.sitio === actual)) opciones.push(el('option', { value: actual }, actual));
            selector.replaceChildren(el('option', { value: '' }, 'Todos'), ...opciones);
            selector.value = actual;
        } catch (error) {
            console.warn('No se pudo cargar la lista de sitios:', error);
        }
    },

    async cargar() {
        const numero = ++this.peticion;  // para descartar respuestas de búsquedas anteriores
        const filtros = this.parametros(false);
        $('#exportar-csv').href = `/api/exportar?formato=csv&${filtros}`;
        $('#exportar-json').href = `/api/exportar?formato=json&${filtros}`;
        mostrar(this.salida, estadoCarga('Cargando productos…'));
        try {
            const datos = await api(`/api/productos?${this.parametros(true)}`);
            if (numero === this.peticion) mostrar(this.salida, this.render(datos));
        } catch (error) {
            if (numero === this.peticion) mostrar(this.salida, estadoError(error, () => this.cargar()));
        }
    },

    render(datos) {
        if (!datos.total) {
            return this.hayFiltros()
                ? estadoVacio('Ningún producto coincide con los filtros', 'Prueba con otra búsqueda o limpia los filtros.')
                : estadoVacio('Todavía no hay productos guardados', 'Scrapea una URL para empezar.',
                    el('a', { class: 'boton boton-primario', href: '#scrapear' }, 'Ir a Scrapear'));
        }
        const desde = (datos.pagina - 1) * datos.por_pagina + 1;
        const hasta = desde + datos.productos.length - 1;
        return [
            el('div', { class: 'barra-resultados' }, `${ENTERO.format(desde)}–${ENTERO.format(hasta)} de ${ENTERO.format(datos.total)} productos`),
            el('div', { class: 'rejilla-productos' }, datos.productos.map((p) => this.tarjeta(p))),
            datos.paginas > 1 && el('nav', { class: 'paginacion', 'aria-label': 'Paginación' },
                el('button', { class: 'boton boton-secundario boton-pequeno', type: 'button', disabled: datos.pagina <= 1,
                    onclick: () => this.irAPagina(datos.pagina - 1) }, 'Anterior'),
                el('span', {}, `Página ${datos.pagina} de ${datos.paginas}`),
                el('button', { class: 'boton boton-secundario boton-pequeno', type: 'button', disabled: datos.pagina >= datos.paginas,
                    onclick: () => this.irAPagina(datos.pagina + 1) }, 'Siguiente')),
        ];
    },

    irAPagina(pagina) {
        this.estado.pagina = pagina;
        this.cargar();
        $('#vista-productos').scrollIntoView({ block: 'start' });
    },

    tarjeta(producto) {
        const abrir = () => Historial.abrir(producto);
        const sinPrecio = producto.precio === null;
        return el('article', { class: 'producto', onclick: abrir },
            imagenProducto(producto.imagen),
            el('div', { class: 'producto-cuerpo' },
                el('h3', { class: 'producto-titulo', title: producto.titulo },
                    // El título es un botón para poder abrir el historial con el teclado
                    el('button', { class: 'boton-texto', type: 'button', onclick: (evento) => { evento.stopPropagation(); abrir(); } },
                        producto.titulo)),
                el('p', { class: sinPrecio ? 'producto-precio sin-precio' : 'producto-precio' },
                    formatearPrecio(producto.precio, producto.moneda, producto.precio_texto)),
                el('p', { class: 'producto-meta' }, `${producto.sitio || 'Sin sitio'} · ${formatearFechaUtc(producto.fecha_scraping)}`),
                enlaceExterno(producto.enlace, 'Abrir en la tienda')));
    },

    filtrarPorSitio(sitio) {
        $('#form-filtros').reset();
        this.estado = { ...FILTROS_INICIALES, sitio, pagina: 1 };
        const selector = $('#filtro-sitio');
        if (![...selector.options].some((opcion) => opcion.value === sitio)) selector.append(el('option', { value: sitio }, sitio));
        selector.value = sitio;
        irAVista('productos');
    },
};

// =====================================================================
// Historial de precios (diálogo)
// =====================================================================

const Historial = {
    dialogo: $('#dialogo-historial'),
    cuerpo: $('#historial-cuerpo'),
    grafica: null,

    init() {
        $('#historial-cerrar').addEventListener('click', () => this.dialogo.close());
        this.dialogo.addEventListener('close', () => this.destruirGrafica());
        // Clic fuera del contenido (en el fondo) cierra el diálogo
        this.dialogo.addEventListener('click', (evento) => { if (evento.target === this.dialogo) this.dialogo.close(); });
    },

    async abrir(producto) {
        this.destruirGrafica();
        $('#historial-titulo').textContent = producto.titulo;
        $('#historial-subtitulo').textContent =
            `${producto.sitio || 'Sin sitio'} · Precio actual: ${formatearPrecio(producto.precio, producto.moneda, producto.precio_texto)}`;
        mostrar(this.cuerpo, estadoCarga('Cargando historial…'));
        if (!this.dialogo.open) this.dialogo.showModal();
        try {
            this.render(await api(`/api/productos/${encodeURIComponent(producto.id)}/historial`));
        } catch (error) {
            mostrar(this.cuerpo, estadoError(error, () => this.abrir(producto)));
        }
    },

    render({ producto, historial }) {
        const enlace = enlaceExterno(producto.enlace, 'Abrir en la tienda');
        if (!historial.length) {
            return mostrar(this.cuerpo, estadoVacio('Sin historial de precios',
                'No se encontró un precio numérico las veces que se scrapeó este producto.'), enlace);
        }

        const puntos = [...historial].reverse();  // la API los devuelve del más reciente al más antiguo
        const moneda = producto.moneda || puntos.find((p) => p.moneda)?.moneda || null;
        const precios = puntos.map((p) => p.precio).filter((p) => p !== null);
        const registros = historial.length === 1 ? '1 registro' : `${ENTERO.format(historial.length)} registros`;
        const resumen = el('p', { class: 'texto-suave' }, precios.length
            ? `${registros} · mínimo ${formatearPrecio(Math.min(...precios), moneda)}`
              + ` · máximo ${formatearPrecio(Math.max(...precios), moneda)}`
            : `${registros} sin precio numérico`);

        const lienzo = el('canvas', { role: 'img', 'aria-label': 'Gráfica de la evolución del precio' });
        const grafica = window.Chart
            ? el('div', { class: 'grafica' }, lienzo)
            : el('p', { class: 'aviso' }, 'No se pudo cargar la librería de gráficas (Chart.js se descarga de internet). Se muestra solo la tabla.');

        const filas = historial.map((h) => el('tr', {},
            el('td', { class: 'fecha' }, formatearFechaUtc(h.fecha)),
            el('td', { class: 'numero' }, formatearPrecio(h.precio, h.moneda)),
            el('td', { class: 'texto-suave' }, h.precio_texto || '—')));

        mostrar(this.cuerpo, resumen, grafica, tabla(['Fecha', 'Precio', 'Texto original'], filas, { numericas: [1] }), enlace);
        if (window.Chart) this.dibujar(lienzo, puntos, moneda);
    },

    dibujar(lienzo, puntos, moneda) {
        const estilos = getComputedStyle(document.documentElement);
        const color = (variable) => estilos.getPropertyValue(variable).trim();
        this.grafica = new window.Chart(lienzo, {
            type: 'line',
            data: {
                labels: puntos.map((p) => formatearFechaUtc(p.fecha)),
                datasets: [{
                    label: 'Precio',
                    data: puntos.map((p) => p.precio),
                    borderColor: color('--primario'),
                    backgroundColor: color('--primario-suave'),
                    pointBackgroundColor: color('--primario'),
                    fill: true,
                    tension: 0.2,
                    spanGaps: true,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (contexto) => formatearPrecio(contexto.parsed.y, moneda) } },
                },
                scales: {
                    x: { ticks: { color: color('--texto-suave'), maxRotation: 0, autoSkip: true }, grid: { display: false } },
                    y: { ticks: { color: color('--texto-suave'), callback: (v) => formatearPrecio(v, moneda) }, grid: { color: color('--borde') } },
                },
            },
        });
    },

    destruirGrafica() {
        if (this.grafica) {
            this.grafica.destroy();
            this.grafica = null;
        }
    },
};

// =====================================================================
// Comparar
// =====================================================================

const Comparar = {
    form: $('#form-comparar'),
    boton: $('#comparar-enviar'),
    salida: $('#comparar-estado'),

    init() {
        const umbral = $('#comparar-umbral');
        const actualizarUmbral = () => { $('#comparar-umbral-valor').textContent = `${Math.round(Number(umbral.value) * 100)} %`; };
        umbral.addEventListener('input', actualizarUmbral);
        actualizarUmbral();
        this.form.addEventListener('submit', (evento) => this.enviar(evento));
        const pendiente = sessionStorage.getItem('job-comparar');
        if (pendiente) this.seguir(pendiente);
    },

    async enviar(evento) {
        evento.preventDefault();
        const f = this.form;
        const cuerpo = { url1: f.url1.value.trim(), url2: f.url2.value.trim(), umbral: Number(f.umbral.value) };
        if (!cuerpo.url1 || !cuerpo.url2) return mostrar(this.salida, mensajeError('Escribe las dos URLs.'));
        if (f.nombre1.value.trim()) cuerpo.nombre1 = f.nombre1.value.trim();
        if (f.nombre2.value.trim()) cuerpo.nombre2 = f.nombre2.value.trim();

        this.ocupado(true);
        try {
            const { job_id: id } = await api('/api/comparar', { json: cuerpo });
            sessionStorage.setItem('job-comparar', id);
            this.seguir(id);
        } catch (error) {
            this.ocupado(false);
            mostrar(this.salida, estadoError(error));
        }
    },

    seguir(id) {
        this.ocupado(true);
        const progreso = crearProgreso('Scrapeando y comparando');
        mostrar(this.salida, progreso.nodo);
        const terminar = (...nodos) => {
            sessionStorage.removeItem('job-comparar');
            this.ocupado(false);
            mostrar(this.salida, ...nodos);
        };
        seguirJob(id, {
            alActualizar: (job) => progreso.actualizar(job),
            alTerminar: (job) => terminar(this.resultado(job.resultado)),
            alFallar: (error) => terminar(estadoError(error)),
        });
    },

    ocupado(activo) {
        this.boton.disabled = activo;
        this.boton.textContent = activo ? 'Comparando…' : 'Comparar';
    },

    resultado(r) {
        const { resumen } = r;
        const ahorros = resumen.ahorro.filter((a) => a.importe > 0).map((a) => formatearPrecio(a.importe, a.moneda));
        const tarjetas = el('div', { class: 'resumen' },
            tarjetaDato('Productos emparejados', ENTERO.format(resumen.comparados),
                `${r.productos1} en ${r.nombre1} y ${r.productos2} en ${r.nombre2}`),
            tarjetaDato(`Más barato en ${r.nombre1}`, ENTERO.format(resumen.mas_baratos_sitio1)),
            tarjetaDato(`Más barato en ${r.nombre2}`, ENTERO.format(resumen.mas_baratos_sitio2)),
            tarjetaDato('Ahorro total', ahorros.length ? ahorros.join(' + ') : '0', 'Comprando cada producto donde es más barato'));

        if (!r.coincidencias.length) {
            const motivo = r.productos1 && r.productos2
                ? 'Prueba a bajar la similitud mínima.'
                : 'Uno de los sitios no devolvió ningún producto.';
            return [tarjetas, estadoVacio('No se encontraron productos parecidos', motivo)];
        }

        const celdaPrecio = (importe, moneda, texto, esMasBarato) => el('td', { class: esMasBarato ? 'numero mas-barato' : 'numero' },
            formatearPrecio(importe, moneda, texto),
            esMasBarato && el('div', {}, el('span', { class: 'insignia insignia-exito' }, 'Más barato')));

        const filas = r.coincidencias.map((c) => {
            let diferencia = '—';
            if (c.mas_barato === 'igual') diferencia = el('span', { class: 'insignia' }, 'Mismo precio');
            else if (c.diferencia !== null) {
                const porcentaje = c.porcentaje_diferencia !== null
                    ? ` (${c.porcentaje_diferencia.toLocaleString('es-ES', { maximumFractionDigits: 1 })} %)` : '';
                diferencia = formatearPrecio(c.diferencia, c.moneda1 || c.moneda2) + porcentaje;
            } else if (c.precio1 !== null && c.precio2 !== null) diferencia = 'Monedas distintas';

            return el('tr', {},
                el('td', { class: 'celda-titulo' }, textoConEnlace(c.producto1.titulo, c.producto1.enlace)),
                celdaPrecio(c.precio1, c.moneda1, c.producto1.precio, c.mas_barato === 'sitio1'),
                el('td', { class: 'celda-titulo' }, textoConEnlace(c.producto2.titulo, c.producto2.enlace)),
                celdaPrecio(c.precio2, c.moneda2, c.producto2.precio, c.mas_barato === 'sitio2'),
                el('td', { class: 'numero' }, diferencia),
                el('td', { class: 'numero' }, `${Math.round(c.similitud * 100)} %`));
        });

        return [tarjetas, tabla([`Producto en ${r.nombre1}`, 'Precio', `Producto en ${r.nombre2}`, 'Precio', 'Diferencia', 'Similitud'],
            filas, { numericas: [1, 3, 4, 5] })];
    },
};

// =====================================================================
// Tareas
// =====================================================================

const Tareas = {
    form: $('#form-tarea'),
    boton: $('#tarea-enviar'),
    salida: $('#tareas-lista'),

    init() {
        this.form.addEventListener('submit', (evento) => this.enviar(evento));
    },

    aviso(texto, esError = false) {
        const nodo = $('#tarea-mensaje');
        nodo.textContent = texto;
        nodo.className = esError ? 'texto-error' : 'texto-suave';
    },

    async enviar(evento) {
        evento.preventDefault();
        const f = this.form;
        const cuerpo = {
            nombre: f.nombre.value.trim(),
            url: f.url.value.trim(),
            intervalo_minutos: Number(f.intervalo_minutos.value),
            max_paginas: Number(f.max_paginas.value),
        };
        if (!cuerpo.nombre || !cuerpo.url) return this.aviso('Rellena el nombre y la URL.', true);

        this.boton.disabled = true;
        try {
            await api('/api/tareas', { json: cuerpo });
            f.reset();
            this.aviso(`Tarea «${cuerpo.nombre}» creada.`);
            await this.cargar();
            // El programador calcula la próxima ejecución en su siguiente ciclo (1 s)
            setTimeout(() => this.cargar({ silencioso: true }), 1500);
        } catch (error) {
            this.aviso(textoError(error), true);
        } finally {
            this.boton.disabled = false;
        }
    },

    async cargar({ silencioso = false } = {}) {
        if (!silencioso) mostrar(this.salida, estadoCarga('Cargando tareas…'));
        try {
            const datos = await api('/api/tareas');
            $('#tareas-programador').replaceChildren(datos.programador_activo
                ? el('span', { class: 'insignia insignia-exito' }, 'Programador en marcha')
                : el('span', { class: 'insignia insignia-aviso' }, 'Programador detenido'));
            mostrar(this.salida, this.render(datos.tareas));
        } catch (error) {
            mostrar(this.salida, estadoError(error, () => this.cargar()));
        }
    },

    render(tareas) {
        if (!tareas.length) return estadoVacio('No hay tareas programadas', 'Crea una con el formulario de arriba.');
        const filas = tareas.map((t) => {
            const boton = el('button', { class: 'boton boton-peligro boton-pequeno', type: 'button' }, 'Eliminar');
            boton.addEventListener('click', () => this.eliminar(t.nombre, boton));
            return el('tr', {},
                el('td', {}, el('strong', {}, t.nombre)),
                el('td', { class: 'celda-url', title: t.url }, textoConEnlace(t.url, t.url)),
                el('td', {}, formatearIntervalo(t.intervalo)),
                el('td', { class: 'numero' }, t.max_paginas),
                el('td', { class: 'numero' }, ENTERO.format(t.total_ejecuciones)),
                el('td', { class: 'fecha' }, formatearFechaLocal(t.ultima_ejecucion)),
                el('td', { class: 'fecha' }, formatearFechaLocal(t.proxima_ejecucion)),
                el('td', {}, boton));
        });
        return tabla(['Nombre', 'URL', 'Frecuencia', 'Páginas', 'Ejecuciones', 'Última', 'Próxima', 'Acciones'], filas, { numericas: [3, 4] });
    },

    async eliminar(nombre, boton) {
        if (!window.confirm(`¿Eliminar la tarea «${nombre}»?`)) return;
        boton.disabled = true;
        try {
            await api(`/api/tareas/${encodeURIComponent(nombre)}`, { method: 'DELETE' });
            this.aviso(`Tarea «${nombre}» eliminada.`);
            await this.cargar();
        } catch (error) {
            boton.disabled = false;
            this.aviso(textoError(error), true);
        }
    },
};

// =====================================================================
// Estadísticas
// =====================================================================

const ESTADOS_EJECUCION = {
    completado: ['Completado', 'insignia-exito'],
    sin_datos: ['Sin datos', 'insignia-aviso'],
    error: ['Error', 'insignia-peligro'],
    cancelado: ['Cancelado', 'insignia-peligro'],
};

const Estadisticas = {
    salida: $('#estadisticas-contenido'),

    init() {
        $('#estadisticas-actualizar').addEventListener('click', () => this.cargar());
    },

    async cargar() {
        mostrar(this.salida, estadoCarga('Cargando estadísticas…'));
        try {
            mostrar(this.salida, this.render(await api('/api/estadisticas')));
        } catch (error) {
            mostrar(this.salida, estadoError(error, () => this.cargar()));
        }
    },

    render(d) {
        if (!d.total_productos && !d.total_jobs) {
            return estadoVacio('Todavía no hay datos', 'Las estadísticas aparecerán cuando scrapees alguna URL.',
                el('a', { class: 'boton boton-primario', href: '#scrapear' }, 'Ir a Scrapear'));
        }

        const tarjetas = el('div', { class: 'tarjetas' },
            tarjetaDato('Productos guardados', ENTERO.format(d.total_productos)),
            tarjetaDato('Sitios', ENTERO.format(d.total_sitios)),
            tarjetaDato('Ejecuciones registradas', ENTERO.format(d.total_jobs)),
            d.precio_medio.map((m) => tarjetaDato(
                m.moneda ? `Precio medio (${m.moneda})` : 'Precio medio (sin moneda)',
                formatearPrecio(m.media, m.moneda),
                `Sobre ${ENTERO.format(m.productos)} productos con precio`)));

        const sitios = d.por_sitio.length
            ? tabla(['Sitio', 'Productos'], d.por_sitio.map((s) => el('tr', {},
                el('td', {}, s.sitio || 'Sin sitio'), el('td', { class: 'numero' }, ENTERO.format(s.productos)))), { numericas: [1] })
            : el('p', { class: 'texto-suave' }, 'No hay productos guardados.');

        const ejecuciones = d.ultimos_jobs.length
            ? tabla(['Fecha', 'URL', 'Sitio', 'Elementos', 'Estado', 'Duración'], d.ultimos_jobs.map((j) => {
                const [texto, clase] = ESTADOS_EJECUCION[j.estado] || [j.estado || '—', ''];
                return el('tr', {},
                    el('td', { class: 'fecha' }, formatearFechaUtc(j.fecha)),
                    el('td', { class: 'celda-url', title: j.url }, textoConEnlace(j.url, j.url)),
                    el('td', {}, j.sitio || '—'),
                    el('td', { class: 'numero' }, ENTERO.format(j.total_items ?? 0)),
                    el('td', {}, el('span', { class: `insignia ${clase}` }, texto)),
                    el('td', { class: 'numero' }, formatearDuracion(j.duracion_segundos)));
            }), { numericas: [3, 5] })
            : el('p', { class: 'texto-suave' }, 'Aún no hay ejecuciones registradas.');

        return [
            tarjetas,
            el('section', { class: 'panel' }, el('h2', {}, 'Últimas ejecuciones'), ejecuciones),
            el('section', { class: 'panel' }, el('h2', {}, 'Productos por sitio'), sitios),
        ];
    },
};

// =====================================================================
// Arranque
// =====================================================================

iniciarPestanas();
Historial.init();
Scrapear.init();
Productos.init();
Comparar.init();
Tareas.init();
Estadisticas.init();
activarVista(vistaDesdeHash());
