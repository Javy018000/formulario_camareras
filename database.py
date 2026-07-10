import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Ruta absoluta: en hosting (WSGI) el directorio de trabajo no es el del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'hotel_limpieza.db')

# Rooms: número → cantidad de camas (determina tipo: 2=Doble, 3=Triple, 4=Suite)
_ROOMS = {
    # Piso 1
    '101':4,'102':2,'103':3,'104':3,'105':3,'106':3,'107':3,'108':3,
    '109':3,'110':3,'111':3,'112':3,'113':3,'114':3,'115':2,'116':3,
    '117':3,'118':3,'119':3,'120':3,
    '126':3,'127':3,'128':3,'129':3,'130':3,'131':3,'132':3,'133':3,
    '134':3,'135':3,'136':3,'137':3,'138':3,'139':3,
    '140':2,'141':2,'142':2,'143':2,'144':2,'145':2,'146':2,'147':2,
    '148':2,'149':2,'150':2,'151':2,
    # Piso 2
    '200':3,'201':3,'202':2,'203':3,'204':3,'205':3,'206':3,'207':3,
    '208':3,'209':3,'210':3,'211':3,'212':3,'213':3,'214':3,'215':2,
    '216':3,'217':3,'218':3,'219':3,'220':3,'221':2,'222':3,'223':3,
    '224':3,'225':3,'226':3,'227':3,'228':3,'229':3,'230':3,'231':3,
    '232':3,'233':3,'234':2,'235':3,'236':3,'237':3,'238':3,'239':3,
    '240':3,'241':3,'242':3,'243':3,'244':3,'245':3,'246':3,'247':3,
    '248':3,'249':3,'250':3,'251':3,
    # Piso 3
    '300':3,'301':3,'302':2,'303':3,'304':3,'305':3,'306':3,'307':3,
    '308':3,'309':3,'310':3,'311':3,'312':3,'313':3,'314':3,'315':2,
    '316':3,'317':3,'318':3,'319':3,'320':3,'321':2,'322':3,'323':3,
    '324':3,'325':3,'326':3,'327':3,'328':3,'329':3,'330':3,'331':3,
    '332':3,'333':3,'334':2,'335':3,'336':3,'337':3,'338':3,'339':3,
    '340':3,'341':3,'342':3,'343':3,'344':3,'345':3,'346':3,'347':3,
    '348':3,'349':3,'350':3,'351':3,
    # Piso 4
    '400':3,'401':3,'402':3,'403':3,'404':3,'405':3,'406':3,'407':3,
    '408':3,'409':3,'410':3,'411':3,'412':3,'413':3,'414':3,'415':2,
    '416':3,'417':4,'418':3,'419':3,'420':3,'421':3,'422':3,'423':3,
    '424':3,'425':3,'426':3,'427':3,'428':3,'429':3,'430':3,'431':3,
    '432':3,'433':3,'434':2,'435':3,'436':3,'437':3,'438':3,'439':3,
    '440':3,'441':3,'442':3,'443':3,'444':3,'445':3,'446':3,'447':3,
    '448':3,'449':3,'450':3,'451':3,
    # Piso 5
    '500':3,'501':3,'502':3,'503':3,'504':3,'505':3,'506':3,'507':3,
    '508':3,'509':3,'510':3,'511':3,'512':3,'513':3,'514':3,'515':2,
    '516':3,'517':3,'518':3,'519':3,'520':3,'521':3,'522':3,'523':3,
    '524':3,'525':3,'526':3,'527':3,'528':3,'529':3,'530':3,'531':3,
    '532':3,'533':3,'534':2,'535':3,'536':3,'537':3,'538':3,'539':3,
    '540':3,'541':3,'542':3,'543':3,'544':3,'545':3,'546':3,'547':3,
    '548':3,'549':3,'550':3,'551':3,
    # Piso 6
    '600':3,'601':3,'602':3,'603':3,'604':3,'605':3,'606':3,'607':3,
    '608':3,'609':3,'610':2,'611':3,'612':3,'613':3,'614':3,'615':2,
    '616':3,'617':3,'618':3,'619':3,'620':3,'621':3,'622':3,'623':3,
    '624':3,'625':3,'626':3,'627':3,'628':3,'629':3,'630':3,'631':3,
    '632':3,'633':3,'634':2,'635':3,'636':4,'637':3,'638':3,'639':3,
    '640':3,'641':3,'642':3,'643':3,'644':3,'645':3,'646':3,'647':3,
    '648':3,'649':3,'650':3,'651':3,
}

