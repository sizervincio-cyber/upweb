"""Enriquece e VALIDA contatos institucionais a partir do site oficial da entidade.

Como o site e descoberto (sem buscador, sem adivinhacao):
  1. dominio do e-mail cadastrado na Receita, quando nao e e-mail gratuito (gmail, hotmail...);
  2. sites informados manualmente em um CSV (--sites arquivo.csv com colunas cnpj,url).

Validacao do vinculo site <-> CNPJ:
  - "site_cita_cnpj": a pagina exibe o CNPJ (raiz de 8 digitos) da entidade  -> contato CONFIRMADO
  - "dominio_do_email_cadastral": dominio igual ao e-mail na Receita, sem CNPJ na pagina -> PROVAVEL
  - sem site: so contatos declarados a Receita (podem ser do contador) -> NAO CONFIRMADO

Etica e limites: respeita robots.txt, 1 requisicao/segundo por host, no maximo 4 paginas
por site, sem login, sem formulario, sem CAPTCHA. Somente leitura. Cache local por URL.
Nao coleta dados pessoais: e-mails/telefones so sao guardados se aparecem no site
institucional como canal da entidade.

Uso:
  python enriquecer_contatos.py                     # classes 2,3,5, somente matrizes
  python enriquecer_contatos.py --uf GO --classes 2 --limite 50
  python enriquecer_contatos.py --sites meus_sites.csv
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regras as R  # noqa: E402
from common import CACHE_DIR, USER_AGENT, WORK_DIR, get_logger, norm_text, now_iso, only_digits  # noqa: E402

log = get_logger("enriquecer_contatos")
S = requests.Session()
S.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
_last_hit: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

RX_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}\s*/?\s*\d{4}\s*-?\s*\d{2}\b")
RX_FONE = re.compile(r"(?:\+?55\s?)?\(?\b([1-9]{2})\)?[\s.-]?(9?\d{4})[\s.-]?(\d{4})\b")
RX_0800 = re.compile(r"\b0[\s.-]?800[\s.-]?\d{3}[\s.-]?\d{4}\b")
RX_WA = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=|whatsapp\.com/send\?phone=)(\+?\d{10,13})", re.I)
RX_MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RX_SOCIAL = re.compile(r"https?://(?:www\.)?(instagram\.com|facebook\.com|linkedin\.com/company|youtube\.com)/[A-Za-z0-9_.\-/]+", re.I)
RX_LINK = re.compile(r"href=[\"']([^\"'#]+)[\"']", re.I)
PAGINAS_CONTATO = re.compile(r"contato|fale|atendimento|quem-somos|sobre|institucional", re.I)


def _cache_get(url: str):
    f = CACHE_DIR / "sites" / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def _cache_put(url: str, data: dict) -> None:
    d = CACHE_DIR / "sites"
    d.mkdir(parents=True, exist_ok=True)
    (d / (hashlib.sha1(url.encode()).hexdigest() + ".json")).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def robots_ok(url: str) -> bool:
    host = urlparse(url).scheme + "://" + urlparse(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = S.get(host + "/robots.txt", timeout=10)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            _robots[host] = rp
        except requests.RequestException:
            _robots[host] = None  # sem robots acessivel: segue com cautela (so paginas publicas)
    rp = _robots[host]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def fetch(url: str) -> dict:
    c = _cache_get(url)
    if c is not None:
        return c
    if not robots_ok(url):
        res = {"url": url, "status": "bloqueado_robots", "html": ""}
        _cache_put(url, res)
        return res
    host = urlparse(url).netloc
    wait = 1.0 - (time.time() - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()
    try:
        r = S.get(url, timeout=15, allow_redirects=True)
        ctype = r.headers.get("content-type", "")
        html = r.text[:1_500_000] if "html" in ctype or not ctype else ""
        res = {"url": r.url, "status": r.status_code, "html": html, "coletado_em": now_iso()}
    except requests.RequestException as e:
        return {"url": url, "status": "erro:" + type(e).__name__, "html": ""}  # erro de rede nao vai para o cache
    _cache_put(url, res)
    return res


def texto(html: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def norm_fone(ddd: str, p1: str, p2: str) -> str:
    return f"({ddd}) {p1}-{p2}"


def analisar(site: str, cnpj_basico: str) -> dict:
    base = site if site.startswith("http") else "https://" + site
    pages, visit = [], [base]
    first = fetch(base)
    if first["status"] != 200 and not base.startswith("http://"):
        alt = base.replace("https://", "https://www.", 1) if "://www." not in base else base.replace("https://", "http://", 1)
        first = fetch(alt)
    if first["status"] != 200:
        return {"site": base, "site_status": str(first["status"])}
    pages.append(first)
    links = [urljoin(first["url"], h) for h in RX_LINK.findall(first["html"])]
    dom = urlparse(first["url"]).netloc
    internos = [u for u in dict.fromkeys(links) if urlparse(u).netloc == dom and PAGINAS_CONTATO.search(u)]
    for u in internos[:3]:
        p = fetch(u)
        if p["status"] == 200:
            pages.append(p)
            visit.append(u)
    html_all = "\n".join(p["html"] for p in pages)
    txt = texto(html_all)
    up = norm_text(txt)
    cnpjs = {only_digits(m) for m in RX_CNPJ.findall(txt)}
    cita = any(c[:8] == cnpj_basico for c in cnpjs)
    fones = sorted({norm_fone(*m) for m in RX_FONE.findall(txt)})[:8]
    f0800 = sorted({only_digits(m) for m in RX_0800.findall(txt)})[:3]
    was = sorted({only_digits(m) for m in RX_WA.findall(html_all)})[:5]
    mails = sorted({m.lower() for m in RX_MAIL.findall(html_all)
                    if not re.search(r"\.(png|jpg|jpeg|gif|svg|webp)$|sentry|wixpress|example|domain\.com", m, re.I)})[:8]
    social = sorted({m.group(0).rstrip("/") for m in RX_SOCIAL.finditer(html_all)})[:6]
    sinais = {k: any(re.search(t, up) for t in v) for k, v in R.SINAIS_SITE.items()}
    soft = [k for k, rx in R.SOFTWARE_HINTS.items() if re.search(rx, html_all.upper())]
    return {
        "site": first["url"], "site_status": "200", "paginas_lidas": json.dumps(visit, ensure_ascii=False),
        "site_cita_cnpj": cita, "cnpjs_no_site": json.dumps(sorted(cnpjs)),
        "site_telefones": json.dumps(fones, ensure_ascii=False), "site_0800": json.dumps(f0800),
        "site_whatsapp": json.dumps(was), "site_emails": json.dumps(mails, ensure_ascii=False),
        "site_redes_sociais": json.dumps(social, ensure_ascii=False),
        **{f"sinal_{k}": v for k, v in sinais.items()},
        "indicios_software": json.dumps(soft), "site_coletado_em": first.get("coletado_em", now_iso()),
    }


def dominio_email(mail: str | None) -> str | None:
    if not mail or "@" not in str(mail):
        return None
    d = str(mail).split("@")[-1].strip().strip("'\"").lower()
    if d.upper() in R.FREE_MAIL or "." not in d:
        return None
    if DOMINIO_TERCEIRO.search(d):
        return None  # e-mail do contador/escritorio: nao e site da entidade
    return d


# Dominios que tipicamente pertencem a contadores/escritorios que fazem o registro na Receita
DOMINIO_TERCEIRO = re.compile(r"contab|contabil|\.cnt\.br$|contador|assessoria|coworking|escritorio|advoca|consultoria|locadora", re.I)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uf", nargs="+")
    ap.add_argument("--classes", nargs="+", type=int, default=[2, 3, 5])
    ap.add_argument("--incluir-filiais", action="store_true")
    ap.add_argument("--sites", help="CSV com colunas cnpj,url (sites conferidos manualmente)")
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args()

    cand = pd.read_parquet(WORK_DIR / "candidatos.parquet")
    cand = cand[cand["classe_preliminar"].isin(a.classes)]
    if a.uf:
        cand = cand[cand["uf"].isin(a.uf)]
    if not a.incluir_filiais:
        cand = cand[cand["identificador_matriz_filial"] == "1"]
    manual = {}
    if a.sites:
        m = pd.read_csv(a.sites, dtype=str)
        manual = {only_digits(r.cnpj).zfill(14): r.url.strip() for r in m.itertuples()}

    rows = []
    alvo = cand.to_dict("records")
    if a.limite:
        alvo = alvo[: a.limite]
    for i, r in enumerate(alvo, 1):
        site, origem = manual.get(r["cnpj"]), "informado_manual"
        if not site:
            site, origem = dominio_email(r["correio_eletronico"]), "dominio_do_email_cadastral"
        rec = {"cnpj": r["cnpj"], "site_origem": origem if site else None}
        if site:
            try:
                rec.update(analisar(site, r["cnpj_basico"]))
            except Exception as e:  # nunca derruba o lote inteiro
                log.warning("erro analisando %s: %s", site, e)
                rec.update({"site": site, "site_status": "erro"})
        if i % 20 == 0:
            log.info("%d/%d analisados", i, len(alvo))
        rows.append(rec)
    df = pd.DataFrame(rows)
    out = WORK_DIR / "enriquecimento.parquet"
    if out.exists():  # atualizacao incremental: novos resultados substituem os antigos do mesmo CNPJ
        old = pd.read_parquet(out)
        df = pd.concat([old[~old["cnpj"].isin(df["cnpj"])], df], ignore_index=True)
    df.to_parquet(out, index=False)
    ok = (df.get("site_status") == "200").sum() if "site_status" in df else 0
    log.info("enriquecimento: %s entidades, %s sites lidos, %s citam o CNPJ", len(df), ok,
             int(df.get("site_cita_cnpj", pd.Series(dtype=bool)).fillna(False).sum()))


if __name__ == "__main__":
    main()
