import unittest

from diagnostico.testes_rede import interpretar_gateway, interpretar_saida_ping

PING_WINDOWS_PT = """
Disparando 8.8.8.8 com 32 bytes de dados:
Resposta de 8.8.8.8: bytes=32 tempo=20ms TTL=117
Resposta de 8.8.8.8: bytes=32 tempo=22ms TTL=117
Esgotado o tempo limite do pedido.
Resposta de 8.8.8.8: bytes=32 tempo=30ms TTL=117
"""

PING_WINDOWS_LOCAL = """
Reply from 192.168.0.1: bytes=32 time<1ms TTL=64
Reply from 192.168.0.1: bytes=32 time=1ms TTL=64
"""

PING_LINUX = """
64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=15.2 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=117 time=16.8 ms
"""

IPCONFIG_PT = """
Adaptador de Rede sem Fio Wi-Fi:
   Endereço IPv4. . . . . . . .  . . . . . . . : 192.168.1.10
   Máscara de Sub-rede . . . . . . . . . . . . : 255.255.255.0
   Gateway Padrão. . . . . . . . . . . . . . . : 192.168.1.1
"""


class TestPing(unittest.TestCase):
    def test_windows_portugues_com_perda(self):
        r = interpretar_saida_ping(PING_WINDOWS_PT, "8.8.8.8", 4)
        self.assertEqual(r.recebidos, 3)
        self.assertEqual(r.perda_percentual, 25.0)
        self.assertEqual(r.latencia_media_ms, 24.0)
        self.assertEqual(r.jitter_ms, 5.0)

    def test_windows_menor_que_1ms(self):
        r = interpretar_saida_ping(PING_WINDOWS_LOCAL, "192.168.0.1", 2)
        self.assertEqual(r.recebidos, 2)
        self.assertEqual(r.perda_percentual, 0.0)

    def test_linux(self):
        r = interpretar_saida_ping(PING_LINUX, "8.8.8.8", 2)
        self.assertEqual(r.tempos_ms, [15.2, 16.8])

    def test_sem_resposta(self):
        r = interpretar_saida_ping("", "8.8.8.8", 4)
        self.assertFalse(r.respondeu)
        self.assertEqual(r.perda_percentual, 100.0)
        self.assertIsNone(r.latencia_media_ms)


class TestGateway(unittest.TestCase):
    def test_windows_portugues(self):
        self.assertEqual(interpretar_gateway(IPCONFIG_PT, "windows"), "192.168.1.1")

    def test_linux(self):
        saida = "default via 10.0.0.1 dev wlan0 proto dhcp metric 600"
        self.assertEqual(interpretar_gateway(saida, "linux"), "10.0.0.1")

    def test_macos(self):
        saida = "   route to: default\n    gateway: 192.168.15.1\n"
        self.assertEqual(interpretar_gateway(saida, "darwin"), "192.168.15.1")

    def test_nao_encontrado(self):
        self.assertIsNone(interpretar_gateway("nada aqui", "linux"))


if __name__ == "__main__":
    unittest.main()
