"""Extrai nomes e CNPJs de um VIDEO (gravacao de tela) da consulta de associacoes da SUSEP.

Arquivo unico e independente: pode ser copiado e rodado em qualquer pasta do Windows.

INSTALACAO (uma vez, no Prompt de Comando ou PowerShell):
    pip install opencv-python rapidocr-onnxruntime

USO:
    python extrair_video_susep.py "C:\\Users\\voce\\Videos\\gravacao.mp4"
    python extrair_video_susep.py "gravacao.mp4" --fps 3            # mais quadros (rolagem rapida)
    python extrair_video_susep.py "gravacao.mp4" --recorte 0,150,1920,850   # so a area da tabela (x,y,largura,altura)

SAIDA (na mesma pasta do video):
    <video>_cnpjs_susep.csv     uma linha por CNPJ valido: cnpj, nome lido, em que segundo apareceu, quantas vezes
    <video>_ocr_bruto.txt       todo o texto lido, quadro a quadro (auditoria)
    <video>_rejeitados.csv      sequencias parecidas com CNPJ mas com digito verificador invalido (conferir a olho)

Como funciona: amostra o video (2 quadros/s por padrao), ignora quadros repetidos (tela parada),
faz OCR local (nada e enviado para a internet) e so aceita CNPJ com digito verificador correto,
o que elimina quase todos os erros de leitura. Corrige confusoes comuns do OCR (O->0, I/l->1, S->5, B->8)
apenas dentro de sequencias com formato de CNPJ.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    sys.exit("Falta o OpenCV. Rode: pip install opencv-python")
try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    sys.exit("Falta o OCR. Rode: pip install rapidocr-onnxruntime")

# Sequencia com formato de CNPJ, tolerando caracteres que o OCR confunde com digitos
D = r"[0-9OoQDIl|SB]"
RX_CNPJ = re.compile(rf"{D}{{2}}[.,\s]?{D}{{3}}[.,\s]?{D}{{3}}\s?[/\\|1l]?\s?{D}{{4}}\s?[-–—]?\s?{D}{{2}}")
TROCA = str.maketrans({"O": "0", "o": "0", "Q": "0", "D": "0", "I": "1", "l": "1", "|": "1", "S": "5", "B": "8"})


def cnpj_valido(c: str) -> bool:
    if len(c) != 14 or not c.isdigit() or len(set(c)) == 1:
        return False
    def dv(base, pesos):
        r = sum(int(a) * b for a, b in zip(base, pesos)) % 11
        return "0" if r < 2 else str(11 - r)
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return c[12] == dv(c[:12], p1) and c[13] == dv(c[:13], [6] + p1)


def fmt(c: str) -> str:
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def candidatos(texto: str):
    """Retorna (cnpj_14_digitos, trecho_original) para cada sequencia com cara de CNPJ."""
    out = []
    for m in RX_CNPJ.finditer(texto):
        bruto = m.group(0)
        # a barra pode ter sido lida como 1/l/|: remove so o separador da posicao da barra
        dig = re.sub(r"\D", "", bruto.translate(TROCA))
        if len(dig) == 15:  # barra virou "1"
            dig = dig[:8] + dig[9:]
        out.append((dig, bruto))
    return out


def linhas_ocr(resultado, tol=0.6):
    """Agrupa caixas do OCR em linhas da tela (mesma altura), ordenadas da esquerda para a direita."""
    if not resultado:
        return []
    itens = []
    for box, txt, score in resultado:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        itens.append({"y": sum(ys) / 4, "h": max(ys) - min(ys), "x": min(xs), "t": txt, "s": float(score)})
    itens.sort(key=lambda i: i["y"])
    linhas, atual = [], [itens[0]]
    for it in itens[1:]:
        ref = atual[-1]
        if abs(it["y"] - ref["y"]) <= tol * max(ref["h"], it["h"], 8):
            atual.append(it)
        else:
            linhas.append(atual)
            atual = [it]
    linhas.append(atual)
    return [" ".join(i["t"] for i in sorted(l, key=lambda i: i["x"])) for l in linhas]


RX_SIT = re.compile(r"Em\s?regulariza\w*(\s?junto\s?[aà]\s?Susep)?|Regular\b|Cancelad\w*|Suspens\w*|Inativ\w*|Ativ[ao]\b", re.I)


def situacao_da_linha(linha: str) -> str:
    m = RX_SIT.search(linha)
    return re.sub(r"(?i)emregulariza", "Em regulariza", m.group(0)) if m else ""


def nome_da_linha(linha: str, bruto: str) -> str:
    resto = RX_SIT.sub(" ", linha.replace(bruto, " "))
    resto = re.sub(r"\b(CNPJ|Raz[aã]o Social|Nome|Situa[cç][aã]o)\b:?", " ", resto, flags=re.I)
    return re.sub(r"\s{2,}", " ", resto).strip(" -|;:,")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--fps", type=float, default=2.0, help="quadros analisados por segundo (padrao 2)")
    ap.add_argument("--recorte", help="x,y,largura,altura da area da tabela, em pixels do video")
    ap.add_argument("--limiar-mudanca", type=float, default=2.0,
                    help="diferenca media minima (0-255) para considerar que a tela mudou")
    a = ap.parse_args()

    origem = Path(a.video)
    if not origem.exists():
        sys.exit(f"Arquivo nao encontrado: {origem}")
    caminho = origem
    temp = None
    if not str(origem).isascii():  # OpenCV no Windows falha com acentos no caminho ("Vídeos", "Gravações")
        temp = Path(tempfile.gettempdir()) / f"video_susep_{os.getpid()}{origem.suffix}"
        print(f"Copiando o video para um caminho sem acentos: {temp}")
        shutil.copyfile(origem, temp)
        caminho = temp

    cap = cv2.VideoCapture(str(caminho))
    if not cap.isOpened():
        sys.exit("Nao consegui abrir o video. Confira se o arquivo abre no player do Windows.")
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    passo = max(1, round(fps_video / a.fps))
    dur = total / fps_video if total else 0
    print(f"Video: {dur:.0f}s, {fps_video:.0f} fps; analisando 1 de cada {passo} quadros")
    rec = [int(v) for v in a.recorte.split(",")] if a.recorte else None

    ocr = RapidOCR()
    base = origem.with_suffix("")
    achados = {}  # cnpj -> dict
    nomes = defaultdict(lambda: defaultdict(int))
    rejeitados = {}
    anterior = None
    analisados = 0
    t0 = time.time()
    with open(f"{base}_ocr_bruto.txt", "w", encoding="utf-8") as bruto_txt:
        idx = 0
        while True:
            ok = cap.grab()
            if not ok:
                break
            if idx % passo:
                idx += 1
                continue
            ok, frame = cap.retrieve()
            seg = idx / fps_video
            idx += 1
            if not ok:
                continue
            if rec:
                x, y, w, h = rec
                frame = frame[y:y + h, x:x + w]
            cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            pequeno = cv2.resize(cinza, (320, max(1, int(320 * cinza.shape[0] / cinza.shape[1]))))
            if anterior is not None and float(np.mean(cv2.absdiff(pequeno, anterior))) < a.limiar_mudanca:
                continue  # tela parada: mesmo conteudo do quadro anterior
            anterior = pequeno
            # amplia telas pequenas: OCR erra menos digitos
            if frame.shape[1] < 1600:
                frame = cv2.resize(frame, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
            resultado, _ = ocr(frame)
            analisados += 1
            linhas = linhas_ocr(resultado)
            bruto_txt.write(f"\n===== {seg:8.1f}s =====\n" + "\n".join(linhas) + "\n")
            for linha in linhas:
                for dig, bruto in candidatos(linha):
                    if cnpj_valido(dig):
                        r = achados.setdefault(dig, {"primeiro_seg": round(seg, 1), "ocorrencias": 0})
                        r["ocorrencias"] += 1
                        sit = situacao_da_linha(linha)
                        if sit:
                            r["situacao"] = sit
                        nm = nome_da_linha(linha, bruto)
                        if len(nm) >= 3:
                            nomes[dig][nm] += 1
                    elif len(dig) == 14:
                        rejeitados.setdefault(dig, {"trecho": bruto, "linha": linha, "seg": round(seg, 1)})
            if analisados % 10 == 0:
                print(f"  {seg:6.0f}s de {dur:.0f}s | {analisados} quadros | {len(achados)} CNPJs validos "
                      f"| {time.time() - t0:.0f}s")
    cap.release()
    if temp:
        temp.unlink(missing_ok=True)

    saida = f"{base}_cnpjs_susep.csv"
    with open(saida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["cnpj", "cnpj_formatado", "nome_lido_no_video", "situacao_lida_no_video", "primeiro_segundo", "ocorrencias"])
        for dig, r in sorted(achados.items(), key=lambda kv: kv[1]["primeiro_seg"]):
            nome = max(nomes[dig].items(), key=lambda kv: kv[1])[0] if nomes[dig] else ""
            w.writerow([dig, fmt(dig), nome, r.get("situacao", ""), r["primeiro_seg"], r["ocorrencias"]])
    # rejeitados que nao viraram validos depois (outra leitura do mesmo CNPJ pode ter acertado)
    with open(f"{base}_rejeitados.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["sequencia_lida", "trecho", "linha", "segundo"])
        for dig, r in rejeitados.items():
            w.writerow([dig, r["trecho"], r["linha"], r["seg"]])
    print(f"\nPronto: {len(achados)} CNPJs validos em {analisados} quadros ({time.time() - t0:.0f}s).")
    print(f"  {saida}\n  {base}_ocr_bruto.txt\n  {base}_rejeitados.csv ({len(rejeitados)} sequencias invalidas para conferir)")
    print("Envie o arquivo _cnpjs_susep.csv (e, se possivel, o _rejeitados.csv) para o cruzamento com a base.")


if __name__ == "__main__":
    main()
