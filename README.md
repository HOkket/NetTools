# NetTools

NetTools é um repositório de estudos práticos em Python voltado a ferramentas simples de rede e utilitários de linha de comando.

## Pré-requisitos
- Python 3.8+ recomendado
- Em alguns comandos (ex.: sniffing, binding em portas baixas) permissões de administrador podem ser necessárias.
- A maioria dos scripts usa apenas a biblioteca padrão do Python.
- Extras opcionais: `psutil` (para `systool.py top` e para o `sysmon_svg.py`) e `matplotlib` (`systool.py disk --svg` e `sysmon_svg.py`). Sem eles, os demais comandos continuam funcionando.

## Uso dos scripts

Observação importante: execute varreduras ou conexões apenas em hosts/rede para os quais você tem autorização explícita.

### Portas.py
Scanner de portas em faixa usando threads e timeout curto.

Exemplo de execução:
```bash
python Portas.py
# O script pedirá:
#   Digite o IP/Dominio:
#   Digite a porta inicial:
#   Digite a porta final:
```

Comportamento:
- Inicia threads para cada porta no intervalo informado.
- Timeout de conexão de 0.5s.
- Mensagem exibida quando encontra porta aberta: "Porta Aberta ==> <porta>"

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

## Boas práticas e segurança
- Nunca execute scanners, varreduras ou uploads em redes/hosts sem autorização.
- Use ambientes isolados (VMs/containers) para testes invasivos.
- Ferramentas que permitem execução remota de comandos (como `netcat.py`) representam riscos; use apenas para fins educacionais em ambientes controlados.
- Ajuste timeouts e limites de threads conforme capacidade da sua máquina e da rede.

## Contribuição
- Este repositório é voltado a estudos pessoais. Para contribuições:
  - Abra uma issue descrevendo a proposta.
  - Envie PRs pequenos e focados (scripts separados, melhorias de segurança, documentação).
  - Inclua testes ou instruções de uso quando aplicar mudanças significativas.

## Licença
Consulte o arquivo `LICENSE` presente no repositório para os termos de uso.

## Observações finais
- Este README foi escrito especificamente para refletir apenas os arquivos que estão neste repositório atualmente.
- Se quiser, eu posso:
  - Substituir o README existente no repositório por este conteúdo,
  - Ou criar um PR com o README em uma branch separada.
  Indique qual ação prefere e em qual branch devo aplicar.
