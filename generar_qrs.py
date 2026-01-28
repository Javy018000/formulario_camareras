import qrcode
import os
import socket
from database import obtener_habitaciones

def generar_qrs():
    """Genera códigos QR para todas las habitaciones"""

    # Crear carpeta si no existe
    qr_folder = 'static/qrs'
    if not os.path.exists(qr_folder):
        os.makedirs(qr_folder)

    # Obtener IP local
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    base_url = f"http://{local_ip}:3000/limpiar?hab="

    print("\n" + "="*60)
    print("🔲 GENERADOR DE CÓDIGOS QR")
    print("="*60)
    print(f"📱 Acción URL base: {base_url}")
    print("="*60 + "\n")

    # Obtener habitaciones de la base de datos
    habitaciones = obtener_habitaciones()

    total = len(habitaciones)
    print(f"Generando {total} códigos QR...\n")

    for idx, hab in enumerate(habitaciones, 1):
        numero = hab[0]
        url = f"{base_url}{numero}"

        # Crear QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        qr.add_data(url)
        qr.make(fit=True)

        # Generar imagen
        img = qr.make_image(fill_color="black", back_color="white")

        # Guardar
        filename = f"{qr_folder}/habitacion_{numero}.png"
        img.save(filename)

        print(f"[{idx}/{total}] ✅ QR generado: Habitación {numero}")

    print("\n" + "="*60)
    print(f"✅ {total} códigos QR generados exitosamente")
    print(f"📁 Ubicación: {os.path.abspath(qr_folder)}")
    print("="*60)
    print("\n📌 INSTRUCCIONES:")
    print("1. Imprime los códigos QR desde la carpeta 'static/qrs'")
    print("2. Plastifícalos para protegerlos")
    print("3. Pégalos en cada puerta de habitación")
    print("4. Las camareras escanearán con su celular")
    print("="*60 + "\n")

if __name__ == '__main__':
    generar_qrs()
