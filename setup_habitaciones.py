"""
Ejecuta este script UNA SOLA VEZ para cargar las habitaciones reales del hotel.
Reemplaza cualquier habitación anterior en la base de datos.

Uso:
    python setup_habitaciones.py
"""
import database as db

db.init_db()  # crea tablas si no existen
db.migrar_habitaciones()
print("Listo. Puedes volver a ejecutar generar_qrs.py para regenerar los QR.")
