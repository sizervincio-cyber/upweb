"""Exporta a base consolidada em CSV, XLSX (abas por UF + dicionario) e JSON,
e gera o relatorio nacional de cobertura em Markdown.

Uso:
  python exportar_resultados.py                         # classes 1,2,3,5 (exclui fora do escopo)
  python exportar_resultados.py --uf GO MT TO --nome piloto_go_mt_to
  python exportar_resultados.py --classes 1 2 --somente-matriz --com-contato
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regras as R  # noqa: E402
from common import OUT_DIR, SKILL_DIR, UFS, WORK_DIR, get_logger, now_iso  # noqa: E402

log = get_logger("exportar_resultados")

# Ordem e nome das colunas exportadas (mesmo dicionario de references/dicionario-dados.md)
COLUNAS = {
    "cnpj_formatado": "CNPJ completo (14 digitos, formatado)",
    "matriz_filial": "MATRIZ ou FILIAL",
    "razao_social": "Razao social (Receita)",
    "nome_fantasia": "Nome fantasia (Receita)",
    "natureza_juridica": "Codigo da natureza juridica",
    "natureza_juridica_desc": "Descricao da natureza juridica",
    "subtipo": "associacao | cooperativa | empresa_ecossistema_pv | outra_natureza",
    "classe": "Classe final 1-5 (ver regras-classificacao.md)",
    "classe_desc": "Descricao da classe",
    "score_confianca": "Score de confianca 0-100 (evidencias cadastrais + externas)",
    "evidencias": "Lista JSON de evidencias cadastrais usadas no score",
    "cnae_fiscal_principal": "CNAE principal (7 digitos)",
    "cnae_principal_desc": "Descricao do CNAE principal",
    "cnae_fiscal_secundaria": "CNAEs secundarios (separados por virgula)",
    "uf": "UF do estabelecimento",
    "municipio": "Municipio (tabela Receita)",
    "bairro": "Bairro",
    "endereco_empresarial": "Endereco empresarial (Receita)",
    "cep": "CEP",
    "telefone_institucional_receita": "Telefones declarados a Receita (podem ser do contador)",
    "email_cadastral": "E-mail declarado a Receita",
    "email_cadastral_tipo": "dominio_proprio | gratuito | provavel_terceiro_contador | ausente",
    "site_institucional": "Site oficial lido (vinculo validado)",
    "contato_status": "confirmado_site_cita_cnpj | provavel_site_dominio_cadastral | somente_declarado_receita | sem_contato_publico",
    "whatsapp_comercial_confirmado": "WhatsApp publicado no site que cita o CNPJ",
    "whatsapp_site_nao_confirmado": "WhatsApp em site sem citacao do CNPJ (conferir)",
    "telefones_site": "Telefones publicados no site oficial",
    "emails_site": "E-mails publicados no site oficial",
    "redes_sociais": "Redes sociais linkadas no site oficial",
    "dirigentes_publicos": "QSA publico: nome (qualificacao, data de entrada). Sem CPF",
    "qtd_dirigentes_qsa": "Quantidade de registros no QSA",
    "data_abertura": "Data de inicio de atividade",
    "situacao_cadastral_desc": "Situacao cadastral na Receita",
    "porte_desc": "Porte cadastral",
    "capital_social_valor": "Capital social (campo oficial, R$)",
    "capital_social_status": "informado | zero_informado | ausente_na_base",
    "status_susep": "Codigo da situacao SUSEP",
    "status_susep_desc": "Descricao da situacao SUSEP",
    "data_consulta_susep": "Data da consulta SUSEP",
    "evidencia_susep": "Evidencia SUSEP (certidao, protocolo, lista oficial)",
    "alerta_susep": "Alerta juridico quando ha certidao negativa",
    "qtd_estabelecimentos_ativos": "Estabelecimentos ativos da mesma raiz (matriz+filiais)",
    "ufs_atuacao": "UFs com estabelecimento ativo",
    "email_compartilhado_qtd_entidades": "Quantas entidades usam o mesmo dominio de e-mail (indicio de gestao comum)",
    "sinal_assistencia_24h": "Site cita assistencia 24h/guincho",
    "sinal_vistoria": "Site cita vistoria",
    "sinal_sinistro": "Site cita sinistro/evento/indenizacao",
    "sinal_oficinas": "Site cita oficinas/rede credenciada",
    "sinal_rastreamento": "Site cita rastreamento",
    "sinal_area_associado": "Site tem area/app do associado",
    "indicios_software_gestao": "Indicios de software de gestao no site (nao prova contrato)",
    "oportunidade_gestao_digital": "Leitura comercial baseada nos sinais",
    "prioridade_comercial_score": "Prioridade comercial 0-100 (somente evidencias)",
    "prioridade_comercial": "A (>=60) | B (35-59) | C (<35)",
    "competencia_cnpj": "Competencia da base CNPJ (AAAA-MM)",
    "fontes": "Fontes usadas na ficha",
    "coletado_em": "Data/hora da coleta cadastral (UTC)",
}


def relatorio(df: pd.DataFrame, path: Path, titulo: str) -> None:
    ent = df.sort_values("identificador_matriz_filial").drop_duplicates("cnpj_basico")  # 1 linha por entidade
    alvo = ent[ent["classe"].isin([1, 2, 3, 5])]
    por_uf = alvo.pivot_table(index="uf", columns="classe", values="cnpj", aggfunc="count", fill_value=0)
    por_uf = por_uf.reindex(UFS, fill_value=0)
    por_uf.columns = [f"classe_{c}" for c in por_uf.columns]
    por_uf["total_1_2_3"] = por_uf[[c for c in por_uf.columns if c in ("classe_1", "classe_2", "classe_3")]].sum(axis=1)
    contato = alvo["contato_status"].value_counts()
    susep = alvo["status_susep"].value_counts()
    comp = df["competencia_cnpj"].iloc[0] if len(df) else "?"
    linhas = [
        f"# {titulo}", "", f"Gerado em {now_iso()} | Base CNPJ competencia {comp}.", "",
        "## Resumo", "",
        f"- Entidades (raiz CNPJ) nas classes 1, 2, 3 e 5: **{len(alvo)}**",
        f"- Estabelecimentos (matriz + filiais) dessas entidades: **{df[df['classe'].isin([1,2,3,5])].shape[0]}**",
        f"- Classe 1 confirmadas: {int((alvo.classe==1).sum())} | Classe 2 provaveis: {int((alvo.classe==2).sum())} | "
        f"Classe 3 patrimonial s/ confirmacao veicular: {int((alvo.classe==3).sum())} | Classe 5 pendentes: {int((alvo.classe==5).sum())}",
        f"- Fora do escopo (classe 4) descartadas com justificativa: {int((ent.classe==4).sum())}",
        "", "## Contatos", "",
        *[f"- {k}: {v} ({v/len(alvo):.1%})" for k, v in contato.items()],
        "", "## SUSEP", "", *[f"- {R.SUSEP_STATUS.get(k, k)}: {v}" for k, v in susep.items()],
        "", "## Distribuicao por UF (entidades)", "", por_uf.to_markdown(),
        "", "## Limitacoes", "",
        "- Descoberta baseada em nome, CNAE, natureza juridica e e-mail na base aberta da Receita. Entidades sem nenhum desses "
        "sinais (ex.: nome fantasia neutro, CNAE generico) podem nao aparecer. Nao ha evidencia de cobertura completa.",
        "- Referencia externa: a SUSEP informou 2.217 associacoes com cadastro concluido na Fase I (prazo 15/07/2025). "
        "Usar como ordem de grandeza, nao como gabarito (a lista nominal nao e publicada em dados abertos).",
        "- Situacao SUSEP depende de conferencia manual (reCAPTCHA na consulta oficial).",
        "- Contatos 'somente_declarado_receita' podem pertencer ao escritorio contabil.",
    ]
    path.write_text("\n".join(linhas), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uf", nargs="+", choices=UFS)
    ap.add_argument("--classes", nargs="+", type=int, default=[1, 2, 3, 5])
    ap.add_argument("--somente-matriz", action="store_true")
    ap.add_argument("--com-contato", action="store_true", help="apenas contato confirmado ou provavel")
    ap.add_argument("--min-score", type=int, default=0)
    ap.add_argument("--nome", default="radar_protecao_veicular")
    a = ap.parse_args()

    full = pd.read_parquet(WORK_DIR / "base_final.parquet")
    if a.uf:
        full = full[full["uf"].isin(a.uf)]
    relatorio(full, OUT_DIR / f"{a.nome}_relatorio.md", f"Relatorio de cobertura - {a.nome}")
    df = full[full["classe"].isin(a.classes) & (full["score_confianca"] >= a.min_score)]
    if a.somente_matriz:
        df = df[df["identificador_matriz_filial"] == "1"]
    if a.com_contato:
        df = df[df["contato_status"].isin(["confirmado_site_cita_cnpj", "provavel_site_dominio_cadastral"])]
    df = df.sort_values(["uf", "classe", "prioridade_comercial_score", "score_confianca"], ascending=[True, True, False, False])
    cols = [c for c in COLUNAS if c in df.columns]
    out = df[cols]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_DIR / f"{a.nome}.csv", index=False, encoding="utf-8-sig")
    out.to_json(OUT_DIR / f"{a.nome}.json", orient="records", force_ascii=False, indent=1, date_format="iso")
    with pd.ExcelWriter(OUT_DIR / f"{a.nome}.xlsx", engine="openpyxl") as w:
        resumo = out.groupby(["uf", "classe_desc"]).size().unstack(fill_value=0)
        resumo.to_excel(w, sheet_name="Resumo")
        for uf, g in out.groupby("uf"):
            g.to_excel(w, sheet_name=uf, index=False)
        pd.DataFrame({"coluna": cols, "descricao": [COLUNAS[c] for c in cols]}).to_excel(w, sheet_name="Dicionario", index=False)
        pd.DataFrame({"classe": list(R.CLASSES), "descricao": list(R.CLASSES.values())}).to_excel(w, sheet_name="Classes", index=False)
        for ws in w.book.worksheets:  # largura legivel + filtro + congelar cabecalho
            ws.auto_filter.ref = ws.dimensions
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(45, max(10, max(len(str(c.value or "")) for c in col[:50]) + 2))
    meta = {"arquivo": a.nome, "linhas": len(out), "gerado_em": now_iso(), "filtros": vars(a),
            "skill": str(SKILL_DIR.name)}
    (OUT_DIR / f"{a.nome}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("exportado: %s.{csv,xlsx,json} (%d linhas) e relatorio", OUT_DIR / a.nome, len(out))


if __name__ == "__main__":
    main()
