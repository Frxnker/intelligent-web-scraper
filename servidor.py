"""
Arranca la interfaz web local y abre el navegador.

    python servidor.py                 # http://127.0.0.1:8000
    python servidor.py --port 8001     # otro puerto
    python servidor.py --no-abrir      # sin abrir el navegador

Se detiene con Ctrl+C. Los trabajos en curso terminan la página que estén
scrapeando y cierran su navegador antes de que el servidor se apague.
El menú de consola (python main.py) sigue funcionando por separado.
"""

import argparse
import socket
import sys
import threading
import time
import webbrowser

import config

HOSTS_LOCALES = ('127.0.0.1', 'localhost')


def _configurar_consola():
    """Evita que un emoji en un print tumbe un trabajo si la consola no es UTF-8."""
    for flujo in (sys.stdout, sys.stderr):
        if flujo is not None and hasattr(flujo, 'reconfigure'):
            flujo.reconfigure(errors='replace')


def _puerto_libre(host: str, puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as prueba:
        try:
            prueba.bind((host, puerto))
        except OSError:
            return False
    return True


def _abrir_navegador_al_arrancar(servidor, url: str):
    """Espera a que Uvicorn esté escuchando y abre la interfaz en el navegador."""
    for _ in range(300):  # hasta 30 s
        if servidor.started:
            webbrowser.open(url)
            return
        if servidor.should_exit:
            return
        time.sleep(0.1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Interfaz web de Intelligent Web Scraper')
    parser.add_argument('--host', default=config.SERVIDOR_HOST,
                        help=f'Dirección en la que escuchar (por defecto {config.SERVIDOR_HOST})')
    parser.add_argument('--port', type=int, default=config.SERVIDOR_PUERTO,
                        help=f'Puerto (por defecto {config.SERVIDOR_PUERTO})')
    parser.add_argument('--no-abrir', action='store_true', help='No abrir el navegador automáticamente')
    args = parser.parse_args(argv)

    _configurar_consola()

    if not _puerto_libre(args.host, args.port):
        print(f"El puerto {args.port} ya está en uso (¿hay otro servidor abierto?). "
              f"Ciérralo o usa otro puerto: python servidor.py --port {args.port + 1}")
        return 1

    local = args.host in HOSTS_LOCALES
    if not local:
        print(f"AVISO: escuchando en {args.host}. La API no tiene autenticación: cualquiera que "
              f"llegue a este equipo por red podrá usarla.")

    # Imports aquí para que --help y el aviso de puerto ocupado respondan al instante
    import uvicorn

    from web.app import crear_app

    app = crear_app(hosts_permitidos=None if local else ['*'])
    url = f"http://{args.host if local else '127.0.0.1'}:{args.port}"
    servidor = uvicorn.Server(uvicorn.Config(app, host=args.host, port=args.port, log_level='info'))

    if not args.no_abrir:
        threading.Thread(target=_abrir_navegador_al_arrancar, args=(servidor, url), daemon=True).start()

    print(f"Interfaz web en {url}  (Ctrl+C para detener)")
    print(f"Datos en {config.OUTPUT_DIR}")
    try:
        servidor.run()
    except KeyboardInterrupt:
        # Uvicorn vuelve a lanzar la señal de Ctrl+C después de apagarse ordenadamente
        pass
    print("Servidor detenido")
    return 0


if __name__ == '__main__':
    sys.exit(main())