_TIPO = {2: 'Doble', 3: 'Triple', 4: 'Suite'}

def _get_habitaciones():
    """Devuelve la lista completa de habitaciones como tuplas (numero, piso, tipo)."""
    return [
        (num, int(num[0]), _TIPO.get(camas, 'Sencilla'))
        for num, camas in sorted(_ROOMS.items())
    ]


def migrar_habitaciones():
    """Reemplaza todas las habitaciones en la BD con la lista real del hotel."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM habitaciones')
    cursor.executemany(
        'INSERT INTO habitaciones (numero, piso, tipo) VALUES (?, ?, ?)',
        _get_habitaciones()
    )
    conn.commit()
    total = len(_get_habitaciones())
    conn.close()
    print(f"✅ {total} habitaciones cargadas correctamente.")


def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            activo INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            piso INTEGER NOT NULL,
            tipo TEXT,
            activa INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reportes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habitacion_numero TEXT NOT NULL,
            camarera_id INTEGER NOT NULL,
            camarera_nombre TEXT NOT NULL,
            fecha DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fin TIME,
            tareas_realizadas TEXT NOT NULL,
            estado TEXT NOT NULL,
            observaciones TEXT,
            foto_path TEXT,
            aprobado INTEGER DEFAULT 0,
            FOREIGN KEY (camarera_id) REFERENCES usuarios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS novedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habitacion_numero TEXT NOT NULL,
            area TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            huesped_nombre TEXT,
            huesped_cedula TEXT,
            fecha DATE NOT NULL,
            hora TIME NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            foto_path TEXT,
            gestionado_por TEXT,
            fecha_gestion TEXT,
            nota_gestion TEXT
        )
    ''')

    # Migración de roles: el antiguo 'admin' pasa a ser 'superadmin'
    cursor.execute("UPDATE usuarios SET rol = 'superadmin' WHERE rol = 'admin'")

    # Migración: asignación de novedades (quién atiende cada tarea).
    cursor.execute('PRAGMA table_info(novedades)')
    cols_nov = [c[1] for c in cursor.fetchall()]
    if 'asignado_a' not in cols_nov:
        cursor.execute('ALTER TABLE novedades ADD COLUMN asignado_a INTEGER')
        cursor.execute('ALTER TABLE novedades ADD COLUMN asignado_a_nombre TEXT')
        cursor.execute('ALTER TABLE novedades ADD COLUMN asignado_por TEXT')
        cursor.execute('ALTER TABLE novedades ADD COLUMN fecha_asignacion TEXT')
        # Las que ya estaban en proceso quedan asignadas a quien las gestionaba
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        en_curso = cursor.execute(
            "SELECT id, gestionado_por FROM novedades "
            "WHERE estado = 'en_proceso' AND gestionado_por IS NOT NULL "
            "AND gestionado_por != ''").fetchall()
        for nid, quien in en_curso:
            fila = cursor.execute(
                'SELECT id FROM usuarios WHERE nombre = ?', (quien,)).fetchone()
            cursor.execute(
                'UPDATE novedades SET asignado_a = ?, asignado_a_nombre = ?, '
                'fecha_asignacion = ? WHERE id = ?',
                (fila[0] if fila else None, quien, ahora, nid))

    # Migración (una sola vez): columna debe_cambiar_password.
    # - Hashea contraseñas que quedaron en texto plano (usuarios que nunca
    #   volvieron a entrar desde la migración a hashes).
    # - Marca con el flag a quien tenga una contraseña por defecto conocida,
    #   para forzar el cambio en su próximo inicio de sesión.
    cursor.execute('PRAGMA table_info(usuarios)')
    columnas = [c[1] for c in cursor.fetchall()]
    if 'debe_cambiar_password' not in columnas:
        cursor.execute(
            'ALTER TABLE usuarios ADD COLUMN debe_cambiar_password INTEGER DEFAULT 0')
        DEFAULTS_CONOCIDAS = ('1234', '123456', 'admin123', 'hotel123')
        for uid, pwd in cursor.execute('SELECT id, password FROM usuarios').fetchall():
            if not str(pwd).startswith(('scrypt:', 'pbkdf2:')):
                # Texto plano: hashear ya y exigir cambio
                cursor.execute(
                    'UPDATE usuarios SET password = ?, debe_cambiar_password = 1 WHERE id = ?',
                    (generate_password_hash(str(pwd)), uid))
            elif any(check_password_hash(pwd, d) for d in DEFAULTS_CONOCIDAS):
                cursor.execute(
                    'UPDATE usuarios SET debe_cambiar_password = 1 WHERE id = ?', (uid,))

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        usuarios_default = [
            ('Super Administrador', 'admin', generate_password_hash('admin123'), 'superadmin'),
            ('Hotelero', 'hotelero', generate_password_hash('hotel123'), 'hotelero'),
            ('Jefa de Camareras', 'jefa', generate_password_hash('123456'), 'jefa'),
            ('Jefe de Mantenimiento', 'jefemant', generate_password_hash('123456'), 'jefe_mantenimiento'),
            ('Técnico de Mantenimiento', 'tecnico', generate_password_hash('1234'), 'mantenimiento'),
            ('María González', 'maria', generate_password_hash('1234'), 'camarera'),
            ('Ana López', 'ana', generate_password_hash('1234'), 'camarera'),
            ('Carmen Ruiz', 'carmen', generate_password_hash('1234'), 'camarera')
        ]
        cursor.executemany(
            'INSERT INTO usuarios (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)',
            usuarios_default
        )

    cursor.execute("SELECT COUNT(*) FROM habitaciones")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            'INSERT INTO habitaciones (numero, piso, tipo) VALUES (?, ?, ?)',
            _get_habitaciones()
        )

    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")


def verificar_usuario(usuario, password):
    """Verifica credenciales.

    Devuelve (id, nombre, rol, debe_cambiar_password) o None.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, nombre, rol, password, debe_cambiar_password '
        'FROM usuarios WHERE usuario = ? AND activo = 1',
        (usuario,)
    )
    resultado = cursor.fetchone()
    conn.close()

    if not resultado:
        return None

    user_id, nombre, rol, stored_password, debe_cambiar = resultado

    if check_password_hash(stored_password, password):
        return (user_id, nombre, rol, bool(debe_cambiar))

    return None


