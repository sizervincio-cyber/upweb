"""Gera o dashboard HTML unico (sem dependencias externas) a partir da base consolidada.

Uso:
  python gerar_dashboard.py                         # -> $RADAR_PV_DATA/out/radar_dashboard.html
  python gerar_dashboard.py --saida painel.html

O arquivo traz nomes de dirigentes (QSA publico). Compartilhe com acesso restrito;
nao publique em repositorio ou site aberto (LGPD: minimizacao e finalidade).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT_DIR, SKILL_DIR, WORK_DIR, get_logger  # noqa: E402

log = get_logger("gerar_dashboard")
COLS = ["cnpj", "razao", "fantasia", "uf", "mun", "classe", "score", "contato", "tel", "email", "emailTipo", "wa",
        "site", "dirig", "prio", "prioScore", "estab", "ufs", "emailComp", "soft", "abertura", "nDir", "s24h", "sSin",
        "sVist", "mf"]


def s(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) or str(v) in ("nan", "None", "NaT", "") else str(v)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", default=str(OUT_DIR / "radar_dashboard.html"))
    a = ap.parse_args()
    b = pd.read_parquet(WORK_DIR / "base_final.parquet").sort_values("identificador_matriz_filial")
    ent = b.drop_duplicates("cnpj_basico")  # 1 linha por entidade, preferindo a matriz
    alvo = ent[ent["classe"].isin([1, 2, 3, 5])]
    rows = [[r.cnpj_formatado, s(r.razao_social), s(r.nome_fantasia), r.uf, s(r.municipio), int(r.classe),
             int(r.score_confianca), r.contato_status, s(r.telefone_institucional_receita), s(r.email_cadastral),
             r.email_cadastral_tipo, s(r.whatsapp_comercial_confirmado), s(r.site_institucional),
             s(r.dirigentes_publicos) if pd.notna(r.qtd_dirigentes_qsa) else None, r.prioridade_comercial,
             int(r.prioridade_comercial_score), int(r.qtd_estabelecimentos_ativos), s(r.ufs_atuacao),
             None if pd.isna(r.email_compartilhado_qtd_entidades) else int(r.email_compartilhado_qtd_entidades),
             s(r.indicios_software_gestao), s(r.data_abertura),
             int(r.qtd_dirigentes_qsa) if pd.notna(r.qtd_dirigentes_qsa) else 0,
             bool(r.sinal_assistencia_24h), bool(r.sinal_sinistro), bool(r.sinal_vistoria), r.matriz_filial]
            for r in alvo.itertuples()]
    meta = {"competencia": str(b["competencia_cnpj"].iloc[0]), "gerado": date.today().strftime("%d/%m/%Y"),
            "descartadas": int((ent["classe"] == 4).sum()),
            "descSub": {k: int(v) for k, v in ent[ent["classe"] == 4]["subtipo"].value_counts().items()},
            "estabTotal": int(b["classe"].isin([1, 2, 3, 5]).sum()), "susepRef": 2217,
            "sitesLidos": int(alvo["site_institucional"].notna().sum())}
    data = json.dumps({"cols": COLS, "rows": rows, "meta": meta}, ensure_ascii=False, separators=(",", ":"))
    tpl = (SKILL_DIR / "assets" / "dashboard_template.html").read_text(encoding="utf-8")
    out = Path(a.saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tpl.replace("__DATA__", data.replace("</", "<\\/")), encoding="utf-8")
    log.info("dashboard: %s (%d entidades, %.1f MB)", out, len(rows), out.stat().st_size / 1e6)


if __name__ == "__main__":
    main()
