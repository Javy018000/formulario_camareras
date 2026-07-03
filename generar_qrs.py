import qrcode
import os
import socket
from database import obtener_habitaciones

DOMINIO = "camarerasshbi.com"
PUERTO = 3000

def obtener_ips_locales():
    """Obtiene todas las IPs locales del servidor"""
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip != "127.0.0.1" and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            ips.append("127.0.0.1")
    return ips


def generar_qrs_con_host(host):
    """Genera codigos QR para todas las habitaciones usando el host dado.

    Acepta un host local ("192.168.1.10", "camarerasshbi.com") o una URL
    completa de hosting ("https://usuario.pythonanywhere.com").
    """
    qr_folder = 'static/qrs'
    if not os.path.exists(qr_folder):
        os.makedirs(qr_folder)

    if host.startswith('http://') or host.startswith('https://'):
        base_url = f"{host.rstrip('/')}/limpiar?hab="
    else:
        base_url = f"http://{host}:{PUERTO}/limpiar?hab="

    habitaciones = obtener_habitaciones()
    total = len(habitaciones)

    print(f"\n  Generando {total} codigos QR...")
    print(f"  URL base: {base_url}\n")

    for idx, hab in enumerate(habitaciones, 1):
        numero = hab[0]
        url = f"{base_url}{numero}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        filename = f"{qr_folder}/habitacion_{numero}.png"
        img.save(filename)

        print(f"  [{idx}/{total}] QR generado: Habitacion {numero}")

    print(f"\n  {total} codigos QR generados exitosamente")
    print(f"  Ubicacion: {os.path.abspath(qr_folder)}")


def menu():
    """Menu interactivo para elegir como generar los QR"""
    ips = obtener_ips_locales()

    print("\n" + "=" * 60)
    print("  GENERADOR DE CODIGOS QR")
    print("=" * 60)
    print("\n  Como quieres generar los QR?\n")

    # Opcion 1: Dominio
    print(f"  1) Dominio: {DOMINIO}")
    print(f"     (requiere dns_server.py activo + DNS en router)")

    # Opciones de IP detectadas
    for i, ip in enumerate(ips):
        print(f"  {i + 2}) IP: {ip}")

    # Opcion manual
    idx_manual = len(ips) + 2
    print(f"  {idx_manual}) Escribir IP manualmente")

    # Opcion hosting publico
    idx_hosting = len(ips) + 3
    print(f"  {idx_hosting}) URL de hosting publico (ej: https://usuario.pythonanywhere.com)")

    print()
    opcion = input("  Elige una opcion: ").strip()

    # Determinar el host
    if opcion == "1":
        host = DOMINIO
    elif opcion == str(idx_manual):
        host = input("  Escribe la IP: ").strip()
    elif opcion == str(idx_hosting):
        host = input("  Escribe la URL completa (con https://): ").strip()
    else:
        try:
            idx = int(opcion) - 2
            if 0 <= idx < len(ips):
                host = ips[idx]
            else:
                print("  Opcion no valida, usando primera IP detectada.")
                host = ips[0]
        except ValueError:
            print("  Opcion no valida, usando primera IP detectada.")
            host = ips[0]

    print(f"\n  Usando: {host}")
    generar_qrs_con_host(host)

    print("\n  INSTRUCCIONES:")
    print("  1. Imprime los QR desde la carpeta 'static/qrs'")
    print("  2. Plastificalos para protegerlos")
    print("  3. Pegalos en cada puerta de habitacion")
    print("  4. Las camareras escanearan con su celular")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    menu()
