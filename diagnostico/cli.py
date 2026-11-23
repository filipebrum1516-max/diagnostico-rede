"""Interface de linha de comando.

Exemplos:
    python -m diagnostico
    python -m diagnostico --plano 300 --velocidade
    python -m diagnostico --cliente "João Silva" --traceroute
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from . import __version__
from . import testes_rede as t
from .analise import Coleta, analisar
from .relatorio import gerar_json, gerar_texto, salvar

DOMINIOS_PADRAO = ["google.com", "youtube.com", "whatsapp.com"]
IP_INTERNET = "8.8.8.8"


def criar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="diagnostico",
        description="Automatiza o diagnóstico de internet lenta ou sem conexão.")
    p.add_argument("--cliente", help="nome ou código do cliente (vai no relatório)")
    p.add_argument("--plano", type=float, metavar="MBPS",
                   help="velocidade do plano contratado, para comparar")
    p.add_argument("--velocidade", action="store_true",
                   help="faz o teste de velocidade de download (~10 MB)")
    p.add_argument("--traceroute", action="store_true",
                   help="mostra o caminho até a internet (mais demorado)")
    p.add_argument("--pings", type=int, default=10,
                   help="quantidade de pings por teste (padrão: 10)")
    p.add_argument("--pasta", default="relatorios",
                   help="pasta onde salvar os relatórios (padrão: relatorios)")
    p.add_argument("--sem-salvar", action="store_true",
                   help="apenas mostra o relatório, sem salvar arquivos")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _passo(msg: str) -> None:
    print(f"  -> {msg}...", flush=True)


def coletar(args: argparse.Namespace) -> Coleta:
    c = Coleta(plano_mbps=args.plano)

    _passo("Verificando a rede local")
    c.ip_local = t.ip_local()
    c.gateway = t.gateway_padrao()

    if c.ip_local:
        if c.gateway:
            _passo(f"Testando o roteador ({c.gateway})")
            c.ping_gateway = t.ping(c.gateway, args.pings)

        _passo(f"Testando a internet ({IP_INTERNET})")
        c.ping_internet = t.ping(IP_INTERNET, args.pings)

        _passo("Testando a resolução de nomes (DNS)")
        c.dns = [t.resolver_dns(d) for d in DOMINIOS_PADRAO]

        if c.dns and c.dns[0].ok:
            _passo(f"Testando o acesso a sites ({DOMINIOS_PADRAO[0]})")
            c.ping_site = t.ping(DOMINIOS_PADRAO[0], args.pings)
            c.portas = [t.testar_porta(DOMINIOS_PADRAO[0], porta) for porta in (80, 443)]

        if args.traceroute:
            _passo("Executando traceroute")
            c.traceroute = t.traceroute(IP_INTERNET)

        if args.velocidade:
            _passo("Medindo a velocidade de download")
            c.velocidade_mbps = t.testar_velocidade()
    return c


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)
    print("\nDiagnóstico de Rede: iniciando os testes\n")
    quando = datetime.now()
    coleta = coletar(args)
    diag = analisar(coleta)

    texto = gerar_texto(coleta, diag, args.cliente, quando)
    print("\n" + texto)

    if not args.sem_salvar:
        txt, js = salvar(texto, gerar_json(coleta, diag, args.cliente, quando),
                         args.pasta, quando)
        print(f"\nRelatório salvo em: {txt}  e  {js}")

    return {"OK": 0, "ATENCAO": 1, "PROBLEMA": 2}[diag.status_geral]


if __name__ == "__main__":
    sys.exit(main())
