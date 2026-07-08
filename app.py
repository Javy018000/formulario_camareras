from flask import (Flask, render_template, request, redirect, url_for, session,
                   jsonify, send_file, abort)
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image, ImageOps, UnidentifiedImageError
import io
import os
import secrets
import sys
import time

# Consolas Windows con cp1252 fallan al imprimir emojis
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse, quote
import database as db
import ocupacion
import backup

# Token para descargar respaldos desde el script local automático (sin sesión).
# Configúralo en el entorno junto con SECRET_KEY.
BACKUP_TOKEN = os.environ.get('BACKUP_TOKEN', '')

# MODO ARCHIVO LOCAL: se activa solo al correr `python app.py` en tu PC con la
# sincronización configurada. Mientras esté activo, la app NUNCA borra fotos
# (es tu archivo/evidencia permanente). En el hosting siempre es False.
MODO_ARCHIVO = False

app = Flask(__name__)

# Detrás de un hosting/proxy (PythonAnywhere, etc.) la IP real del cliente
# llega en X-Forwarded-For; sin esto el rate-limit vería la IP del proxy.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# SECRET_KEY desde variable de entorno; si no está configurada, genera una temporal
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    print("\n⚠️  SECRET_KEY no configurada. Se generó una temporal.")
    print("   Las sesiones no sobreviven reinicios del servidor.")
    print("   Para fijarla: set SECRET_KEY=<texto_aleatorio_largo>\n")
app.secret_key = _secret_key

# Configuración de uploads (ruta absoluta: en WSGI el cwd no es el proyecto)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# El grueso del reescalado lo hace el navegador del celular (static/js/resize-upload.js);
# aquí solo re-guardamos barato. Por eso 1280px/BILINEAR/sin optimize: 4x menos CPU que
# LANCZOS+optimize, algo crítico en el plan gratis de hosting (100 seg de CPU/día).
MAX_IMAGE_SIDE = 1280
IMAGE_JPEG_QUALITY = 78
IMAGE_RESAMPLE_FILTER = getattr(Image, 'Resampling', Image).BILINEAR
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# En hosting (WSGI) el bloque __main__ no se ejecuta: inicializar aquí.
# init_db es idempotente (solo crea lo que falte y migra roles).
db.init_db()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_optimized_image(file, filename_prefix):
    """Guarda una foto comprimida gastando la mínima CPU posible.

    Normalmente el celular ya envía la imagen reducida (~1280px), así que
    aquí solo se re-guarda (~12 ms). Si llega una foto grande (navegador sin
    JS), se usa draft() para decodificar el JPEG ya escalado —unas 4x más
    barato que decodificar a resolución completa— antes de reducir.
    """
    if not file or not file.filename or not allowed_file(file.filename):
        return ''

    safe_prefix = secure_filename(str(filename_prefix)) or 'foto'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_prefix}_{timestamp}_{secrets.token_hex(3)}.jpg"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        image = Image.open(file.stream)
        image.draft('RGB', (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))  # decodifica JPEG ya reducido
        image = ImageOps.exif_transpose(image)

        if max(image.size) > MAX_IMAGE_SIDE:
            image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), IMAGE_RESAMPLE_FILTER)

        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            background = Image.new('RGB', image.size, (255, 255, 255))
            alpha = image.convert('RGBA').getchannel('A')
            background.paste(image.convert('RGBA'), mask=alpha)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        image.save(filepath, 'JPEG', quality=IMAGE_JPEG_QUALITY)
        return filename
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError('La foto no se pudo leer. Sube una imagen JPG, PNG o GIF válida.') from exc


def _borrar_foto(foto_path):
    """Borra un archivo de foto del disco (ignora si no existe).

    En modo archivo local nunca borra: la copia de tu PC es evidencia permanente.
    """
    if MODO_ARCHIVO or not foto_path:
        return
    try:
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(foto_path))
        if os.path.isfile(ruta):
            os.remove(ruta)
    except OSError:
        pass


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


