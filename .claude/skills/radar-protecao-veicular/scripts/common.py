"""Configuracao compartilhada da Skill radar-protecao-veicular.

Tudo roda localmente. Nenhum dado e enviado a terceiros: os scripts apenas
LEEM fontes publicas (Receita Federal, espelho Hugging Face, SUSEP, sites
institucionais) e gravam resultados em disco local.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
# Diretorio de dados: variavel RADAR_PV_DATA ou ~/.radar_pv (funciona no Windows: C:\Users\<voce>\.radar_pv)
DATA_DIR = Path(os.environ.get("RADAR_PV_DATA", Path.home() / ".radar_pv")).expanduser()
RAW_DIR = DATA_DIR / "raw"          # parquet da Receita (por competencia)
WORK_DIR = DATA_DIR / "work"        # resultados intermediarios
OUT_DIR = DATA_DIR / "out"          # exportacoes finais
CACHE_DIR = DATA_DIR / "cache"      # cache HTTP (sites, SUSEP, APIs)
LOG_DIR = DATA_DIR / "logs"

USER_AGENT = "radar-protecao-veicular/1.0 (pesquisa B2B; somente leitura; respeita robots.txt)"

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
       "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

CNAE_ASSOCIATIVO = "9499500"  # ponto de partida, NAO classificador definitivo


def ensure_dirs() -> None:
    for d in (RAW_DIR, WORK_DIR, OUT_DIR, CACHE_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    ensure_dirs()
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)
    return log


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c))


def norm_text(s: str) -> str:
    """Maiusculas, sem acento, espacos simples."""
    return re.sub(r"\s+", " ", strip_accents(s).upper()).strip()


def only_digits(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def fmt_cnpj(cnpj14: str) -> str:
    c = only_digits(cnpj14).zfill(14)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def cnpj_valido(cnpj: str) -> bool:
    c = only_digits(cnpj)
    if len(c) != 14 or len(set(c)) == 1:
        return False
    def dv(base: str, pesos: list[int]) -> str:
        s = sum(int(d) * p for d, p in zip(base, pesos))
        r = s % 11
        return "0" if r < 2 else str(11 - r)
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    p2 = [6] + p1
    return c[12] == dv(c[:12], p1) and c[13] == dv(c[:13], p2)


def current_competencia() -> str | None:
    f = RAW_DIR / "competencia.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8")).get("competencia")
    return None


def raw_path(competencia: str | None = None) -> Path:
    comp = competencia or current_competencia()
    if not comp:
        raise SystemExit("Base CNPJ nao encontrada. Rode: python scripts/baixar_cnpj.py")
    return RAW_DIR / comp
