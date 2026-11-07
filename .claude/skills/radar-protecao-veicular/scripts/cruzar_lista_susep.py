"""Cruza uma lista de CNPJs da SUSEP (ex.: extraida de video com extrair_video_susep.py) com a base.

Para cada CNPJ da lista:
  - confere na base oficial do CNPJ (Receita): razao social, CNAE principal e secundarios (com descricao),
    endereco, situacao cadastral, natureza juridica, capital social e dirigentes (QSA, sem CPF);
  - diz se ja esta na SUA lista (classes 1, 2, 3 ou 5), se foi descartada pela regra (classe 4, com o motivo)
    ou se ficou fora da descoberta (nao capturada);
  - opcionalmente registra a evidencia SUSEP na base (--importar-susep).

Uso:
  python cruzar_lista_susep.py --lista gravacao_cnpjs_susep.csv
  python cruzar_lista_susep.py --lista gravacao_cnpjs_susep.csv --importar-susep --fonte "video consulta SUSEP 07/11/2026"

Saida: $RADAR_PV_DATA/out/cruzamento_susep.xlsx (+ .csv)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT_DIR, WORK_DIR, cnpj_valido, current_competencia, fmt_cnpj, get_logger, now_iso, only_digits, raw_path  # noqa: E402
from validar_susep import BASE_LEGAL, status_de_texto  # noqa: E402

log = get_logger("cruzar_lista_susep")
SIT = {"01": "NULA", "02": "ATIVA", "03": "SUSPENSA", "04": "INAPTA", "08": "BAIXADA"}


def ler_lista(p: Path) -> pd.DataFrame:
    if p.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(p, dtype=str)
    else:
        df = pd.read_csv(p, dtype=str, sep=None, engine="python", encoding="utf-8-sig")
    col = next((c for c in df.columns if "cnpj" in c.lower()), df.columns[0])
    df["cnpj"] = df[col].map(only_digits).str.zfill(14)
    df = df[df["cnpj"].str.len() == 14].drop_duplicates("cnpj")
    df["cnpj_valido"] = df["cnpj"].map(cnpj_valido)
    keep = ["cnpj", "cnpj_valido"] + [c for c in df.columns if c in ("nome_lido_no_video", "situacao_lida_no_video", "situacao")]
    return df[keep]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lista", required=True)
    ap.add_argument("--importar-susep", action="store_true", help="registra os CNPJs como cadastrados na SUSEP")
    ap.add_argument("--fonte", default="lista SUSEP extraida de gravacao de tela da consulta oficial")
    ap.add_argument("--nome", default="cruzamento_susep")
    a = ap.parse_args()

    lista = ler_lista(Path(a.lista))
    log.info("lista: %d CNPJs (%d com digito verificador valido)", len(lista), int(lista["cnpj_valido"].sum()))
    base = raw_path()
    comp = current_competencia()
    con = duckdb.connect()
    con.register("lista", lista[["cnpj"]].assign(cnpj_basico=lista["cnpj"].str[:8]))
    q = lambda t: f"read_parquet('{(base / t / '*.parquet').as_posix()}')"  # noqa: E731

    log.info("buscando na base CNPJ %s", comp)
    est = con.execute(f"""
        SELECT l.cnpj, e.cnpj_basico, e.identificador_matriz_filial, e.nome_fantasia, e.situacao_cadastral,
               e.data_situacao_cadastral, e.data_inicio_atividade, e.cnae_fiscal_principal, cn.descricao AS cnae_principal_desc,
               e.cnae_fiscal_secundaria, e.tipo_logradouro, e.logradouro, e.numero, e.complemento, e.bairro, e.cep, e.uf,
               mu.descricao AS municipio, e.ddd1, e.telefone1, e.ddd2, e.telefone2, e.correio_eletronico,
               m.razao_social, m.natureza_juridica, nj.descricao AS natureza_desc, m.capital_social, m.porte_empresa
        FROM lista l
        LEFT JOIN {q('estabelecimentos')} e ON e.cnpj_basico || e.cnpj_ordem || e.cnpj_dv = l.cnpj
        LEFT JOIN {q('empresas')} m ON m.cnpj_basico = l.cnpj_basico
        LEFT JOIN {q('cnaes')} cn ON cn.codigo = e.cnae_fiscal_principal
        LEFT JOIN {q('municipios')} mu ON mu.codigo = e.municipio
        LEFT JOIN {q('naturezas_juridicas')} nj ON nj.codigo = m.natureza_juridica
    """).df()
    cnaes = dict(con.execute(f"SELECT codigo, descricao FROM {q('cnaes')}").fetchall())
    soc = con.execute(f"""
        SELECT s.cnpj_basico, s.nome_socio AS nome, qq.descricao AS cargo, s.data_entrada_sociedade AS desde
        FROM {q('socios')} s JOIN (SELECT DISTINCT cnpj_basico FROM lista) l USING (cnpj_basico)
        LEFT JOIN {q('qualificacoes_socios')} qq ON qq.codigo = s.qualificacao_socio
    """).df()  # sem CPF, sem faixa etaria (minimizacao LGPD)

    def sec_desc(v):
        if not v or pd.isna(v):
            return None
        return "; ".join(f"{c} {cnaes.get(c, '?')}" for c in str(v).split(",") if c)

    soc["txt"] = soc["nome"].str.title() + " (" + soc["cargo"].fillna("?") + \
        soc["desde"].fillna("").map(lambda x: f", desde {x[:4]}-{x[4:6]}-{x[6:]}" if len(x) == 8 else "") + ")"
    dirig = soc.groupby("cnpj_basico")["txt"].agg("; ".join).rename("dirigentes_qsa")
    est["cnpj_basico"] = est["cnpj"].str[:8]  # raiz vem da lista (mesmo quando o CNPJ nao existe na base)
    est = est.merge(dirig, left_on="cnpj_basico", right_index=True, how="left")

    # Situacao na minha lista
    cand = pd.read_parquet(WORK_DIR / "base_final.parquet",
                           columns=["cnpj_basico", "classe", "classe_desc", "score_confianca", "evidencias", "subtipo"]) \
        .sort_values("classe").drop_duplicates("cnpj_basico")
    df = lista.merge(est, on="cnpj", how="left").merge(cand, on="cnpj_basico", how="left")

    def status_lista(r):
        if pd.isna(r.situacao_cadastral):  # o CNPJ completo (estabelecimento) nao existe na base
            return "nao_encontrado_na_base_cnpj"
        if pd.isna(r.classe):
            return "fora_da_lista_nao_capturado"
        if int(r.classe) == 4:
            return "fora_da_lista_descartado_pela_regra"
        return "ja_na_lista"
    df["status_na_minha_lista"] = df.apply(status_lista, axis=1)
    df["cnpj_formatado"] = df["cnpj"].map(fmt_cnpj)
    df["situacao_cadastral_receita"] = df["situacao_cadastral"].map(SIT)
    df["cnaes_secundarios"] = df["cnae_fiscal_secundaria"].map(sec_desc)
    df["endereco"] = (df["tipo_logradouro"].fillna("") + " " + df["logradouro"].fillna("") + ", " + df["numero"].fillna("S/N") +
                      (" " + df["complemento"].fillna("")).str.rstrip() + " - " + df["bairro"].fillna("")).str.strip(" ,-")
    cap = df["capital_social"].fillna("").astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["capital_social_valor"] = pd.to_numeric(cap, errors="coerce")
    df["capital_social_status"] = df["capital_social_valor"].map(
        lambda v: "ausente_na_base" if pd.isna(v) else ("zero_informado" if v == 0 else "informado"))
    df["telefones_receita"] = [
        "; ".join(f"({d}) {t}" for d, t in ((a1, b1), (a2, b2)) if t and not pd.isna(t) and str(t).strip("0"))
        for a1, b1, a2, b2 in zip(df["ddd1"], df["telefone1"], df["ddd2"], df["telefone2"])]
    df["matriz_filial"] = df["identificador_matriz_filial"].map({"1": "MATRIZ", "2": "FILIAL"})
    df["motivo_descarte"] = df["evidencias"].where(df["status_na_minha_lista"].eq("fora_da_lista_descartado_pela_regra"))
    df["alerta"] = None
    df.loc[df["cnpj_valido"].eq(False), "alerta"] = "CNPJ com digito verificador invalido (erro de leitura?)"
    df.loc[df["situacao_cadastral"].notna() & df["situacao_cadastral"].ne("02"), "alerta"] = "Situacao cadastral nao ATIVA na Receita"
    nao_achou = df["situacao_cadastral"].isna()
    df.loc[nao_achou & df["razao_social"].notna(), "alerta"] = \
        "CNPJ completo nao existe na base (a raiz pertence a outro cadastro): provavel erro de leitura, conferir no video"
    df.loc[nao_achou, [c for c in ("razao_social", "natureza_desc", "capital_social_valor", "dirigentes_qsa") if c in df]] = None
    df["fonte"] = f"Lista SUSEP: {a.fonte} | Receita Federal CNPJ dados abertos, competencia {comp}"
    df["conferido_em"] = now_iso()

    cols = {"cnpj_formatado": "CNPJ", "status_na_minha_lista": "Status na minha lista", "razao_social": "Razao social (Receita)",
            "nome_fantasia": "Nome fantasia", "nome_lido_no_video": "Nome lido no video", "situacao_lida_no_video": "Situacao lida (SUSEP)",
            "matriz_filial": "Matriz/Filial", "situacao_cadastral_receita": "Situacao cadastral (Receita)",
            "natureza_desc": "Natureza juridica", "cnae_fiscal_principal": "CNAE principal", "cnae_principal_desc": "CNAE principal (descricao)",
            "cnaes_secundarios": "CNAEs secundarios", "endereco": "Endereco", "municipio": "Municipio", "uf": "UF", "cep": "CEP",
            "capital_social_valor": "Capital social (R$)", "capital_social_status": "Status capital", "dirigentes_qsa": "Dirigentes (QSA)",
            "telefones_receita": "Telefones (Receita)", "correio_eletronico": "E-mail (Receita)", "data_inicio_atividade": "Inicio atividade",
            "classe_desc": "Classe na minha lista", "score_confianca": "Score", "motivo_descarte": "Motivo do descarte",
            "alerta": "Alerta", "fonte": "Fonte", "conferido_em": "Conferido em"}
    out = df[[c for c in cols if c in df.columns]].rename(columns=cols)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    xlsx = OUT_DIR / f"{a.nome}.xlsx"
    resumo = df["status_na_minha_lista"].value_counts().rename_axis("status").reset_index(name="cnpjs")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        resumo.to_excel(w, sheet_name="Resumo", index=False)
        for nome, filt in [("Ja na lista", "ja_na_lista"), ("Fora - descartadas", "fora_da_lista_descartado_pela_regra"),
                           ("Fora - nao capturadas", "fora_da_lista_nao_capturado"), ("Nao encontradas", "nao_encontrado_na_base_cnpj")]:
            out[df["status_na_minha_lista"].eq(filt).values].to_excel(w, sheet_name=nome, index=False)
        soc_out = soc[soc["cnpj_basico"].isin(df["cnpj"].str[:8])].merge(
            df[["cnpj", "razao_social"]].assign(cnpj_basico=df["cnpj"].str[:8]), on="cnpj_basico")
        soc_out.assign(cnpj=soc_out["cnpj"].map(fmt_cnpj))[["cnpj", "razao_social", "nome", "cargo", "desde"]] \
            .to_excel(w, sheet_name="Dirigentes", index=False)
        for ws in w.book.worksheets:
            ws.auto_filter.ref = ws.dimensions
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(50, max(10, max(len(str(c.value or "")) for c in col[:60]) + 2))
    out.to_csv(OUT_DIR / f"{a.nome}.csv", index=False, sep=";", encoding="utf-8-sig")

    if a.importar_susep:
        sit = df.get("situacao_lida_no_video", pd.Series([""] * len(df))).fillna("")
        reg = pd.DataFrame({
            "cnpj": df["cnpj"], "cnpj_basico": df["cnpj"].str[:8],
            "status_susep": [status_de_texto(s) if s and status_de_texto(s) != "nao_foi_possivel" else "cadastrada_em_regularizacao" for s in sit],
            "evidencia_susep": a.fonte, "data_consulta_susep": date.today().isoformat(),
            "obs_susep": "CNPJ consta na lista da consulta oficial SUSEP (extraido por OCR com digito verificador valido)",
            "base_legal_susep": BASE_LEGAL, "importado_em": now_iso()})
        reg = reg[df["cnpj_valido"].values]
        p = WORK_DIR / "susep.parquet"
        if p.exists():
            old = pd.read_parquet(p)
            reg = pd.concat([old[~old["cnpj_basico"].isin(reg["cnpj_basico"])], reg], ignore_index=True)
        reg.to_parquet(p, index=False)
        log.info("SUSEP: %d registros na base de evidencias. Rode normalizar_dados.py para refletir nas classes.", len(reg))

    print(json.dumps({"lista": len(lista), "por_status": resumo.set_index("status")["cnpjs"].to_dict(),
                      "saida": str(xlsx)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
