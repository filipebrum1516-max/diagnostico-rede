# Diagnóstico de Rede

![testes](https://github.com/filipebrum1516-max/diagnostico-rede/actions/workflows/testes.yml/badge.svg)

Ferramenta de linha de comando desenvolvida em **Python** que automatiza o diagnóstico de conexões de internet, seguindo o roteiro utilizado pelo suporte técnico de um provedor quando o cliente relata lentidão ou ausência de conexão.

Em vez de executar manualmente `ping`, `ipconfig`, `tracert` e testes de velocidade, a ferramenta realiza todas as verificações em sequência, identifica a causa provável do problema, recomenda os próximos passos e gera um relatório para registro no chamado.

Também está disponível uma [versão web em TypeScript](https://github.com/filipebrum1516-max/diagnostico-rede-web), que pode ser acessada diretamente pelo navegador.

## Verificações realizadas

1. Endereço IP local e gateway padrão (roteador)
2. Ping até o roteador: latência, perda de pacotes e jitter
3. Ping até a internet por endereço IP (8.8.8.8)
4. Resolução DNS de domínios comuns
5. Conexão nas portas 80 e 443
6. Traceroute (opcional)
7. Velocidade de download comparada ao plano contratado (opcional)

A ordem das verificações isola o problema da camada mais próxima do cliente até o provedor. Se o roteador não responde, a falha está na rede local. Se o ping por IP funciona e o DNS falha, o problema é de resolução de nomes. Se a perda de pacotes já aparece até o roteador, a causa mais provável é o Wi-Fi. As regras estão em `diagnostico/analise.py`.

## Requisitos e execução

Requer Python 3.10 ou superior. Não utiliza bibliotecas externas.

```
git clone https://github.com/filipebrum1516-max/diagnostico-rede.git
cd diagnostico-rede
python -m diagnostico
```

Opções disponíveis:

```
python -m diagnostico --plano 300 --velocidade        # compara com um plano de 300 Mbps
python -m diagnostico --cliente "10482" --traceroute  # identifica o cliente e inclui o traceroute
python -m diagnostico --help
```

No Windows, caso o comando `python` não seja reconhecido, utilize `py`. Os relatórios são salvos na pasta `relatorios/`, nos formatos `.txt` e `.json`.

## Exemplo de relatório

Cliente conectado via Wi-Fi, com plano de 300 Mbps, relatando lentidão (trecho; o relatório completo está em `docs/exemplo_relatorio.txt`):

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

## Estrutura do projeto

```
diagnostico/
  testes_rede.py   ping, DNS, portas, gateway, traceroute e velocidade
  analise.py       regras que transformam os resultados em diagnóstico
  relatorio.py     relatório em texto e JSON
  cli.py           interface de linha de comando
tests/             testes automatizados (unittest)
```

## Testes automatizados

```
python -m unittest discover -v
```

Os testes são executados pelo GitHub Actions a cada alteração, em Windows e Linux. Cobrem a interpretação da saída dos comandos `ping` e `ipconfig` (inclusive em português) e os cenários de diagnóstico: ausência de rede, ausência de internet, falha de DNS, Wi-Fi instável e velocidade abaixo do plano.

## Melhorias previstas

- Interface gráfica
- Teste de upload
- Histórico de diagnósticos por cliente
- Medição da intensidade do sinal Wi-Fi

## Autor

Filipe Brum, estudante de Análise e Desenvolvimento de Sistemas.

## Licença

MIT