def guardar_reporte(datos):
    """Guarda un nuevo reporte de limpieza"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO reportes
        (habitacion_numero, camarera_id, camarera_nombre, fecha, hora_inicio, hora_fin,
         tareas_realizadas, estado, observaciones, foto_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datos['habitacion'],
        datos['camarera_id'],
        datos['camarera_nombre'],
        datos['fecha'],
        datos['hora_inicio'],
        datos.get('hora_fin', ''),
        datos['tareas'],
        datos['estado'],
        datos['observaciones'],
        datos.get('foto_path', '')
    ))

    conn.commit()
    reporte_id = cursor.lastrowid
    conn.close()
    return reporte_id


def obtener_reportes_hoy():
    """Obtiene todos los reportes del día actual"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    hoy = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT id, habitacion_numero, camarera_nombre, hora_inicio,
               estado, observaciones, foto_path, aprobado
        FROM reportes
        WHERE fecha = ?
        ORDER BY hora_inicio DESC
    ''', (hoy,))

    reportes = cursor.fetchall()
    conn.close()
    return reportes


def obtener_reporte_detalle(reporte_id):
    """Obtiene el detalle completo de un reporte"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM reportes WHERE id = ?', (reporte_id,))
    reporte = cursor.fetchone()
    conn.close()
    return reporte


def obtener_habitaciones():
    """Obtiene todas las habitaciones activas"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT numero, piso, tipo FROM habitaciones WHERE activa = 1 ORDER BY numero')
    habitaciones = cursor.fetchall()
    conn.close()
    return habitaciones


def obtener_estadisticas_hoy():
    """Obtiene estadísticas del día"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    hoy = datetime.now().strftime('%Y-%m-%d')

    cursor.execute('SELECT COUNT(*) FROM habitaciones WHERE activa = 1')
    total_habitaciones = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM reportes WHERE fecha = ?', (hoy,))
    limpias = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM reportes
        WHERE fecha = ? AND (observaciones IS NOT NULL AND observaciones != '')
    ''', (hoy,))
    con_observaciones = cursor.fetchone()[0]

    conn.close()

    return {
        'total': total_habitaciones,
        'limpias': limpias,
        'pendientes': total_habitaciones - limpias,
        'con_observaciones': con_observaciones
    }


# ==================== FUNCIONES ADMIN ====================

