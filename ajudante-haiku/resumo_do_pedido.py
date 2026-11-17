#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resumo_do_pedido.py - Diz quanto do ultimo pedido foi lido pelo ajudante no Haiku
e quanto ficou com o modelo da conversa. Somente leitura: nao altera a sessao,
nao acessa a rede e nao le o texto das mensagens, so os contadores de uso.

Uso:
  python3 resumo_do_pedido.py            # ultimo pedido da sessao mais recente desta pasta
  python3 resumo_do_pedido.py --sessao   # a sessao inteira
  python3 resumo_do_pedido.py --hook     # chamado pelo hook Stop do Claude Code

No modo --hook ele nunca falha em voz alta: em qualquer erro, sai em silencio.
"""
import json
import os
import re
import sys
from pathlib import Path

# Precos publicos da API em 17/11/2026, US$ por milhao de tokens.
PRECOS = {
    "opus": {"in": 4.0, "out": 20.0, "cr": 0.20, "nome": "Opus"},
    "sonnet": {"in": 2.0, "out": 10.0, "cr": 0.10, "nome": "Sonnet"},
    "haiku": {"in": 0.10, "out": 0.50, "cr": 0.01, "nome": "Haiku"},
    "fable": {"in": 8.0, "out": 40.0, "cr": 0.20, "nome": "Fable"},
}
ESCRITA_5M, ESCRITA_1H = 1.25, 2.0
AGENTE = "ajudante-haiku"
PASTA_KIT = Path(os.environ.get("KIT_TOKENS_PASTA") or Path.home() / ".claude" / "kit-economia-de-tokens")
LEMBRETE_A_CADA = 10


def familia(modelo):
    m = (modelo or "").lower()
    for nome in ("fable", "opus", "sonnet", "haiku"):
        if nome in m:
            return nome
    return "sonnet"


def custo(c, fam=None):
    pr = PRECOS[fam or familia(c["modelo"])]
    cw5 = max(c["cw"] - c["cw1h"], 0)
    return (c["i"] * pr["in"] + cw5 * pr["in"] * ESCRITA_5M + c["cw1h"] * pr["in"] * ESCRITA_1H
            + c["cr"] * pr["cr"] + c["o"] * pr["out"]) / 1e6


def fmt(n):
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} mi".replace(".", ",")
    if n >= 10_000:
        return f"{n / 1000:.0f} mil"
    if n >= 1000:
        return f"{n / 1000:.1f} mil".replace(".", ",")
    return f"{n:.0f}"


def dolar(x):
    if 0 < x < 0.01:
        return "menos de US$ 0,01"
    return "US$ " + f"{x:.2f}".replace(".", ",")


def eh_humano(o):
    if o.get("isMeta") or o.get("isCompactSummary") or o.get("isSidechain"):
        return False
    org = o.get("origin")
    if isinstance(org, dict) and org.get("kind"):
        return org.get("kind") == "human"
    c = (o.get("message") or {}).get("content")
    if isinstance(c, str):
        return not c.lstrip().startswith("<")
    if isinstance(c, list):
        return not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
    return False


def ler(caminho, principal):
    """Devolve (chamadas, instante do ultimo pedido humano)."""
    chamadas, ultimo = {}, ""
    try:
        f = open(caminho, "r", encoding="utf-8", errors="replace")
    except OSError:
        return [], ""
    with f:
        for linha in f:
            eh_resposta = '"type":"assistant"' in linha
            eh_pedido = principal and '"type":"user"' in linha and '"tool_result"' not in linha
            if not (eh_resposta or eh_pedido):
                continue
            try:
                o = json.loads(linha)
            except Exception:
                continue
            t = o.get("type")
            if t == "user" and principal:
                if eh_humano(o):
                    ultimo = max(ultimo, o.get("timestamp") or "")
            elif t == "assistant":
                m = o.get("message") or {}
                u = m.get("usage") or {}
                modelo = m.get("model") or ""
                if not u or modelo.startswith("<"):
                    continue
                cc = u.get("cache_creation") or {}
                reg = {"ts": o.get("timestamp") or "", "modelo": modelo, "i": u.get("input_tokens") or 0,
                       "cw": u.get("cache_creation_input_tokens") or 0,
                       "cw1h": cc.get("ephemeral_1h_input_tokens") or 0,
                       "cr": u.get("cache_read_input_tokens") or 0, "o": u.get("output_tokens") or 0}
                mid = m.get("id") or o.get("uuid")
                ant = chamadas.get(mid)
                if ant is not None:
                    reg["o"] = max(reg["o"], ant["o"])
                    reg["ts"] = min(reg["ts"], ant["ts"]) if ant["ts"] else reg["ts"]
                chamadas[mid] = reg
    return list(chamadas.values()), ultimo


def soma(chamadas):
    lidos = sum(c["i"] + c["cw"] + c["cr"] for c in chamadas)
    return {"n": len(chamadas), "lidos": lidos, "escritos": sum(c["o"] for c in chamadas),
            "custo": sum(custo(c) for c in chamadas)}


def achar_sessao(cwd):
    raiz = Path.home() / ".claude" / "projects"
    pasta = raiz / re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
    cands = list(pasta.glob("*.jsonl")) if pasta.is_dir() else []
    if not cands:
        cands = list(raiz.glob("*/*.jsonl"))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def analisar(transcricao, sessao_inteira=False):
    transcricao = Path(transcricao)
    principais, ultimo = ler(transcricao, True)
    inicio = "" if sessao_inteira else ultimo
    principais = [c for c in principais if c["ts"] >= inicio]
    ajud, outros = [], []
    pasta_sub = transcricao.with_suffix("") / "subagents"
    if pasta_sub.is_dir():
        for arq in pasta_sub.glob("*.jsonl"):
            cs, _ = ler(arq, False)
            cs = [c for c in cs if c["ts"] >= inicio]
            if not cs:
                continue
            tipo = ""
            try:
                tipo = json.load(open(arq.with_suffix("").with_suffix(".meta.json"), encoding="utf-8")).get("agentType") or ""
            except Exception:
                pass
            (ajud if tipo == AGENTE or all(familia(c["modelo"]) == "haiku" for c in cs) else outros).extend(cs)
    por_fam = {}
    for c in principais:
        por_fam[familia(c["modelo"])] = por_fam.get(familia(c["modelo"]), 0) + custo(c)
    fam_principal = max(por_fam, key=por_fam.get) if por_fam else "opus"
    return {"principal": soma(principais), "fam": fam_principal, "ajudante": soma(ajud),
            "se_fosse_no_principal": sum(custo(c, fam_principal) for c in ajud), "outros": soma(outros)}


def frase(r, sessao_inteira=False):
    nome = PRECOS[r["fam"]]["nome"]
    onde = "nesta sessão" if sessao_inteira else "neste pedido"
    p, a, o = r["principal"], r["ajudante"], r["outros"]
    resto = (f"O {nome} fez o restante: {fmt(p['lidos'])} tokens lidos e {fmt(p['escritos'])} escritos, "
             f"cerca de {dolar(p['custo'])}.")
    if o["n"]:
        resto += f" Outros ajudantes, no modelo deles: {fmt(o['lidos'])} tokens, cerca de {dolar(o['custo'])}."
    if not a["n"]:
        return f"Observação do kit de tokens: {onde}, nada foi delegado ao ajudante no Haiku. " + resto.replace(
            "fez o restante", "fez tudo")
    sem = r["se_fosse_no_principal"]
    ganho = 100 * (1 - a["custo"] / sem) if sem else 0
    return (f"Observação do kit de tokens: {onde}, a leitura foi feita pelo ajudante no Haiku "
            f"({a['n']} chamadas, {fmt(a['lidos'])} tokens, cerca de {dolar(a['custo'])}). Nos preços do {nome}, "
            f"os mesmos tokens custariam cerca de {dolar(sem)}: ganho de cerca de {ganho:.0f}%. " + resto +
            " Valores em preço de API, só para comparar.")


def lembrete():
    """Conta os avisos e, de tempos em tempos, lembra que da para remover."""
    try:
        PASTA_KIT.mkdir(parents=True, exist_ok=True)
        arq = PASTA_KIT / "estado.json"
        n = 0
        if arq.is_file():
            n = int(json.load(open(arq, encoding="utf-8")).get("avisos", 0))
        n += 1
        json.dump({"avisos": n}, open(arq, "w", encoding="utf-8"))
        if n == 1 or n % LEMBRETE_A_CADA == 0:
            return (' Não está ajudando? Diga "sem ajudante" para desligar nesta sessão, ou remova o kit com: '
                    "bash ~/.claude/kit-economia-de-tokens/desinstalar.sh")
    except Exception:
        pass
    return ""


def main():
    args = sys.argv[1:]
    if "--hook" in args:
        try:
            entrada = json.load(sys.stdin)
            r = analisar(entrada.get("transcript_path"))
            if r["ajudante"]["n"]:
                print(json.dumps({"systemMessage": frase(r) + lembrete()}, ensure_ascii=False))
        except Exception:
            pass
        return 0
    inteira = "--sessao" in args
    caminho = next((a for a in args if not a.startswith("--")), None) or achar_sessao(os.getcwd())
    if not caminho:
        print("Não encontrei nenhuma sessão do Claude Code nesta máquina.")
        return 1
    print(frase(analisar(caminho, inteira), inteira))
    return 0


if __name__ == "__main__":
    sys.exit(main())
