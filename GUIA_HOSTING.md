# Guía de hosting gratis — PythonAnywhere

Con esto el sistema queda accesible desde **cualquier red** (datos móviles,
WiFi de la casa, etc.) en una URL tipo `https://tuusuario.pythonanywhere.com`.

**¿Por qué PythonAnywhere?** Es el único hosting gratis que encaja con esta app:

| | PythonAnywhere (gratis) |
|---|---|
| Disco persistente (la BD SQLite y las fotos NO se borran) | ✅ |
| No se "duerme" (Render gratis tarda ~1 min en despertar) | ✅ |
| HTTPS con URL fija | ✅ |
| Tarjeta de crédito | No pide |
| Publicidad | No tiene |

Única obligación del plan gratis: cada 3 meses te llega un correo y debes
entrar y pulsar **"Run until 3 months from today"** en la pestaña Web para
que la app siga viva.

---

## Paso 1 — Subir el código a GitHub (desde tu PC)

```
git add .
git commit -m "Sistema de novedades + preparación para hosting"
git push origin main
```

> La BD (`hotel_limpieza.db`), las fotos (`uploads/`) y la caché de cédulas
> (`ocupacion_cache.csv`) están en `.gitignore` y NO se suben a GitHub.
> Esas se suben directo a PythonAnywhere en el paso 4.

## Paso 2 — Crear la cuenta

1. Entra a https://www.pythonanywhere.com → **Pricing & signup** →
   **Create a Beginner account** (gratis).
2. El nombre de usuario que elijas será tu URL:
   `https://TUUSUARIO.pythonanywhere.com` (elige algo corto, ej: `shbihotel`).

## Paso 3 — Clonar el proyecto e instalar dependencias

En PythonAnywhere: **Consoles → Bash**, y ejecuta:

```
git clone https://github.com/Javy018000/formulario_camareras.git
cd formulario_camareras
pip3 install --user -r requirements.txt
```

## Paso 4 — Subir la base de datos y la caché de ocupación

En la pestaña **Files**, entra a la carpeta `formulario_camareras` y usa el
botón **Upload a file** para subir desde tu PC:

- `hotel_limpieza.db`  (tus usuarios, habitaciones y reportes actuales)
- `ocupacion_cache.csv` y `ocupacion_cache.meta.json`  (cédulas de huéspedes)

*(Si no subes la BD, se crea una nueva vacía con los usuarios por defecto.)*

## Paso 5 — Crear la web app

1. Pestaña **Web → Add a new web app**.
2. Acepta el dominio gratis → **Manual configuration** → la versión de
   **Python más reciente** que ofrezca.
3. En la sección **Code**:
   - *Source code*: `/home/TUUSUARIO/formulario_camareras`
   - *Working directory*: `/home/TUUSUARIO/formulario_camareras`
4. Clic en el enlace del **WSGI configuration file** y reemplaza TODO su
   contenido con el del archivo `wsgi_pythonanywhere.py` del proyecto,
   cambiando los 2 TODO (tu usuario y la SECRET_KEY).
5. (Opcional, más rápido) En **Static files** agrega:
   - URL: `/static/`  →  Directory: `/home/TUUSUARIO/formulario_camareras/static`
6. Botón verde **Reload**.

¡Listo! Abre `https://TUUSUARIO.pythonanywhere.com` y prueba el login.

## Paso 6 — Regenerar e imprimir los QR

Los QR actuales apuntan a la red local, hay que reimprimirlos apuntando al
hosting. En tu PC:

```
python generar_qrs.py
```

Elige la opción **"URL de hosting publico"** y escribe:
`https://TUUSUARIO.pythonanywhere.com`

Luego imprime los PNG de `static/qrs/` (o regenera el Word con
`python generar_word_qrs.py`).

## Paso 7 — Google Sheet de ocupación

- Comparte la hoja como **"Cualquier persona con el enlace → Lector"** y la
  app la leerá sola cada 5 minutos (docs.google.com está permitido en el
  plan gratis de PythonAnywhere).
- Si prefieres no compartirla, sube un Excel actualizado cuando cambie la
  ocupación y en una consola Bash de PythonAnywhere ejecuta:
  `cd formulario_camareras && python3 sincronizar_ocupacion.py archivo.xlsx`

---

## Respaldos (backups) y trazabilidad

El sistema tiene respaldos integrados. Un respaldo es un ZIP con la base de
datos completa + las novedades y reportes en CSV (legible en Excel) + opcional
las fotos.

**Manual (cuando quieras):** entra como superadmin → panel **Admin → pestaña
💾 Respaldos**. Ahí ves el uso de disco y dos botones para descargar el
respaldo (con o sin fotos) a tu PC.

**Automático a tu PC (recomendado, deja historial con fecha):**

1. En PythonAnywhere, pestaña **Web → sección "Environment variables"**, agrega
   `BACKUP_TOKEN` con un texto aleatorio (distinto al SECRET_KEY). Reload.
   *(O ya viene en el `wsgi_pythonanywhere.py`, TODO 3.)*
2. En tu PC, edita `backup_local.py` y pon los mismos `URL_BASE` y `BACKUP_TOKEN`.
3. Pruébalo: `python backup_local.py` → debe crear `backups/backup_hotel_FECHA.zip`.
4. Prográmalo con el **Programador de tareas de Windows**:
   - Abre "Programador de tareas" → **Crear tarea básica**.
   - Desencadenador: **Diariamente** a la hora que quieras (ej. 2:00 a.m.).
   - Acción: **Iniciar un programa** →
     - Programa: `python`
     - Argumentos: `backup_local.py` (o `backup_local.py --fotos` para incluir fotos)
     - Iniciar en: la carpeta del proyecto en tu PC.
   - Listo: cada día tu PC descarga un respaldo con fecha. Nunca se
     sobreescriben → ese es tu historial y trazabilidad.

> Sugerencia: respaldo **sin fotos a diario** (es pequeño y guarda todos los
> datos) y **con fotos una vez por semana** (`--fotos`).

## Limpieza de fotos (solo si el disco se llena)

Con la compresión actual caben miles de fotos, pero si algún día te acercas al
límite (lo ves en la pestaña Respaldos), en una consola Bash de PythonAnywhere:

```
cd formulario_camareras
python3 mantenimiento_fotos.py                    # simula, no borra
python3 mantenimiento_fotos.py --aplicar          # borra fotos huérfanas
python3 mantenimiento_fotos.py --aplicar --dias 90   # + caduca fotos de +90 días
```

Solo borra imágenes; los registros (quién reportó qué y cuándo) se conservan.
**Descarga un respaldo antes.**

---

## Mantenimiento

| Tarea | Cómo |
|---|---|
| Actualizar el código | Bash: `cd formulario_camareras && git pull` → Web → **Reload** |
| Mantener viva la app | Cada <3 meses: Web → **"Run until 3 months from today"** |
| Respaldar la BD | Panel Admin → 💾 Respaldos, o automático con `backup_local.py` |

## Importante ahora que está en internet

- **Cambia las contraseñas débiles** (`1234`, `admin123`): cualquiera puede
  intentar entrar. El sistema bloquea IPs tras 10 intentos fallidos, pero
  contraseñas fuertes son la defensa real. Cada usuario puede cambiarla en
  "Mi cuenta", y el superadmin desde el panel.
- `dns_server.py` ya no se necesita (era solo para la red local).
- El plan gratis da ~100 s de CPU al día: suficiente para el hotel. Si un
  día se agota, la app sigue funcionando (solo un poco más lenta).