# ==================== RATE LIMITING (por IP) ====================

_intentos_fallidos = {}      # (ámbito, ip) → [timestamps de intentos fallidos]
VENTANA_INTENTOS = 10 * 60   # ventana de 10 minutos


def _ip_bloqueada(ambito, ip, maximo):
    ahora = time.time()
    clave = (ambito, ip)
    intentos = [t for t in _intentos_fallidos.get(clave, []) if ahora - t < VENTANA_INTENTOS]
    _intentos_fallidos[clave] = intentos
    return len(intentos) >= maximo


def _registrar_fallo(ambito, ip):
    _intentos_fallidos.setdefault((ambito, ip), []).append(time.time())


def _limpiar_fallos(ambito, ip):
    _intentos_fallidos.pop((ambito, ip), None)


# ==================== ROLES ====================
# Jerarquía: superadmin > hotelero > jefa / jefe_mantenimiento > camarera / mantenimiento
# ('admin' se mantiene como alias de superadmin por compatibilidad)

ROLES_SUPER = ('superadmin', 'admin')
ROLES_HOTEL = ('hotelero',) + ROLES_SUPER                    # ve ambas áreas
ROLES_DASHBOARD = ('jefa',) + ROLES_HOTEL                    # dashboard de limpieza
ROLES_AREA_ASEO = ('camarera', 'jefa') + ROLES_HOTEL         # novedades de aseo
ROLES_AREA_MANT = ('mantenimiento', 'jefe_mantenimiento') + ROLES_HOTEL

ROLES_VALIDOS = ('camarera', 'jefa', 'mantenimiento', 'jefe_mantenimiento',
                 'hotelero', 'superadmin')


def areas_visibles(rol):
    """Áreas de novedades que puede ver un rol."""
    areas = []
    if rol in ROLES_AREA_MANT:
        areas.append('mantenimiento')
    if rol in ROLES_AREA_ASEO:
        areas.append('aseo')
    return areas


def destino_por_rol(rol):
    """Página de inicio según el rol."""
    if rol in ROLES_SUPER:
        return url_for('admin_panel')
    if rol == 'hotelero':
        return url_for('panel_hotel')
    if rol == 'jefa':
        return url_for('dashboard')
    if rol in ('mantenimiento', 'jefe_mantenimiento'):
        return url_for('novedades')
    return url_for('seleccionar_habitacion')


def roles_required(*roles):
    """Exige sesión iniciada con uno de los roles dados."""
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'usuario_id' not in session:
                if request.method == 'GET':
                    return redirect(url_for('login', next=request.full_path.rstrip('?')))
                return redirect(url_for('login'))
            if session.get('rol') not in roles:
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapper
    return decorador


# ==================== RUTAS DE LOGIN ====================

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(destino_por_rol(session['rol']))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next', '') or request.form.get('next', '')
    if not is_safe_redirect(next_url):
        next_url = ''

    if request.method == 'POST':
        ip = request.remote_addr or '?'
        if _ip_bloqueada('login', ip, 10):
            return render_template('login.html',
                                   error='Demasiados intentos fallidos. Espera unos minutos.',
                                   next_url=next_url)

        usuario = request.form['usuario']
        password = request.form['password']

        resultado = db.verificar_usuario(usuario, password)

        if resultado:
            _limpiar_fallos('login', ip)
            session['usuario_id'] = resultado[0]
            session['nombre'] = resultado[1]
            session['rol'] = resultado[2]
            session['usuario_login'] = usuario

            if next_url:
                return redirect(next_url)
            return redirect(destino_por_rol(resultado[2]))
        else:
            _registrar_fallo('login', ip)
            return render_template('login.html', error='Usuario o contraseña incorrectos', next_url=next_url)

    return render_template('login.html', next_url=next_url)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ==================== RUTAS PARA CAMARERAS ====================

