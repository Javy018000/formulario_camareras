"""
Descarga un respaldo del sistema a ESTE computador. Pensado para ejecutarse
solo (Programador de tareas de Windows) y así tener historial con fecha.

Configura las 3 variables de abajo (o usa variables de entorno) y prueba con:
    python backup_local.py            → respaldo del día (sin fotos)
    python backup_local.py --fotos    → respaldo completo con fotos

Cada ejecución guarda un archivo distinto:
    backups/backup_hotel_2026-07-08_0730.zip
Nunca se sobreescriben: eso es tu trazabilidad e historial.
"""
import os
import sys
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests

# ---- CONFIGURACIÓN (ajusta estos 3 valores) ----------------------------------
URL_BASE = os.environ.get('HOTEL_URL', 'https://TUUSUARIO.pythonanywhere.com')
TOKEN = os.environ.get('BACKUP_TOKEN', 'PON-AQUI-EL-MISMO-BACKUP_TOKEN-DEL-SERVIDOR')
CARPETA_DESTINO = os.environ.get('HOTEL_BACKUP_DIR',
                                 os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups'))
# Borra respaldos locales con más de estos días (0 = conservar todos)
CONSERVAR_DIAS = int(os.environ.get('HOTEL_BACKUP_KEEP_DAYS', '0'))
# ------------------------------------------------------------------------------


def descargar(incluir_fotos):
    os.makedirs(CARPETA_DESTINO, exist_ok=True)
    params = {'token': TOKEN}
    if incluir_fotos:
        params['fotos'] = '1'

    print(f'Descargando respaldo desde {URL_BASE} ...')
    r = requests.get(f'{URL_BASE.rstrip("/")}/admin/backup', params=params,
                     timeout=120, stream=True)
    if r.status_code == 403:
        print('❌ Token incorrecto. Revisa BACKUP_TOKEN (debe coincidir con el del servidor).')
        sys.exit(1)
    r.raise_for_status()

    nombre = f'backup_hotel_{datetime.now():%Y-%m-%d_%H%M}.zip'
    ruta = os.path.join(CARPETA_DESTINO, nombre)
    with open(ruta, 'wb') as f:
        for trozo in r.iter_content(chunk_size=65536):
            f.write(trozo)

    mb = os.path.getsize(ruta) / 1048576
    print(f'✅ Guardado: {ruta}  ({mb:.1f} MB)')
    return ruta


def limpiar_antiguos():
    if CONSERVAR_DIAS <= 0 or not os.path.isdir(CARPETA_DESTINO):
        return
    limite = datetime.now().timestamp() - CONSERVAR_DIAS * 86400
    for nombre in os.listdir(CARPETA_DESTINO):
        ruta = os.path.join(CARPETA_DESTINO, nombre)
        if nombre.endswith('.zip') and os.path.getmtime(ruta) < limite:
            os.remove(ruta)
            print(f'🗑️  Eliminado respaldo antiguo: {nombre}')


if __name__ == '__main__':
    incluir_fotos = '--fotos' in sys.argv
    try:
        descargar(incluir_fotos)
        limpiar_antiguos()
    except requests.RequestException as e:
        print(f'❌ No se pudo descargar el respaldo: {e}')
        sys.exit(1)
