"""
Carga masiva de camareras. Ejecutar una sola vez:
    python setup_camareras.py
"""
import database as db

db.init_db()

camareras = [
    # (nombre completo,        usuario,      contraseña)
    ('Luvivia Cruz',           'luvivia',    '1234'),
    ('Gloria Cardenas',        'gloria',     '1234'),
    ('Kelly Morales',          'kelly',      '1234'),
    ('Luz Leyton',             'luz',        '1234'),
    ('Viviana Ortiz',          'viviana',    '1234'),
    ('Angie Cardenas',         'angie',      '1234'),
    ('Andrea Moreno',          'andrea',     '1234'),
    ('Maria Carolina Cañas',   'carolina',   '1234'),
    ('Ingrid Chavez',          'ingrid',     '1234'),
    ('Estefania Castellanos',  'estefania',  '1234'),
    ('Sandra Chaves',          'sandra',     '1234'),
    ('Yanira Alvarado',        'yanira',     '1234'),
    ('Pablo Gomez',            'pablo',      '1234'),
    ('Daniela Garcia',         'daniela',    '1234'),
    ('Monica Chacon',          'monica',     '1234'),
    ('Anyela Caballero',       'anyela',     '1234'),
    ('Maribel Blandon',        'maribel',    '1234'),
    ('Katerine Forero',        'katerine',   '1234'),
    ('Adrina Rocancio',        'adrina',     '1234'),
    ('Dallana Cardenas',       'dallana',    '1234'),
    ('Sol Pinzon',             'sol',        '1234'),
    ('Sandra Rodriguez',       'sandra2',    '1234'),
    ('Tiany Jimenez',          'tiany',      '1234'),
    ('Alejandra Gonzales',     'alejandra',  '1234'),
    ('Angela Mendivelso',      'angela',     '1234'),
    ('Olga Guerrero',          'olga',       '1234'),
    ('Maritza Correa',         'maritza',    '1234'),
    ('Amanda Coronado',        'amanda',     '1234'),
    ('Jaqueline Ortiz',        'jaqueline',  '1234'),
    ('Angelica Alfonso',       'angelica',   '1234'),
    ('Alejandra Cespedes',     'alejandra2', '1234'),
]

creadas = 0
omitidas = 0

for nombre, usuario, password in camareras:
    try:
        db.crear_usuario(nombre, usuario, password, 'camarera')
        print(f"  ✅ {nombre:30s}  usuario: {usuario}")
        creadas += 1
    except Exception as e:
        print(f"  ⚠️  {nombre:30s}  omitida ({e})")
        omitidas += 1

print(f"\n  {creadas} camareras creadas, {omitidas} omitidas (ya existían o usuario duplicado).")
print("  Todas con contraseña: 1234")
print("  Puedes cambiar usuario/contraseña desde el panel admin.")
