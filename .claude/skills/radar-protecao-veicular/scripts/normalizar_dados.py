"""Consolida candidatos + dirigentes + sites + SUSEP em uma ficha cadastral unica.

Gera $RADAR_PV_DATA/work/base_final.parquet (1 linha por estabelecimento) com:
classe final (1-5), score de confianca, status de contato, situacao SUSEP,
prioridade comercial (baseada SOMENTE em evidencias) e trilha de auditoria.

Uso: python normalizar_dados.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regras as R  # noqa: E402
from common import WORK_DIR, fmt_cnpj, get_logger, norm_text, now_iso  # noqa: E402
from enriquecer_contatos import DOMINIO_TERCEIRO, dominio_email  # noqa: E402

log = get_logger("normalizar_dados")


def _j(v) -> list:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        return []
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return []


def fone(ddd, tel) -> str | None:
    if not tel or pd.isna(tel) or not str(tel).strip():
        return None
    t = str(tel).strip()
    if not t.strip("0"):
        return None  # placeholder "00000000" da Receita
    t = f"{t[:-4]}-{t[-4:]}" if len(t) >= 8 else t
    return f"({str(ddd).strip()}) {t}" if ddd and not pd.isna(ddd) else t


def tipo_email(mail) -> str:
    if not mail or pd.isna(mail) or "@" not in str(mail):
        return "ausente"
    d = str(mail).split("@")[-1].strip().upper()
    if d in R.FREE_MAIL:
        return "gratuito"
    if DOMINIO_TERCEIRO.search(d):
        return "provavel_terceiro_contador"
    return "dominio_proprio"


def dirigentes_txt(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["cnpj_basico", "dirigentes_publicos", "qtd_dirigentes_qsa"])
    df = df.copy()
    dt = df["data_entrada"].fillna("").astype(str)
    df["d"] = df["nome"].str.title() + " (" + df["qualificacao"].fillna("qualificacao nao informada") + \
        dt.map(lambda x: f", desde {x[:4]}-{x[4:6]}-{x[6:]}" if len(x) == 8 else "") + ")"
    g = df.groupby("cnpj_basico").agg(dirigentes_publicos=("d", lambda s: "; ".join(s)),
                                      qtd_dirigentes_qsa=("d", "count")).reset_index()
    return g


def main() -> None:
    c = pd.read_parquet(WORK_DIR / "candidatos.parquet")
    dirig = pd.read_parquet(WORK_DIR / "dirigentes.parquet") if (WORK_DIR / "dirigentes.parquet").exists() else pd.DataFrame()
    enr = pd.read_parquet(WORK_DIR / "enriquecimento.parquet") if (WORK_DIR / "enriquecimento.parquet").exists() else pd.DataFrame(columns=["cnpj"])
    sus = pd.read_parquet(WORK_DIR / "susep.parquet") if (WORK_DIR / "susep.parquet").exists() else pd.DataFrame(columns=["cnpj_basico"])

    df = c.merge(dirigentes_txt(dirig), on="cnpj_basico", how="left")
    # enriquecimento e feito na matriz: propaga para filiais da mesma raiz
    if not enr.empty:
        enr = enr.copy()
        enr["cnpj_basico"] = enr["cnpj"].str[:8]
        df = df.merge(enr.drop(columns=["cnpj"]).drop_duplicates("cnpj_basico"), on="cnpj_basico", how="left")
    if not sus.empty:
        df = df.merge(sus.drop(columns=["cnpj"]).drop_duplicates("cnpj_basico", keep="last"), on="cnpj_basico", how="left")
    for col, default in [("site_status", None), ("site_cita_cnpj", False), ("status_susep", "nao_verificado"),
                         ("site", None), ("site_origem", None)]:
        if col not in df:
            df[col] = default
    df["status_susep"] = df["status_susep"].fillna("nao_verificado")
    df["site_cita_cnpj"] = df["site_cita_cnpj"].fillna(False).astype(bool)
    site_ok = df["site_status"].eq("200")
    for s in list(R.SINAIS_SITE):
        col = f"sinal_{s}"
        df[col] = df[col].fillna(False).astype(bool) if col in df else False
    df.loc[~site_ok, [f"sinal_{s}" for s in R.SINAIS_SITE]] = False

    # ---------------- contatos
    df["telefone_institucional_receita"] = [
        "; ".join(x for x in (fone(a, b), fone(c_, d)) if x) or None
        for a, b, c_, d in zip(df["ddd_1"], df["telefone_1"], df["ddd_2"], df["telefone_2"])]
    df["email_cadastral_tipo"] = df["correio_eletronico"].map(tipo_email)
    df["email_cadastral"] = df["correio_eletronico"].str.lower()
    conf = site_ok & df["site_cita_cnpj"]
    prov = site_ok & ~df["site_cita_cnpj"] & df["site_origem"].eq("dominio_do_email_cadastral")
    df["contato_status"] = "somente_declarado_receita"
    df.loc[df["telefone_institucional_receita"].isna() & df["email_cadastral"].isna(), "contato_status"] = "sem_contato_publico"
    df.loc[prov, "contato_status"] = "provavel_site_dominio_cadastral"
    df.loc[conf, "contato_status"] = "confirmado_site_cita_cnpj"
    wa = df.get("site_whatsapp", pd.Series([None] * len(df))).map(_j)
    df["whatsapp_comercial_confirmado"] = [", ".join("+" + w for w in x) if ok and x else None for x, ok in zip(wa, conf)]
    df["whatsapp_site_nao_confirmado"] = [", ".join("+" + w for w in x) if (not ok) and x else None for x, ok in zip(wa, conf)]
    df["telefones_site"] = df.get("site_telefones", pd.Series([None] * len(df))).map(lambda v: "; ".join(_j(v)) or None)
    df["emails_site"] = df.get("site_emails", pd.Series([None] * len(df))).map(lambda v: "; ".join(_j(v)) or None)
    df["redes_sociais"] = df.get("site_redes_sociais", pd.Series([None] * len(df))).map(lambda v: "; ".join(_j(v)) or None)
    df["indicios_software_gestao"] = df.get("indicios_software", pd.Series([None] * len(df))).map(
        lambda v: ", ".join(x for x in _j(v) if x not in ("wordpress", "wix", "rd_station")) or None)
    df["site_institucional"] = df["site"].where(site_ok)
    # Site candidato: dominio proprio do e-mail cadastral (nao gratuito, nao do contador). Nao verificado ate ser lido.
    dom_site = df["correio_eletronico"].map(dominio_email)
    df["site_candidato"] = ("https://" + dom_site).where(dom_site.notna())
    tentou = df["site_status"].notna() & ~site_ok
    df["site_situacao"] = "sem_site_identificado"
    df.loc[df["site_candidato"].notna(), "site_situacao"] = "candidato_nao_verificado"
    df.loc[tentou & df["site_status"].astype(str).str.startswith("bloqueado"), "site_situacao"] = "bloqueia_robos"
    df.loc[tentou & ~df["site_status"].astype(str).str.startswith("bloqueado"), "site_situacao"] = "inacessivel_na_coleta"
    df.loc[prov, "site_situacao"] = "validado_dominio_cadastral"
    df.loc[conf, "site_situacao"] = "validado_cita_cnpj"
    # e-mail compartilhado por varias associacoes = indicio de gestao centralizada (grupo/administradora)
    dom = df["email_cadastral"].str.split("@").str[-1]
    comp = df[df["email_cadastral_tipo"].eq("dominio_proprio")].groupby(dom)["cnpj_basico"].nunique()
    df["email_compartilhado_qtd_entidades"] = dom.map(comp).where(df["email_cadastral_tipo"].eq("dominio_proprio"))

    # ---------------- classificacao final
    sus_cad = df["status_susep"].isin(["cadastrada_em_regularizacao", "regular"])
    site_veic = df["sinal_protecao_veicular"] & (conf | prov)
    site_patr = df["sinal_protecao_patrimonial"] & (conf | prov)
    score = df["score_cadastral"].astype(int).copy()
    score += (site_veic | site_patr).astype(int) * R.EXTERNO["site_confirma_setor"]
    score += conf.astype(int) * R.EXTERNO["site_confirma_cnpj"]
    score += sus_cad.astype(int) * R.EXTERNO["susep_cadastrada"]
    df["score_confianca"] = score.clip(0, 100)
    cl = df["classe_preliminar"].copy()
    pre = df["classe_preliminar"]
    elegivel = pre.isin([2, 3, 5]) & df["subtipo"].eq("associacao")
    cl[elegivel & pre.eq(2) & (sus_cad | (conf & (site_veic | site_patr)))] = 1
    cl[elegivel & pre.isin([3, 5]) & conf & site_veic] = 1
    cl[elegivel & pre.eq(5) & ~(conf & site_veic) & (site_veic | sus_cad)] = 2
    cl[elegivel & pre.eq(5) & ~site_veic & ~sus_cad & site_patr] = 3
    # Segmento veicular (carro/caminhao/moto) por nome, fantasia e dominio do e-mail
    txt = (df["razao_social"].fillna("") + " " + df["nome_fantasia"].fillna("") + " " +
           df["correio_eletronico"].fillna("").str.split("@").str[-1]).map(norm_text)
    segs = txt.map(R.segmento_veicular)
    df["segmento_veicular"] = segs.map(lambda x: ", ".join(x) if x else None)
    tem_seg = segs.map(bool) | site_veic
    outro = txt.str.contains(R.OUTRO_RAMO, regex=True) & ~tem_seg
    # Evidencia SUSEP (cadastro oficial) em ASSOCIACAO: PPM confirmada; veicular se ha segmento
    assoc = df["natureza_juridica"].eq("3999")
    cl[assoc & sus_cad & tem_seg] = 1
    cl[assoc & sus_cad & ~tem_seg & ~outro] = 3
    df["outro_ramo"] = outro
    # Classificacao e da ENTIDADE (raiz do CNPJ): filiais herdam a melhor evidencia do grupo
    rank = {1: 0, 2: 1, 3: 2, 5: 3, 4: 4}
    inv = {v: k for k, v in rank.items()}
    df["_r"] = cl.map(rank)
    df["classe"] = df.groupby("cnpj_basico")["_r"].transform("min").map(inv)
    df["score_confianca"] = df.groupby("cnpj_basico")["score_confianca"].transform("max")
    df = df.drop(columns="_r")
    df["classe_desc"] = df["classe"].map(R.CLASSES)
    df["status_susep_desc"] = df["status_susep"].map(R.SUSEP_STATUS)
    df["alerta_susep"] = df["status_susep"].eq("nao_consta_oficial").map(
        {True: "Certidao oficial negativa: requer analise juridica antes de qualquer conclusao", False: None})

    # ---------------- prioridade comercial (somente evidencias)
    p = pd.Series(0, index=df.index)
    canal_conf = conf & (df["whatsapp_comercial_confirmado"].notna() | df["telefones_site"].notna() | df["emails_site"].notna())
    p += canal_conf * 25 + (prov & ~canal_conf) * 12
    p += site_ok * 10
    n = df["qtd_estabelecimentos_ativos"].fillna(1)
    p += (n >= 2) * 10 + (n >= 5) * 5
    p += (df["ufs_atuacao"].fillna("").str.count(",") >= 1) * 10
    p += df["sinal_assistencia_24h"] * 5 + df["sinal_vistoria"] * 5 + df["sinal_sinistro"] * 10 + \
        df["sinal_oficinas"] * 5 + df["sinal_area_associado"] * 5
    p += sus_cad * 10
    df["prioridade_comercial_score"] = p.clip(0, 100).where(df["classe"].isin([1, 2, 3, 5]), 0)
    df["prioridade_comercial"] = pd.cut(df["prioridade_comercial_score"], [-1, 34, 59, 100], labels=["C", "B", "A"]).astype(str)
    df["oportunidade_gestao_digital"] = [
        "sinais de operacao de sinistros/assistencia sem software identificado" if (s and not soft)
        else ("ja usa software de gestao identificado: " + soft if soft else None)
        for s, soft in zip(df["sinal_sinistro"] | df["sinal_vistoria"] | df["sinal_assistencia_24h"],
                           df["indicios_software_gestao"].fillna(""))]

    # ---------------- ficha
    df["cnpj_formatado"] = df["cnpj"].map(fmt_cnpj)
    df["endereco_empresarial"] = (df["tipo_logradouro"].fillna("") + " " + df["logradouro"].fillna("") + ", " +
                                  df["numero"].fillna("S/N") + (" " + df["complemento"].fillna("")).str.rstrip()).str.strip()
    df["dirigentes_publicos"] = df["dirigentes_publicos"].fillna(
        "QSA nao publicado na base aberta da Receita (comum em associacoes); consultar estatuto/ata ou cadastro SUSEP")
    df["data_abertura"] = pd.to_datetime(df["data_inicio_atividade"], format="%Y%m%d", errors="coerce").dt.date
    df["fontes"] = [
        "; ".join(x for x in [fc, (f"site: {s}" if s else None), (f"SUSEP: {e}" if isinstance(e, str) else None)] if x)
        for fc, s, e in zip(df["fonte_cadastral"], df["site_institucional"], df.get("evidencia_susep", [None] * len(df)))]
    df["normalizado_em"] = now_iso()
    df.to_parquet(WORK_DIR / "base_final.parquet", index=False)
    log.info("base_final: %d estabelecimentos | classes: %s | contatos: %s", len(df),
             df["classe"].value_counts().sort_index().to_dict(), df["contato_status"].value_counts().to_dict())


if __name__ == "__main__":
    main()
