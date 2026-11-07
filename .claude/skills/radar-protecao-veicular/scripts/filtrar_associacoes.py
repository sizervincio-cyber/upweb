"""Descoberta de candidatas a associacoes de protecao veicular na base CNPJ local.

Nao depende so do CNAE 9499-5/00: combina razao social, nome fantasia, CNAE principal
e secundarios, natureza juridica e dominio de e-mail. Cada estabelecimento recebe
lista de evidencias e score de confianca (0-100), sem nenhum dado inventado.

Uso:
  python filtrar_associacoes.py                       # Brasil inteiro, somente ATIVAS
  python filtrar_associacoes.py --uf GO MT TO
  python filtrar_associacoes.py --incluir-inativas --memoria 4GB

Saidas (em $RADAR_PV_DATA/work):
  candidatos.parquet   1 linha por estabelecimento (matriz e filiais), com evidencias
  dirigentes.parquet   QSA publico (nome, qualificacao, data de entrada); SEM CPF
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regras as R  # noqa: E402
from common import UFS, WORK_DIR, current_competencia, ensure_dirs, get_logger, norm_text, now_iso, raw_path  # noqa: E402

log = get_logger("filtrar_associacoes")

SITUACAO = {"01": "NULA", "02": "ATIVA", "03": "SUSPENSA", "04": "INAPTA", "08": "BAIXADA"}
PORTE = {"00": "NAO INFORMADO", "01": "MICRO EMPRESA", "03": "EMPRESA DE PEQUENO PORTE", "05": "DEMAIS"}


def sql_rx(termos: list[str]) -> str:
    # RE2 (DuckDB) aceita a mesma sintaxe usada aqui; aspas simples escapadas
    return R.regex_any(termos).replace("'", "''")


def build(con: duckdb.DuckDBPyConnection, base: Path, ufs: list[str] | None, inativas: bool) -> pd.DataFrame:
    est = f"'{(base / 'estabelecimentos' / '*.parquet').as_posix()}'"
    emp = f"'{(base / 'empresas' / '*.parquet').as_posix()}'"
    forte = sql_rx(R.FORTE_VEICULAR + R.FORTE_PATRIMONIAL + R.FORTE_CATEGORIA)
    medio = sql_rx(R.MEDIO)
    nat_assoc = ",".join(f"'{k}'" for k in list(R.NATUREZA_ASSOCIACAO) + list(R.NATUREZA_COOPERATIVA))
    norm = "upper(strip_accents(coalesce({c}, '')))"

    log.info("passo 1/3: razao social (empresas)")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE emp_hit AS
        SELECT cnpj_basico FROM read_parquet({emp})
        WHERE regexp_matches({norm.format(c='razao_social')}, '{forte}')
           OR (natureza_juridica IN ({nat_assoc}) AND regexp_matches({norm.format(c='razao_social')}, '{medio}'))
    """)
    log.info("  %s empresas por razao social", con.execute("select count(*) from emp_hit").fetchone()[0])

    log.info("passo 2/3: nome fantasia, CNAE e e-mail (estabelecimentos)")
    cnae9499 = "(cnae_fiscal_principal = '9499500' OR coalesce(cnae_fiscal_secundaria,'') LIKE '%9499500%')"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE est_hit AS
        SELECT DISTINCT cnpj_basico FROM read_parquet({est})
        WHERE regexp_matches({norm.format(c='nome_fantasia')}, '{forte}')
           OR ({cnae9499} AND (regexp_matches({norm.format(c='nome_fantasia')}, '{medio}')
                OR regexp_matches(upper(coalesce(correio_eletronico,'')), '(PROTEC|VEICULAR|MUTU|AUTOPRO|MOTOPRO|PROTEG)')))
    """)
    log.info("  %s empresas por fantasia/CNAE/e-mail", con.execute("select count(*) from est_hit").fetchone()[0])

    con.execute("CREATE OR REPLACE TEMP TABLE alvo AS SELECT cnpj_basico FROM emp_hit UNION SELECT cnpj_basico FROM est_hit")

    log.info("passo 3/3: juntando todos os estabelecimentos das candidatas")
    filtro_sit = "" if inativas else "AND e.situacao_cadastral = '02'"
    df = con.execute(f"""
        SELECT e.cnpj_basico || e.cnpj_ordem || e.cnpj_dv AS cnpj, e.cnpj_basico, e.identificador_matriz_filial,
               m.razao_social, e.nome_fantasia, m.natureza_juridica, nj.descricao AS natureza_juridica_desc,
               m.capital_social, m.porte_empresa, m.qualificacao_responsavel, e.situacao_cadastral,
               e.data_situacao_cadastral, e.data_inicio_atividade, e.cnae_fiscal_principal,
               cn.descricao AS cnae_principal_desc, e.cnae_fiscal_secundaria, e.tipo_logradouro, e.logradouro,
               e.numero, e.complemento, e.bairro, e.cep, e.uf, e.municipio AS municipio_cod,
               mu.descricao AS municipio, e.ddd1 AS ddd_1, e.telefone1 AS telefone_1, e.ddd2 AS ddd_2, e.telefone2 AS telefone_2, e.correio_eletronico
        FROM read_parquet({est}) e
        JOIN alvo a USING (cnpj_basico)
        LEFT JOIN read_parquet({emp}) m USING (cnpj_basico)
        LEFT JOIN read_parquet('{(base / 'naturezas_juridicas' / '*.parquet').as_posix()}') nj ON nj.codigo = m.natureza_juridica
        LEFT JOIN read_parquet('{(base / 'cnaes' / '*.parquet').as_posix()}') cn ON cn.codigo = e.cnae_fiscal_principal
        LEFT JOIN read_parquet('{(base / 'municipios' / '*.parquet').as_posix()}') mu ON mu.codigo = e.municipio
        WHERE 1=1 {filtro_sit}
    """).df()
    log.info("  %s estabelecimentos brutos", len(df))
    # Presenca regional calculada antes do filtro de UF (filiais em outros estados contam)
    grp = df.groupby("cnpj_basico")
    df["qtd_estabelecimentos_ativos"] = grp["cnpj"].transform("count")
    df["ufs_atuacao"] = grp["uf"].transform(lambda s: ",".join(sorted(set(x for x in s if x))))
    if ufs:
        df = df[df["uf"].isin(ufs)].copy()
    return df


def score_row(r: pd.Series) -> tuple[int, list[str], dict]:
    nome = norm_text(f"{r.razao_social or ''} | {r.nome_fantasia or ''}")
    ev: list[str] = []
    flags = {}
    s = 0

    def hits(termos):
        return sorted({m.group(0) for t in termos for m in [re.search(t, nome)] if m})

    fv, fp, md, ng = hits(R.FORTE_VEICULAR), hits(R.FORTE_PATRIMONIAL), hits(R.MEDIO), hits(R.NEGATIVO)
    fc, ip = hits(R.FORTE_CATEGORIA), hits(R.INDICIO_PROTECAO)
    flags.update(forte_veicular=bool(fv), forte_patrimonial=bool(fp), negativo=bool(ng),
                 forte_categoria=bool(fc), indicio_protecao=bool(ip or fv or fp))
    if fv:
        s += R.PESOS["forte_veicular"]; ev.append("nome: termo veicular forte " + "/".join(fv))
    if fp:
        s += R.PESOS["forte_patrimonial"] if not fv else 10; ev.append("nome: termo patrimonial/mutualista " + "/".join(fp))
    combo = (not fv) and bool(hits(R.COMBO_PROTECAO)) and bool(hits(R.COMBO_VEICULO)) and not ng
    flags["combo"] = combo
    if combo:
        s += R.PESOS["combinacao_protecao_veiculo"]; ev.append("nome: protecao/beneficio + contexto veicular")
    if fc and not fv:
        s += R.PESOS["forte_categoria"]; ev.append("nome: associacao de categoria " + "/".join(fc))
    if md:
        k = min(2, len(md)); s += R.PESOS["medio"] * k; ev.append("nome: termos de reforco " + "/".join(md[:4]))
    sec = str(r.cnae_fiscal_secundaria or "")
    if r.cnae_fiscal_principal in R.CNAE_ASSOCIATIVO:
        s += R.PESOS["cnae_principal_9499"]; ev.append("CNAE principal 9499-5/00")
    elif "9499500" in sec:
        s += R.PESOS["cnae_secundario_9499"]; ev.append("CNAE secundario 9499-5/00")
    rel = [c for c in R.CNAE_RELACIONADOS if c == r.cnae_fiscal_principal or c in sec]
    if rel:
        s += R.PESOS["cnae_relacionado"]; ev.append("CNAE relacionado " + ",".join(rel))
    nat = str(r.natureza_juridica or "")
    if nat in R.NATUREZA_ASSOCIACAO:
        s += R.PESOS["natureza_associacao"]; ev.append("natureza juridica 399-9 Associacao Privada")
    elif nat in R.NATUREZA_COOPERATIVA:
        s += R.PESOS["cooperativa"]; ev.append("natureza cooperativa (fora do regime PPM; revisar)")
    else:
        s += R.PESOS["nao_associacao"]; ev.append(f"natureza {nat} nao associativa (possivel administradora/corretora/consultoria)")
    mail = str(r.correio_eletronico or "").upper()
    if re.search(r"PROTEC|VEICULAR|MUTU|AUTOPRO|MOTOPRO|PROTEG", mail):
        s += R.PESOS["email_termo_setor"]; ev.append("e-mail cadastral com termo do setor")
    if ng and not fv:
        s += R.PESOS["negativo"]; ev.append("termo negativo " + "/".join(ng[:3]))
    flags["associacao"] = nat in R.NATUREZA_ASSOCIACAO
    flags["cnae_seguro"] = bool(set(rel) & {"6520100", "6629100", "5229002", "8020001"})
    return max(0, min(100, s)), ev, flags


def classificar_base(score: int, f: dict) -> int:
    """Classe preliminar so com dados cadastrais (classe 1 exige evidencia externa)."""
    if f["negativo"] and not f["forte_veicular"]:
        return 4
    if not f["associacao"]:
        return 4  # nao e associacao: fora do escopo (empresas do ecossistema ficam marcadas em "subtipo")
    if score < 30:
        return 4
    # associacao de categoria (taxistas, caminhoneiros...) sem nenhum indicio de protecao/beneficio
    if not f["indicio_protecao"] and not f["forte_categoria"] and not f["cnae_seguro"]:
        return 4
    if (f["forte_veicular"] or f["combo"]) and f["associacao"] and score >= 60:
        return 2
    if f["forte_patrimonial"] and not f["forte_veicular"] and f["associacao"]:
        return 3
    return 5


def subtipo(classe: int, f: dict, nat: str) -> str:
    if nat in R.NATUREZA_COOPERATIVA:
        return "cooperativa"
    if not f["associacao"] and (f["forte_veicular"] or f["forte_patrimonial"] or f["combo"]):
        return "empresa_ecossistema_pv"  # regional de vendas, consultoria, administradora, corretora
    if f["associacao"]:
        return "associacao"
    return "outra_natureza"


def capital_status(v) -> tuple[float | None, str]:
    if v is None or str(v).strip() == "":
        return None, "ausente_na_base"
    try:
        # formato da Receita: "120000000000,00" (virgula decimal, sem separador de milhar)
        x = float(str(v).strip().replace(".", "").replace(",", "."))
    except ValueError:
        return None, "ausente_na_base"
    return x, ("zero_informado" if x == 0 else "informado")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uf", nargs="+", choices=UFS)
    ap.add_argument("--incluir-inativas", action="store_true")
    ap.add_argument("--memoria", default="3GB", help="limite de memoria do DuckDB (ex.: 2GB em notebooks)")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    ensure_dirs()
    base = raw_path()
    comp = current_competencia()
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.memoria}'; SET threads={a.threads}; SET preserve_insertion_order=false;")
    con.execute(f"SET temp_directory='{(WORK_DIR / 'duckdb_tmp').as_posix()}'")

    df = build(con, base, a.uf, a.incluir_inativas)
    out = df.apply(score_row, axis=1, result_type="expand")
    df["score_cadastral"], df["evidencias"], flags = out[0], out[1], out[2]
    df["classe_preliminar"] = [classificar_base(s, f) for s, f in zip(df["score_cadastral"], flags)]
    df["subtipo"] = [subtipo(c, f, str(n)) for c, f, n in zip(df["classe_preliminar"], flags, df["natureza_juridica"])]
    df["evidencias"] = df["evidencias"].apply(lambda x: json.dumps(x, ensure_ascii=False))
    cap = df["capital_social"].apply(capital_status)
    df["capital_social_valor"] = [c[0] for c in cap]
    df["capital_social_status"] = [c[1] for c in cap]
    df["situacao_cadastral_desc"] = df["situacao_cadastral"].map(SITUACAO)
    df["porte_desc"] = df["porte_empresa"].map(PORTE)
    df["matriz_filial"] = df["identificador_matriz_filial"].map({"1": "MATRIZ", "2": "FILIAL"})
    df["competencia_cnpj"] = comp
    df["fonte_cadastral"] = f"Receita Federal - CNPJ dados abertos, competencia {comp}"
    df["coletado_em"] = now_iso()
    df = df.drop_duplicates(subset=["cnpj"])  # deduplicacao por CNPJ completo
    df.to_parquet(WORK_DIR / "candidatos.parquet", index=False)

    # Dirigentes publicos (QSA). Associacoes frequentemente NAO tem QSA na base aberta.
    bas = sorted(df["cnpj_basico"].unique())
    con.register("bas", pd.DataFrame({"cnpj_basico": bas}))
    soc = con.execute(f"""
        SELECT s.cnpj_basico, s.nome_socio AS nome, s.qualificacao_socio AS qualificacao_cod,
               q.descricao AS qualificacao, s.data_entrada_sociedade AS data_entrada,
               s.identificador_socio AS tipo
        FROM read_parquet('{(base / 'socios' / '*.parquet').as_posix()}') s
        JOIN bas USING (cnpj_basico)
        LEFT JOIN read_parquet('{(base / 'qualificacoes_socios' / '*.parquet').as_posix()}') q ON q.codigo = s.qualificacao_socio
    """).df()  # CPF (mesmo mascarado), faixa etaria e representante de menor NAO sao coletados (minimizacao LGPD)
    soc["fonte"] = f"Receita Federal - QSA, competencia {comp}"
    soc.to_parquet(WORK_DIR / "dirigentes.parquet", index=False)

    resumo = df.groupby("classe_preliminar").size().to_dict()
    log.info("candidatos: %s estabelecimentos | por classe: %s | dirigentes QSA: %s linhas",
             len(df), resumo, len(soc))
    print(json.dumps({"competencia": comp, "estabelecimentos": len(df), "por_classe": resumo,
                      "dirigentes_qsa": len(soc)}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