@app.route('/seleccionar-habitacion')
@roles_required('camarera')
def seleccionar_habitacion():
    habitaciones = db.obtener_habitaciones()
    novedades_aseo = db.contar_novedades_abiertas()['aseo']
    return render_template('seleccionar_habitacion.html',
                           habitaciones=habitaciones,
                           novedades_aseo=novedades_aseo)


@app.route('/limpiar')
def formulario_limpieza():
    """Punto de entrada de los QR pegados en las puertas.

    Camarera con sesión → formulario de limpieza directo.
    Cualquier otra persona → pantalla de elección camarera/huésped.
    """
    habitacion = request.args.get('hab', '')

    if 'usuario_id' in session and session['rol'] == 'camarera':
        if not habitacion:
            return redirect(url_for('seleccionar_habitacion'))
        return render_template('formulario.html', habitacion=habitacion)

    if not habitacion:
        return redirect(url_for('login'))
    return redirect(url_for('quien_eres', hab=habitacion))


@app.route('/qr')
def quien_eres():
    """Pantalla que pregunta si quien escaneó el QR es camarera o huésped."""
    habitacion = request.args.get('hab', '').strip()
    if not habitacion or not db.habitacion_existe(habitacion):
        return redirect(url_for('login'))
    next_camarera = quote(f'/limpiar?hab={habitacion}', safe='')
    return render_template('quien_eres.html',
                           habitacion=habitacion,
                           next_camarera=next_camarera)


# ==================== PORTAL DEL HUÉSPED ====================

GUEST_SESSION_TTL = 30 * 60      # 30 min de sesión de huésped

CATEGORIAS_NOVEDAD = {
    'mantenimiento': ['Fuga de agua', 'Luz / Electricidad', 'Aire acondicionado',
                      'Televisor / WiFi', 'Cerradura / Puerta', 'Mobiliario', 'Otro'],
    'aseo': ['Limpieza de habitación', 'Limpieza de baño', 'Cambio de sábanas',
             'Toallas / Amenidades', 'Basura', 'Otro'],
}


def _huesped_actual():
    """Datos del huésped validado en sesión, o None si expiró."""
    h = session.get('huesped')
    if not h or time.time() - h.get('ts', 0) > GUEST_SESSION_TTL:
        session.pop('huesped', None)
        return None
    return h


@app.route('/huesped/validar', methods=['GET', 'POST'])
@csrf_required
def huesped_validar():
    habitacion = (request.args.get('hab') or request.form.get('hab') or '').strip()
    if not habitacion or not db.habitacion_existe(habitacion):
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        ip = request.remote_addr or '?'
        if _ip_bloqueada('huesped', ip, 8):
            error = 'Demasiados intentos. Espera unos minutos e inténtalo de nuevo.'
        else:
            cedula = request.form.get('cedula', '').strip()
            huesped = ocupacion.validar_huesped(cedula, habitacion)
            if huesped:
                _limpiar_fallos('huesped', ip)
                session['huesped'] = {
                    'cedula': huesped['cedula'],
                    'hab': habitacion,
                    'nombre': huesped['nombre'],
                    'ts': time.time(),
                }
                return redirect(url_for('huesped_novedad'))
            _registrar_fallo('huesped', ip)
            error = ('No encontramos esa cédula registrada en la habitación '
                     f'{habitacion}. Verifica el número o acércate a recepción.')

    return render_template('huesped_validar.html', habitacion=habitacion, error=error)


