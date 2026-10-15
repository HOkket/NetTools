# NetTools

NetTools é um repositório de estudos práticos em Python voltado a ferramentas simples de rede e utilitários de linha de comando.

## Pré-requisitos
- Python 3.8+ recomendado.
- Alguns comandos podem exigir permissões de administrador (ex.: sniffing, binding em portas baixas, ver o processo dono dos sockets).
- A maioria dos scripts usa apenas a biblioteca padrão do Python.
- Dependências opcionais: `psutil` e `matplotlib` — usadas por `systool.py` (top e `disk --svg`) e exigidas por `sysmon_svg.py`. Sem elas, os demais comandos continuam funcionando.
- O subdiretório `Cliente-Servidor SSH/` tem seu próprio `requirements.txt` (Paramiko).

## Uso dos scripts

Observação importante: execute varreduras ou conexões apenas em hosts/rede para os quais você tem autorização explícita.

### Doorman.py
Scanner de portas em faixa usando threads e timeout curto.

Exemplo de execução:
```bash
python Doorman.py
# O script pedirá:
#   Digite o IP/Dominio:
#   Digite a porta inicial:
#   Digite a porta final:
```

Comportamento:
- Cria uma thread por porta do intervalo informado.
- Limita a 300 conexões simultâneas via `threading.Semaphore`.
- Timeout de conexão de 0.5s.
- Mensagem exibida quando encontra porta aberta: "Porta Aberta ==> <porta>"
- Trata `Ctrl+C`, host não resolvido e porta inválida.

> Observação: este arquivo chamava-se `Portas.py` e foi renomeado para `Doorman.py`.

### Portas_especifica.py
Checa se uma porta específica em um host está aberta ou fechada.

Exemplo de execução:
```bash
python Portas_especifica.py
# O script pedirá:
#   Digite o IP/Dominio:
#   Digite a porta:
```

Comportamento:
- Cria um socket TCP com timeout de 0.5s.
- Exibe "Porta Aberta ==>" ou "Porta Fechada ==>" conforme o resultado.
- Trata `Ctrl+C`, host não resolvido e porta inválida.

### conversosr_de_ips.py
Converte um endereço IPv4 (base 10, ex.: `127.0.0.1`) para outras representações.

Exemplo de execução:
```bash
python conversosr_de_ips.py
# Insira o IP: 127.0.0.1
```

Comportamento — para o IP informado, exibe:
- Hexadecimal com pontos (ex.: `0x7f.0x00.0x00.0x01`)
- Hexadecimal único (ex.: `0x7f000001`)
- Octal com pontos (ex.: `0177.00.00.01`)
- Decimal inteiro / DWORD (ex.: `2130706433`)

### netcat.py
Ferramenta estilo netcat com modos cliente e servidor, suporte a upload, execução de comando e shell interativo.

Principais opções (veja as opções internas do parser em `netcat.py`):
- -l, --listen : executar em modo listener (servidor)
- -t, --target : alvo (IP) — padrão no script: 192.168.1.203
- -p, --port   : porta (padrão 5555)
- -c, --command: iniciar shell de comando remoto (quando em listen)
- -e, --execute: executar comando ao receber conexão (quando em listen)
- -u, --upload : salvar upload recebido em arquivo especificado

Exemplos:
- Ouvir em uma máquina e abrir shell interativo:
  ```bash
  python netcat.py -t 0.0.0.0 -p 5555 -l -c
  ```
- Ouvir e salvar upload em `arquivo.txt`:
  ```bash
  python netcat.py -t 0.0.0.0 -p 5555 -l -u arquivo.txt
  ```
- Ouvir e executar um comando ao conectar:
  ```bash
  python netcat.py -t 0.0.0.0 -p 5555 -l -e "cat /etc/passwd"
  ```
- Conectar como cliente para enviar dados via stdin:
  ```bash
  echo 'ABC' | python netcat.py -t 192.168.1.108 -p 135
  ```

Comportamento:
- Em modo cliente, conecta e permite troca interativa de dados.
- Em modo servidor, aceita conexões e, dependendo das flags, executa comando, salva upload ou fornece shell de comando.
- Implementa tratamento básico de mudanças de diretório (`cd`) e execução via subprocess.

