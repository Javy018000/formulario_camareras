"""
Modo ARCHIVO LOCAL.

Cuando corres `python app.py` en tu PC, la app se convierte en un espejo del
sistema en vivo: se trae la base de datos y las fotos de producción para que
puedas navegar TODO el historial con la interfaz normal. Nunca borra nada — las
fotos se acumulan localmente como evidencia permanente.

Esto NO se ejecuta en el hosting (allá se importa el objeto `app` vía WSGI y el
bloque __main__ nunca corre).
"""
import io
import os
import shutil
import zipfile
from datetime import datetime

import requests


def _get(url, token, timeout=120, **kw):
    r = requests.get(url, params={'token': token}, timeout=timeout, **kw)
    if r.status_code == 403:
        raise PermissionError('token de respaldo incorrecto')
    r.raise_for_status()
    return r


def sincronizar_db(url_base, token, db_path, respaldo_dir, log=print):
    """Reemplaza la BD local con la de producción, guardando antes una copia
    fechada de la local (nunca se pierde nada) y los CSV para historial."""
    base = url_base.rstrip('/')
    os.makedirs(respaldo_dir, exist_ok=True)

    # 1) Respaldar la BD local actual antes de reemplazarla
    if os.path.exists(db_path):
        copia = os.path.join(respaldo_dir, f'local_previo_{datetime.now():%Y-%m-%d_%H%M%S}.db')
        shutil.copy2(db_path, copia)

    # 2) Descargar el ZIP de producción y extraer la BD + los CSV
    r = _get(f'{base}/admin/backup', token)
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        with zf.open('hotel_limpieza.db') as src, open(db_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        hoy = datetime.now().strftime('%Y-%m-%d')
        for csv_name in ('novedades.csv', 'reportes.csv'):
            try:
                data = zf.read(csv_name)
            except KeyError:
                continue
            with open(os.path.join(respaldo_dir, f'{csv_name[:-4]}_{hoy}.csv'), 'wb') as f:
                f.write(data)
    log('   ✅ Base de datos sincronizada desde producción.')


def sincronizar_fotos(url_base, token, uploads_dir, log=print):
    """Descarga solo las fotos que faltan (incremental). Nunca borra."""
    base = url_base.rstrip('/')
    os.makedirs(uploads_dir, exist_ok=True)

    remotas = _get(f'{base}/admin/backup/fotos', token, timeout=60).json().get('fotos', [])
    locales = set(os.listdir(uploads_dir))
    faltan = [n for n in remotas if n not in locales]

    if not faltan:
        log(f'   ✅ Fotos al día ({len(remotas)} en total).')
        return

    log(f'   ⏳ Descargando {len(faltan)} fotos nuevas (de {len(remotas)})...')
    bajadas = 0
    for nombre in faltan:
        try:
            rr = _get(f'{base}/uploads/{nombre}', token, timeout=60)
            with open(os.path.join(uploads_dir, nombre), 'wb') as f:
                f.write(rr.content)
            bajadas += 1
        except requests.RequestException:
            pass
    log(f'   ✅ {bajadas} fotos nuevas guardadas (archivo local: nada se borra).')
