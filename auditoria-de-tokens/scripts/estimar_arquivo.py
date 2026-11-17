#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
estimar_arquivo.py - Estima quanto um arquivo pesa numa conversa antes de anexar.

Um anexo fica na conversa e e relido a cada mensagem seguinte. O script estima
o tamanho em tokens e mostra o custo acumulado em uma conversa de N mensagens.

Uso:
  python3 estimar_arquivo.py relatorio.pdf planilha.csv print.png
  python3 estimar_arquivo.py contrato.docx --mensagens 30

Formatos: texto e codigo (txt, md, csv, json, html...), docx, pdf (melhor com a
biblioteca pypdf instalada), png, jpg, gif e webp. So usa a biblioteca padrao.
As contas de PDF e imagem seguem a documentacao da API; no chat sao aproximacoes.
"""
import argparse
import math
import os
import re
import struct
import sys
import zipfile

PDF_PAGINA = (1500, 3000)      # tokens por pagina, faixa da documentacao da API
IMAGEM_TETO = 1568             # teto aproximado por imagem em modelos padrao


def fmt(n):
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} mi".replace(".", ",")
    if n >= 10_000:
        return f"{n / 1000:.0f} mil"
    if n >= 1000:
        return f"{n / 1000:.1f} mil".replace(".", ",")
    return f"{n:.0f}"


def dimensoes(caminho):
    with open(caminho, "rb") as f:
        b = f.read(64 * 1024)
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", b[16:24])
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", b[6:10])
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        if b[12:16] == b"VP8X":
            return (int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1)
        if b[12:16] == b"VP8 ":
            w, h = struct.unpack("<HH", b[26:30])
            return (w & 0x3FFF, h & 0x3FFF)
    if b[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            marca = b[i + 1]
            if marca in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return (w, h)
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None


def estimar(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    tam = os.path.getsize(caminho)
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        d = dimensoes(caminho)
        if not d:
            return IMAGEM_TETO, IMAGEM_TETO, "imagem (dimensões não lidas; usei o teto)"
        t = min(math.ceil(d[0] / 28) * math.ceil(d[1] / 28), IMAGEM_TETO)
        return t, t, f"imagem {d[0]}×{d[1]}"
    if ext == ".pdf":
        paginas = chars = None
        try:
            from pypdf import PdfReader  # opcional
            r = PdfReader(caminho)
            paginas = len(r.pages)
            chars = sum(len(pg.extract_text() or "") for pg in r.pages[:300])
        except Exception:
            with open(caminho, "rb") as f:
                paginas = len(re.findall(rb"/Type\s*/Page[^s]", f.read())) or None
        if not paginas:
            return int(tam / 8), int(tam / 2), "pdf (não consegui contar páginas; faixa pelo tamanho)"
        baixo = max(paginas * PDF_PAGINA[0], int((chars or 0) / 4))
        return baixo, max(paginas * PDF_PAGINA[1], baixo), f"pdf de {paginas} páginas"
    if ext == ".docx":
        try:
            with zipfile.ZipFile(caminho) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="replace")
            t = int(len(re.sub(r"<[^>]+>", "", xml)) / 4)
            return t, t, "docx (só o texto)"
        except Exception:
            return int(tam / 20), int(tam / 5), "docx (não consegui abrir; faixa pelo tamanho)"
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            t = int(len(f.read()) / 4)
        return t, t, "texto"
    except Exception:
        return int(tam / 8), int(tam / 3), "formato não reconhecido (faixa pelo tamanho)"


def conselho(tokens, tipo):
    if tokens >= 50_000:
        return ("Muito grande para deixar na conversa. Extraia só as páginas ou seções necessárias, ou coloque em um "
                "Projeto se for reutilizar.")
    if tokens >= 10_000:
        return "Grande. Anexe só o trecho necessário ou faça todas as perguntas sobre ele em uma mensagem."
    if tipo.startswith("imagem") and tokens >= 1000:
        return "Se a imagem só tem texto, cole o texto. Recorte a parte que importa."
    return "Tamanho tranquilo."


def main():
    ap = argparse.ArgumentParser(description="Estima quanto um arquivo pesa numa conversa.")
    ap.add_argument("arquivos", nargs="+")
    ap.add_argument("--mensagens", type=int, default=20, help="mensagens suas depois de anexar (padrão: 20)")
    a = ap.parse_args()
    print(f"| Arquivo | Tipo | Tokens (estimativa) | Relido em {a.mensagens} mensagens | O que fazer |")
    print("|---|---|---|---|---|")
    for caminho in a.arquivos:
        if not os.path.isfile(caminho):
            print(f"| {os.path.basename(caminho)} | não encontrado | | | |")
            continue
        lo, hi, tipo = estimar(caminho)
        faixa = fmt(lo) if lo == hi else f"{fmt(lo)} a {fmt(hi)}"
        acum = fmt(lo * a.mensagens) if lo == hi else f"{fmt(lo * a.mensagens)} a {fmt(hi * a.mensagens)}"
        print(f"| {os.path.basename(caminho)} | {tipo} | {faixa} | {acum} | {conselho(hi, tipo)} |")
    print()
    print("Um anexo é relido a cada mensagem enquanto a conversa continua. Em Projetos, o conteúdo reutilizado fica "
          "em cache e conta menos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
