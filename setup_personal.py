"""
Carga de personal de mantenimiento y administración. Ejecutar una sola vez:
    python setup_personal.py

Edita la lista antes de ejecutar con los nombres reales.
Roles disponibles:
    camarera, jefa, mantenimiento, jefe_mantenimiento, hotelero, superadmin
"""
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database as db

db.init_db()

personal = [
    # (nombre completo,           usuario,       contraseña,  rol)
    ('Hotelero',                  'hotelero',    'hotel123',  'hotelero'),
    ('Jefe de Mantenimiento',     'jefemant',    '123456',    'jefe_mantenimiento'),
    ('Técnico de Mantenimiento',  'tecnico1',    '1234',      'mantenimiento'),
    # ('Otro Técnico',            'tecnico2',    '1234',      'mantenimiento'),
]

creados = 0
omitidos = 0

for nombre, usuario, password, rol in personal:
    try:
        db.crear_usuario(nombre, usuario, password, rol)
        print(f"  ✅ {nombre:28s}  →  {usuario} ({rol})")
        creados += 1
    except Exception as e:
        print(f"  ⚠️  {nombre:28s}  omitido ({e})")
        omitidos += 1

print(f"\n  {creados} usuarios creados, {omitidos} omitidos.")
print("  Cada usuario puede cambiar su contraseña desde 'Mi cuenta'.")