@app.route('/huesped/novedad', methods=['GET', 'POST'])
@csrf_required
def huesped_novedad():
    huesped = _huesped_actual()
    if not huesped:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            area = request.form.get('area', '')
            categoria = request.form.get('categoria', '').strip()
            descripcion = request.form.get('descripcion', '').strip()

            if area not in CATEGORIAS_NOVEDAD:
                return jsonify({'success': False, 'error': 'Selecciona el tipo de novedad'}), 400
            if categoria not in CATEGORIAS_NOVEDAD[area]:
                return jsonify({'success': False, 'error': 'Selecciona una categoría válida'}), 400
            if len(descripcion) < 5:
                return jsonify({'success': False, 'error': 'Describe brevemente el problema'}), 400

            foto_path = ''
            if 'foto' in request.files:
                file = request.files['foto']
                foto_path = save_optimized_image(file, f"NOV{huesped['hab']}")

            novedad_id = db.crear_novedad({
                'habitacion': huesped['hab'],
                'area': area,
                'categoria': categoria,
                'descripcion': descripcion,
                'huesped_nombre': huesped['nombre'],
                'huesped_cedula': huesped['cedula'],
                'foto_path': foto_path,
            })

            return jsonify({'success': True,
                            'redirect': url_for('huesped_gracias', novedad_id=novedad_id)})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    anteriores = db.obtener_novedades_habitacion(huesped['hab'])
    return render_template('huesped_novedad.html',
                           huesped=huesped,
                           categorias=CATEGORIAS_NOVEDAD,
                           anteriores=anteriores)


@app.route('/huesped/gracias/<int:novedad_id>')
def huesped_gracias(novedad_id):
    huesped = _huesped_actual()
    if not huesped:
        return redirect(url_for('login'))
    novedad = db.obtener_novedad(novedad_id)
    if not novedad or novedad[1] != huesped['hab']:
        return redirect(url_for('huesped_novedad'))
    return render_template('huesped_exito.html', novedad=novedad, huesped=huesped)


@app.route('/huesped/salir')
def huesped_salir():
    huesped = session.pop('huesped', None)
    if huesped:
        return redirect(url_for('quien_eres', hab=huesped['hab']))
    return redirect(url_for('login'))


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
            foto_path = save_optimized_image(file, habitacion)

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


# ==================== MI CUENTA (camareras) ====================

@app.route('/mi-cuenta', methods=['GET', 'POST'])
@csrf_required
def mi_cuenta():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    error = None
    exito = None

    if request.method == 'POST':
        password_actual = request.form.get('password_actual', '')
        nuevo_usuario   = request.form.get('nuevo_usuario', '').strip()
        nueva_password  = request.form.get('nueva_password', '')
        confirmar       = request.form.get('confirmar_password', '')

        if not db.verificar_password_por_id(session['usuario_id'], password_actual):
            error = 'La contraseña actual es incorrecta.'
        elif not nuevo_usuario:
            error = 'El nombre de usuario no puede estar vacío.'
        elif nueva_password and nueva_password != confirmar:
            error = 'Las contraseñas nuevas no coinciden.'
        elif nueva_password and len(nueva_password) < 4:
            error = 'La contraseña debe tener al menos 4 caracteres.'
        else:
            usuario_cambio   = nuevo_usuario if nuevo_usuario != session.get('usuario_login') else None
            password_cambio  = nueva_password if nueva_password else None

            try:
                db.cambiar_credenciales(
                    session['usuario_id'],
                    nuevo_usuario=nuevo_usuario,
                    nueva_password=password_cambio
                )
                session['usuario_login'] = nuevo_usuario
                exito = 'Datos actualizados correctamente.'
            except Exception:
                error = 'Ese nombre de usuario ya está en uso, elige otro.'

    return render_template('mi_cuenta.html',
                           error=error,
                           exito=exito,
                           usuario_actual=session.get('usuario_login', ''))


# ==================== RUTAS PARA JEFA ====================

@app.route('/dashboard')
@roles_required(*ROLES_DASHBOARD)
def dashboard():
    estadisticas = db.obtener_estadisticas_hoy()
    reportes = db.obtener_reportes_hoy()
    novedades_aseo = db.contar_novedades_abiertas()['aseo']

    return render_template('dashboard.html',
                           estadisticas=estadisticas,
                           reportes=reportes,
                           novedades_aseo=novedades_aseo)


