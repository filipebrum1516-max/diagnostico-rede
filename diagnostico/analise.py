"""Análise dos resultados: transforma os números dos testes em um diagnóstico
com causa provável e próximos passos, seguindo o raciocínio de um atendente
de suporte N2 de provedor de internet."""

from __future__ import annotations

from dataclasses import dataclass, field

from .testes_rede import ResultadoDNS, ResultadoPing, ResultadoPorta

# Limites usados na análise (podem ser ajustados conforme o provedor)
LATENCIA_ALTA_MS = 100
JITTER_ALTO_MS = 30
PERDA_ALTA_PCT = 5
LATENCIA_ROTEADOR_ALTA_MS = 20
DNS_LENTO_MS = 300


@dataclass
class Coleta:
    """Todos os dados coletados em um diagnóstico."""
    ip_local: str | None = None
    gateway: str | None = None
    ping_gateway: ResultadoPing | None = None
    ping_internet: ResultadoPing | None = None      # ping por IP (ex.: 8.8.8.8)
    ping_site: ResultadoPing | None = None          # ping por nome (ex.: google.com)
    dns: list[ResultadoDNS] = field(default_factory=list)
    portas: list[ResultadoPorta] = field(default_factory=list)
    traceroute: list[str] = field(default_factory=list)
    velocidade_mbps: float | None = None
    plano_mbps: float | None = None


@dataclass
class Achado:
    nivel: str          # "OK", "ATENCAO" ou "PROBLEMA"
    titulo: str
    detalhe: str
    acoes: list[str] = field(default_factory=list)


@dataclass
class Diagnostico:
    achados: list[Achado]

    @property
    def status_geral(self) -> str:
        niveis = {a.nivel for a in self.achados}
        if "PROBLEMA" in niveis:
            return "PROBLEMA"
        if "ATENCAO" in niveis:
            return "ATENCAO"
        return "OK"

    @property
    def precisa_escalar(self) -> bool:
        """Indica se o caso deve ser encaminhado para visita técnica/NOC."""
        return any("escalar" in acao.lower() or "visita técnica" in acao.lower()
                   for a in self.achados if a.nivel == "PROBLEMA"
                   for acao in a.acoes)


