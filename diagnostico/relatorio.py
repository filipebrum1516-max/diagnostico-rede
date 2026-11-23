"""Geração do relatório em texto (para anexar ao chamado) e em JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .analise import Coleta, Diagnostico

ICONES = {"OK": "[ OK ]", "ATENCAO": "[ ! ]", "PROBLEMA": "[ X ]"}
STATUS = {"OK": "Conexão saudável", "ATENCAO": "Conexão com pontos de atenção",
          "PROBLEMA": "Problema encontrado"}


def _linha_ping(nome: str, p) -> str:
    if p is None:
        return f"  {nome:<22} não testado"
    if not p.respondeu:
        return f"  {nome:<22} {p.destino}: SEM RESPOSTA"
    return (f"  {nome:<22} {p.destino}: média {p.latencia_media_ms} ms | "
            f"perda {p.perda_percentual}% | jitter {p.jitter_ms if p.jitter_ms is not None else '-'} ms")


def gerar_texto(c: Coleta, d: Diagnostico, cliente: str | None = None,
                quando: datetime | None = None) -> str:
    quando = quando or datetime.now()
    linhas = [
        "=" * 64,
        "  RELATÓRIO DE DIAGNÓSTICO DE REDE",
        "=" * 64,
        f"  Data/hora: {quando:%d/%m/%Y %H:%M:%S}",
    ]
    if cliente:
        linhas.append(f"  Cliente:   {cliente}")
    linhas += [
        f"  Resultado: {ICONES[d.status_geral]} {STATUS[d.status_geral]}",
        "",
        "DADOS COLETADOS",
        f"  {'IP local':<22} {c.ip_local or 'não encontrado'}",
        f"  {'Gateway (roteador)':<22} {c.gateway or 'não encontrado'}",
        _linha_ping("Ping roteador", c.ping_gateway),
        _linha_ping("Ping internet (IP)", c.ping_internet),
        _linha_ping("Ping site (nome)", c.ping_site),
    ]
    for r in c.dns:
        valor = f"{r.tempo_ms} ms -> {', '.join(r.ips[:2])}" if r.ok else "FALHOU"
        linhas.append(f"  {'DNS ' + r.dominio:<22} {valor}")
    for p in c.portas:
        valor = f"aberta ({p.tempo_ms} ms)" if p.aberta else "FECHADA"
        linhas.append(f"  {'Porta ' + p.host + ':' + str(p.porta):<22} {valor}")
    if c.velocidade_mbps is not None:
        linhas.append(f"  {'Velocidade download':<22} {c.velocidade_mbps} Mbps")
    if c.traceroute:
        linhas += ["", "TRACEROUTE"] + [f"  {l}" for l in c.traceroute]

    linhas += ["", "DIAGNÓSTICO"]
    for a in d.achados:
        linhas.append(f"  {ICONES[a.nivel]} {a.titulo}: {a.detalhe}")
        for acao in a.acoes:
            linhas.append(f"        -> {acao}")
    if d.precisa_escalar:
        linhas += ["", "  >> Recomendação: se os passos acima não resolverem, ESCALAR o chamado."]
    linhas.append("=" * 64)
    return "\n".join(linhas)


def gerar_json(c: Coleta, d: Diagnostico, cliente: str | None = None,
               quando: datetime | None = None) -> str:
    quando = quando or datetime.now()
    dados = {
        "data_hora": quando.isoformat(timespec="seconds"),
        "cliente": cliente,
        "status_geral": d.status_geral,
        "precisa_escalar": d.precisa_escalar,
        "coleta": asdict(c),
        "achados": [asdict(a) for a in d.achados],
    }
    return json.dumps(dados, ensure_ascii=False, indent=2)


def salvar(texto: str, json_txt: str, pasta: str | Path = "relatorios",
           quando: datetime | None = None) -> tuple[Path, Path]:
    quando = quando or datetime.now()
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    base = pasta / f"diagnostico_{quando:%Y-%m-%d_%H-%M-%S}"
    caminho_txt = base.with_suffix(".txt")
    caminho_json = base.with_suffix(".json")
    caminho_txt.write_text(texto, encoding="utf-8")
    caminho_json.write_text(json_txt, encoding="utf-8")
    return caminho_txt, caminho_json