@app.route('/api/reportes-hoy')
def api_reportes_hoy():
    if 'usuario_id' not in session or session['rol'] not in ROLES_DASHBOARD:
        return jsonify({'error': 'No autorizado'}), 401

    reportes = db.obtener_reportes_hoy()
    return jsonify({'reportes': [list(r) for r in reportes]})


@app.route('/api/estadisticas-hoy')
def api_estadisticas_hoy():
    if 'usuario_id' not in session or session['rol'] not in ROLES_DASHBOARD:
        return jsonify({'error': 'No autorizado'}), 401

    return jsonify(db.obtener_estadisticas_hoy())


@app.route('/detalle-reporte/<int:reporte_id>')
@roles_required(*ROLES_DASHBOARD)
def detalle_reporte(reporte_id):
    reporte = db.obtener_reporte_detalle(reporte_id)
    return render_template('detalle_reporte.html', reporte=reporte)


# ==================== NOVEDADES (personal) ====================

ROLES_NOVEDADES = tuple(set(ROLES_AREA_ASEO) | set(ROLES_AREA_MANT))


def _puede_gestionar(rol, area):
    if area == 'aseo':
        return rol in ROLES_AREA_ASEO
    if area == 'mantenimiento':
        return rol in ROLES_AREA_MANT
    return False


@app.route('/novedades')
@roles_required(*ROLES_NOVEDADES)
def novedades():
    rol = session['rol']
    areas = areas_visibles(rol)

    filtro = request.args.get('estado', 'abiertas')
    if filtro not in ('abiertas', 'todas', 'pendiente', 'en_proceso', 'resuelta'):
        filtro = 'abiertas'

    area_filtro = request.args.get('area', '')
    areas_consulta = [area_filtro] if area_filtro in areas else areas

    lista = db.obtener_novedades(areas_consulta, filtro)
    stats = db.estadisticas_novedades()

    # Botón "volver" según el rol (mantenimiento vive en esta página)
    volver = {
        'camarera': url_for('seleccionar_habitacion'),
        'jefa': url_for('dashboard'),
        'hotelero': url_for('panel_hotel'),
        'superadmin': url_for('admin_panel'),
        'admin': url_for('admin_panel'),
    }.get(rol)

    return render_template('novedades.html',
                           novedades=lista,
                           areas=areas,
                           area_filtro=area_filtro,
                           filtro=filtro,
                           stats=stats,
                           volver=volver)


@app.route('/novedades/<int:novedad_id>/estado', methods=['POST'])
@csrf_required
@roles_required(*ROLES_NOVEDADES)
def novedad_cambiar_estado(novedad_id):
    novedad = db.obtener_novedad(novedad_id)
    if not novedad or not _puede_gestionar(session['rol'], novedad[2]):
        return redirect(url_for('novedades'))

    estado = request.form.get('estado', '')
    if estado in ('pendiente', 'en_proceso', 'resuelta'):
        nota = request.form.get('nota', '').strip()
        db.cambiar_estado_novedad(novedad_id, estado, session['nombre'], nota)

    return redirect(url_for('novedades',
                            estado=request.form.get('filtro', 'abiertas'),
                            area=request.form.get('area_filtro', '')))


@app.route('/api/novedades-abiertas')
def api_novedades_abiertas():
    if 'usuario_id' not in session or session['rol'] not in ROLES_NOVEDADES:
        return jsonify({'error': 'No autorizado'}), 401
    conteo = db.contar_novedades_abiertas()
    visibles = {a: conteo[a] for a in areas_visibles(session['rol'])}
    visibles['total'] = sum(visibles.values())
    return jsonify(visibles)


# ==================== PANEL DEL HOTELERO ====================

