# Este critp tem como objetivo converter IPs de base 10 Ex: 127.0.0.1 para outras bases
#

import socket
import struct


# Função que converte as bases dos IPs
def converter_ip(ip_str):
    # Converte a string do IP para bytes (32 bits)
    try:
        ip_bytes = socket.inet_aton(ip_str)
    except OSError:
        return "Endereço IP inválido"

    # Desempacota os bytes em 4 octetos individuais e em um único inteiro (DWORD)
    octetos = list(ip_bytes)
    dword = struct.unpack("!I", ip_bytes)[0]

    # 1. Hexadecimal com pontos
    hex_pontos = ".".join(f"0x{o:02x}" for o in octetos)

    # 2. Hexadecimal único
    hex_unico = f"0x{dword:08x}"

    # 3. Octal com pontos
    octal_pontos = ".".join(f"0{o:o}" if o != 0 else "00" for o in octetos)

    # Exibe os resultados
    print(f"IP Original: {ip_str}\n")
    print(f"Hexadecimal (com pontos): {hex_pontos}")
    print(f"Hexadecimal (único):       {hex_unico}")
    print(f"Octal (com pontos):       {octal_pontos}")
    print(f"Decimal Inteiro (DWORD):   {dword}")


# recebe um valor
valor_base_10 = input("Insira o IP: ")

# Executa a função
converter_ip(valor_base_10)
