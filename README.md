# 🛠️ Diagnóstico de Rede

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Testes](https://github.com/filipebrum1516-max/diagnostico-rede/actions/workflows/testes.yml/badge.svg)
![Sem dependências](https://img.shields.io/badge/depend%C3%AAncias-nenhuma-brightgreen)
![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)

Ferramenta de linha de comando em **Python** que automatiza o diagnóstico que o **suporte técnico** de um provedor de internet faz quando o cliente diz: *"minha internet está lenta"* ou *"estou sem internet"*.

Em menos de um minuto, ela testa a conexão por etapas (computador → roteador → internet → DNS → sites → velocidade), **identifica onde está o problema**, sugere os **próximos passos** e gera um **relatório pronto para anexar ao chamado**.

## 💡 Por que criei este projeto

No atendimento de suporte N1/N2, boa parte do tempo é gasta repetindo os mesmos testes manualmente (`ping`, `ipconfig`, `tracert`, `nslookup`, teste de velocidade) e interpretando os resultados. Este projeto transforma esse roteiro em uma ferramenta que:

- padroniza o diagnóstico, para que todo atendimento siga os mesmos passos;
- reduz o tempo de atendimento;
- indica com clareza **quando o problema é do cliente (Wi-Fi, cabo, roteador)** e **quando deve ser escalado** (fibra, ONU, NOC);
- gera evidências em texto e JSON para registrar no sistema de chamados.

## ✨ Funcionalidades

| Teste | O que verifica | Problema que identifica |
|---|---|---|
| IP local e gateway | Se o computador está conectado ao roteador | Cabo desconectado, Wi-Fi desligado |
| Ping ao roteador | Latência, perda e jitter na rede local | Sinal Wi-Fi fraco, interferência |
| Ping à internet (8.8.8.8) | Saída do roteador para a internet | Fibra rompida (LOS), PPPoE, bloqueio |
| Resolução DNS | Tradução de nomes (google.com, youtube.com...) | "Internet funciona, mas sites não abrem" |
| Portas 80/443 | Acesso HTTP/HTTPS | Firewall, antivírus, proxy |
| Traceroute (opcional) | Caminho até a internet | Onde a conexão está travando |
| Velocidade (opcional) | Download comparado ao plano contratado | Velocidade abaixo do contratado |

O resultado final é classificado em **OK**, **ATENÇÃO** ou **PROBLEMA**, com a causa provável e as ações recomendadas.

## 📋 Exemplo de relatório

Cliente com reclamação de lentidão, conectado via Wi-Fi em um plano de 300 Mbps:

```text
================================================================
  RELATÓRIO DE DIAGNÓSTICO DE REDE
================================================================
  Data/hora: 23/11/2026 14:32:10
  Cliente:   Cliente 10482
  Resultado: [ X ] Problema encontrado

DADOS COLETADOS
  IP local               192.168.1.10
  Gateway (roteador)     192.168.1.1
  Ping roteador          192.168.1.1: média 23.6 ms | perda 10.0% | jitter 45.5 ms
  Ping internet (IP)     8.8.8.8: média 51.1 ms | perda 10.0% | jitter 51.9 ms
  DNS google.com         18.4 ms -> 142.250.79.46
  Porta google.com:443   aberta (30.4 ms)
  Velocidade download    96.3 Mbps

DIAGNÓSTICO
  [ ! ] Conexão instável com o roteador: Latência até o roteador de 23.6 ms e
        perda de 10.0%. Indica sinal Wi-Fi fraco ou interferência.
        -> Testar via cabo para confirmar se o problema é o Wi-Fi
        -> Usar a rede de 5 GHz se o dispositivo estiver perto do roteador
        -> Trocar o canal do Wi-Fi 2.4 GHz (1, 6 ou 11) para fugir de interferência
  [ OK ] DNS: Todos os domínios foram resolvidos.
  [ X ] Velocidade: 96.3 Mbps medidos, 32% do plano de 300 Mbps.
        -> Refazer o teste via cabo (o Wi-Fi limita a velocidade)
        -> Se via cabo continuar abaixo de 40%: escalar para análise do NOC
================================================================
```

Relatório completo: [`docs/exemplo_relatorio.txt`](docs/exemplo_relatorio.txt)

## 🚀 Como usar

Requer apenas **Python 3.9 ou superior**. Não precisa instalar nenhuma biblioteca.

```bash
git clone https://github.com/filipebrum1516-max/diagnostico-rede.git
cd diagnostico-rede

# Diagnóstico básico
python -m diagnostico

# Com teste de velocidade, comparando com um plano de 300 Mbps
python -m diagnostico --plano 300 --velocidade

# Identificando o cliente e incluindo o traceroute
python -m diagnostico --cliente "Cliente 10482" --traceroute
```

| Opção | Descrição |
|---|---|
| `--cliente NOME` | Nome ou código do cliente, incluído no relatório |
| `--plano MBPS` | Velocidade contratada, para comparar com a medida |
| `--velocidade` | Executa o teste de download (~10 MB) |
| `--traceroute` | Mostra o caminho até a internet |
| `--pings N` | Quantidade de pings por teste (padrão: 10) |
| `--pasta CAMINHO` | Pasta dos relatórios (padrão: `relatorios/`) |
| `--sem-salvar` | Só mostra na tela, sem gerar arquivos |

Os relatórios são salvos em `.txt` (para colar no chamado) e `.json` (para integração com outros sistemas).
O código de saída do programa é `0` (OK), `1` (atenção) ou `2` (problema), o que permite usá-lo em scripts.

Funciona no **Windows**, **Linux** e **macOS**, e entende a saída dos comandos do sistema em português e inglês.

## 🧠 Lógica do diagnóstico

O diagnóstico segue a mesma ordem que um técnico usa para isolar o problema, da camada mais próxima do cliente até o provedor:

```text
Computador tem IP? ──não──> Problema na rede local (cabo / Wi-Fi)
        │ sim
Roteador responde? ──não──> Roteador ou Wi-Fi com problema
        │ sim
Internet (IP) responde? ──não──> Problema entre roteador e provedor
        │ sim                     (ONU, fibra, PPPoE) → escalar
DNS resolve? ──não──> Falha de DNS → trocar DNS / flushdns
        │ sim
Latência, perda e velocidade ok? ──não──> Instabilidade → Wi-Fi ou NOC
        │ sim
   Conexão saudável ✅
```

Os limites usados (latência acima de 100 ms, perda acima de 5%, jitter acima de 30 ms, velocidade abaixo de 40% e 80% do plano) ficam em [`diagnostico/analise.py`](diagnostico/analise.py) e podem ser ajustados.

## 🗂️ Estrutura do projeto

```text
diagnostico-rede/
├── diagnostico/
│   ├── testes_rede.py   # Testes: ping, DNS, portas, gateway, traceroute, velocidade
│   ├── analise.py       # Regras que transformam os resultados em diagnóstico
│   ├── relatorio.py     # Relatório em texto e JSON
│   └── cli.py           # Interface de linha de comando (argparse)
├── tests/               # Testes automatizados (unittest)
├── docs/                # Exemplo de relatório
└── .github/workflows/   # Integração contínua com GitHub Actions
```

## ✅ Testes automatizados

```bash
python -m unittest discover -v
```

Os testes cobrem a leitura da saída do `ping` e do `ipconfig` (Windows em português, Linux e macOS) e todos os cenários de diagnóstico: conexão saudável, sem rede, sem internet, falha de DNS, Wi-Fi instável, perda de pacotes e velocidade abaixo do plano. Eles rodam automaticamente a cada commit pelo **GitHub Actions**, em Windows e Linux.

## 🛣️ Próximos passos

- [ ] Interface gráfica (Tkinter) para uso por atendentes sem experiência com terminal
- [ ] Teste de upload
- [ ] Histórico de diagnósticos do mesmo cliente para comparar ao longo do tempo
- [ ] Exportar relatório em PDF
- [ ] Teste de qualidade do sinal Wi-Fi (RSSI)

## 🧰 Tecnologias e conceitos

**Python** · **Redes TCP/IP** · ICMP (ping) · DNS · TCP/portas · Traceroute · Latência, jitter e perda de pacotes · FTTH/ONU · Suporte técnico N1/N2 · Troubleshooting · CLI (argparse) · Testes automatizados (unittest) · CI/CD (GitHub Actions)

## 👤 Autor

**Filipe Brum**, estudante de Análise e Desenvolvimento de Sistemas, focado em suporte técnico, redes e desenvolvimento.

[GitHub](https://github.com/filipebrum1516-max) · [E-mail](mailto:filipebrum1516@gmail.com)

## 📄 Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE).