def obtener_usuarios():
    """Obtiene todos los usuarios (sin contraseña)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nombre, usuario, rol, activo, debe_cambiar_password '
                   'FROM usuarios ORDER BY id')
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios


def crear_usuario(nombre, usuario, password, rol, debe_cambiar=True):
    """Crea un nuevo usuario con contraseña hasheada.

    Por defecto nace con debe_cambiar_password=1: la contraseña asignada es
    temporal y la persona debe elegir la suya en su primer inicio de sesión.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO usuarios (nombre, usuario, password, rol, debe_cambiar_password) '
        'VALUES (?, ?, ?, ?, ?)',
        (nombre, usuario, generate_password_hash(password), rol, 1 if debe_cambiar else 0)
    )
    conn.commit()
    conn.close()


def marcar_cambio_password(user_id, requerido=True):
    """Activa/desactiva el flag de cambio de contraseña obligatorio."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE usuarios SET debe_cambiar_password = ? WHERE id = ?',
        (1 if requerido else 0, user_id)
    )
    conn.commit()
    conn.close()


def actualizar_usuario(id, nombre, usuario, password, rol):
    """Actualiza un usuario existente"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if password:
        cursor.execute(
            'UPDATE usuarios SET nombre = ?, usuario = ?, password = ?, rol = ? WHERE id = ?',
            (nombre, usuario, generate_password_hash(password), rol, id)
        )
    else:
        cursor.execute(
            'UPDATE usuarios SET nombre = ?, usuario = ?, rol = ? WHERE id = ?',
            (nombre, usuario, rol, id)
        )
    conn.commit()
    conn.close()


def eliminar_usuario(id):
    """Desactiva un usuario"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET activo = 0 WHERE id = ?', (id,))
    conn.commit()
    conn.close()


def obtener_todas_habitaciones():
    """Obtiene todas las habitaciones (activas e inactivas)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, numero, piso, tipo, activa FROM habitaciones ORDER BY numero')
    habitaciones = cursor.fetchall()
    conn.close()
    return habitaciones


def crear_habitacion(numero, piso, tipo):
    """Crea una nueva habitación"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO habitaciones (numero, piso, tipo) VALUES (?, ?, ?)',
        (numero, piso, tipo)
    )
    conn.commit()
    conn.close()


def actualizar_habitacion(id, numero, piso, tipo):
    """Actualiza una habitación existente"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE habitaciones SET numero = ?, piso = ?, tipo = ? WHERE id = ?',
        (numero, piso, tipo, id)
    )
    conn.commit()
    conn.close()


