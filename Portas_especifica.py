import socket
import sys

# Redireciona a entrada para ler o teclado do usuário
try:
    sys.stdin = open('/dev/tty')
except FileNotFoundError:
    pass

try:
	# O host alvo e a porta alvo será digitado pelo usuário
	alvo = input('Digite o IP/Dominio: ')
	porta = int(input('Digite a porta: '))

	# Setando e configurando o cliente
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
		client.settimeout(0.5)
		# Se a porta estiver aberta, jogue ela na tela
		if client.connect_ex((alvo, porta)) == 0:
			print('Porta Aberta ==>', porta)
		else:
			print('Porta Fechada ==>', porta)

except KeyboardInterrupt:
    print('\n[!] Scan interrompido.')
except socket.gaierror:
    print('\n[!] O nome do host não pôde ser resolvido.')
except ValueError:
    print('\n[!] Porta inválida.')
except Exception as e:
    print(f'\n[!] Erro: {e}')
