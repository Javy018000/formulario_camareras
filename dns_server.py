import socket
import struct
import threading
from dnslib import DNSRecord, DNSHeader, RR, A, QTYPE

# ==================== CONFIGURACION ====================

DOMINIO = "camarerasshbi.com"   # Dominio personalizado
PUERTO_DNS = 53                  # Puerto DNS estandar
DNS_UPSTREAM = "8.8.8.8"        # DNS de Google para reenviar otras consultas

# ==================== DETECTAR IPs LOCALES ====================

def obtener_ips_locales():
    """Obtiene todas las IPs locales del servidor (una por cada red conectada)"""
    ips = []
    try:
        # Obtener todas las interfaces de red
        hostname = socket.gethostname()
        # getaddrinfo devuelve todas las IPs asociadas
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip != "127.0.0.1" and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    # Metodo alternativo si no encontro ninguna
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            ips.append("127.0.0.1")

    return ips


# ==================== REENVIAR CONSULTAS ====================

def reenviar_consulta(datos):
    """Reenvia consultas DNS que NO son para nuestro dominio al DNS de Google"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        sock.sendto(datos, (DNS_UPSTREAM, 53))
        respuesta, _ = sock.recvfrom(4096)
        sock.close()
        return respuesta
    except Exception:
        return None


# ==================== PROCESAR CONSULTA ====================

def procesar_consulta(datos, ips_locales):
    """Procesa una consulta DNS y devuelve la respuesta"""
    try:
        consulta = DNSRecord.parse(datos)
        nombre = str(consulta.q.qname).rstrip(".")
        tipo = QTYPE[consulta.q.qtype]

        # Verificar si es nuestro dominio (o subdominio)
        if nombre == DOMINIO or nombre.endswith("." + DOMINIO):
            # Construir respuesta con nuestras IPs
            respuesta = consulta.reply()

            if tipo == "A":
                for ip in ips_locales:
                    respuesta.add_answer(
                        RR(consulta.q.qname, QTYPE.A, rdata=A(ip), ttl=60)
                    )

            return respuesta.pack()
        else:
            # No es nuestro dominio, reenviar al DNS real
            return reenviar_consulta(datos)

    except Exception as e:
        print(f"  [!] Error procesando consulta: {e}")
        return None


# ==================== SERVIDOR DNS ====================

def iniciar_servidor():
    """Inicia el servidor DNS en el puerto 53"""
    ips_locales = obtener_ips_locales()

    print("\n" + "=" * 60)
    print("  SERVIDOR DNS LOCAL")
    print("=" * 60)
    print(f"  Dominio:  {DOMINIO}")
    print(f"  Puerto:   {PUERTO_DNS}")
    print(f"  Upstream: {DNS_UPSTREAM}")
    print("-" * 60)
    print("  IPs locales detectadas:")
    for ip in ips_locales:
        print(f"    -> {ip}")
    print("-" * 60)
    print(f"  {DOMINIO} resuelve a: {', '.join(ips_locales)}")
    print("=" * 60)
    print("\n  CONFIGURACION EN DISPOSITIVOS:")
    print("  En la config WiFi del celular/PC, cambiar DNS a:")
    for ip in ips_locales:
        print(f"    -> {ip}")
    print(f"\n  Luego abrir en el navegador: http://{DOMINIO}:3000")
    print("=" * 60)
    print("\n  Esperando consultas DNS...\n")

    # Crear socket UDP
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind(("0.0.0.0", PUERTO_DNS))
    except PermissionError:
        print("=" * 60)
        print("  ERROR: Se requieren permisos de administrador")
        print("  El puerto 53 requiere ejecutar como administrador.")
        print("")
        print("  Ejecuta asi:")
        print("    1. Abre CMD o PowerShell como Administrador")
        print("    2. Ejecuta: python -X utf8 dns_server.py")
        print("=" * 60)
        return
    except OSError as e:
        print("=" * 60)
        print(f"  ERROR: No se pudo iniciar en el puerto {PUERTO_DNS}")
        print(f"  Detalle: {e}")
        print("")
        print("  Posible causa: otro servicio usa el puerto 53.")
        print("  Solucion en Windows:")
        print("    1. Abre CMD como Administrador")
        print("    2. Ejecuta: net stop DNS")
        print("    3. O desactiva 'Cliente DNS' en servicios")
        print("=" * 60)
        return

    while True:
        try:
            datos, direccion = servidor.recvfrom(4096)

            # Procesar en un hilo separado para no bloquear
            def manejar(datos, direccion):
                respuesta = procesar_consulta(datos, ips_locales)
                if respuesta:
                    servidor.sendto(respuesta, direccion)
                    # Log de la consulta
                    try:
                        consulta = DNSRecord.parse(datos)
                        nombre = str(consulta.q.qname).rstrip(".")
                        es_nuestro = nombre == DOMINIO or nombre.endswith("." + DOMINIO)
                        estado = "LOCAL" if es_nuestro else "REENVIO"
                        print(f"  [{estado}] {direccion[0]} -> {nombre}")
                    except Exception:
                        pass

            hilo = threading.Thread(target=manejar, args=(datos, direccion))
            hilo.daemon = True
            hilo.start()

        except KeyboardInterrupt:
            print("\n  Servidor DNS detenido.")
            break
        except Exception as e:
            print(f"  [!] Error: {e}")

    servidor.close()


if __name__ == "__main__":
    iniciar_servidor()
