"""Testes de rede individuais (ping, DNS, portas, gateway, traceroute, velocidade).

Usa apenas a biblioteca padrão do Python e funciona no Windows, Linux e macOS.
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field

SISTEMA = platform.system().lower()  # "windows", "linux" ou "darwin"


# --------------------------------------------------------------------------- #
# Estruturas de resultado
# --------------------------------------------------------------------------- #
@dataclass
class ResultadoPing:
    destino: str
    enviados: int
    recebidos: int
    tempos_ms: list[float] = field(default_factory=list)

    @property
    def perda_percentual(self) -> float:
        if self.enviados == 0:
            return 100.0
        return round(100 * (self.enviados - self.recebidos) / self.enviados, 1)

    @property
    def latencia_media_ms(self) -> float | None:
        if not self.tempos_ms:
            return None
        return round(sum(self.tempos_ms) / len(self.tempos_ms), 1)

    @property
    def jitter_ms(self) -> float | None:
        """Variação média entre pings consecutivos (instabilidade)."""
        if len(self.tempos_ms) < 2:
            return None
        difs = [abs(a - b) for a, b in zip(self.tempos_ms, self.tempos_ms[1:])]
        return round(sum(difs) / len(difs), 1)

    @property
    def respondeu(self) -> bool:
        return self.recebidos > 0


@dataclass
class ResultadoDNS:
    dominio: str
    ips: list[str]
    tempo_ms: float | None
    erro: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.ips)


@dataclass
class ResultadoPorta:
    host: str
    porta: int
    aberta: bool
    tempo_ms: float | None


# --------------------------------------------------------------------------- #
# Ping
# --------------------------------------------------------------------------- #
_RE_TEMPO = re.compile(r"(?:time|tempo|tiempo)\s*[=<]\s*([\d.,]+)\s*ms", re.IGNORECASE)


def interpretar_saida_ping(saida: str, destino: str, enviados: int) -> ResultadoPing:
    """Extrai os tempos de resposta da saída do comando ping.

    Funciona com a saída em português e inglês do Windows e com a do Linux/macOS.
    """
    tempos = [float(t.replace(",", ".")) for t in _RE_TEMPO.findall(saida)]
    return ResultadoPing(destino=destino, enviados=enviados,
                         recebidos=len(tempos), tempos_ms=tempos)


def ping(destino: str, quantidade: int = 4, timeout_s: int = 2) -> ResultadoPing:
    """Executa o ping do sistema operacional e devolve o resultado."""
    if SISTEMA == "windows":
        cmd = ["ping", "-n", str(quantidade), "-w", str(timeout_s * 1000), destino]
    else:
        cmd = ["ping", "-c", str(quantidade), "-W", str(timeout_s), destino]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=quantidade * (timeout_s + 1) + 5,
                              errors="replace")
        saida = proc.stdout + proc.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired):
        saida = ""
    return interpretar_saida_ping(saida, destino, quantidade)


# --------------------------------------------------------------------------- #
# DNS
# --------------------------------------------------------------------------- #
def resolver_dns(dominio: str) -> ResultadoDNS:
    """Resolve um domínio e mede o tempo da consulta DNS."""
    inicio = time.perf_counter()
    try:
        infos = socket.getaddrinfo(dominio, None)
        tempo = (time.perf_counter() - inicio) * 1000
        ips = sorted({info[4][0] for info in infos})
        return ResultadoDNS(dominio, ips, round(tempo, 1))
    except socket.gaierror as exc:
        return ResultadoDNS(dominio, [], None, erro=str(exc))


# --------------------------------------------------------------------------- #
# Portas
# --------------------------------------------------------------------------- #
def testar_porta(host: str, porta: int, timeout_s: float = 3.0) -> ResultadoPorta:
    """Verifica se é possível abrir uma conexão TCP com host:porta."""
    inicio = time.perf_counter()
    try:
        with socket.create_connection((host, porta), timeout=timeout_s):
            tempo = (time.perf_counter() - inicio) * 1000
            return ResultadoPorta(host, porta, True, round(tempo, 1))
    except OSError:
        return ResultadoPorta(host, porta, False, None)


# --------------------------------------------------------------------------- #
# Informações locais
# --------------------------------------------------------------------------- #
def ip_local() -> str | None:
    """Descobre o IP local usado para sair para a internet (não envia dados)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


_RE_GATEWAY_WIN = re.compile(
    r"(?:Gateway Padr[ãa]o|Default Gateway|Puerta de enlace predeterminada)"
    r"[ .]*:\s*((?:\d{1,3}\.){3}\d{1,3})",
    re.IGNORECASE,
)


def interpretar_gateway(saida: str, sistema: str = SISTEMA) -> str | None:
    """Extrai o IP do gateway (roteador) da saída do comando do sistema."""
    if sistema == "windows":
        m = _RE_GATEWAY_WIN.search(saida)
    elif sistema == "darwin":
        m = re.search(r"gateway:\s*((?:\d{1,3}\.){3}\d{1,3})", saida)
    else:
        m = re.search(r"default via\s+((?:\d{1,3}\.){3}\d{1,3})", saida)
    return m.group(1) if m else None


def gateway_padrao() -> str | None:
    """Descobre o IP do roteador (gateway padrão)."""
    comandos = {
        "windows": ["ipconfig"],
        "darwin": ["route", "-n", "get", "default"],
    }
    cmd = comandos.get(SISTEMA, ["ip", "route"])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=10, errors="replace")
        return interpretar_gateway(proc.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# --------------------------------------------------------------------------- #
# Traceroute
# --------------------------------------------------------------------------- #
def traceroute(destino: str, max_saltos: int = 15) -> list[str]:
    """Executa o traceroute (tracert no Windows) e devolve as linhas dos saltos."""
    if SISTEMA == "windows":
        cmd = ["tracert", "-d", "-h", str(max_saltos), "-w", "1000", destino]
    else:
        cmd = ["traceroute", "-n", "-m", str(max_saltos), "-w", "1", destino]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=max_saltos * 4 + 10, errors="replace")
    except FileNotFoundError:
        return ["traceroute não está instalado neste sistema."]
    except subprocess.TimeoutExpired:
        return ["traceroute demorou demais e foi interrompido."]
    return [linha.rstrip() for linha in proc.stdout.splitlines()
            if re.match(r"^\s*\d+\s", linha)]


# --------------------------------------------------------------------------- #
# Velocidade
# --------------------------------------------------------------------------- #
URL_VELOCIDADE = "https://speed.cloudflare.com/__down?bytes={bytes}"


def testar_velocidade(megabytes: int = 10, timeout_s: int = 30) -> float | None:
    """Baixa um arquivo de teste e devolve a velocidade aproximada em Mbps."""
    url = URL_VELOCIDADE.format(bytes=megabytes * 1_000_000)
    req = urllib.request.Request(url, headers={"User-Agent": "diagnostico-rede"})
    try:
        inicio = time.perf_counter()
        total = 0
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            while bloco := resp.read(64 * 1024):
                total += len(bloco)
        duracao = time.perf_counter() - inicio
    except OSError:
        return None
    if duracao <= 0 or total == 0:
        return None
    return round(total * 8 / duracao / 1_000_000, 1)
