#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_export_chat.py - Mostra quais conversas do chat (claude.ai) mais pesaram.

Entrada: o arquivo conversations.json da exportacao de dados do Claude
(Configuracoes > Privacidade > Exportar dados) ou o .zip inteiro.

O script nao imprime o texto das conversas. Ele mede tamanhos e conta
mensagens para estimar quanto o modelo precisou reler em cada conversa.

Uso:
  python3 analisar_export_chat.py conversations.json
  python3 analisar_export_chat.py export.zip --dias 30
  python3 analisar_export_chat.py conversations.json --anonimo   # esconde os titulos

Limites: a exportacao nao traz o modelo usado, o raciocinio, as ferramentas,
o conhecimento de Projetos nem as imagens. Os numeros sao um piso, bons para
comparar conversas entre si.
"""
import argparse
import json
import sys
import zipfile
from datetime import datetime, timedelta, timezone

CORTE_TURNOS = 15        # simulacao: abrir conversa nova a cada N mensagens suas
RESUMO_PASSAGEM = 500    # tokens de um resumo levado para a conversa nova


def tok(chars):
    return int(chars / 4)


def fmt(n):
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} mi".replace(".", ",")
    if n >= 10_000:
        return f"{n / 1000:.0f} mil"
    if n >= 1000:
        return f"{n / 1000:.1f} mil".replace(".", ",")
    return f"{n:.0f}"


def carregar(caminho):
    if caminho.lower().endswith(".zip"):
        with zipfile.ZipFile(caminho) as z:
            nome = next((n for n in z.namelist() if n.endswith("conversations.json")), None)
            if not nome:
                raise SystemExit("Não encontrei conversations.json dentro do .zip.")
            return json.loads(z.read(nome).decode("utf-8", errors="replace"))
    with open(caminho, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


def conversas(dados):
    if isinstance(dados, dict):
        for k in ("conversations", "chats", "data"):
            if isinstance(dados.get(k), list):
                return dados[k]
        return [dados]
    return dados if isinstance(dados, list) else []


def texto_de(msg):
    t = msg.get("text")
    chars = len(t) if isinstance(t, str) else 0
    c = msg.get("content")
    if isinstance(c, str):
        chars = max(chars, len(c))
    elif isinstance(c, list):
        soma = 0
        for b in c:
            if isinstance(b, dict):
                for k in ("text", "thinking", "input", "content"):
                    v = b.get(k)
                    if isinstance(v, str):
                        soma += len(v)
                    elif isinstance(v, (dict, list)):
                        soma += len(json.dumps(v, ensure_ascii=False))
        chars = max(chars, soma)
    return chars


def anexos_de(msg):
    chars = n = 0
    chaves = set()
    for k in ("attachments", "files"):
        for a in msg.get(k) or []:
            if not isinstance(a, dict):
                continue
            n += 1
            ec = a.get("extracted_content")
            if isinstance(ec, str):
                chars += len(ec)
            nome = a.get("file_name") or a.get("name")
            if nome:
                chaves.add((str(nome), a.get("file_size") or (len(ec) if isinstance(ec, str) else 0)))
    return chars, n, chaves


def humano(msg):
    quem = str(msg.get("sender") or msg.get("role") or "").lower()
    return quem in ("human", "user")


def data_de(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def analisar(conv):
    msgs = conv.get("chat_messages") or conv.get("messages") or []
    msgs = [m for m in msgs if isinstance(m, dict)]
    contexto = 0          # tokens acumulados na conversa
    relido = 0            # soma do contexto relido a cada mensagem sua
    novo = 0
    anexos_tok = anexos_n = anexos_relido = 0
    turnos = 0
    # simulacao: conversa nova a cada CORTE_TURNOS mensagens
    sim_ctx = sim_relido = 0
    restantes = sum(1 for m in msgs if humano(m))
    arquivos = set()
    for m in msgs:
        t = tok(texto_de(m))
        ac, an, chaves = anexos_de(m)
        arquivos |= chaves
        at = tok(ac)
        if humano(m):
            turnos += 1
            restantes -= 1
            if turnos > 1 and (turnos - 1) % CORTE_TURNOS == 0:
                sim_ctx = RESUMO_PASSAGEM
            contexto += t + at
            sim_ctx += t + at
            relido += contexto
            sim_relido += sim_ctx
            anexos_tok += at
            anexos_n += an
            anexos_relido += at * (restantes + 1)
        else:
            contexto += t
            sim_ctx += t
        novo += t + at
    d0 = data_de(conv.get("created_at"))
    d1 = data_de(conv.get("updated_at")) or d0
    return {"titulo": str(conv.get("name") or conv.get("title") or "(sem título)")[:48], "turnos": turnos,
            "mensagens": len(msgs), "novo": novo, "relido": relido, "final": contexto, "anexos_n": anexos_n,
            "anexos_tok": anexos_tok, "anexos_relido": anexos_relido, "sim": sim_relido, "inicio": d0, "arquivos": arquivos,
            "dias": max((d1 - d0).days, 0) if d0 and d1 else 0}


def main():
    ap = argparse.ArgumentParser(description="Mostra quais conversas do chat mais pesaram.")
    ap.add_argument("arquivo", help="conversations.json ou o .zip da exportação")
    ap.add_argument("--dias", type=int, default=30, help="considera conversas iniciadas nos últimos N dias (0 = todas)")
    ap.add_argument("--anonimo", action="store_true", help="não mostra os títulos das conversas")
    a = ap.parse_args()
    lista = [analisar(c) for c in conversas(carregar(a.arquivo)) if isinstance(c, dict)]
    lista = [c for c in lista if c["turnos"]]
    if a.dias:
        corte = datetime.now(timezone.utc) - timedelta(days=a.dias)
        lista = [c for c in lista if c["inicio"] is None or c["inicio"] >= corte]
    if not lista:
        print("Nenhuma conversa com mensagens no período. Tente --dias 0 ou confira o arquivo.")
        return 1
    total = sum(c["relido"] for c in lista) or 1
    novo = sum(c["novo"] for c in lista) or 1
    longas = [c for c in lista if c["turnos"] > CORTE_TURNOS]
    sim = sum(c["sim"] for c in lista)
    anex = sum(c["anexos_relido"] for c in lista)
    lista.sort(key=lambda c: -c["relido"])
    print("# Raio-x do chat")
    print(f"Período: {'últimos ' + str(a.dias) + ' dias' if a.dias else 'todo o histórico'} · {len(lista)} conversas · "
          f"{sum(c['turnos'] for c in lista)} mensagens suas")
    print()
    print("## Resumo")
    print(f"- Texto novo trocado: cerca de {fmt(novo)} tokens. Texto relido pelo modelo: cerca de {fmt(total)} tokens, "
          f"{total / novo:.0f} vezes o que foi escrito.")
    print(f"- Conversas com mais de {CORTE_TURNOS} mensagens suas: {len(longas)} de {len(lista)}. Elas respondem por "
          f"{100 * sum(c['relido'] for c in longas) / total:.0f}% de toda a releitura.")
    vezes = {}
    for c in lista:
        for ch in c["arquivos"]:
            vezes[ch] = vezes.get(ch, 0) + 1
    repetidos = sum(1 for v in vezes.values() if v > 1)
    print(f"- Anexos: {sum(c['anexos_n'] for c in lista)} arquivos, {repetidos} deles anexados em mais de uma conversa. "
          f"Reler anexos respondeu por cerca de {100 * anex / total:.0f}% da releitura (essa parte está dentro das "
          "conversas acima; os percentuais não se somam).")
    print(f"- Simulação: abrindo conversa nova a cada {CORTE_TURNOS} mensagens, com um resumo de "
          f"{RESUMO_PASSAGEM} tokens, a releitura cairia cerca de {100 * (1 - sim / total):.0f}%.")
    print()
    print("## Conversas mais pesadas")
    print("| # | Conversa | Mensagens suas | Dias aberta | Tamanho final | Relido no total | Parte | Anexos |")
    print("|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(lista[:10], 1):
        nome = f"conversa-{i}" if a.anonimo else c["titulo"].replace("|", "/")
        print(f"| {i} | {nome} | {c['turnos']} | {c['dias']} | {fmt(c['final'])} | {fmt(c['relido'])} | "
              f"{100 * c['relido'] / total:.0f}% | {c['anexos_n']} ({fmt(c['anexos_tok'])}) |")
    print()
    print("## Limites")
    print("- Estimativa por tamanho do texto (4 caracteres por token). A exportação não traz modelo, raciocínio, "
          "ferramentas, conectores, Projetos nem imagens, então o gasto real foi maior.")
    print("- Serve para comparar conversas e hábitos, não para calcular o limite do plano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
