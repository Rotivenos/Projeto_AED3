import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as servidor
import roteamento


class TestesRoteamento(unittest.TestCase):
    def setUp(self):
        self.deposito = dict(endereco="Base", latitude=0, longitude=0)
        self.caminhoes = [dict(id=1, placa="ABC1234", capacidade_kg=100)]

    def getpedido(self, identificador, peso=10, prazo="17:00"):
        return dict(id=identificador, cliente=f"Cliente {identificador}",
                    endereco="Entrega", latitude=1, longitude=1,
                    peso_kg=peso, prazo=prazo)

    def getresultado(self, pedidos, tempos, distancias=None):
        with patch.object(roteamento, "matriz_rotas",
                          return_value=(distancias or tempos, tempos)):
            return roteamento.getotimizar(pedidos, self.caminhoes, self.deposito)

    def getdados(self, tempos, cargas=None, capacidades=None, prazos=None):
        quantidade = len(tempos)
        return dict(matriz_tempos_min=tempos,
                    cargas_kg=cargas or [0] + [10] * (quantidade - 1),
                    capacidades_kg=capacidades or [100],
                    janelas_horario=[(360, 1080)] + [
                        (360, prazo) for prazo in (prazos or [1080] * (quantidade - 1))],
                    tempos_atendimento_min=[0] + [10] * (quantidade - 1))

    def test_retorno_assimetrico_e_totais(self):
        resultado = self.getresultado([self.getpedido(1)],
                                      [[0, 10], [20, 0]], [[0, 5], [7, 0]])
        rota = resultado["rotas"][0]
        self.assertEqual(resultado["tempo_deslocamento_total_min"], 30)
        self.assertEqual(resultado["distancia_total_km"], 12)
        self.assertEqual(rota["paradas"][0]["chegada"], "06:10")
        self.assertEqual(rota["retorno_deposito"]["chegada"], "06:40")
        self.assertEqual(rota["retorno_deposito"]["distancia_km"], 7)

    def test_retorno_limite_inclui_atendimento(self):
        pedido = self.getpedido(1)
        viavel = self.getresultado([pedido], [[0, 10], [700, 0]])
        self.assertEqual(viavel["rotas"][0]["retorno_deposito"]["chegada"], "18:00")
        inviavel = self.getresultado([pedido], [[0, 10], [701, 0]])
        self.assertEqual(inviavel["pedidos_atendidos"], 0)
        self.assertEqual(inviavel["tempo_deslocamento_total_min"], 0)
        self.assertEqual(inviavel["distancia_total_km"], 0)

    def test_prazo_de_chegada(self):
        resultado = self.getresultado([self.getpedido(1, prazo="06:09")],
                                      [[0, 10], [10, 0]])
        self.assertEqual(resultado["pedidos_atendidos"], 0)
        resultado = self.getresultado([self.getpedido(1, prazo="06:10")],
                                      [[0, 10], [10, 0]])
        self.assertEqual(resultado["pedidos_atendidos"], 1)

    def test_capacidade_fracionaria_nao_trunca_peso(self):
        resultado = self.getresultado([self.getpedido(1, peso=100.5)], [[0, 1], [1, 0]])
        self.assertEqual(resultado["pedidos_atendidos"], 0)
        resultado = self.getresultado([self.getpedido(1, peso=99.5)], [[0, 1], [1, 0]])
        self.assertEqual(resultado["rotas"][0]["carga_kg"], 99.5)

    def test_distribuicao_sem_duplicar_pedidos(self):
        self.caminhoes.append(dict(id=2, placa="DEF5678", capacidade_kg=100))
        pedidos = [self.getpedido(1, 80), self.getpedido(2, 80), self.getpedido(3, 150)]
        tempos = [[0 if origem == destino else 10 for destino in range(4)]
                  for origem in range(4)]
        resultado = self.getresultado(pedidos, tempos)
        atendidos = [p["pedido_id"] for r in resultado["rotas"] for p in r["paradas"]]
        self.assertEqual(sorted(atendidos), [1, 2])
        self.assertEqual(resultado["caminhoes_utilizados"], 2)
        self.assertEqual(len(resultado["pedidos_nao_atendidos"]), 1)

    def test_busca_melhora_ordem_em_matriz_assimetrica(self):
        dados = self.getdados([[0, 10, 1], [1, 0, 10], [10, 1, 0]])
        rotas = [[1, 2]]
        roteamento.setmelhorarrotas(rotas, set(), dados)
        self.assertEqual(rotas, [[2, 1]])
        self.assertEqual(roteamento.getavaliarrota(rotas[0], 100, dados)["deslocamento"], 3)

    def test_busca_consolida_caminhoes(self):
        dados = self.getdados([[0, 10, 10], [10, 0, 1], [10, 1, 0]], capacidades=[100, 100])
        rotas = [[1], [2]]
        roteamento.setmelhorarrotas(rotas, set(), dados)
        self.assertEqual(sum(bool(rota) for rota in rotas), 1)
        self.assertEqual(sorted(no for rota in rotas for no in rota), [1, 2])

    def test_busca_nao_aceita_melhoria_que_viola_prazo(self):
        dados = self.getdados([[0, 10, 1], [1, 0, 10], [10, 1, 0]], prazos=[370, 1080])
        rotas = [[1, 2]]
        roteamento.setmelhorarrotas(rotas, set(), dados)
        self.assertEqual(rotas, [[1, 2]])

    def test_fallback_sem_api(self):
        with patch.object(roteamento, "matriz_rotas", return_value=None):
            resultado = roteamento.getotimizar([self.getpedido(1)], self.caminhoes, self.deposito)
        self.assertEqual(resultado["pedidos_atendidos"], 1)
        self.assertGreater(resultado["distancia_total_km"], 0)

    def test_entradas_vazias(self):
        self.assertIn("erro", roteamento.getotimizar([], self.caminhoes, self.deposito))
        self.assertIn("erro", roteamento.getotimizar([self.getpedido(1)], [], self.deposito))
        self.assertIn("erro", roteamento.getotimizar([self.getpedido(1)], self.caminhoes, None))

    def test_invariantes_em_cenarios_aleatorios(self):
        gerador = random.Random(42)
        for _ in range(15):
            tempos = [[0 if origem == destino else gerador.randint(1, 100)
                       for destino in range(7)] for origem in range(7)]
            dados = self.getdados(tempos, cargas=[0] + [gerador.randint(1, 60) for _ in range(6)],
                                 capacidades=[100, 80],
                                 prazos=[gerador.randint(400, 1000) for _ in range(6)])
            rotas = [[], []]
            pendentes = set(range(1, 7))
            roteamento.setinserirpendentes(rotas, pendentes, dados)
            antes = sum(roteamento.getavaliarrota(r, c, dados)["custo"]
                        for r, c in zip(rotas, dados["capacidades_kg"]))
            quantidade_antes = len(pendentes)
            roteamento.setmelhorarrotas(rotas, pendentes, dados)
            atendidos = [no for rota in rotas for no in rota]
            self.assertEqual(len(atendidos), len(set(atendidos)))
            self.assertEqual(set(atendidos) | pendentes, set(range(1, 7)))
            self.assertFalse(set(atendidos) & pendentes)
            depois = 0
            for rota, capacidade in zip(rotas, dados["capacidades_kg"]):
                avaliacao = roteamento.getavaliarrota(rota, capacidade, dados)
                self.assertIsNotNone(avaliacao)
                depois += avaliacao["custo"]
            if len(pendentes) == quantidade_antes:
                self.assertLessEqual(depois, antes)
            self.assertLessEqual(len(pendentes), quantidade_antes)

    def test_integracao_flask_com_banco_temporario(self):
        with tempfile.TemporaryDirectory() as pasta:
            with patch.object(servidor, "DB_PATH", Path(pasta) / "teste.db"):
                servidor.init_db()
                conexao = servidor.get_db()
                conexao.execute("INSERT INTO caminhoes (placa, capacidade_kg) VALUES ('TESTE', 100)")
                conexao.execute("""INSERT INTO pedidos
                    (cliente, endereco, latitude, longitude, peso_kg, prazo)
                    VALUES ('Cliente teste', 'Entrega', 1, 1, 10, '17:00')""")
                conexao.commit()
                conexao.close()
                with patch.object(roteamento, "matriz_rotas",
                                  return_value=([[0, 5], [7, 0]], [[0, 10], [20, 0]])):
                    resposta = servidor.app.test_client().post("/otimizar")
                self.assertEqual(resposta.status_code, 200)
                pagina = resposta.get_data(as_text=True)
                self.assertIn("Retorno ao depósito", pagina)
                self.assertIn("06:40", pagina)
                self.assertIn("12 km", pagina)
                self.assertNotIn("OR-Tools", pagina)


if __name__ == "__main__":
    unittest.main()
