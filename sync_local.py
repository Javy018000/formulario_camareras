"""
Sincroniza a ESTE computador los datos y fotos del sistema en vivo.

Pensado para el PC que siempre está encendido: prográmalo con el Programador de
tareas de Windows (p. ej. cada 6-12 h) y tendrás un espejo permanente:

    respaldo_hotel/
        fotos/                          → TODAS las fotos, se acumulan y NUNCA se
                                          vuelven a descargar (sincronización incremental)
        datos/datos_2026-07-08_0200.zip → base de datos + CSV con fecha (historial)

A diferencia de backup_local.py (que baja todo cada vez), aquí las fotos solo se
descargan una vez: las que ya tienes no se vuelven a bajar. Ideal para dejarlo
corriendo siempre sin gastar red de más.

Configura los 2 valores de abajo (o usa variables de entorno) y prueba con:
    python sync_local.py
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

# ---- CONFIGURACIÓN (ajusta estos valores) ------------------------------------
URL_BASE = os.environ.get('HOTEL_URL', 'https://TUUSUARIO.pythonanywhere.com')
TOKEN = os.environ.get('BACKUP_TOKEN', 'PON-AQUI-EL-MISMO-BACKUP_TOKEN-DEL-SERVIDOR')
DESTINO = os.environ.get('HOTEL_BACKUP_DIR',
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), 'respaldo_hotel'))
# ------------------------------------------------------------------------------


def _get(base, ruta, **kwargs):
    r = requests.get(f'{base}{ruta}', params={'token': TOKEN}, timeout=120, **kwargs)
    if r.status_code == 403:
        print('❌ Token incorrecto. Revisa BACKUP_TOKEN (debe coincidir con el del servidor).')
        sys.exit(1)
    r.raise_for_status()
    return r


def sincronizar():
    base = URL_BASE.rstrip('/')
    fotos_dir = os.path.join(DESTINO, 'fotos')
    datos_dir = os.path.join(DESTINO, 'datos')
    os.makedirs(fotos_dir, exist_ok=True)
    os.makedirs(datos_dir, exist_ok=True)

    # 1) Datos: base de datos + CSV (zip pequeño, con fecha = historial)
    print('Descargando datos (BD + CSV)...')
    r = _get(base, '/admin/backup')  # sin fotos: liviano
    zip_path = os.path.join(datos_dir, f'datos_{datetime.now():%Y-%m-%d_%H%M}.zip')
    with open(zip_path, 'wb') as f:
        f.write(r.content)
    print(f'  ✅ {os.path.basename(zip_path)} ({len(r.content)/1024:.0f} KB)')

    # 2) Fotos: solo las que faltan (incremental)
    print('Revisando fotos...')
    remotas = _get(base, '/admin/backup/fotos').json().get('fotos', [])
    locales = set(os.listdir(fotos_dir))
    faltantes = [n for n in remotas if n not in locales]
    print(f'  {len(remotas)} en el servidor · {len(locales)} ya en tu PC · {len(faltantes)} nuevas')

    bajadas = errores = 0
    for nombre in faltantes:
        try:
            rr = _get(base, f'/uploads/{nombre}')
            with open(os.path.join(fotos_dir, nombre), 'wb') as f:
                f.write(rr.content)
            bajadas += 1
        except requests.RequestException:
            errores += 1

    print(f'  ✅ {bajadas} fotos nuevas guardadas en {fotos_dir}'
          + (f' ({errores} con error)' if errores else ''))
    print('Sincronización completa.')


if __name__ == '__main__':
    try:
        sincronizar()
    except requests.RequestException as e:
        print(f'❌ No se pudo sincronizar: {e}')
        sys.exit(1)
