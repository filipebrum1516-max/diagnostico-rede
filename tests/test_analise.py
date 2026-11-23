import unittest

from diagnostico.analise import Coleta, analisar
from diagnostico.relatorio import gerar_json, gerar_texto
from diagnostico.testes_rede import ResultadoDNS, ResultadoPing


def ping_ok(destino, tempos=(10, 11, 10, 12)):
    return ResultadoPing(destino, len(tempos), len(tempos), list(tempos))


def ping_falhou(destino):
    return ResultadoPing(destino, 4, 0, [])


def dns_ok(dominio="google.com", tempo=20):
    return ResultadoDNS(dominio, ["142.250.0.1"], tempo)


def coleta_saudavel(**kwargs):
    base = dict(ip_local="192.168.1.10", gateway="192.168.1.1",
                ping_gateway=ping_ok("192.168.1.1", (1, 1, 2, 1)),
                ping_internet=ping_ok("8.8.8.8"), dns=[dns_ok()])
    base.update(kwargs)
    return Coleta(**base)


def titulos(diag):
    return [a.titulo for a in diag.achados]


class TestAnalise(unittest.TestCase):
    def test_conexao_saudavel(self):
        d = analisar(coleta_saudavel())
        self.assertEqual(d.status_geral, "OK")
        self.assertFalse(d.precisa_escalar)

    def test_sem_ip_local(self):
        d = analisar(Coleta(ip_local=None))
        self.assertEqual(d.status_geral, "PROBLEMA")
        self.assertIn("Computador sem rede", titulos(d))

    def test_roteador_ok_sem_internet_escala(self):
        d = analisar(coleta_saudavel(ping_internet=ping_falhou("8.8.8.8"), dns=[]))
        self.assertIn("Sem acesso à internet", titulos(d))
        self.assertTrue(d.precisa_escalar)

    def test_falha_de_dns(self):
        dns_falhou = ResultadoDNS("google.com", [], None, erro="Name or service not known")
        d = analisar(coleta_saudavel(dns=[dns_falhou]))
        self.assertIn("Falha de DNS", titulos(d))

    def test_wifi_instavel(self):
        d = analisar(coleta_saudavel(
            ping_gateway=ResultadoPing("192.168.1.1", 10, 8, [5, 40, 3, 60, 4, 55, 2, 70])))
        self.assertIn("Conexão instável com o roteador", titulos(d))
        self.assertEqual(d.status_geral, "ATENCAO")

    def test_internet_com_perda_e_latencia(self):
        d = analisar(coleta_saudavel(
            ping_internet=ResultadoPing("8.8.8.8", 10, 7, [150, 160, 155, 300, 140, 150, 145])))
        self.assertIn("Internet instável", titulos(d))

    def test_velocidade_abaixo_do_plano(self):
        d = analisar(coleta_saudavel(velocidade_mbps=80, plano_mbps=300))
        achado = next(a for a in d.achados if a.titulo == "Velocidade")
        self.assertEqual(achado.nivel, "PROBLEMA")
        self.assertTrue(d.precisa_escalar)

    def test_velocidade_dentro_do_plano(self):
        d = analisar(coleta_saudavel(velocidade_mbps=280, plano_mbps=300))
        self.assertEqual(d.status_geral, "OK")


class TestRelatorio(unittest.TestCase):
    def test_relatorio_texto_e_json(self):
        c = coleta_saudavel(ping_internet=ping_falhou("8.8.8.8"), dns=[])
        d = analisar(c)
        texto = gerar_texto(c, d, cliente="Cliente Teste")
        self.assertIn("Cliente Teste", texto)
        self.assertIn("SEM RESPOSTA", texto)
        self.assertIn("ESCALAR", texto)
        self.assertIn('"status_geral": "PROBLEMA"', gerar_json(c, d))


if __name__ == "__main__":
    unittest.main()
