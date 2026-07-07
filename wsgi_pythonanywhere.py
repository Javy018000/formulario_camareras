"""
Archivo WSGI para PythonAnywhere.

En la pestaña "Web" de PythonAnywhere, edita el archivo WSGI que te crean
(/var/www/TUUSUARIO_pythonanywhere_com_wsgi.py) y reemplaza TODO su
contenido por esto, cambiando las 2 líneas marcadas con TODO.
"""
import os
import sys
import time

# Zona horaria del hotel: el servidor corre en UTC y sin esto los reportes
# quedarían con 5 horas de diferencia
os.environ['TZ'] = 'America/Bogota'
time.tzset()

# TODO 1: cambia TUUSUARIO por tu usuario de PythonAnywhere
path = '/home/TUUSUARIO/formulario_camareras'
if path not in sys.path:
    sys.path.insert(0, path)

# TODO 2: cambia esto por un texto largo y aleatorio (mínimo 32 caracteres).
# Puedes generarlo con:  python -c "import secrets; print(secrets.token_hex(32))"
os.environ.setdefault('SECRET_KEY', 'CAMBIA-ESTO-POR-UN-TEXTO-ALEATORIO-LARGO')

# TODO 3 (opcional): token para el respaldo automático desde tu PC (backup_local.py).
# Genera otro distinto al SECRET_KEY y ponlo también en backup_local.py.
os.environ.setdefault('BACKUP_TOKEN', 'CAMBIA-ESTO-POR-OTRO-TEXTO-ALEATORIO')

from app import app as application  # noqa: E402
