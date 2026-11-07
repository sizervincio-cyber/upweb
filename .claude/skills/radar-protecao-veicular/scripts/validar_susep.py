"""Situacao das entidades perante a SUSEP (LC 213/2025 e Resolucao CNSP 491/2026).

POR QUE NAO HA CONSULTA AUTOMATICA
  A consulta publica oficial ("Sistema de Emissao de Certidao" e "Consultar associacoes")
  fica em www2.susep.gov.br e exige reCAPTCHA. A Skill NAO contorna CAPTCHA nem usa APIs
  internas nao documentadas. Em vez disso:
    1) gera uma FILA de conferencia manual priorizada (CSV/XLSX), com link oficial;
    2) IMPORTA o resultado preenchido por voce (e, opcionalmente, PDFs de certidao salvos);
    3) se a SUSEP publicar lista oficial (dados abertos ou resposta via LAI/Fala.BR),
       importa o arquivo com --lista-oficial.

REGRAS (data de referencia exibida em cada registro)
  - Cadastro (Fase I, ate 15/07/2025) gera status "Em regularizacao junto a Susep".
  - Cadastro NAO e regularidade. Regular = contrato com administradora AUTORIZADA pela SUSEP
    incluido no sistema (Fase III, prazo final 07/05/2028), alem das demais exigencias.
  - Ausencia de resultado em busca NAO e prova de irregularidade. "nao_consta_oficial"
    so com certidao/consulta oficial negativa, e sempre "requer analise juridica".

Uso:
  python validar_susep.py fila    [--uf GO MT TO] [--classes 2 3 5]
  python validar_susep.py importar --arquivo fila_susep_preenchida.csv [--pdfs pasta_certidoes]
  python validar_susep.py importar --lista-oficial lista_susep.csv   # colunas: cnpj[,situacao]
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regras as R  # noqa: E402
from common import OUT_DIR, WORK_DIR, fmt_cnpj, get_logger, norm_text, now_iso, only_digits  # noqa: E402

log = get_logger("validar_susep")
URL_CERTIDAO = "https://www2.susep.gov.br/safe/certidoes/app/certidao/emitir"
URL_CONSULTA = "https://www2.susep.gov.br/safe/autorizacoes/app/"
URL_PAGINA = ("https://www.gov.br/susep/pt-br/assuntos/protecao-patrimonial-mutualista/"
              "associacoes-de-protecao-patrimonial-mutualista")
BASE_LEGAL = ("LC 213/2025; Resolucao Susep 49/2025 (cadastro); Resolucao CNSP 491/2026 (regulamentacao). "
              "Fase I cadastro ate 15/07/2025; Fase III regularidade ate 07/05/2028.")


def fila(a) -> None:
    c = pd.read_parquet(WORK_DIR / "candidatos.parquet")
    c = c[c["classe_preliminar"].isin(a.classes) & (c["identificador_matriz_filial"] == "1")]
    if a.uf:
        c = c[c["uf"].isin(a.uf)]
    c = c.sort_values(["classe_preliminar", "score_cadastral"], ascending=[True, False])
    f = pd.DataFrame({
        "cnpj": c["cnpj"].map(fmt_cnpj), "razao_social": c["razao_social"], "uf": c["uf"],
        "municipio": c["municipio"], "classe_preliminar": c["classe_preliminar"],
        "link_consulta_oficial": URL_CERTIDAO,
        "status_susep": "",  # preencher com um dos codigos abaixo
        "data_consulta": "", "numero_certidao_ou_protocolo": "", "observacao": "",
    })
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "fila_susep.xlsx"
    with pd.ExcelWriter(out) as w:
        f.to_excel(w, sheet_name="fila", index=False)
        pd.DataFrame({"codigo": list(R.SUSEP_STATUS), "significado": list(R.SUSEP_STATUS.values())}) \
            .to_excel(w, sheet_name="codigos_status", index=False)
        pd.DataFrame({"instrucao": [
            f"1. Abra {URL_CERTIDAO} (ou 'Consultar associacoes' em {URL_CONSULTA}).",
            "2. Informe o CNPJ, resolva o reCAPTCHA manualmente e emita/consulte.",
            "3. Preencha status_susep com um codigo da aba codigos_status, a data e o numero da certidao.",
            "4. Salve o PDF da certidao (opcional) com o CNPJ no nome do arquivo.",
            "5. Rode: python validar_susep.py importar --arquivo <esta planilha> [--pdfs <pasta>]",
            "Nunca marque 'nao_consta_oficial' sem documento oficial; ausencia de resultado != irregular.",
            "Base legal: " + BASE_LEGAL, "Pagina oficial: " + URL_PAGINA]}).to_excel(w, sheet_name="instrucoes", index=False)
    f.to_csv(OUT_DIR / "fila_susep.csv", index=False, encoding="utf-8-sig")
    log.info("fila SUSEP gerada: %s (%d entidades)", out, len(f))


def status_de_texto(txt: str) -> str:
    t = norm_text(txt)
    if re.search(r"NAO (CONSTA|FOI LOCALIZAD|ENCONTRAD)|INEXISTENCIA DE CADASTRO", t):
        return "nao_consta_oficial"
    if "EM REGULARIZACAO" in t:
        return "cadastrada_em_regularizacao"
    if re.search(r"\bREGULAR PERANTE\b|SITUACAO:? REGULAR\b", t):
        return "regular"
    return "nao_foi_possivel"


def ler_pdfs(pasta: Path) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError:
        log.warning("pypdf nao instalado (pip install pypdf); PDFs ignorados")
        return []
    regs = []
    for pdf in sorted(pasta.glob("*.pdf")):
        try:
            txt = " ".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
        except Exception as e:
            log.warning("falha lendo %s: %s", pdf.name, e)
            continue
        cnpjs = {only_digits(m) for m in re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", txt)}
        for c in cnpjs:
            regs.append({"cnpj": c, "status_susep": status_de_texto(txt), "evidencia_susep": f"certidao PDF: {pdf.name}",
                         "data_consulta_susep": date.fromtimestamp(pdf.stat().st_mtime).isoformat()})
    return regs


def importar(a) -> None:
    regs: list[dict] = []
    if a.arquivo:
        p = Path(a.arquivo)
        df = pd.read_excel(p, sheet_name="fila", dtype=str) if p.suffix.lower() in (".xlsx", ".xls") \
            else pd.read_csv(p, dtype=str)
        df = df.fillna("")
        for r in df.itertuples():
            st = str(r.status_susep).strip()
            if not st:
                continue
            if st not in R.SUSEP_STATUS:
                log.warning("status invalido '%s' para %s; ignorado", st, r.cnpj)
                continue
            regs.append({"cnpj": only_digits(r.cnpj).zfill(14), "status_susep": st,
                         "evidencia_susep": f"conferencia manual {URL_CERTIDAO} " + str(r.numero_certidao_ou_protocolo),
                         "data_consulta_susep": str(r.data_consulta) or date.today().isoformat(),
                         "obs_susep": str(r.observacao)})
    if a.pdfs:
        regs += ler_pdfs(Path(a.pdfs))
    if a.lista_oficial:
        lo = pd.read_csv(a.lista_oficial, dtype=str).fillna("")
        for r in lo.to_dict("records"):
            regs.append({"cnpj": only_digits(r["cnpj"]).zfill(14),
                         "status_susep": "cadastrada_em_regularizacao" if not r.get("situacao")
                         else status_de_texto(r["situacao"]),
                         "evidencia_susep": f"lista oficial: {Path(a.lista_oficial).name}",
                         "data_consulta_susep": date.today().isoformat()})
    if not regs:
        raise SystemExit("Nada para importar.")
    new = pd.DataFrame(regs)
    new["base_legal_susep"] = BASE_LEGAL
    new["importado_em"] = now_iso()
    out = WORK_DIR / "susep.parquet"
    if out.exists():
        old = pd.read_parquet(out)
        new = pd.concat([old[~old["cnpj"].isin(new["cnpj"])], new], ignore_index=True)
    # CNPJ de matriz vale para a raiz (8 digitos): o cadastro SUSEP e da associacao
    new["cnpj_basico"] = new["cnpj"].str[:8]
    new.to_parquet(out, index=False)
    log.info("SUSEP: %d registros importados; por status: %s", len(new), new["status_susep"].value_counts().to_dict())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fila")
    f.add_argument("--uf", nargs="+")
    f.add_argument("--classes", nargs="+", type=int, default=[2, 3, 5])
    i = sub.add_parser("importar")
    i.add_argument("--arquivo")
    i.add_argument("--pdfs")
    i.add_argument("--lista-oficial")
    a = ap.parse_args()
    fila(a) if a.cmd == "fila" else importar(a)


if __name__ == "__main__":
    main()