def eliminar_habitacion(id):
    """Desactiva una habitación"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE habitaciones SET activa = 0 WHERE id = ?', (id,))
    conn.commit()
    conn.close()


def obtener_todos_reportes():
    """Obtiene todos los reportes"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, habitacion_numero, camarera_nombre, fecha, hora_inicio,
               estado, observaciones, foto_path
        FROM reportes
        ORDER BY fecha DESC, hora_inicio DESC
    ''')
    reportes = cursor.fetchall()
    conn.close()
    return reportes


def eliminar_reporte(id):
    """Elimina un reporte"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reportes WHERE id = ?', (id,))
    conn.commit()
    conn.close()


def verificar_password_por_id(user_id, password):
    """Verifica si la contraseña dada es correcta para el usuario con ese id."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM usuarios WHERE id = ? AND activo = 1', (user_id,))
    resultado = cursor.fetchone()
    conn.close()
    if not resultado:
        return False
    return check_password_hash(resultado[0], password)


def cambiar_credenciales(user_id, nuevo_usuario=None, nueva_password=None):
    """Permite a un usuario actualizar su propio usuario y/o contraseña.

    Al establecer contraseña propia se limpia el flag de cambio obligatorio.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if nuevo_usuario and nueva_password:
        cursor.execute(
            'UPDATE usuarios SET usuario = ?, password = ?, debe_cambiar_password = 0 '
            'WHERE id = ?',
            (nuevo_usuario, generate_password_hash(nueva_password), user_id)
        )
    elif nuevo_usuario:
        cursor.execute('UPDATE usuarios SET usuario = ? WHERE id = ?', (nuevo_usuario, user_id))
    elif nueva_password:
        cursor.execute(
            'UPDATE usuarios SET password = ?, debe_cambiar_password = 0 WHERE id = ?',
            (generate_password_hash(nueva_password), user_id)
        )
    conn.commit()
    conn.close()


# ==================== NOVEDADES (reportes de huéspedes) ====================

_NOV_COLS = ('id, habitacion_numero, area, categoria, descripcion, huesped_nombre, '
             'huesped_cedula, fecha, hora, estado, foto_path, gestionado_por, '
             'fecha_gestion, nota_gestion, asignado_a, asignado_a_nombre, '
             'asignado_por, fecha_asignacion')
# Índices útiles en plantillas: 14=asignado_a  15=asignado_a_nombre
#                               16=asignado_por (jefe)  17=fecha_asignacion

_ORDEN_ESTADO = "CASE estado WHEN 'pendiente' THEN 0 WHEN 'en_proceso' THEN 1 ELSE 2 END"


def crear_novedad(datos):
    """Registra una novedad reportada por un huésped. Devuelve su id (folio)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO novedades
        (habitacion_numero, area, categoria, descripcion, huesped_nombre,
         huesped_cedula, fecha, hora, foto_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datos['habitacion'],
        datos['area'],
        datos['categoria'],
        datos['descripcion'],
        datos.get('huesped_nombre', ''),
        datos.get('huesped_cedula', ''),
        datetime.now().strftime('%Y-%m-%d'),
        datetime.now().strftime('%H:%M:%S'),
        datos.get('foto_path', '')
    ))
    conn.commit()
    novedad_id = cursor.lastrowid
    conn.close()
    return novedad_id


def obtener_novedades(areas, filtro='abiertas', asignadas_a=None):
    """Novedades de las áreas dadas.

    filtro: 'abiertas', 'todas' o un estado concreto.
    asignadas_a: si se pasa un id de usuario, solo devuelve sus tareas.
    """
    if not areas:
        return []
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    marcas = ','.join('?' * len(areas))
    sql = f'SELECT {_NOV_COLS} FROM novedades WHERE area IN ({marcas})'
    params = list(areas)

    if filtro == 'abiertas':
        sql += " AND estado != 'resuelta'"
    elif filtro != 'todas':
        sql += ' AND estado = ?'
        params.append(filtro)

    if asignadas_a is not None:
        sql += ' AND asignado_a = ?'
        params.append(asignadas_a)

    sql += f' ORDER BY {_ORDEN_ESTADO}, fecha DESC, hora DESC'
    cursor.execute(sql, params)
    novedades = cursor.fetchall()
    conn.close()
    return novedades


def obtener_novedades_abiertas_habitacion(habitacion, area):
    """Novedades sin resolver de una habitación y área concretas.

    Se usa para mostrarle a la camarera, dentro del formulario de limpieza,
    lo que el huésped de ESA habitación reportó.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT {_NOV_COLS} FROM novedades
        WHERE habitacion_numero = ? AND area = ? AND estado != 'resuelta'
        ORDER BY fecha, hora
    ''', (habitacion, area))
    novedades = cursor.fetchall()
    conn.close()
    return novedades


def obtener_novedad(novedad_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'SELECT {_NOV_COLS} FROM novedades WHERE id = ?', (novedad_id,))
    novedad = cursor.fetchone()
    conn.close()
    return novedad


