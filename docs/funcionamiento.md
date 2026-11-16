# Cómo funciona

[Volver al README](../README.md)

## Extracción

El scraper busca elementos repetidos en la página (tarjetas de producto,
`<article>`, elementos de lista...) y de cada uno saca título, precio,
descripción, enlace e imagen. Usa heurísticas: atributos `data-*` como
`data-product-name` o `data-price`, encabezados, clases que contienen `price`,
`precio`, `cost` o `amount`, y símbolos de moneda en el texto. No necesita configuración
por sitio, pero tampoco acierta siempre. Prueba los selectores por orden y se
queda con el primero que da algún elemento con datos. Por defecto se queda con
un máximo de 50 elementos por página (`MAX_ELEMENTOS`).

Los enlaces y las imágenes relativos se convierten en absolutos, y en las
imágenes con carga diferida se usa `data-src` en lugar del marcador de
posición.

## Primero sin navegador, Selenium solo si hace falta

En el modo por defecto (`MODO_SCRAPING = 'auto'`):

1. Descarga la página con `requests` y la analiza con BeautifulSoup. Es rápido
   y no abre ningún navegador.
2. Si la descarga falla (error de red, 403, 503...), la respuesta no es HTML o
   no aparece ningún elemento, abre Chrome con Selenium y repite la extracción
   sobre la página ya renderizada.

El navegador se abre una sola vez por sesión de scraping (todas las páginas de
una paginación, o los dos sitios de una comparación) y solo si se necesita. Se
cierra siempre, también si hay un error.

Con `MODO_SCRAPING = 'estatico'` nunca se abre el navegador; con `'selenium'`
siempre se usa (ver [Configuración](configuracion.md)).

## Scripts específicos por sitio

`scripts.js` contiene scripts que se ejecutan dentro del navegador para
Amazon, PcComponentes, eBay, AliExpress y blogs de wordpress.com. El sitio se
reconoce por el dominio. Estos dominios van directamente a Selenium; si el
script no encuentra nada, se usa la extracción genérica sobre la página
renderizada.

## Con Selenium

- Espera a que el documento termine de cargar (`document.readyState`) y a que
  no haya peticiones jQuery pendientes, como mucho `WAIT_TIMEOUT` segundos.
- Espera hasta `ESPERA_CONTENIDO` segundos (5 por defecto) a que aparezca algo
  con forma de listado, para el contenido que se carga con JavaScript después
  de la página.
- Elimina los avisos de cookies, newsletter y modales que flotan sobre la
  página (elementos con posición `fixed` o `absolute`).
- Hace scroll hasta el final para cargar el contenido diferido: tras cada
  scroll espera hasta `SCROLL_ESPERA_MAX` segundos a que la página crezca.
- Si la página no se puede cargar (por ejemplo, conexión rechazada), lo
  indica en lugar de dar la carga por buena.

Necesita Google Chrome instalado. Selenium Manager, incluido en Selenium desde
la versión 4.6, descarga automáticamente el chromedriver compatible la primera
vez, así que esa primera ejecución necesita conexión a internet. En un servidor
Linux sin entorno gráfico hace falta Chrome o Chromium; el navegador se ejecuta
en modo headless.

## Paginación

Las páginas siguientes se generan con un parámetro en la URL (`?page=2`,
`?p=2`, `?pg=2` o `?pagina=2`; si la URL no trae ninguno se añade `?page=N`).
Si la URL ya trae un número de página, se continúa desde ahí. Entre página y
página se espera `DELAY_BETWEEN_REQUESTS` segundos. Se eliminan los elementos
repetidos entre páginas y la paginación se detiene si una página no trae datos
o no aporta nada nuevo (señal de que el sitio ignora el parámetro). Si falla una
página después de la primera, se conservan las anteriores.

## Comparación de precios

Para cada producto del primer sitio se busca el del segundo con el título más
parecido (por encima de la similitud mínima, por defecto 60 %). Los títulos se
comparan en minúsculas y sin signos de puntuación. La diferencia de precio solo
se calcula si los dos productos tienen la misma moneda o a alguno le falta (ver
[Precios](precios.md)).
