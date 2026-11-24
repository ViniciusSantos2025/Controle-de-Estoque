"""
Testes automáticos das regras do sistema.
Para rodar:  python -m unittest -v
(":memory:" cria um banco temporário, que some quando o teste termina.)
"""

import sqlite3
import unittest

import banco


class TestBanco(unittest.TestCase):
    def setUp(self):
        self.conn = banco.conectar(":memory:")
        self.id = banco.cadastrar_produto(self.conn, "Coca 2L", "9,50", "Ana", estoque_inicial=10)

    def test_estoque_inicial(self):
        self.assertEqual(banco.estoque_atual(self.conn, self.id), 10)

    def test_entrada_venda_e_saida(self):
        banco.registrar_movimento(self.conn, self.id, banco.ENTRADA, 5, "Ana")
        banco.registrar_movimento(self.conn, self.id, banco.VENDA, 3, "Ana")
        novo = banco.registrar_movimento(
            self.conn, self.id, banco.SAIDA_SEM_VENDA, 2, "Ana", "quebrou"
        )
        self.assertEqual(novo, 10)  # 10 + 5 - 3 - 2

    def test_saida_sem_venda_exige_motivo(self):
        with self.assertRaises(banco.ErroDeRegra):
            banco.registrar_movimento(self.conn, self.id, banco.SAIDA_SEM_VENDA, 1, "Ana", "  ")

    def test_exige_usuario(self):
        with self.assertRaises(banco.ErroDeRegra):
            banco.registrar_movimento(self.conn, self.id, banco.VENDA, 1, "")

    def test_quantidade_invalida(self):
        for ruim in ["abc", "0", "-2", "", "1,5"]:
            with self.assertRaises(banco.ErroDeRegra):
                banco.registrar_movimento(self.conn, self.id, banco.VENDA, ruim, "Ana")

    def test_produto_duplicado(self):
        with self.assertRaises(banco.ErroDeRegra):
            banco.cadastrar_produto(self.conn, "coca 2l", "9,50", "Ana")

    def test_historico_nao_pode_ser_alterado_nem_apagado(self):
        # A trava do banco só dispara quando existe uma linha para mexer,
        # então primeiro criamos uma contagem.
        banco.registrar_contagem(self.conn, self.id, 10, "Ana")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE movimentos SET quantidade = 99")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM movimentos")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE contagens SET contado = 99")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM contagens")

    def test_contagem_sem_diferenca(self):
        r = banco.registrar_contagem(self.conn, self.id, 10, "Ana")
        self.assertEqual(r["diferenca"], 0)
        self.assertEqual(banco.divergencias(self.conn), [])

    def test_contagem_com_falta_gera_divergencia_e_ajuste(self):
        r = banco.registrar_contagem(self.conn, self.id, 7, "Beto")
        self.assertEqual(r, {"esperado": 10, "contado": 7, "diferenca": -3})
        # estoque do sistema volta a bater com a realidade
        self.assertEqual(banco.estoque_atual(self.conn, self.id), 7)
        div = banco.divergencias(self.conn)
        self.assertEqual(len(div), 1)
        self.assertEqual(div[0]["diferenca"], -3)
        self.assertEqual(div[0]["preco"], 950)
        # uma segunda contagem igual não gera nova divergência
        banco.registrar_contagem(self.conn, self.id, 7, "Beto")
        self.assertEqual(len(banco.divergencias(self.conn)), 1)

    def test_dinheiro(self):
        self.assertEqual(banco.reais_para_centavos("4,50"), 450)
        self.assertEqual(banco.reais_para_centavos("4.5"), 450)
        self.assertEqual(banco.reais_para_centavos(""), 0)
        self.assertEqual(banco.centavos_para_texto(1250), "R$ 12,50")
        self.assertEqual(banco.centavos_para_texto(-950), "-R$ 9,50")
        with self.assertRaises(banco.ErroDeRegra):
            banco.reais_para_centavos("abc")

    def test_listar_produtos_mostra_estoque(self):
        banco.registrar_movimento(self.conn, self.id, banco.VENDA, 4, "Ana")
        produtos = banco.listar_produtos(self.conn)
        self.assertEqual(produtos[0]["estoque"], 6)


if __name__ == "__main__":
    unittest.main()
