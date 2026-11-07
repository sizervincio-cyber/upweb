"""Testes das regras de classificacao e utilitarios. Rodam SEM baixar a base CNPJ.

  python -m unittest discover -s tests -v      (a partir da pasta da Skill)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from common import cnpj_valido, fmt_cnpj, norm_text  # noqa: E402
from enriquecer_contatos import dominio_email  # noqa: E402
from filtrar_associacoes import capital_status, classificar_base, score_row  # noqa: E402
from validar_susep import status_de_texto  # noqa: E402


def row(razao, fantasia=None, nat="3999", cnae="9499500", sec=None, mail=None):
    return pd.Series({"razao_social": razao, "nome_fantasia": fantasia, "natureza_juridica": nat,
                      "cnae_fiscal_principal": cnae, "cnae_fiscal_secundaria": sec, "correio_eletronico": mail})


def classe(*a, **k):
    s, _, f = score_row(row(*a, **k))
    return classificar_base(s, f)


class TestClassificacao(unittest.TestCase):
    # ---- positivos (classe 2: provavel protecao veicular)
    def test_positivos_veiculares(self):
        for nome in ["ASSOCIACAO DE PROTECAO VEICULAR BLINTEC", "APV BRASIL - ASSOCIACAO DE PROTECAO A VEICULOS",
                     "JP ASSOCIACAO DE SOCORRO MUTUO A MOTOCICLISTAS", "PROTEGE CAR PROTECAO MUTUALISTA",
                     "ASSOCIACAO DE PROTECAO E BENEFICIO AO PROPRIETARIO DE VEICULOS PROTEGE BRASIL"]:
            with self.subTest(nome=nome):
                self.assertEqual(classe(nome), 2)

    def test_cnae_diferente_nao_exclui(self):
        # CNAE 9430-8/00 (defesa de direitos) ainda e encontrado pelo nome
        self.assertEqual(classe("FORZA - ASSOCIACAO DE BENEFICIOS E PROTECAO VEICULAR", cnae="9430800"), 2)

    def test_patrimonial_sem_veicular(self):
        self.assertEqual(classe("STRONG PROTECAO PATRIMONIAL MUTUALISTA"), 3)

    # ---- negativos (classe 4)
    def test_negativos(self):
        for nome in ["ASSOCIACAO DE PROTECAO AOS ANIMAIS DE PITANGA", "ASSOCIACAO DE PROTECAO E BEM-ESTAR ANIMAL AMIGO BICHO",
                     "ASSOCIACAO DOS TAXISTAS DO LEBLON", "MOTO CLUBE MOICANA", "CLUBE DE VEICULOS ANTIGOS DE PATO BRANCO",
                     "ASSOCIACAO DE PROTECAO AOS CONDENADOS APAC", "SOCIEDADE DE PROTECAO E ASSISTENCIA A INFANCIA",
                     "ASSOCIACAO DE TRANSPORTE ALTERNATIVO MUNICIPAL COMPLEMENTAR DE PORTO SEGURO"]:
            with self.subTest(nome=nome):
                self.assertEqual(classe(nome), 4)

    def test_empresa_ltda_fora_do_escopo_de_associacoes(self):
        self.assertEqual(classe("AVALANCHE PROTECAO VEICULAR LTDA", nat="2062", cnae="8299799"), 4)

    def test_cooperativa_fora(self):
        self.assertEqual(classe("COOPMOTAM - COOPERATIVA DE MOTOTAXISTAS", nat="2143"), 4)

    def test_termo_isolado_nao_basta(self):
        # "clube" + "beneficios" sem segmento: pendente, nunca classe 2
        self.assertIn(classe("ZEN CLUBE DE BENEFICIOS"), (5,))

    def test_score_limites(self):
        s, ev, _ = score_row(row("ASSOCIACAO MUTUALISTA DE AUTOGESTAO E BENEFICIOS PARA PROTECAO VEICULAR"))
        self.assertTrue(0 <= s <= 100)
        self.assertTrue(any("9499" in e for e in ev))


class TestUtilitarios(unittest.TestCase):
    def test_cnpj(self):
        self.assertTrue(cnpj_valido("00.000.000/0001-91"))
        self.assertFalse(cnpj_valido("11.111.111/1111-11"))
        self.assertEqual(fmt_cnpj("54801882000113"), "54.801.882/0001-13")

    def test_norm(self):
        self.assertEqual(norm_text("  Proteção   Veicular "), "PROTECAO VEICULAR")

    def test_capital_social(self):
        self.assertEqual(capital_status("120000000000,00"), (120000000000.0, "informado"))
        self.assertEqual(capital_status("0,00"), (0.0, "zero_informado"))
        self.assertEqual(capital_status(None), (None, "ausente_na_base"))

    def test_dominio_email(self):
        self.assertIsNone(dominio_email("fulano@gmail.com"))
        self.assertIsNone(dominio_email("x@consultacontabil.com.br"))  # contador nao e site da entidade
        self.assertEqual(dominio_email("contato@maxcar.org.br"), "maxcar.org.br")

    def test_susep_status(self):
        self.assertEqual(status_de_texto("Situacao: Em regularização junto à Susep"), "cadastrada_em_regularizacao")
        self.assertEqual(status_de_texto("Não consta cadastro para o CNPJ informado"), "nao_consta_oficial")
        self.assertEqual(status_de_texto("documento ilegivel"), "nao_foi_possivel")


class TestAmostraValidacao(unittest.TestCase):
    """Gabarito rotulado: nenhum 'positivo' pode cair em classe 4 e nenhum 'negativo' em classe 2."""

    def test_gabarito(self):
        f = Path(__file__).with_name("amostra_validacao.csv")
        g = pd.read_csv(f, dtype=str)
        for r in g.itertuples():
            c = classe(r.razao_social, None if pd.isna(r.nome_fantasia) else r.nome_fantasia)
            with self.subTest(nome=r.razao_social, rotulo=r.rotulo_revisao):
                if r.rotulo_revisao == "positivo":
                    self.assertIn(c, (1, 2))
                elif r.rotulo_revisao == "negativo":
                    self.assertNotIn(c, (1, 2))


if __name__ == "__main__":
    unittest.main()
