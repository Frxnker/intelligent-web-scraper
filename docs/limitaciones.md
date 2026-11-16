# Limitaciones

[Volver al README](../README.md)

## Extracción

- **Las heurísticas fallan a veces.** La extracción genérica puede tomar
  elementos que no son productos (menús, tarjetas decorativas) o no reconocer el
  listado. Revisa el HTML guardado en `output/` cuando el resultado no sea el
  esperado.
- **Los sitios cambian su HTML.** Los scripts específicos de `scripts.js` y los
  selectores genéricos dependen de la estructura actual de cada página y dejan
  de funcionar cuando el sitio la cambia. No hay ninguna garantía de que sigan
  funcionando con Amazon, PcComponentes, eBay o AliExpress.
- **Bloqueos.** Muchas tiendas detectan el acceso automatizado y responden con
  captchas o errores. Esta herramienta no intenta saltarse esas protecciones.
- **Modo automático.** Si la página descargada sin navegador contiene algo que
  parece un listado pero no es el contenido real (que se carga después con
  JavaScript), no se usa Selenium. En ese caso, pon `MODO_SCRAPING = 'selenium'`
  en `config.py`.
- **Paginación.** Solo funciona con sitios que paginan con un parámetro en la
  URL. Si el sitio lo ignora, se detiene al ver que la página se repite.

## Datos

- **Precios ambiguos.** `1.299` se lee como 1299. Si un texto tiene precio
  anterior y actual, normalmente se toma el primero. `$` siempre se trata como
  dólar estadounidense y `¥` como yen. Más detalles en [Precios](precios.md).
- **Comparador.** Que dos títulos se parezcan no garantiza que sean el mismo
  producto (variantes, packs). Un producto del segundo sitio puede emparejarse
  con varios del primero. Los productos comparados no se guardan en la base de
  datos.
- **Productos sin enlace.** Se identifican por título y sitio: dos productos
  distintos con el mismo título en el mismo sitio se guardan como uno.

## Programador e interfaz web

- **Programador.** Las tareas solo se ejecutan mientras `main.py` está abierto
  con el programador iniciado, o mientras `servidor.py` está encendido. No
  conviene tener los dos programadores en marcha a la vez: cada uno ejecutaría
  las tareas por su cuenta.
- **Sin usuarios ni contraseñas.** La interfaz web está pensada para uso local.
  Con `--host 0.0.0.0`, cualquiera que llegue al equipo por la red puede usarla.
- **Trabajos en memoria.** El estado de los scrapings lanzados desde la web se
  pierde al reiniciar el servidor (el registro de cada ejecución sí queda en la
  base de datos). Si se apaga el servidor a mitad de un scraping, las páginas ya
  descargadas de ese trabajo no se guardan.
- **Cerrar la consola.** Si se cierra la ventana de la consola en lugar de
  pulsar Ctrl+C con un scraping en marcha, Windows termina el proceso sin
  dejarle cerrar el navegador y puede quedar un Chrome abierto en segundo plano.
- **Gráfica.** Chart.js se descarga de un CDN; sin internet, el historial se
  muestra solo como tabla.
- **Ejecutable.** Necesita Google Chrome instalado en el equipo y algunos
  antivirus desconfían de los ejecutables generados con PyInstaller.

## Uso responsable

- Lee los términos de uso de cada sitio antes de scrapearlo. Muchos prohíben el
  acceso automatizado o la reutilización de sus datos.
- Respeta `robots.txt` (`https://<sitio>/robots.txt`). La herramienta **no** lo
  comprueba automáticamente; es responsabilidad de quien la usa.
- No sobrecargues los servidores: mantén la pausa entre páginas y usa
  intervalos amplios en las tareas programadas (15 minutos o más).
- No recojas datos personales.