def obtener_novedades_habitacion(habitacion, limite=8):
    """Últimas novedades de una habitación (para mostrárselas al huésped)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT {_NOV_COLS} FROM novedades
        WHERE habitacion_numero = ?
        ORDER BY fecha DESC, hora DESC LIMIT ?
    ''', (habitacion, limite))
    novedades = cursor.fetchall()
    conn.close()
    return novedades


def tomar_novedad(novedad_id, user_id, nombre):
    """Un trabajador se hace cargo de una tarea libre.

    Devuelve (True, None) si la tomó, o (False, quien_la_tiene) si otra persona
    se le adelantó. La condición `asignado_a IS NULL` dentro del UPDATE evita
    que dos personas que pulsan a la vez se pisen la tarea.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE novedades
        SET asignado_a = ?, asignado_a_nombre = ?, asignado_por = NULL,
            fecha_asignacion = ?, estado = 'en_proceso'
        WHERE id = ? AND asignado_a IS NULL AND estado != 'resuelta'
    ''', (user_id, nombre, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), novedad_id))
    tomada = cursor.rowcount == 1
    conn.commit()

    ocupada_por = None
    if not tomada:
        fila = cursor.execute(
            'SELECT asignado_a_nombre FROM novedades WHERE id = ?', (novedad_id,)).fetchone()
        ocupada_por = fila[0] if fila else None

    conn.close()
    return tomada, ocupada_por


def asignar_novedad(novedad_id, user_id, nombre, asignado_por):
    """Un jefe asigna (o reasigna) la tarea a una persona de su área."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE novedades
        SET asignado_a = ?, asignado_a_nombre = ?, asignado_por = ?,
            fecha_asignacion = ?,
            estado = CASE WHEN estado = 'resuelta' THEN estado ELSE 'en_proceso' END
        WHERE id = ?
    ''', (user_id, nombre, asignado_por,
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'), novedad_id))
    conn.commit()
    conn.close()


def liberar_novedad(novedad_id, user_id=None, solo_autoasignada=False):
    """Deja la tarea sin dueño y vuelve a 'pendiente'.

    Con solo_autoasignada=True únicamente la suelta si la pidió su propio dueño
    y nadie se la había asignado (regla: si un jefe te la asignó, no la sueltas).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    sql = ("UPDATE novedades SET asignado_a = NULL, asignado_a_nombre = NULL, "
           "asignado_por = NULL, fecha_asignacion = NULL, estado = 'pendiente' "
           "WHERE id = ? AND estado != 'resuelta'")
    params = [novedad_id]
    if solo_autoasignada:
        sql += ' AND asignado_a = ? AND asignado_por IS NULL'
        params.append(user_id)

    cursor.execute(sql, params)
    liberada = cursor.rowcount == 1
    conn.commit()
    conn.close()
    return liberada


def finalizar_novedad(novedad_id, quien, nota=''):
    """Marca la tarea como resuelta."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE novedades
        SET estado = 'resuelta', gestionado_por = ?, fecha_gestion = ?, nota_gestion = ?
        WHERE id = ? AND estado != 'resuelta'
    ''', (quien, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), nota, novedad_id))
    ok = cursor.rowcount == 1
    conn.commit()
    conn.close()
    return ok


def resolver_novedad_en_limpieza(novedad_id, habitacion, user_id, nombre):
    """Cierra una novedad de aseo desde el formulario de limpieza.

    Solo si es de esa habitación, es de aseo, no está resuelta y está libre o
    ya es de esa camarera. Si estaba libre, se la asigna de paso.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        UPDATE novedades
        SET estado = 'resuelta', gestionado_por = ?, fecha_gestion = ?,
            nota_gestion = 'Resuelto durante la limpieza',
            asignado_a = COALESCE(asignado_a, ?),
            asignado_a_nombre = COALESCE(asignado_a_nombre, ?),
            fecha_asignacion = COALESCE(fecha_asignacion, ?)
        WHERE id = ? AND habitacion_numero = ? AND area = 'aseo'
          AND estado != 'resuelta'
          AND (asignado_a IS NULL OR asignado_a = ?)
    ''', (nombre, ahora, user_id, nombre, ahora, novedad_id, habitacion, user_id))
    ok = cursor.rowcount == 1
    conn.commit()
    conn.close()
    return ok


def obtener_usuarios_por_roles(roles):
    """Personal activo con alguno de los roles dados (para asignar tareas)."""
    if not roles:
        return []
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    marcas = ','.join('?' * len(roles))
    cursor.execute(
        f'SELECT id, nombre, rol FROM usuarios WHERE activo = 1 AND rol IN ({marcas}) '
        'ORDER BY nombre', tuple(roles))
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios


def contar_novedades_abiertas():
    """{'aseo': n, 'mantenimiento': m} con estado pendiente o en proceso."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT area, COUNT(*) FROM novedades
        WHERE estado != 'resuelta' GROUP BY area
    ''')
    conteo = {'aseo': 0, 'mantenimiento': 0}
    for area, n in cursor.fetchall():
        conteo[area] = n
    conn.close()
    return conteo


def estadisticas_novedades():
    """Resumen por área: pendientes, en proceso y resueltas hoy."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    stats = {
        'aseo': {'pendiente': 0, 'en_proceso': 0, 'resueltas_hoy': 0},
        'mantenimiento': {'pendiente': 0, 'en_proceso': 0, 'resueltas_hoy': 0},
    }

    cursor.execute('''
        SELECT area, estado, COUNT(*) FROM novedades
        WHERE estado != 'resuelta' GROUP BY area, estado
    ''')
    for area, estado, n in cursor.fetchall():
        if area in stats and estado in stats[area]:
            stats[area][estado] = n

    hoy = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT area, COUNT(*) FROM novedades
        WHERE estado = 'resuelta' AND fecha_gestion LIKE ? GROUP BY area
    ''', (hoy + '%',))
    for area, n in cursor.fetchall():
        if area in stats:
            stats[area]['resueltas_hoy'] = n

    conn.close()
    return stats


def habitacion_existe(numero):
    """True si la habitación está registrada y activa."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM habitaciones WHERE numero = ? AND activa = 1', (numero,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe


if __name__ == '__main__':
    init_db()
