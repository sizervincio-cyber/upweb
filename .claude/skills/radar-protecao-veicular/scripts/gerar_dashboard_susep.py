"""Gera o dashboard HTML (arquivo unico, offline) da LISTA SUSEP cruzada com a base CNPJ.

Pre-requisitos: cruzar_lista_susep.py (out/cruzamento_susep.csv) e normalizar_dados.py (work/base_final.parquet).

Uso:
  python gerar_dashboard_susep.py --bruta lista_susep_bruta.csv     # opcional: totais antes da limpeza
  python gerar_dashboard_susep.py --saida painel_susep.html

Contem nomes de dirigentes (QSA publico): compartilhar com acesso restrito (LGPD).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regras as R  # noqa: E402
from common import OUT_DIR, SKILL_DIR, WORK_DIR, current_competencia, get_logger, norm_text, only_digits  # noqa: E402
from enriquecer_contatos import dominio_email  # noqa: E402
from normalizar_dados import tipo_email  # noqa: E402

log = get_logger("gerar_dashboard_susep")
COLS = ["cnpj", "razao", "fantasia", "uf", "mun", "end", "cep", "tipo", "seg", "sit", "nat", "cnae", "cnaeSec",
        "cap", "dirig", "nDir", "email", "emailTipo", "site", "siteSit", "tel", "wa", "abertura", "noRadar", "classe",
        "estab", "ufs", "soft", "nomeVideo"]
TIPO_ORD = ["veicular", "patrimonial", "outro_ramo", "supervisionado", "nao_encontrado"]


def s(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) or str(v) in ("nan", "None", "NaT", "") else str(v)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cruzamento", default=str(OUT_DIR / "cruzamento_susep.csv"))
    ap.add_argument("--bruta", help="CSV bruto da lista (colunas cnpj; nome) para contar zerados/invalidos")
    ap.add_argument("--fonte", default="Lista de entidades da SUSEP (gravação de tela)")
    ap.add_argument("--saida", default=str(OUT_DIR / "painel_susep.html"))
    ap.add_argument("--recall-antes", type=float, help="%% de associacoes ativas da SUSEP que o radar tinha antes da lista")
    a = ap.parse_args()

    x = pd.read_csv(a.cruzamento, sep=";", dtype=str)
    x["cnpj14"] = x["CNPJ"].map(only_digits)
    b = pd.read_parquet(WORK_DIR / "base_final.parquet")
    b = b[["cnpj", "classe", "site_institucional", "site_situacao", "whatsapp_comercial_confirmado", "qtd_estabelecimentos_ativos",
           "ufs_atuacao", "indicios_software_gestao", "contato_status"]].drop_duplicates("cnpj")
    df = x.merge(b, left_on="cnpj14", right_on="cnpj", how="left")

    rows = []
    for g in df.to_dict("records"):
        nat = s(g.get("Natureza juridica"))
        razao = s(g.get("Razao social (Receita)"))
        email = s(g.get("E-mail (Receita)"))
        txt = norm_text(f"{razao or ''} {s(g.get('Nome fantasia')) or ''} {(email or '').split('@')[-1]}")
        seg = R.segmento_veicular(txt)
        if g["Status na minha lista"] == "nao_encontrado_na_base_cnpj":
            tipo = "nao_encontrado"
        elif nat != "Associação Privada":
            tipo = "supervisionado"
        elif seg:
            tipo = "veicular"
        elif re.search(R.OUTRO_RAMO, txt):
            tipo = "outro_ramo"
        else:
            tipo = "patrimonial"
        site_val = s(g.get("site_institucional"))
        cand = dominio_email(email)
        site_sit = s(g.get("site_situacao")) or ("candidato_nao_verificado" if cand else "sem_site_identificado")
        cap = pd.to_numeric(g.get("Capital social (R$)"), errors="coerce")
        dirig = s(g.get("Dirigentes (QSA)"))
        rows.append([
            g["CNPJ"], razao or s(g.get("Nome lido no video")), s(g.get("Nome fantasia")), s(g.get("UF")), s(g.get("Municipio")),
            s(g.get("Endereco")), s(g.get("CEP")), tipo, seg,
            s(g.get("Situacao cadastral (Receita)")), nat, s(g.get("CNAE principal (descricao)")), s(g.get("CNAEs secundarios")),
            None if pd.isna(cap) else float(cap), dirig, len(dirig.split("; ")) if dirig else 0,
            email, tipo_email(email), site_val or (f"https://{cand}" if cand else None), site_sit,
            s(g.get("Telefones (Receita)")), s(g.get("whatsapp_comercial_confirmado")), s(g.get("Inicio atividade")),
            g["Status na minha lista"], None if pd.isna(g.get("classe")) else int(g["classe"]),
            None if pd.isna(g.get("qtd_estabelecimentos_ativos")) else int(g["qtd_estabelecimentos_ativos"]),
            s(g.get("ufs_atuacao")), s(g.get("indicios_software_gestao")), s(g.get("Nome lido no video")),
        ])
    meta = {"competencia": current_competencia(), "gerado": date.today().strftime("%d/%m/%Y"), "fonte": a.fonte,
            "validos": len(rows), "susepRef": 2217}
    # Cobertura das regras (sem a lista): classe preliminar 2/3/5 entre associacoes ATIVAS da SUSEP
    cand = pd.read_parquet(WORK_DIR / "candidatos.parquet", columns=["cnpj", "classe_preliminar"]).drop_duplicates("cnpj")
    at = df[df["Natureza juridica"].eq("Associação Privada") & df["Situacao cadastral (Receita)"].eq("ATIVA")]
    rec = at.merge(cand, left_on="cnpj14", right_on="cnpj", how="left")["classe_preliminar"].isin([2, 3, 5]).mean()
    meta["recall"] = {"regras": round(100 * float(rec), 1), "antes": a.recall_antes}
    if a.bruta:
        br = pd.read_csv(a.bruta, sep=";", dtype=str)
        cn = br["cnpj"].map(only_digits).str.zfill(14)
        zer = cn == "0" * 14
        inval = ~zer & ~br["valido"].astype(str).eq("True")
        meta.update(bruto=len(br), zerados=int(zer.sum()), invalidos=int(inval.sum()),
                    duplicados=int(len(br) - zer.sum() - inval.sum() - len(rows)))
    data = json.dumps({"cols": COLS, "rows": rows, "meta": meta}, ensure_ascii=False, separators=(",", ":"))
    tpl = (SKILL_DIR / "assets" / "dashboard_susep.html").read_text(encoding="utf-8")
    out = Path(a.saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tpl.replace("__DATA__", data.replace("</", "<\\/")), encoding="utf-8")
    # Planilha verificada (mesmos dados do painel), abas por tipo/segmento
    t = pd.DataFrame(rows, columns=COLS)
    t["seg"] = t["seg"].map(lambda x: ", ".join(x) if isinstance(x, list) and x else None)
    nomes = {"cnpj": "CNPJ", "razao": "Razao social", "fantasia": "Nome fantasia", "uf": "UF", "mun": "Municipio", "end": "Endereco",
             "cep": "CEP", "tipo": "Tipo", "seg": "Segmento veicular", "sit": "Situacao Receita", "nat": "Natureza juridica",
             "cnae": "CNAE principal", "cnaeSec": "CNAEs secundarios", "cap": "Capital social (R$)", "dirig": "Dirigentes (QSA)",
             "email": "E-mail (Receita)", "emailTipo": "Tipo de e-mail", "site": "Site", "siteSit": "Situacao do site",
             "tel": "Telefones (Receita)", "wa": "WhatsApp confirmado", "abertura": "Inicio atividade", "nomeVideo": "Nome no video"}
    t = t[list(nomes)].rename(columns=nomes)
    xlsx = out.with_name("susep_verificada.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        t.groupby(["Tipo", "Situacao Receita"], dropna=False).size().unstack(fill_value=0).to_excel(w, sheet_name="Resumo")
        abas = [("Veicular - Carro", t["Segmento veicular"].fillna("").str.contains("carro")),
                ("Veicular - Caminhao", t["Segmento veicular"].fillna("").str.contains("caminhao")),
                ("Veicular - Moto", t["Segmento veicular"].fillna("").str.contains("moto")),
                ("Veicular - Nao especif", t["Segmento veicular"].eq("geral")),
                ("Patrimonial s segmento", t["Tipo"].eq("patrimonial")),
                ("Seguradoras e afins", t["Tipo"].isin(["supervisionado", "outro_ramo", "nao_encontrado"])),
                ("Todas", t["Tipo"].notna())]
        for nome, m in abas:
            t[m].sort_values(["UF", "Municipio", "Razao social"]).to_excel(w, sheet_name=nome, index=False)
        for ws in w.book.worksheets:
            ws.auto_filter.ref = ws.dimensions
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(48, max(10, max(len(str(c.value or "")) for c in col[:60]) + 2))
    log.info("planilha: %s", xlsx)
    cont = pd.Series([r[COLS.index("tipo")] for r in rows]).value_counts().to_dict()
    log.info("painel SUSEP: %s (%d CNPJs; %s; %.1f MB)", out, len(rows), cont, out.stat().st_size / 1e6)


if __name__ == "__main__":
    main()
