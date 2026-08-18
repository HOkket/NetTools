# NetTools

NetTools é um repositório de estudos práticos em Python voltado a ferramentas simples de rede e utilitários de linha de comando.

## Pré-requisitos
- Python 3.8+ recomendado
- Em alguns comandos (ex.: sniffing, binding em portas baixas) permissões de administrador podem ser necessárias.
- Não há requirements.txt neste repositório; as dependências são apenas as bibliotecas padrão do Python utilizadas nos scripts.

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
