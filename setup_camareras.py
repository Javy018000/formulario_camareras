"""
Carga masiva de camareras. Ejecutar una sola vez:
    python setup_camareras.py
"""
import database as db

db.init_db()

camareras = [
    # (nombre completo,          usuario,          contraseña)
    ('Luvivia Cruz',             'LuviCruz',       '1234'),
    ('Gloria Cardenas',          'GloriaCar',      '1234'),
    ('Kelly Morales',            'KellyM',         '1234'),
    ('Luz Leyton',               'Luz',            '1234'),
    ('Viviana Ortiz',            'ViviOrtiz',      '1234'),
    ('Angie Cardenas',           'AngieCard',      '1234'),
    ('Andrea Moreno',            'AndreMoreno',    '1234'),
    ('Maria Carolina Cañas',     'Carolina',       '1234'),
    ('Ingrid Chavez',            'IngridCh',       '1234'),
    ('Estefania Castellanos',    'Estefi',         '1234'),
    ('Sandra Chaves',            'SandraChaves',   '1234'),
    ('Yanira Alvarado',          'Yanira',         '1234'),
    ('Pablo Gomez',              'PabloG',         '1234'),
    ('Daniela Garcia',           'DanielaG',       '1234'),
    ('Monica Chacon',            'MChacon',        '1234'),
    ('Anyela Caballero',         'Anyela',         '1234'),
    ('Maribel Blandon',          'Maribel',        '1234'),
    ('Katerine Forero',          'KaterineF',      '1234'),
    ('Adrina Rocancio',          'Adrina',         '1234'),
    ('Dallana Cardenas',         'Dallana',        '1234'),
    ('Sol Pinzon',               'Sol',            '1234'),
    ('Sandra Rodriguez',         'SRodriguez',     '1234'),
    ('Tiany Jimenez',            'Tiany',          '1234'),
    ('Alejandra Gonzales',       'AleGonzales',    '1234'),
    ('Angela Mendivelso',        'AngelaMendi',    '1234'),
    ('Olga Guerrero',            'OlgaG',          '1234'),
    ('Maritza Correa',           'Maritza',        '1234'),
    ('Amanda Coronado',          'Amanda',         '1234'),
    ('Jaqueline Ortiz',          'JaqOrtiz',       '1234'),
    ('Angelica Alfonso',         'AngelicaA',      '1234'),
    ('Alejandra Cespedes',       'AleCespedes',    '1234'),
]

creadas = 0
omitidas = 0

for nombre, usuario, password in camareras:
    try:
        db.crear_usuario(nombre, usuario, password, 'camarera')
        print(f"  ✅ {nombre:28s}  →  {usuario}")
        creadas += 1
    except Exception as e:
        print(f"  ⚠️  {nombre:28s}  omitida ({e})")
        omitidas += 1

print(f"\n  {creadas} camareras creadas, {omitidas} omitidas.")
print("  Contraseña inicial de todas: 1234")
print("  Cada camarera puede cambiarla desde su perfil.")
