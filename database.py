import sqlite3
from datetime import datetime
import os

DB_NAME = 'hotel_limpieza.db'

def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabla de usuarios (camareras y jefa)
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

    # Tabla de habitaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            piso INTEGER NOT NULL,
            tipo TEXT,
            activa INTEGER DEFAULT 1
        )
    ''')

    # Tabla de reportes de limpieza
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

    # Insertar usuarios de prueba si no existen
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        usuarios_default = [
            ('Jefa de Área', 'jefa', '123456', 'jefa'),
            ('María González', 'maria', '1234', 'camarera'),
            ('Ana López', 'ana', '1234', 'camarera'),
            ('Carmen Ruiz', 'carmen', '1234', 'camarera')
        ]
        cursor.executemany(
            'INSERT INTO usuarios (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)',
            usuarios_default
        )

    # Insertar habitaciones de prueba si no existen
    cursor.execute("SELECT COUNT(*) FROM habitaciones")
    if cursor.fetchone()[0] == 0:
        habitaciones = []
        # Generar habitaciones del 101 al 110, 201 al 210, 301 al 310
        for piso in range(1, 4):
            for num in range(1, 11):
                numero = f"{piso}0{num}"
                tipo = "Doble" if num % 2 == 0 else "Sencilla"
                habitaciones.append((numero, piso, tipo))

        cursor.executemany(
            'INSERT INTO habitaciones (numero, piso, tipo) VALUES (?, ?, ?)',
            habitaciones
        )

    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")

def verificar_usuario(usuario, password):
    """Verifica credenciales de usuario"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, nombre, rol FROM usuarios WHERE usuario = ? AND password = ? AND activo = 1',
        (usuario, password)
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def guardar_reporte(datos):
    """Guarda un nuevo reporte de limpieza"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO reportes
        (habitacion_numero, camarera_id, camarera_nombre, fecha, hora_inicio,
         tareas_realizadas, estado, observaciones, foto_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datos['habitacion'],
        datos['camarera_id'],
        datos['camarera_nombre'],
        datos['fecha'],
        datos['hora_inicio'],
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

    cursor.execute('''
        SELECT * FROM reportes WHERE id = ?
    ''', (reporte_id,))

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

    # Total de habitaciones
    cursor.execute('SELECT COUNT(*) FROM habitaciones WHERE activa = 1')
    total_habitaciones = cursor.fetchone()[0]

    # Habitaciones limpiadas hoy
    cursor.execute('SELECT COUNT(*) FROM reportes WHERE fecha = ?', (hoy,))
    limpias = cursor.fetchone()[0]

    # Con observaciones
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

# Inicializar la base de datos al importar el módulo
if __name__ == '__main__':
    init_db()
