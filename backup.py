"""
Generación de respaldos (backups) del sistema.

Un backup es un ZIP que contiene:
  - hotel_limpieza.db      → copia íntegra de la base de datos (recuperación)
  - novedades.csv          → todas las novedades en texto (trazabilidad legible)
  - reportes.csv           → todos los reportes de limpieza en texto
  - uploads/...            → las fotos (solo si incluir_fotos=True)

La copia de la BD se hace con la API de backup online de SQLite, que es segura
aunque la app esté escribiendo en ese momento.
"""
import csv
import io
import os
import sqlite3
import zipfile
from datetime import datetime

import database as db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')


def _copia_segura_db():
    """Devuelve los bytes de una copia consistente de la base de datos."""
    origen = sqlite3.connect(db.DB_NAME)
    tmp_path = os.path.join(BASE_DIR, f'_backup_tmp_{os.getpid()}.db')
    try:
        destino = sqlite3.connect(tmp_path)
        with destino:
            origen.backup(destino)
        destino.close()
        with open(tmp_path, 'rb') as f:
            return f.read()
    finally:
        origen.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _tabla_a_csv(tabla):
    """Exporta una tabla completa a texto CSV (con encabezados)."""
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(f'SELECT * FROM {tabla}')
        columnas = [d[0] for d in cursor.description]
        salida = io.StringIO()
        writer = csv.writer(salida, lineterminator='\n')
        writer.writerow(columnas)
        writer.writerows(cursor.fetchall())
        return salida.getvalue()
    except sqlite3.OperationalError:
        return ''  # la tabla no existe todavía
    finally:
        conn.close()


def crear_backup_zip(incluir_fotos=False):
    """Construye el ZIP de respaldo en memoria y devuelve sus bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('hotel_limpieza.db', _copia_segura_db())
        zf.writestr('novedades.csv', _tabla_a_csv('novedades'))
        zf.writestr('reportes.csv', _tabla_a_csv('reportes'))
        zf.writestr('usuarios.csv', _tabla_a_csv('usuarios'))
        zf.writestr('_backup_info.txt',
                    f'Backup generado: {datetime.now():%Y-%m-%d %H:%M:%S}\n'
                    f'Incluye fotos: {"sí" if incluir_fotos else "no"}\n')

        if incluir_fotos and os.path.isdir(UPLOAD_DIR):
            for nombre in os.listdir(UPLOAD_DIR):
                ruta = os.path.join(UPLOAD_DIR, nombre)
                if os.path.isfile(ruta):
                    zf.write(ruta, arcname=f'uploads/{nombre}')

    buffer.seek(0)
    return buffer.getvalue()


def uso_disco():
    """Resumen de uso de disco: total, fotos (nº y MB), tamaño de la BD."""
    total = 0
    for raiz, _, archivos in os.walk(BASE_DIR):
        if os.sep + '.git' in raiz:
            continue
        for a in archivos:
            try:
                total += os.path.getsize(os.path.join(raiz, a))
            except OSError:
                pass

    fotos_n = fotos_bytes = 0
    if os.path.isdir(UPLOAD_DIR):
        for nombre in os.listdir(UPLOAD_DIR):
            ruta = os.path.join(UPLOAD_DIR, nombre)
            if os.path.isfile(ruta):
                fotos_n += 1
                fotos_bytes += os.path.getsize(ruta)

    db_bytes = os.path.getsize(db.DB_NAME) if os.path.exists(db.DB_NAME) else 0

    return {
        'total_mb': round(total / 1048576, 1),
        'fotos_n': fotos_n,
        'fotos_mb': round(fotos_bytes / 1048576, 1),
        'db_kb': round(db_bytes / 1024, 1),
    }
