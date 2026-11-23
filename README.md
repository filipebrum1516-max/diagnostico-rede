# diagnostico-rede

![testes](https://github.com/filipebrum1516-max/diagnostico-rede/actions/workflows/testes.yml/badge.svg)

Programa de linha de comando em Python que faz o diagnóstico básico de uma conexão de internet, do jeito que o suporte de um provedor faz quando o cliente liga dizendo que a internet está lenta ou caiu.

Em vez de rodar `ping`, `ipconfig`, `tracert` e teste de velocidade um por um e interpretar na mão, o programa faz tudo em sequência, diz onde provavelmente está o problema e salva um relatório que pode ser colado no chamado.

## O que ele testa

1. Se o computador tem IP e qual é o gateway (roteador)
2. Ping até o roteador: latência, perda de pacotes e variação (jitter)
3. Ping até a internet por IP (8.8.8.8)
4. Resolução de DNS (google.com, youtube.com, whatsapp.com)
5. Conexão nas portas 80 e 443
6. Traceroute (opcional)
7. Velocidade de download comparada com o plano contratado (opcional)

A ordem não é por acaso. Se o roteador não responde, não adianta olhar DNS. Se o ping por IP funciona mas o DNS falha, o problema é DNS e não a internet. Se a perda já aparece no ping até o roteador, o mais provável é o Wi-Fi e não o provedor. As regras ficam em `diagnostico/analise.py`.

## Como rodar

Precisa do Python 3.10 ou mais novo. Não usa nenhuma biblioteca externa.

```
git clone https://github.com/filipebrum1516-max/diagnostico-rede.git
cd diagnostico-rede
python -m diagnostico
```

Outras opções:

```
python -m diagnostico --plano 300 --velocidade      # compara com um plano de 300 Mbps
python -m diagnostico --cliente "10482" --traceroute
python -m diagnostico --help
```

No Windows, se o comando `python` não funcionar, use `py`.

Os relatórios ficam na pasta `relatorios/`, em `.txt` e `.json`.

## Exemplo

Cliente no Wi-Fi com plano de 300 Mbps reclamando de lentidão (resumido, o completo está em `docs/exemplo_relatorio.txt`):

```
  Ping roteador          192.168.1.1: média 23.6 ms | perda 10.0% | jitter 45.5 ms
  Ping internet (IP)     8.8.8.8: média 51.1 ms | perda 10.0% | jitter 51.9 ms
  DNS google.com         18.4 ms -> 142.250.79.46
  Velocidade download    96.3 Mbps

DIAGNÓSTICO
  [ ! ] Conexão instável com o roteador: Latência até o roteador de 23.6 ms e
        perda de 10.0%. Indica sinal Wi-Fi fraco ou interferência.
        -> Testar via cabo para confirmar se o problema é o Wi-Fi
        -> Usar a rede de 5 GHz se o dispositivo estiver perto do roteador
  [ OK ] DNS: Todos os domínios foram resolvidos.
  [ X ] Velocidade: 96.3 Mbps medidos, 32% do plano de 300 Mbps.
        -> Refazer o teste via cabo (o Wi-Fi limita a velocidade)
        -> Se via cabo continuar abaixo de 40%: escalar para análise do NOC
```

## Estrutura

```
diagnostico/
  testes_rede.py   ping, DNS, portas, gateway, traceroute e velocidade
  analise.py       regras que transformam os resultados em diagnóstico
  relatorio.py     relatório em texto e JSON
  cli.py           argumentos de linha de comando
tests/             testes com unittest
```

## Testes

```
python -m unittest discover -v
```

Os testes rodam no GitHub Actions a cada commit, no Windows e no Linux. Eles cobrem a leitura da saída do `ping` e do `ipconfig` (inclusive em português) e os cenários de diagnóstico: sem rede, sem internet, falha de DNS, Wi-Fi instável e velocidade abaixo do plano.

## Ideias para depois

- Interface gráfica com Tkinter
- Teste de upload
- Histórico por cliente
- Medir o sinal do Wi-Fi

## Licença

MIT
