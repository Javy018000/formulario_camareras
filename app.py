from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import database as db

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_cambiala'  # Cámbiala por cualquier texto aleatorio

# Configuración de uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Crear carpeta de uploads si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== RUTAS DE LOGIN ====================

@app.route('/')
def index():
    if 'usuario_id' in session:
        if session['rol'] == 'jefa':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('seleccionar_habitacion'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        resultado = db.verificar_usuario(usuario, password)

        if resultado:
            session['usuario_id'] = resultado[0]
            session['nombre'] = resultado[1]
            session['rol'] = resultado[2]

            if resultado[2] == 'jefa':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('seleccionar_habitacion'))
        else:
            return render_template('login.html', error='Usuario o contraseña incorrectos')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== RUTAS PARA CAMARERAS ====================

@app.route('/seleccionar-habitacion')
def seleccionar_habitacion():
    if 'usuario_id' not in session or session['rol'] != 'camarera':
        return redirect(url_for('login'))

    habitaciones = db.obtener_habitaciones()
    return render_template('seleccionar_habitacion.html', habitaciones=habitaciones)

@app.route('/limpiar')
def formulario_limpieza():
    if 'usuario_id' not in session or session['rol'] != 'camarera':
        return redirect(url_for('login'))

    habitacion = request.args.get('hab', '')
    if not habitacion:
        return redirect(url_for('seleccionar_habitacion'))

    return render_template('formulario.html', habitacion=habitacion)

@app.route('/guardar-reporte', methods=['POST'])
def guardar_reporte():
    if 'usuario_id' not in session or session['rol'] != 'camarera':
        return jsonify({'success': False, 'error': 'No autorizado'}), 401

    try:
        # Obtener datos del formulario
        habitacion = request.form['habitacion']
        tareas = request.form.getlist('tareas[]')
        estado = request.form['estado']
        observaciones = request.form.get('observaciones', '')

        # Manejar foto si existe
        foto_path = ''
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{habitacion}_{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                foto_path = filename

        # Preparar datos para guardar
        datos = {
            'habitacion': habitacion,
            'camarera_id': session['usuario_id'],
            'camarera_nombre': session['nombre'],
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora_inicio': datetime.now().strftime('%H:%M:%S'),
            'tareas': ', '.join(tareas),
            'estado': estado,
            'observaciones': observaciones,
            'foto_path': foto_path
        }

        reporte_id = db.guardar_reporte(datos)

        return jsonify({
            'success': True,
            'message': f'Reporte de habitación {habitacion} guardado correctamente',
            'reporte_id': reporte_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== RUTAS PARA JEFA ====================

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session or session['rol'] != 'jefa':
        return redirect(url_for('login'))

    estadisticas = db.obtener_estadisticas_hoy()
    reportes = db.obtener_reportes_hoy()

    return render_template('dashboard.html',
                         estadisticas=estadisticas,
                         reportes=reportes)

@app.route('/api/reportes-hoy')
def api_reportes_hoy():
    if 'usuario_id' not in session or session['rol'] != 'jefa':
        return jsonify({'error': 'No autorizado'}), 401

    reportes = db.obtener_reportes_hoy()
    return jsonify({'reportes': reportes})

@app.route('/detalle-reporte/<int:reporte_id>')
def detalle_reporte(reporte_id):
    if 'usuario_id' not in session or session['rol'] != 'jefa':
        return redirect(url_for('login'))

    reporte = db.obtener_reporte_detalle(reporte_id)
    return render_template('detalle_reporte.html', reporte=reporte)

# ==================== SERVIR ARCHIVOS ESTÁTICOS ====================

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== INICIAR SERVIDOR ====================

if __name__ == '__main__':
    # Inicializar base de datos
    db.init_db()

    # Obtener IP local
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("\n" + "="*50)
    print("🏨 SERVIDOR DE LIMPIEZA DE HOTEL")
    print("="*50)
    print(f"📱 Acceso desde celulares: http://{local_ip}:3000")
    print(f"💻 Acceso local: http://localhost:3000")
    print("="*50)
    print("\n👥 USUARIOS DE PRUEBA:")
    print("   Jefa: usuario=jefa, password=123456")
    print("   Camareras: usuario=maria/ana/carmen, password=1234")
    print("="*50 + "\n")

    # Iniciar servidor
    app.run(host='0.0.0.0', port=3000, debug=True)