@app.route('/panel-hotel')
@roles_required(*ROLES_HOTEL)
def panel_hotel():
    estadisticas = db.obtener_estadisticas_hoy()
    stats_novedades = db.estadisticas_novedades()
    reportes = db.obtener_reportes_hoy()[:8]
    ultimas_novedades = db.obtener_novedades(['aseo', 'mantenimiento'], 'abiertas')[:8]
    fuente = ocupacion.estado_datos()

    return render_template('panel_hotel.html',
                           estadisticas=estadisticas,
                           stats_novedades=stats_novedades,
                           reportes=reportes,
                           ultimas_novedades=ultimas_novedades,
                           fuente=fuente)


# ==================== RUTAS PARA ADMIN ====================

@app.route('/admin')
def admin_panel():
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
        return redirect(url_for('login'))

    usuarios = db.obtener_usuarios()
    habitaciones = db.obtener_todas_habitaciones()
    reportes = db.obtener_todos_reportes()
    disco = backup.uso_disco()
    disco['cuota_mb'] = int(os.environ.get('CUOTA_DISCO_MB', '512'))
    disco['pct'] = min(100, round(disco['total_mb'] / disco['cuota_mb'] * 100, 1))
    return render_template('admin.html',
                           disco=disco,
                           usuarios=usuarios,
                           habitaciones=habitaciones,
                           reportes=reportes)


@app.route('/admin/usuarios/crear', methods=['POST'])
@csrf_required
def admin_crear_usuario():
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
        return jsonify({'error': 'No autorizado'}), 401
    if request.form['rol'] not in ROLES_VALIDOS:
        return redirect(url_for('admin_panel', error='Rol inválido'))
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
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
        return jsonify({'error': 'No autorizado'}), 401
    if request.form['rol'] not in ROLES_VALIDOS:
        return redirect(url_for('admin_panel', error='Rol inválido'))
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
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
        return jsonify({'error': 'No autorizado'}), 401
    db.eliminar_usuario(id)
    return redirect(url_for('admin_panel'))


@app.route('/admin/habitaciones/crear', methods=['POST'])
@csrf_required
def admin_crear_habitacion():
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
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
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
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
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
        return jsonify({'error': 'No autorizado'}), 401
    db.eliminar_habitacion(id)
    return redirect(url_for('admin_panel'))


@app.route('/admin/reportes/eliminar/<int:id>', methods=['POST'])
@csrf_required
def admin_eliminar_reporte(id):
    if 'usuario_id' not in session or session['rol'] not in ROLES_SUPER:
        return jsonify({'error': 'No autorizado'}), 401
    reporte = db.obtener_reporte_detalle(id)
    if reporte:
        _borrar_foto(reporte[10])  # foto_path
    db.eliminar_reporte(id)
    return redirect(url_for('admin_panel'))


# ==================== RESPALDOS (BACKUP) ====================

def _autorizado_backup():
    """True si la petición viene de un superadmin con sesión o del token secreto."""
    por_sesion = 'usuario_id' in session and session.get('rol') in ROLES_SUPER
    por_token = bool(BACKUP_TOKEN) and secrets.compare_digest(
        request.args.get('token', ''), BACKUP_TOKEN)
    return por_sesion or por_token


@app.route('/admin/backup')
def admin_backup():
    """Descarga un ZIP de respaldo.

    Autorizado por sesión de superadmin (botón en el panel) o por token secreto
    en la URL (para los scripts `backup_local.py` / `sync_local.py` en tu PC).
    Parámetro ?fotos=1 para incluir también las imágenes.
    """
    if not _autorizado_backup():
        abort(403)

    incluir_fotos = request.args.get('fotos') == '1'
    datos = backup.crear_backup_zip(incluir_fotos=incluir_fotos)
    nombre = f"backup_hotel_{datetime.now():%Y-%m-%d_%H%M}.zip"
    return send_file(io.BytesIO(datos), mimetype='application/zip',
                     as_attachment=True, download_name=nombre)


