"""Consulta rapida sobre a base consolidada (usada pelo Claude para responder em linguagem natural).

Exemplos:
  python consultar.py --uf GO MT TO --classes 1 2
  python consultar.py --municipio GOIANIA ANAPOLIS --com-contato
  python consultar.py --nome "MAXCAR"                       # ficha completa + dirigentes
  python consultar.py --susep                               # resumo da situacao SUSEP
  python consultar.py --sql "select uf, count(*) from base where classe in (1,2) group by 1 order by 2 desc"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK_DIR, norm_text  # noqa: E402

COLS_LISTA = ["cnpj_formatado", "matriz_filial", "razao_social", "nome_fantasia", "municipio", "uf", "classe",
              "score_confianca", "contato_status", "telefone_institucional_receita", "whatsapp_comercial_confirmado",
              "site_institucional", "status_susep", "prioridade_comercial"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uf", nargs="+")
    ap.add_argument("--municipio", nargs="+")
    ap.add_argument("--classes", nargs="+", type=int, default=[1, 2, 3, 5])
    ap.add_argument("--com-contato", action="store_true")
    ap.add_argument("--nome")
    ap.add_argument("--susep", action="store_true")
    ap.add_argument("--sql", help="SQL DuckDB; a tabela se chama 'base'")
    ap.add_argument("--limite", type=int, default=50)
    a = ap.parse_args()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 70)
    base = pd.read_parquet(WORK_DIR / "base_final.parquet")
    if a.sql:
        con = duckdb.connect()
        con.register("base", base)
        print(con.execute(a.sql).df().to_string(index=False))
        return
    if a.nome:
        n = norm_text(a.nome)
        hit = base[base["razao_social"].fillna("").map(norm_text).str.contains(n, regex=False) |
                   base["nome_fantasia"].fillna("").map(norm_text).str.contains(n, regex=False)]
        for r in hit.head(a.limite).to_dict("records"):
            print("=" * 100)
            for k in ["cnpj_formatado", "matriz_filial", "razao_social", "nome_fantasia", "classe_desc", "score_confianca",
                      "evidencias", "endereco_empresarial", "bairro", "municipio", "uf", "cep", "dirigentes_publicos",
                      "telefone_institucional_receita", "email_cadastral", "email_cadastral_tipo", "site_institucional",
                      "contato_status", "whatsapp_comercial_confirmado", "telefones_site", "emails_site",
                      "status_susep_desc", "capital_social_valor", "capital_social_status", "data_abertura",
                      "competencia_cnpj", "fontes"]:
                print(f"{k:32s} {r.get(k)}")
        print(f"\n{len(hit)} estabelecimento(s) encontrado(s)")
        return
    df = base[base["classe"].isin(a.classes)]
    if a.uf:
        df = df[df["uf"].isin([u.upper() for u in a.uf])]
    if a.municipio:
        alvo = {norm_text(m) for m in a.municipio}
        df = df[df["municipio"].fillna("").map(norm_text).isin(alvo)]
    if a.com_contato:
        df = df[df["contato_status"].isin(["confirmado_site_cita_cnpj", "provavel_site_dominio_cadastral"])]
    if a.susep:
        print(df.drop_duplicates("cnpj_basico").groupby(["status_susep", "classe"]).size().unstack(fill_value=0))
        return
    df = df.sort_values(["prioridade_comercial_score", "score_confianca"], ascending=False)
    print(df[COLS_LISTA].head(a.limite).to_string(index=False))
    print(f"\n{len(df)} estabelecimento(s) | {df['cnpj_basico'].nunique()} entidade(s)")


if __name__ == "__main__":
    main()
