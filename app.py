from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
import os
import secrets
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse
import database as db

app = Flask(__name__)

# SECRET_KEY desde variable de entorno; si no está configurada, genera una temporal
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    print("\n⚠️  SECRET_KEY no configurada. Se generó una temporal.")
    print("   Las sesiones no sobreviven reinicios del servidor.")
    print("   Para fijarla: set SECRET_KEY=<texto_aleatorio_largo>\n")
app.secret_key = _secret_key

# Configuración de uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_safe_redirect(url):
    """Verifica que la URL sea interna para evitar open redirect."""
    if not url:
        return False
    parsed = urlparse(url)
    return not parsed.netloc and not parsed.scheme and url.startswith('/')


# ==================== CSRF ====================

def get_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = get_csrf_token

def csrf_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method == 'POST':
            token = (request.form.get('_csrf_token') or
                     request.headers.get('X-CSRF-Token'))
            if not token or token != session.get('_csrf_token'):
                if request.content_type and 'multipart' in request.content_type:
                    return jsonify({'success': False, 'error': 'Solicitud inválida'}), 403
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


# ==================== RUTAS DE LOGIN ====================

@app.route('/')
def index():
    if 'usuario_id' in session:
        if session['rol'] == 'admin':
            return redirect(url_for('admin_panel'))
        elif session['rol'] == 'jefa':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('seleccionar_habitacion'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next', '') or request.form.get('next', '')
    if not is_safe_redirect(next_url):
        next_url = ''

    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        resultado = db.verificar_usuario(usuario, password)

        if resultado:
            session['usuario_id'] = resultado[0]
            session['nombre'] = resultado[1]
            session['rol'] = resultado[2]

            if next_url:
                return redirect(next_url)
            elif resultado[2] == 'admin':
                return redirect(url_for('admin_panel'))
            elif resultado[2] == 'jefa':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('seleccionar_habitacion'))
        else:
            return render_template('login.html', error='Usuario o contraseña incorrectos', next_url=next_url)

    return render_template('login.html', next_url=next_url)


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
        return redirect(url_for('login', next=request.url))

    habitacion = request.args.get('hab', '')
    if not habitacion:
        return redirect(url_for('seleccionar_habitacion'))

    return render_template('formulario.html', habitacion=habitacion)


@app.route('/guardar-reporte', methods=['POST'])
@csrf_required
def guardar_reporte():
    if 'usuario_id' not in session or session['rol'] != 'camarera':
        return jsonify({'success': False, 'error': 'No autorizado'}), 401

    try:
        habitacion = request.form['habitacion']
        tareas = request.form.getlist('tareas[]')
        estado = request.form['estado']
        observaciones = request.form.get('observaciones', '')
        hora_inicio = request.form.get('hora_inicio', datetime.now().strftime('%H:%M:%S'))

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

        datos = {
            'habitacion': habitacion,
            'camarera_id': session['usuario_id'],
            'camarera_nombre': session['nombre'],
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora_inicio': hora_inicio,
            'hora_fin': datetime.now().strftime('%H:%M:%S'),
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
    return jsonify({'reportes': [list(r) for r in reportes]})


@app.route('/api/estadisticas-hoy')
def api_estadisticas_hoy():
    if 'usuario_id' not in session or session['rol'] != 'jefa':
        return jsonify({'error': 'No autorizado'}), 401

    return jsonify(db.obtener_estadisticas_hoy())


@app.route('/detalle-reporte/<int:reporte_id>')
def detalle_reporte(reporte_id):
    if 'usuario_id' not in session or session['rol'] != 'jefa':
        return redirect(url_for('login'))

    reporte = db.obtener_reporte_detalle(reporte_id)
    return render_template('detalle_reporte.html', reporte=reporte)


# ==================== RUTAS PARA ADMIN ====================

@app.route('/admin')
def admin_panel():
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return redirect(url_for('login'))

    usuarios = db.obtener_usuarios()
    habitaciones = db.obtener_todas_habitaciones()
    reportes = db.obtener_todos_reportes()
    return render_template('admin.html',
                           usuarios=usuarios,
                           habitaciones=habitaciones,
                           reportes=reportes)


@app.route('/admin/usuarios/crear', methods=['POST'])
@csrf_required
def admin_crear_usuario():
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    try:
        db.crear_usuario(
            request.form['nombre'],
            request.form['usuario'],
            request.form['password'],
            request.form['rol']
        )
        return redirect(url_for('admin_panel'))
    except Exception as e:
        return redirect(url_for('admin_panel', error=str(e)))


@app.route('/admin/usuarios/editar/<int:id>', methods=['POST'])
@csrf_required
def admin_editar_usuario(id):
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    db.actualizar_usuario(
        id,
        request.form['nombre'],
        request.form['usuario'],
        request.form.get('password', ''),
        request.form['rol']
    )
    return redirect(url_for('admin_panel'))


@app.route('/admin/usuarios/eliminar/<int:id>', methods=['POST'])
@csrf_required
def admin_eliminar_usuario(id):
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    db.eliminar_usuario(id)
    return redirect(url_for('admin_panel'))


@app.route('/admin/habitaciones/crear', methods=['POST'])
@csrf_required
def admin_crear_habitacion():
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    try:
        db.crear_habitacion(
            request.form['numero'],
            int(request.form['piso']),
            request.form['tipo']
        )
        return redirect(url_for('admin_panel'))
    except Exception as e:
        return redirect(url_for('admin_panel', error=str(e)))


@app.route('/admin/habitaciones/editar/<int:id>', methods=['POST'])
@csrf_required
def admin_editar_habitacion(id):
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    db.actualizar_habitacion(
        id,
        request.form['numero'],
        int(request.form['piso']),
        request.form['tipo']
    )
    return redirect(url_for('admin_panel'))


@app.route('/admin/habitaciones/eliminar/<int:id>', methods=['POST'])
@csrf_required
def admin_eliminar_habitacion(id):
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    db.eliminar_habitacion(id)
    return redirect(url_for('admin_panel'))


@app.route('/admin/reportes/eliminar/<int:id>', methods=['POST'])
@csrf_required
def admin_eliminar_reporte(id):
    if 'usuario_id' not in session or session['rol'] != 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    db.eliminar_reporte(id)
    return redirect(url_for('admin_panel'))


# ==================== SERVIR ARCHIVOS ESTÁTICOS ====================

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ==================== INICIAR SERVIDOR ====================

if __name__ == '__main__':
    db.init_db()

    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("\n" + "="*50)
    print("🏨 SERVIDOR DE LIMPIEZA DE HOTEL")
    print("="*50)
    print(f"📱 Dominio local: http://camarerasshbi.com:3000")
    print(f"📱 Acceso por IP:  http://{local_ip}:3000")
    print(f"💻 Acceso local:   http://localhost:3000")
    print("="*50)
    print("\n👥 USUARIOS DE PRUEBA:")
    print("   Jefa: usuario=jefa, password=123456")
    print("   Camareras: usuario=maria/ana/carmen, password=1234")
    print("="*50 + "\n")

    debug_mode = os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', port=3000, debug=debug_mode)
