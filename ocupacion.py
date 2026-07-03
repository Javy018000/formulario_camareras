"""
Validación de huéspedes contra la hoja de ocupación (Google Sheets).

Fuente principal: export CSV del Google Sheet (requiere que la hoja esté
compartida como "Cualquier persona con el enlace puede ver").
Fallback: última copia descargada en disco (ocupacion_cache.csv), que también
puede sembrarse desde un Excel local con sincronizar_ocupacion.py.
"""
import csv
import io
import json
import os
import re
import threading
import time
from datetime import datetime

SHEET_ID = os.environ.get('OCUPACION_SHEET_ID', '13shOHOXjY2TAKCp3FA-48pn4tXGuS0m8_UKjOpzKhEc')
SHEET_GID = os.environ.get('OCUPACION_SHEET_GID', '392110803')
CSV_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}'

# Rutas absolutas: en hosting (WSGI) el directorio de trabajo no es el del proyecto
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(_BASE_DIR, 'ocupacion_cache.csv')
META_FILE = os.path.join(_BASE_DIR, 'ocupacion_cache.meta.json')
TTL_SEGUNDOS = 300  # refrescar desde Google como máximo cada 5 minutos

_lock = threading.Lock()
_mem = {'ts': 0.0, 'huespedes': [], 'fuente': 'sin_datos', 'actualizado': None}


# ==================== NORMALIZACIÓN ====================

def normalizar_cedula(valor):
    """'1.027.525.509' → '1027525509'; 119211589.0 → '119211589'."""
    if valor is None:
        return ''
    texto = str(valor).strip().upper()
    if texto.endswith('.0'):
        texto = texto[:-2]
    return re.sub(r'[.,\s\-]', '', texto)


def habitacion_base(valor):
    """'101B' → '101' (los QR usan la habitación sin la letra de cama)."""
    if valor is None:
        return ''
    m = re.match(r'\s*(\d+)', str(valor))
    return m.group(1) if m else ''


# ==================== PARSEO ====================

def _parsear_filas(filas):
    """Localiza la fila de encabezados y extrae (cedula, habitación, nombre).

    La hoja real tiene filas de título antes de los encabezados y tablas
    auxiliares a la derecha, por eso se buscan las columnas por nombre.
    """
    idx_hab = idx_ced = idx_nom = None
    fila_hdr = None

    for i, fila in enumerate(filas[:30]):
        cols = [str(c or '').strip().lower() for c in fila]
        if any('nrohab' in c for c in cols) and any('cedula' in c for c in cols):
            fila_hdr = i
            for j, c in enumerate(cols):
                if idx_hab is None and 'nrohab' in c:
                    idx_hab = j
                if idx_ced is None and 'cedula' in c:
                    idx_ced = j
                if idx_nom is None and 'nombre' in c:
                    idx_nom = j
            break

    if fila_hdr is None:
        return []

    huespedes = []
    for fila in filas[fila_hdr + 1:]:
        def celda(idx):
            return fila[idx] if idx is not None and idx < len(fila) else None

        hab = habitacion_base(celda(idx_hab))
        ced = normalizar_cedula(celda(idx_ced))
        if not hab or not ced:
            continue
        nombre = str(celda(idx_nom) or '').strip()
        huespedes.append({
            'cedula': ced,
            'habitacion': str(celda(idx_hab)).strip(),
            'hab_base': hab,
            'nombre': nombre,
        })
    return huespedes


def _parsear_csv(texto):
    return _parsear_filas(list(csv.reader(io.StringIO(texto))))


# ==================== FUENTES DE DATOS ====================

def _descargar_google():
    import requests
    r = requests.get(CSV_URL, timeout=12)
    if r.status_code != 200:
        raise RuntimeError(f'Google Sheets respondió HTTP {r.status_code} '
                           '(¿la hoja está compartida como "cualquiera con el enlace"?)')
    texto = r.content.decode('utf-8', errors='replace')
    if texto.lstrip()[:1] == '<':
        raise RuntimeError('Google devolvió HTML en vez de CSV (hoja no pública)')
    return texto


def guardar_cache(texto, fuente):
    """Guarda el CSV crudo en disco con metadatos de origen y fecha."""
    with open(CACHE_FILE, 'w', encoding='utf-8', newline='') as f:
        f.write(texto)
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump({'fuente': fuente,
                   'actualizado': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f)


def _leer_cache():
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        texto = f.read()
    meta = {'fuente': 'cache', 'actualizado': None}
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, 'r', encoding='utf-8') as f:
                meta.update(json.load(f))
        except Exception:
            pass
    return texto, meta


# ==================== API PÚBLICA ====================

def obtener_huespedes(forzar=False):
    """Lista de huéspedes vigente, refrescando desde Google si el TTL venció."""
    with _lock:
        if not forzar and _mem['huespedes'] and time.time() - _mem['ts'] < TTL_SEGUNDOS:
            return _mem['huespedes']

        try:
            texto = _descargar_google()
            guardar_cache(texto, 'google')
            _mem.update(huespedes=_parsear_csv(texto), fuente='google',
                        actualizado=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        ts=time.time())
            return _mem['huespedes']
        except Exception as e:
            print(f'⚠️  Ocupación: no se pudo leer Google Sheets ({e}). Usando caché local.')

        if os.path.exists(CACHE_FILE):
            try:
                texto, meta = _leer_cache()
                _mem.update(huespedes=_parsear_csv(texto),
                            fuente=f"cache ({meta.get('fuente', '?')})",
                            actualizado=meta.get('actualizado'),
                            ts=time.time())
                return _mem['huespedes']
            except Exception as e:
                print(f'⚠️  Ocupación: caché local ilegible ({e}).')

        _mem.update(huespedes=[], fuente='sin_datos', actualizado=None, ts=time.time())
        return []


def validar_huesped(cedula, habitacion):
    """Devuelve los datos del huésped si su cédula está registrada en esa
    habitación (según la hoja de ocupación); None si no aplica."""
    ced = normalizar_cedula(cedula)
    hab = habitacion_base(habitacion)
    if not ced or not hab:
        return None
    for h in obtener_huespedes():
        if h['cedula'] == ced and h['hab_base'] == hab:
            return h
    return None


def estado_datos():
    """Información de diagnóstico sobre la fuente de ocupación."""
    huespedes = obtener_huespedes()
    return {
        'fuente': _mem['fuente'],
        'actualizado': _mem['actualizado'],
        'total': len(huespedes),
    }