def analisar(c: Coleta) -> Diagnostico:
    achados: list[Achado] = []

    # 1) Rede local: o computador está ligado ao roteador?
    if c.ip_local is None:
        achados.append(Achado(
            "PROBLEMA", "Computador sem rede",
            "O computador não tem endereço IP. Ele não está conectado ao roteador.",
            ["Verificar se o cabo de rede está conectado ou se o Wi-Fi está ligado",
             "Conferir se está conectado na rede Wi-Fi correta e com a senha certa",
             "Reiniciar o roteador (desligar por 30 segundos e ligar novamente)"]))
        return Diagnostico(achados)

    if c.ping_gateway is not None and not c.ping_gateway.respondeu:
        achados.append(Achado(
            "PROBLEMA", "Roteador não responde",
            f"O roteador ({c.gateway}) não respondeu ao ping.",
            ["Aproximar o dispositivo do roteador ou testar via cabo",
             "Reiniciar o roteador",
             "Se persistir, verificar se o roteador está com defeito"]))
    elif c.ping_gateway is not None:
        lat = c.ping_gateway.latencia_media_ms or 0
        if c.ping_gateway.perda_percentual > PERDA_ALTA_PCT or lat > LATENCIA_ROTEADOR_ALTA_MS:
            achados.append(Achado(
                "ATENCAO", "Conexão instável com o roteador",
                f"Latência até o roteador de {lat} ms e perda de "
                f"{c.ping_gateway.perda_percentual}%. Indica sinal Wi-Fi fraco ou interferência.",
                ["Testar via cabo para confirmar se o problema é o Wi-Fi",
                 "Usar a rede de 5 GHz se o dispositivo estiver perto do roteador",
                 "Trocar o canal do Wi-Fi 2.4 GHz (1, 6 ou 11) para fugir de interferência",
                 "Verificar quantos dispositivos estão conectados ao mesmo tempo"]))
        else:
            achados.append(Achado("OK", "Rede local",
                                  f"Roteador respondendo em {lat} ms, sem perdas."))

    # 2) Internet: o roteador tem saída para a internet?
    internet_ok = bool(c.ping_internet and c.ping_internet.respondeu)
    if c.ping_internet is not None and not internet_ok:
        if c.ping_gateway is not None and c.ping_gateway.respondeu:
            achados.append(Achado(
                "PROBLEMA", "Sem acesso à internet",
                "O roteador responde, mas não há resposta da internet. "
                "O problema está entre o roteador e o provedor.",
                ["Verificar as luzes da ONU/ONT: luz LOS vermelha indica rompimento da fibra",
                 "Conferir se a conexão PPPoE do roteador está autenticada",
                 "Verificar no sistema do provedor se há bloqueio por pendência financeira",
                 "Verificar se há manutenção ou queda na região",
                 "Se a luz LOS estiver acesa: escalar para visita técnica"]))
        elif c.ping_gateway is None:
            achados.append(Achado(
                "PROBLEMA", "Sem acesso à internet",
                "Não há resposta da internet e não foi possível identificar o roteador.",
                ["Verificar se o roteador está ligado e com as luzes normais",
                 "Verificar as luzes da ONU/ONT: luz LOS vermelha indica rompimento da fibra",
                 "Reiniciar o roteador e a ONU",
                 "Se a luz LOS estiver acesa: escalar para visita técnica"]))
        else:
            achados.append(Achado(
                "PROBLEMA", "Sem acesso à internet",
                "Sem resposta do roteador e da internet.",
                ["Resolver primeiro o problema da rede local (ver acima)"]))
    elif internet_ok:
        p = c.ping_internet
        lat = p.latencia_media_ms or 0
        jit = p.jitter_ms or 0
        problemas = []
        if p.perda_percentual > PERDA_ALTA_PCT:
            problemas.append(f"perda de pacotes de {p.perda_percentual}%")
        if lat > LATENCIA_ALTA_MS:
            problemas.append(f"latência alta ({lat} ms)")
        if jit > JITTER_ALTO_MS:
            problemas.append(f"variação alta (jitter de {jit} ms)")
        if problemas:
            achados.append(Achado(
                "ATENCAO", "Internet instável",
                "Foi encontrado: " + ", ".join(problemas) + ". "
                "Isso causa lentidão, travamentos em vídeos e lag em jogos.",
                ["Comparar com o ping até o roteador para saber se a causa é o Wi-Fi",
                 "Verificar a potência óptica da ONU (ideal entre -8 e -25 dBm)",
                 "Verificar se algum dispositivo está fazendo download pesado",
                 "Se persistir via cabo: escalar para análise do NOC"]))
        else:
            achados.append(Achado("OK", "Internet",
                                  f"Latência de {lat} ms, sem perda de pacotes."))

    # 3) DNS: a internet funciona por IP mas não por nome?
    if c.dns:
        falhas = [d for d in c.dns if not d.ok]
        lentos = [d for d in c.dns if d.ok and (d.tempo_ms or 0) > DNS_LENTO_MS]
        if falhas and internet_ok:
            achados.append(Achado(
                "PROBLEMA", "Falha de DNS",
                "A internet funciona (o ping por IP responde), mas os sites não abrem "
                "pelo nome. Domínios com falha: " + ", ".join(d.dominio for d in falhas) + ".",
                ["Configurar DNS públicos no roteador: 8.8.8.8 e 1.1.1.1",
                 "Limpar o cache de DNS do computador (Windows: ipconfig /flushdns)",
                 "Reiniciar o roteador"]))
        elif lentos:
            achados.append(Achado(
                "ATENCAO", "DNS lento",
                "A resolução de nomes está demorando (" +
                ", ".join(f"{d.dominio}: {d.tempo_ms} ms" for d in lentos) +
                "). Os sites demoram para começar a carregar.",
                ["Configurar DNS públicos no roteador: 8.8.8.8 e 1.1.1.1"]))
        elif not falhas:
            achados.append(Achado("OK", "DNS", "Todos os domínios foram resolvidos."))

    # 4) Portas: navegação web bloqueada?
    fechadas = [p for p in c.portas if not p.aberta]
    if c.portas and fechadas and internet_ok:
        achados.append(Achado(
            "ATENCAO", "Portas bloqueadas",
            "Não foi possível conectar em: " +
            ", ".join(f"{p.host}:{p.porta}" for p in fechadas) + ".",
            ["Verificar firewall ou antivírus do computador",
             "Verificar se há proxy configurado no navegador"]))

    # 5) Velocidade: está entregando o plano contratado?
    if c.velocidade_mbps is not None and c.plano_mbps:
        pct = round(100 * c.velocidade_mbps / c.plano_mbps)
        if pct < 40:
            nivel = "PROBLEMA"
        elif pct < 80:
            nivel = "ATENCAO"
        else:
            nivel = "OK"
        acoes = [] if nivel == "OK" else [
            "Refazer o teste via cabo (o Wi-Fi limita a velocidade)",
            "Desconectar outros dispositivos durante o teste",
            "Verificar se a placa de rede ou o cabo suporta a velocidade do plano",
            "Se via cabo continuar abaixo de 40%: escalar para análise do NOC"]
        achados.append(Achado(
            nivel, "Velocidade",
            f"{c.velocidade_mbps} Mbps medidos, {pct}% do plano de {c.plano_mbps:g} Mbps.",
            acoes))

    return Diagnostico(achados)
