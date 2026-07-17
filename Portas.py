import socket
import sys
import threading

# Definido para o numero conexões simultâneas
limite_de_conexoes = threading.Semaphore(300)


# Cria o thread de execução das conexoes
def scan_port(alvo, porta_inicial, porta_final):
    for porta in range(porta_inicial, porta_final + 1):
        thread = threading.Thread(target=scan_port_thread, args=(alvo, porta))
        thread.start()


# Cria a conexão
def scan_port_thread(alvo, porta):
    with limite_de_conexoes:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(0.5)
                # connect_ex retorna 0 se a conexão for bem-sucedida
                if client.connect_ex((alvo, porta)) == 0:
                    print("Porta Aberta ==>", porta)
        except Exception:
            pass


# Redireciona a entrada para ler o teclado do usuário
try:
    sys.stdin = open("/dev/tty")
except FileNotFoundError:
    pass

try:
    # O alvo será digitado pelo usuário
    alvo = input("Digite o IP/Dominio: ")
    porta_inicial = int(input("Digite a porta inicial: "))
    porta_final = int(input("Digite a porta final: "))
    print(f"\nEscaneando {alvo}...")

    scan_port(alvo, porta_inicial, porta_final)

except KeyboardInterrupt:
    print("\n[!] Scan interrompido.")
except socket.gaierror:
    print("\n[!] O nome do host não pôde ser resolvido.")
except ValueError:
    print("\n[!] Porta inválida.")
except Exception as e:
    print(f"\n[!] Erro: {e}")