### systool.py
Utilitários **read-only** para administração de Linux: inventário do sistema, top de processos, uso de disco, portas em escuta, conexões (via `ss`), validade de certificados TLS, resumo de erros/logins falhos e um diagnóstico agregado (`health`). Não altera nada no sistema — apenas lê `/proc`, `/sys`, sockets e chama comandos de consulta.

Exemplos:
```bash
python systool.py info                # inventário do sistema
python systool.py top -n 10           # top processos por CPU e memória
python systool.py disk /var/log --svg disco.svg
python systool.py ports               # portas em escuta + processo dono
python systool.py conns -n 10 --listen
python systool.py certs exemplo.com:443 outro.com
python systool.py logs -n 15          # erros do kernel e logins falhos
python systool.py health              # diagnóstico agregado (OK/WARN/CRIT)
```

Comportamento:
- Prioriza dados de `/proc` e `/sys`; usa `psutil` e `matplotlib` quando disponíveis (opcionais).
- `ports` e `conns` podem exigir `sudo` para mostrar o processo dono dos sockets.
- Compatível com Python 3.8+ e sem dependências obrigatórias.

### sysmon_svg.py
Coleta uso de recursos (CPU, RAM, swap, I/O de disco e rede) por um período e exporta um **gráfico SVG**.

Exemplo de execução:
```bash
python sysmon_svg.py                          # 30s, amostra a cada 1s -> sysmon.svg
python sysmon_svg.py -d 60 -i 2 -o cpu.svg
```

Comportamento:
- Requer `psutil` e `matplotlib` (dependências opcionais deste repositório).
- Três painéis: CPU/RAM/Swap (%), disco (leitura/escrita em MB/s) e rede (RX/TX em MB/s).
- Gera o SVG sem precisar de display/X11 (backend `Agg`).

### Cliente-Servidor SSH/
Conjunto de scripts de estudo sobre SSH com a biblioteca [Paramiko](https://www.paramiko.org/). Requer `Paramiko` (veja `requirements.txt` na própria pasta).

- `ssh_server.py` — servidor SSH de teste com Paramiko. Escuta em `192.168.0.174:2222`, autentica com credenciais de exemplo (`tim` / `secret`) e usa a chave de host `test_rsa.key`.
  - ⚠️ Ajuste o IP/porta, troque as credenciais e **gere a chave de host** antes de rodar (ex.: `ssh-keygen -t rsa -b 2048 -f test_rsa.key`). Use apenas em laboratório — nunca em produção.
- `ssh_rcmd.py` — cliente que conecta ao servidor e executa os comandos que o servidor enviar (fluxo de "comando reverso").
- `cliente-SSH.py` — cliente SSH com dois modos: comando único e shell interativo (múltiplos comandos sem reconectar).

Passos típicos:
```bash
cd "Cliente-Servidor SSH"
pip install -r requirements.txt        # Paramiko
python ssh_server.py                   # em uma máquina (após ajustar IP/porta e gerar a chave)
python cliente-SSH.py                  # em outra, para conectar
```

## Boas práticas e segurança
- Nunca execute scanners, varreduras ou uploads em redes/hosts sem autorização.
- Use ambientes isolados (VMs/containers) para testes invasivos.
- Ferramentas que permitem execução remota de comandos (como `netcat.py` e os scripts de SSH) representam riscos; use apenas para fins educacionais em ambientes controlados.
- As credenciais de exemplo em `ssh_server.py` são apenas ilustrativas — não as reutilize fora de um laboratório.
- Ajuste timeouts e limites de threads conforme capacidade da sua máquina e da rede.

## Contribuição
- Este repositório é voltado a estudos pessoais. Para contribuições:
  - Abra uma issue descrevendo a proposta.
  - Envie PRs pequenos e focados (scripts separados, melhorias de segurança, documentação).
  - Inclua testes ou instruções de uso quando aplicar mudanças significativas.

## Licença
Este projeto está sob a **GNU General Public License v3.0 (GPLv3)**. Consulte o arquivo `LICENSE` para os termos completos.
