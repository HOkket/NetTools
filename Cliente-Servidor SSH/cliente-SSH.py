# Importa a biblioteca paramiko, usada para realizar conexoes SSH em Python
# Importa time para controlar o tempo de espera entre comandos interativos
import time

import paramiko


# Funcao que executa um unico comando remoto via SSH
# Recebe: ip (endereco do servidor), port (porta SSH),
# user (usuario), passwd (senha) e cmd (comando a executar)
def ssh_command(ip, port, user, passwd, cmd):
    # Cria um objeto SSHClient, que representa a conexao SSH
    client = paramiko.SSHClient()

    # Configura a politica para aceitar automaticamente
    # a chave do host (evita erro de "host key not found")
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Estabelece a conexao com o servidor usando os dados fornecidos
    client.connect(ip, port=port, username=user, password=passwd)

    # Executa o comando no servidor remoto.
    # Retorna tres canais: stdin, stdout e stderr (aqui ignoramos o stdin)
    _, stdout, stderr = client.exec_command(cmd)

    # Junta as linhas de saida padrao (stdout) com as de erro (stderr)
    stdout = stdout.readlines() + stderr.readlines()

    # Se houver qualquer saida, exibe o resultado no terminal
    if stdout:
        print("----- Saida -----")
        for line in stdout:
            # strip() remove espacos e quebras de linha no inicio/fim
            print(line.strip())


# Funcao que abre um shell interativo via SSH
# Permite enviar multiplos comandos ao servidor sem reconectar
# Recebe: ip (endereco do servidor), port (porta SSH),
# user (usuario) e passwd (senha)
def ssh_interactive(ip, port, user, passwd):
    # Cria um objeto SSHClient para a conexao interativa
    client = paramiko.SSHClient()

    # Aceita automaticamente a chave do host
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Conecta ao servidor remoto
    client.connect(ip, port=port, username=user, password=passwd)

    # Abre um shell interativo (equivale a abrir um terminal remoto)
    # Diferente do exec_command, o shell continua aberto para novos comandos
    shell = client.invoke_shell()

    # Exibe uma mensagem informando como usar o modo interativo
    print("===== Modo Interativo =====")
    print("Digite seus comandos. Para sair, digite 'sair'.")

    # Loop infinito que recebe comandos do usuario ate ele digitar "sair"
    while True:
        # Solicita um comando ao usuario no terminal local
        cmd = input(">>> ")

        # Se o usuario digitar "sair", encerra a sessao
        if cmd == "sair":
            print("Encerrando sessao...")
            break

        # Envia o comando para o servidor seguido de quebra de linha
        shell.send(cmd + "\n")

        # Aguarda 1 segundo para o servidor processar e retornar a saida
        time.sleep(1)

        # Verifica se o shell ainda esta ativo antes de ler a saida
        # Se o shell estiver fechado (servidor desconectou), sai do loop
        if shell.recv_ready():
            # Recebe a saida do servidor (buffer de ate 65535 bytes)
            # e decodifica de bytes para string legivel
            output = shell.recv(65535).decode()

            # Exibe a saida do comando executado no servidor
            print(output)
        else:
            # Caso nao haja saida, continua o loop silenciosamente
            continue

    # Fecha a conexao SSH apos o termino do loop
    client.close()


# O bloco abaixo so executa se o script for rodado diretamente
# (nao quando importado como modulo)
if __name__ == "__main__":
    # Importa getpass para ler a senha sem exibi-la no terminal
    import getpass

    # Solicita o nome de usuario ao usuario
    user = input("Username: ")

    # Solicita a senha de forma oculta (nao aparece na tela)
    password = getpass.getpass()

    # Solicita o IP do servidor; se vazio, usa o IP padrao 192.168.0.0
    ip = input("Insira o IP do servidor: ") or "192.168.0.0"

    # Solicita a porta; se vazio, usa a porta padrao 22
    port = input("Insira a porta do servidor: ") or "22"

    # Pergunta ao usuario qual modo deseja utilizar
    print("\nEscolha o modo de operacao:")
    print("1 - Comando unico")
    print("2 - Shell interativo (multiplos comandos)")

    # Le a escolha do usuario
    mode = input("Modo (1/2): ")

    # Se o usuario escolher modo 1, executa um unico comando
    if mode == "1":
        # Solicita o comando a executar; se vazio, executa "id"
        cmd = input("Insira o comando a executar: ") or "id"
        # Chama a funcao que executa o comando e encerra
        ssh_command(ip, port, user, password, cmd)

    # Se o usuario escolher modo 2, abre o shell interativo
    elif mode == "2":
        # Chama a funcao que mantem a conexao aberta para multiplos comandos
        ssh_interactive(ip, port, user, password)

    # Se a escolha for invalida, exibe mensagem de erro
    else:
        print("Modo invalido.")
