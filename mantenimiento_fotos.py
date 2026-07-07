"""
Limpieza de fotos para no llenar el disco. OPCIONAL: úsalo solo si el
almacenamiento se acerca al límite. SIEMPRE descarga un respaldo antes.

Hace dos cosas seguras:
  1) Borra fotos "huérfanas": archivos en uploads/ que ya no referencia ninguna
     novedad ni reporte (p. ej. reportes borrados antes de la corrección).
  2) (opcional) Caduca fotos ANTIGUAS: borra el archivo de foto de novedades
     resueltas / reportes con más de N días y limpia su foto_path en la BD.
     Los REGISTROS se conservan (trazabilidad); solo se suelta la imagen pesada.

Uso:
    python mantenimiento_fotos.py                 → solo reporta qué haría (no borra)
    python mantenimiento_fotos.py --aplicar       → borra huérfanas
    python mantenimiento_fotos.py --aplicar --dias 90   → + caduca fotos de +90 días
"""
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import database as db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')


def _fotos_en_bd(conn):
    refs = set()
    for tabla in ('novedades', 'reportes'):
        try:
            for (fp,) in conn.execute(f'SELECT foto_path FROM {tabla} WHERE foto_path != ""'):
                if fp:
                    refs.add(os.path.basename(fp))
        except sqlite3.OperationalError:
            pass
    return refs


def _arg(nombre, defecto=None):
    if nombre in sys.argv:
        i = sys.argv.index(nombre)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return defecto


def main():
    aplicar = '--aplicar' in sys.argv
    dias = int(_arg('--dias', '0') or 0)
    conn = sqlite3.connect(db.DB_NAME)

    if not os.path.isdir(UPLOAD_DIR):
        print('No existe la carpeta uploads/.')
        return

    referenciadas = _fotos_en_bd(conn)
    archivos = [n for n in os.listdir(UPLOAD_DIR)
                if os.path.isfile(os.path.join(UPLOAD_DIR, n))]

    # 1) Huérfanas
    huerfanas = [n for n in archivos if n not in referenciadas]
    liberado = 0
    for n in huerfanas:
        ruta = os.path.join(UPLOAD_DIR, n)
        liberado += os.path.getsize(ruta)
        if aplicar:
            os.remove(ruta)
    print(f'Huérfanas: {len(huerfanas)} archivos ({liberado/1048576:.1f} MB)'
          + (' — BORRADAS' if aplicar else ' — (usa --aplicar para borrar)'))

    # 2) Caducar antiguas (solo si se pide con --dias)
    if dias > 0:
        corte = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        caducadas = 0
        libre2 = 0

        # Novedades resueltas y reportes anteriores al corte
        filas = []
        for (fp,) in conn.execute(
                "SELECT foto_path FROM novedades WHERE foto_path != '' "
                "AND estado = 'resuelta' AND fecha < ?", (corte,)):
            filas.append(('novedades', fp))
        for (fp,) in conn.execute(
                "SELECT foto_path FROM reportes WHERE foto_path != '' AND fecha < ?", (corte,)):
            filas.append(('reportes', fp))

        for tabla, fp in filas:
            ruta = os.path.join(UPLOAD_DIR, os.path.basename(fp))
            if os.path.isfile(ruta):
                libre2 += os.path.getsize(ruta)
                if aplicar:
                    os.remove(ruta)
            if aplicar:
                conn.execute(f"UPDATE {tabla} SET foto_path = '' WHERE foto_path = ?", (fp,))
            caducadas += 1

        if aplicar:
            conn.commit()
        print(f'Fotos de +{dias} días (novedades resueltas / reportes): {caducadas} '
              f'({libre2/1048576:.1f} MB)' + (' — CADUCADAS' if aplicar else ' — (simulación)'))

    conn.close()
    if not aplicar:
        print('\n(Modo simulación: no se borró nada. Añade --aplicar para ejecutar.)')


if __name__ == '__main__':
    main()
