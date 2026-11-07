"""Baixa a base CNPJ (Receita Federal) em Parquet, com retomada e verificacao.

Fontes suportadas:
  hf   (padrao) espelho Parquet do CNPJ Aberto no Hugging Face, que declara como
       origem arquivos.receitafederal.gov.br. ~5 GB para todas as tabelas.
  rfb  repositorio oficial da Receita (Nextcloud/SERPRO, CSV zipados ~7 GB).
       Converte CSV -> Parquet com DuckDB, em lotes, sem carregar tudo na RAM.

Uso:
  python baixar_cnpj.py                       # ultima competencia, tabelas essenciais
  python baixar_cnpj.py --competencia 2026-10 --fonte rfb
  python baixar_cnpj.py --listar              # mostra competencias disponiveis
  python baixar_cnpj.py --tabelas estabelecimentos empresas socios

Retomada: arquivos parciais (.part) continuam de onde pararam (HTTP Range).
Verificacao: tamanho em bytes conferido com o _manifest.json (fonte hf).
Somente leitura nas fontes; nada e enviado a terceiros.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW_DIR, USER_AGENT, ensure_dirs, get_logger, now_iso  # noqa: E402

log = get_logger("baixar_cnpj")

HF_ORG = "cnpjaberto"
HF_PREFIX = "cnpj-dados-receita-brasil-"
RFB_SHARE = "gn672Ad4CF8N6TK"  # compartilhamento publico oficial da Receita
RFB_WEBDAV = "https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/"

ESSENCIAIS = ["estabelecimentos", "empresas", "socios", "simples", "cnaes", "municipios",
              "naturezas_juridicas", "qualificacoes_socios", "motivos_situacoes", "paises"]

# Layout oficial dos CSV da Receita (sem cabecalho, separador ';', latin-1).
# Nomes alinhados ao espelho HF para que o resto da Skill funcione com qualquer fonte.
RFB_COLS = {
    "empresas": ["cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel",
                 "capital_social", "porte_empresa", "ente_federativo"],
    "estabelecimentos": ["cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
                         "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
                         "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
                         "data_inicio_atividade", "cnae_fiscal_principal", "cnae_fiscal_secundaria",
                         "tipo_logradouro", "logradouro", "numero", "complemento", "bairro", "cep",
                         "uf", "municipio", "ddd1", "telefone1", "ddd2", "telefone2", "ddd_fax",
                         "fax", "correio_eletronico", "situacao_especial", "data_situacao_especial"],
    "socios": ["cnpj_basico", "identificador_socio", "nome_socio", "cpf_cnpj_socio",
               "qualificacao_socio", "data_entrada_sociedade", "pais", "representante_legal",
               "nome_representante", "qualificacao_representante", "faixa_etaria"],
    "simples": ["cnpj_basico", "opcao_simples", "data_opcao_simples", "data_exclusao_simples",
                "opcao_mei", "data_opcao_mei", "data_exclusao_mei"],
    "cnaes": ["codigo", "descricao"], "municipios": ["codigo", "descricao"],
    "naturezas_juridicas": ["codigo", "descricao"], "qualificacoes_socios": ["codigo", "descricao"],
    "motivos_situacoes": ["codigo", "descricao"], "paises": ["codigo", "descricao"],
}
RFB_ZIP_PREFIX = {"empresas": "Empresas", "estabelecimentos": "Estabelecimentos", "socios": "Socios",
                  "simples": "Simples", "cnaes": "Cnaes", "municipios": "Municipios",
                  "naturezas_juridicas": "Naturezas", "qualificacoes_socios": "Qualificacoes",
                  "motivos_situacoes": "Motivos", "paises": "Paises"}

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT


def download(url: str, dest: Path, expected: int | None = None, auth=None, tries: int = 6) -> None:
    """Download com retomada (Range) e backoff exponencial."""
    if dest.exists() and (expected is None or dest.stat().st_size == expected):
        log.info("ja existe: %s", dest.name)
        return
    part = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, tries + 1):
        pos = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={pos}-"} if pos else {}
        try:
            with session.get(url, headers=headers, stream=True, timeout=60, auth=auth) as r:
                if r.status_code == 416:  # ja completo
                    break
                r.raise_for_status()
                mode = "ab" if pos and r.status_code == 206 else "wb"
                with open(part, mode) as fh:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
            if expected is None or part.stat().st_size == expected:
                break
            log.warning("tamanho incompleto %s (%s/%s), retomando", dest.name, part.stat().st_size, expected)
        except requests.RequestException as e:
            wait = 2 ** attempt
            log.warning("falha %s (tentativa %d): %s; aguardando %ss", dest.name, attempt, type(e).__name__ + ": " + str(e)[:160], wait)
            time.sleep(wait)
    else:
        raise SystemExit(f"Nao foi possivel baixar {url}")
    if expected is not None and part.stat().st_size != expected:
        raise SystemExit(f"Tamanho divergente em {dest.name}: {part.stat().st_size} != {expected}")
    shutil.move(part, dest)
    log.info("ok: %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)


# ---------------------------------------------------------------- Hugging Face
def hf_competencias() -> list[str]:
    r = session.get(f"https://huggingface.co/api/datasets?author={HF_ORG}&limit=200", timeout=30)
    r.raise_for_status()
    comps = [d["id"].split(HF_PREFIX)[-1] for d in r.json() if HF_PREFIX in d["id"]]
    return sorted(c for c in comps if re.fullmatch(r"\d{4}-\d{2}", c))


def baixar_hf(comp: str, tabelas: list[str]) -> Path:
    base = f"https://huggingface.co/datasets/{HF_ORG}/{HF_PREFIX}{comp}/resolve/main/"
    dest_dir = RAW_DIR / comp
    dest_dir.mkdir(parents=True, exist_ok=True)
    man = session.get(base + "_manifest.json", timeout=60)
    man.raise_for_status()
    manifest = man.json()
    (dest_dir / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in manifest["files"]:
        if f["table"] in tabelas:
            download(base + f["file"], dest_dir / f["file"], expected=f["bytes"])
    return dest_dir


# ---------------------------------------------------------------- Receita oficial
def rfb_list(path: str = "") -> list[str]:
    r = session.request("PROPFIND", RFB_WEBDAV + path, headers={"Depth": "1"},
                        auth=(RFB_SHARE, ""), timeout=60)
    r.raise_for_status()
    hrefs = re.findall(r"<d:href>([^<]+)</d:href>", r.text)
    return [h.rstrip("/").split("/")[-1] for h in hrefs[1:]]


def rfb_competencias() -> list[str]:
    return sorted(x for x in rfb_list() if re.fullmatch(r"\d{4}-\d{2}", x))


def baixar_rfb(comp: str, tabelas: list[str]) -> Path:
    import duckdb  # import tardio: so necessario aqui

    zips_dir = RAW_DIR / "_zips" / comp
    dest_dir = RAW_DIR / comp
    arquivos = rfb_list(comp + "/")
    con = duckdb.connect()
    for tab in tabelas:
        prefix = RFB_ZIP_PREFIX[tab]
        for z in sorted(a for a in arquivos if a.startswith(prefix) and a.endswith(".zip")):
            zpath = zips_dir / z
            download(RFB_WEBDAV + comp + "/" + z, zpath, auth=(RFB_SHARE, ""))
            out = dest_dir / tab / (z[:-4].lower() + ".parquet")
            if out.exists():
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zpath) as zf:
                inner = zf.namelist()[0]
                tmp_csv = zips_dir / (inner + ".csv")
                with zf.open(inner) as src, open(tmp_csv, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=1 << 20)
            cols = RFB_COLS[tab]
            colspec = "{" + ", ".join(f"'{c}': 'VARCHAR'" for c in cols) + "}"
            con.execute(f"""
                COPY (SELECT * FROM read_csv('{tmp_csv.as_posix()}', delim=';', quote='"', header=false,
                      encoding='latin-1', columns={colspec}, ignore_errors=true))
                TO '{out.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
            tmp_csv.unlink()
            log.info("convertido %s -> %s", z, out.name)
    return dest_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fonte", choices=["hf", "rfb"], default="hf")
    ap.add_argument("--competencia", help="AAAA-MM (padrao: a mais recente da fonte)")
    ap.add_argument("--tabelas", nargs="+", default=ESSENCIAIS, choices=ESSENCIAIS)
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    ensure_dirs()

    comps = hf_competencias() if a.fonte == "hf" else rfb_competencias()
    if a.listar:
        print("\n".join(comps))
        return
    comp = a.competencia or comps[-1]
    # Alerta se a Receita ja publicou competencia mais nova que o espelho
    if a.fonte == "hf":
        try:
            oficial = rfb_competencias()[-1]
            if oficial > comp:
                log.warning("Receita ja publicou %s; espelho HF esta em %s. Use --fonte rfb.", oficial, comp)
        except Exception as e:  # fonte oficial instavel nao impede o uso do espelho
            log.warning("nao foi possivel consultar a Receita: %s", e)

    log.info("baixando competencia %s via %s: %s", comp, a.fonte, ", ".join(a.tabelas))
    dest = baixar_hf(comp, a.tabelas) if a.fonte == "hf" else baixar_rfb(comp, a.tabelas)
    meta = {"competencia": comp, "fonte": a.fonte, "baixado_em": now_iso(), "tabelas": a.tabelas,
            "origem_declarada": "https://arquivos.receitafederal.gov.br (Receita Federal, CNPJ dados abertos)"}
    (dest / "competencia.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (RAW_DIR / "competencia.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