@app.route('/admin/backup/fotos')
def admin_backup_lista_fotos():
    """Lista los nombres de foto en el servidor (para la sincronización incremental)."""
    if not _autorizado_backup():
        abort(403)
    carpeta = app.config['UPLOAD_FOLDER']
    fotos = [n for n in os.listdir(carpeta) if os.path.isfile(os.path.join(carpeta, n))]
    return jsonify({'fotos': sorted(fotos), 'total': len(fotos)})


# ==================== SERVIR ARCHIVOS ESTÁTICOS ====================

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Cualquier usuario del personal con sesión puede ver fotos en la app;
    # el token de respaldo permite al script de sincronización descargarlas.
    por_sesion = 'usuario_id' in session
    por_token = bool(BACKUP_TOKEN) and secrets.compare_digest(
        request.args.get('token', ''), BACKUP_TOKEN)
    if not (por_sesion or por_token):
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ==================== INICIAR SERVIDOR ====================

if __name__ == '__main__':
    db.init_db()

    # ---- MODO ARCHIVO LOCAL --------------------------------------------------
    # Al correr en tu PC, si configuraste HOTEL_URL + BACKUP_TOKEN, la app se
    # trae la BD y las fotos de producción para usarla como archivo completo.
    # Nada se borra aquí. Si no está configurado o no hay internet, arranca
    # normal con la copia local que tengas.
    _hotel_url = os.environ.get('HOTEL_URL', '')
    _hotel_token = os.environ.get('BACKUP_TOKEN', '')
    _sync_ok = (_hotel_url and _hotel_token
                and 'TUUSUARIO' not in _hotel_url and 'PON-AQUI' not in _hotel_token)

    if _sync_ok:
        import threading
        import archivo_local
        MODO_ARCHIVO = True
        _respaldo_dir = os.path.join(BASE_DIR, 'respaldo_hotel', 'datos')

        print("\n🗂️  MODO ARCHIVO LOCAL — sincronizando desde producción...")
        try:
            archivo_local.sincronizar_db(_hotel_url, _hotel_token, db.DB_NAME, _respaldo_dir)
        except Exception as e:
            print(f"   ⚠️  No se pudo sincronizar la base de datos ({e}). Uso la copia local.")

        def _descargar_fotos_en_segundo_plano():
            try:
                archivo_local.sincronizar_fotos(_hotel_url, _hotel_token,
                                                app.config['UPLOAD_FOLDER'])
            except Exception as e:
                print(f"   ⚠️  Fotos: {e}")

        threading.Thread(target=_descargar_fotos_en_segundo_plano, daemon=True).start()
        print("   Las fotos se descargan en segundo plano. Aquí NADA se borra.")
    else:
        print("\n💡 Modo archivo local desactivado (configura HOTEL_URL y BACKUP_TOKEN"
              " para traer los datos de producción).")

    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("\n" + "="*50)
    print("🏨 SERVIDOR DE LIMPIEZA DE HOTEL" + ("  [ARCHIVO LOCAL]" if MODO_ARCHIVO else ""))
    print("="*50)
    print(f"📱 Dominio local: http://camarerasshbi.com:3000")
    print(f"📱 Acceso por IP:  http://{local_ip}:3000")
    print(f"💻 Acceso local:   http://localhost:3000")
    print("="*50)
    print("\n👥 ROLES DEL SISTEMA:")
    print("   superadmin → gestiona usuarios, roles y todo el sistema")
    print("   hotelero   → ve limpieza + novedades de ambas áreas")
    print("   jefa       → dashboard de limpieza + novedades de aseo")
    print("   jefe_mantenimiento / mantenimiento → novedades de mantenimiento")
    print("   camarera   → formularios de limpieza + novedades de aseo")
    print("   Huéspedes: escanean el QR y validan con su cédula (Google Sheet)")
    print("="*50 + "\n")

    debug_mode = os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', port=3000, debug=debug_mode)
