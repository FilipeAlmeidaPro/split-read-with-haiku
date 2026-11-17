#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auditar_claude_code.py - Auditoria de tokens do Claude Code (somente leitura).

Le as configuracoes e os registros de sessao em ~/.claude e mostra para onde
os tokens foram. Nao altera nenhum arquivo, nao acessa a rede e nao imprime o
texto das conversas: so tamanhos, contagens e nomes de modelos, ferramentas,
skills, plugins e pastas de projeto.

Uso:
  python3 auditar_claude_code.py                # ultimos 14 dias
  python3 auditar_claude_code.py --dias 30
  python3 auditar_claude_code.py --anonimo      # troca nomes de pasta por projeto-1, projeto-2...
  python3 auditar_claude_code.py --json saida.json
  python3 auditar_claude_code.py --so-config    # nao le os registros de sessao

So usa a biblioteca padrao do Python 3.8+.
"""
import argparse
import bisect
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Precos publicos da API em 17/11/2026, em US$ por milhao de tokens. O plano
# nao cobra assim e a formula do limite nao e publica: os precos servem para
# COMPARAR causas entre si. Creditos de uso, esses sim, seguem esta tabela.
# Valores conferidos contra a estimativa de custo que o Claude Code grava.
# ---------------------------------------------------------------------------
PRECOS = {
    "opus": {"in": 4.0, "out": 20.0, "cr": 0.20},
    "sonnet": {"in": 2.0, "out": 10.0, "cr": 0.10},
    "haiku": {"in": 0.10, "out": 0.50, "cr": 0.01},
    "fable": {"in": 8.0, "out": 40.0, "cr": 0.20},
}
ESCRITA_5M, ESCRITA_1H = 1.25, 2.0     # gravar em cache custa mais que a entrada normal

CONTEXTO_LONGO = 150_000        # acima disso a conversa ja esta cara de carregar
RESULTADO_GRANDE = 40_000       # caracteres (cerca de 10 mil tokens) em uma saida de ferramenta
CARGA_INICIAL_ALTA = 25_000     # tokens antes da primeira resposta
LINHAS_CLAUDE_MD = 200          # limite recomendado na documentacao


def med_de(xs):
    return statistics.median(xs) if xs else 0


def tok(chars):
    """Estimativa grosseira: 4 caracteres por token."""
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


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b


def p(x):
    if 0 < x < 0.1:
        return "menos de 0,1%"
    return f"{x:.0f}%" if x >= 10 or x == 0 else f"{x:.1f}%".replace(".", ",")


def ler_json(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def ler_texto(caminho):
    try:
        return Path(caminho).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def familia(modelo):
    m = (modelo or "").lower()
    for nome in ("fable", "mythos", "opus", "sonnet", "haiku"):
        if nome in m:
            return "fable" if nome == "mythos" else nome
    return "outro"


def preco(modelo):
    return PRECOS.get(familia(modelo), PRECOS["sonnet"])


def modelo_caro(modelo):
    return familia(modelo) in ("opus", "fable")


def frontmatter(texto):
    m = re.match(r"^---\s*\n(.*?)\n---", texto or "", re.S)
    if not m:
        return {}
    out, chave = {}, None
    for linha in m.group(1).split("\n"):
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", linha)
        if mm and not linha.startswith((" ", "\t")):
            chave = mm.group(1)
            val = mm.group(2).strip()
            out[chave] = "" if val in (">", "|", ">-", "|-", ">+", "|+") else val.strip("\"'")
        elif chave and linha.strip():
            out[chave] = (out[chave] + " " + linha.strip()).strip()
    return out


# ---------------------------------------------------------------------------
# 1. Configuracao e inventario (o que existe antes de voce digitar)
# ---------------------------------------------------------------------------
def coletar_config(home, proj):
    camadas = [("usuário", home / ".claude" / "settings.json"),
               ("usuário (local)", home / ".claude" / "settings.local.json")]
    if proj.resolve() != home.resolve():
        camadas += [("projeto", proj / ".claude" / "settings.json"),
                    ("projeto (local)", proj / ".claude" / "settings.local.json")]
    efetivo, plugins_ativos, hooks, origem = {}, {}, [], {}
    env_interesse = ("MAX_THINKING_TOKENS", "CLAUDE_CODE_EFFORT_LEVEL", "CLAUDE_CODE_SUBAGENT_MODEL",
                     "CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "ANTHROPIC_MODEL", "ENABLE_TOOL_SEARCH",
                     "DISABLE_AUTO_COMPACT", "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "CLAUDE_CODE_PROMPT_CACHE_TTL",
                     "SLASH_COMMAND_TOOL_CHAR_BUDGET")
    env = {}
    chave_api = False
    for nome, caminho in camadas:
        d = ler_json(caminho)
        if not isinstance(d, dict):
            continue
        for k in ("model", "effortLevel", "maxEffortLevel", "alwaysThinkingEnabled", "autoCompactEnabled",
                  "autoCompactWindow", "idleCompaction", "disableAllHooks", "skillListingBudgetFraction",
                  "promptCacheTtl", "cleanupPeriodDays"):
            if k in d:
                efetivo[k] = d[k]
                origem[k] = nome
        ms = d.get("modelSettings")
        if isinstance(ms, dict):
            efetivo.setdefault("modelSettings", {})
            for modelo, cfg in ms.items():
                if isinstance(cfg, dict) and "effortLevel" in cfg:
                    efetivo["modelSettings"][modelo] = cfg["effortLevel"]
        if isinstance(d.get("enabledPlugins"), dict):
            plugins_ativos.update(d["enabledPlugins"])
        e = d.get("env")
        if isinstance(e, dict):
            for k in env_interesse:
                if k in e:
                    env[k] = str(e[k])
            if "ANTHROPIC_API_KEY" in e:
                chave_api = True
        h = d.get("hooks")
        if isinstance(h, dict):
            for evento, grupos in h.items():
                for g in grupos if isinstance(grupos, list) else []:
                    n = len(g.get("hooks") or []) if isinstance(g, dict) else 0
                    hooks.append({"origem": f"settings ({nome})", "evento": evento,
                                  "matcher": (g.get("matcher") or "*") if isinstance(g, dict) else "*", "comandos": n})
    for k in env_interesse:
        if k in os.environ and k not in env:
            env[k] = os.environ[k]
    if os.environ.get("ANTHROPIC_API_KEY"):
        chave_api = True
    return {"efetivo": efetivo, "origem": origem, "env": env, "chave_api_definida": chave_api,
            "plugins_ativos": plugins_ativos, "hooks_settings": hooks}


def skills_em(pasta, origem):
    out = []
    if not pasta.is_dir():
        return out
    for d in sorted(pasta.iterdir()):
        f = d / "SKILL.md"
        if not f.is_file():
            continue
        t = ler_texto(f) or ""
        fm = frontmatter(t)
        desc = (fm.get("description", "") + " " + fm.get("when_to_use", "")).strip()
        out.append({"nome": fm.get("name") or d.name, "origem": origem, "desc_chars": len(desc),
                    "corpo_chars": len(t), "sem_modelo": fm.get("disable-model-invocation", "").lower() == "true"})
    return out


def agentes_em(pasta, origem):
    out = []
    if not pasta.is_dir():
        return out
    for f in sorted(pasta.glob("*.md")):
        fm = frontmatter(ler_texto(f) or "")
        out.append({"nome": fm.get("name") or f.stem, "origem": origem,
                    "desc_chars": len(fm.get("description", "")), "modelo": fm.get("model") or "herda"})
    return out


def memoria(caminho, rotulo, vistos, nivel=0):
    out = []
    try:
        chave = str(Path(caminho).resolve())
    except Exception:
        return out
    if chave in vistos or nivel > 3:
        return out
    t = ler_texto(caminho)
    if t is None:
        return out
    vistos.add(chave)
    out.append({"arquivo": rotulo, "chars": len(t), "linhas": t.count("\n") + 1})
    for m in re.finditer(r"(?m)(?:^|\s)@(~?[\w./-]+\.(?:md|txt))", t):
        alvo = m.group(1)
        alvo_p = Path(os.path.expanduser(alvo)) if alvo.startswith("~") else Path(caminho).parent / alvo
        out += memoria(alvo_p, f"{rotulo} → @{Path(alvo).name}", vistos, nivel + 1)
    return out


def coletar_inventario(home, proj, cfg):
    cl = home / ".claude"
    inv = {"skills": [], "agentes": [], "memoria": [], "mcp": [], "plugins": [], "hooks": list(cfg["hooks_settings"])}
    inv["skills"] += skills_em(cl / "skills", "usuário")
    inv["agentes"] += agentes_em(cl / "agents", "usuário")
    vistos = set()
    inv["memoria"] += memoria(cl / "CLAUDE.md", "~/.claude/CLAUDE.md", vistos)
    if proj.resolve() != home.resolve():
        inv["skills"] += skills_em(proj / ".claude" / "skills", "projeto")
        inv["agentes"] += agentes_em(proj / ".claude" / "agents", "projeto")
        for rel in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
            inv["memoria"] += memoria(proj / rel, f"projeto/{rel}", vistos)

    # Plugins instalados e o que cada um traz
    inst = (ler_json(cl / "plugins" / "installed_plugins.json") or {}).get("plugins") or {}
    for chave, lista in inst.items():
        if not isinstance(lista, list) or not lista:
            continue
        raiz = Path(str(lista[-1].get("installPath") or ""))
        ativo = cfg["plugins_ativos"].get(chave) is True
        nome = chave.split("@")[0]
        item = {"nome": nome, "ativo": ativo, "skills": 0, "desc_chars": 0, "agentes": 0, "comandos": 0,
                "hooks": [], "mcp": []}
        if raiz.is_dir():
            sk = skills_em(raiz / "skills", f"plugin {nome}")
            item["skills"] = len(sk)
            item["desc_chars"] = sum(s["desc_chars"] for s in sk)
            ag = agentes_em(raiz / "agents", f"plugin {nome}")
            item["agentes"] = len(ag)
            item["comandos"] = len(list((raiz / "commands").glob("*.md"))) if (raiz / "commands").is_dir() else 0
            h = (ler_json(raiz / "hooks" / "hooks.json") or {}).get("hooks") or {}
            for evento, grupos in h.items():
                n = sum(len(g.get("hooks") or []) for g in grupos if isinstance(g, dict))
                item["hooks"].append({"evento": evento, "comandos": n})
                if ativo:
                    inv["hooks"].append({"origem": f"plugin {nome}", "evento": evento, "matcher": "*", "comandos": n})
            m = (ler_json(raiz / ".mcp.json") or {})
            item["mcp"] = sorted((m.get("mcpServers") or m).keys()) if isinstance(m, dict) else []
            if ativo:
                inv["skills"] += sk
                inv["agentes"] += ag
                inv["mcp"] += [{"nome": n, "escopo": f"plugin {nome}"} for n in item["mcp"]]
        inv["plugins"].append(item)

    # Servidores MCP (so nomes; nunca comandos, URLs ou variaveis)
    cj = ler_json(home / ".claude.json") or {}
    for n in sorted((cj.get("mcpServers") or {}).keys()):
        inv["mcp"].append({"nome": n, "escopo": "usuário (todas as sessões)"})
    pj = (cj.get("projects") or {}).get(str(proj)) or {}
    for n in sorted((pj.get("mcpServers") or {}).keys()):
        inv["mcp"].append({"nome": n, "escopo": "local (este projeto)"})
    for n in sorted(((ler_json(proj / ".mcp.json") or {}).get("mcpServers") or {}).keys()):
        inv["mcp"].append({"nome": n, "escopo": "projeto (.mcp.json)"})

    # Uso de skills registrado pelo proprio Claude Code
    uso = cj.get("skillUsage") or {}
    inv["skill_uso"] = {k: (v.get("usageCount", 0) if isinstance(v, dict) else 0) for k, v in uso.items()}
    return inv


# ---------------------------------------------------------------------------
# 2. Uso real (registros de sessao em ~/.claude/projects)
# ---------------------------------------------------------------------------
def iso(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def tamanho_resultado(c):
    if isinstance(c, str):
        return len(c), 0
    chars = img = 0
    for b in c if isinstance(c, list) else []:
        if isinstance(b, dict):
            if b.get("type") == "text":
                chars += len(b.get("text") or "")
            elif b.get("type") == "image":
                img += 1
    return chars, img


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


def origem_hook(att):
    cmd = str(att.get("command") or "")
    m = re.search(r"plugins[/\\]cache[/\\][^/\\]+[/\\]([^/\\]+)[/\\]", cmd)
    if m:
        return f"plugin {m.group(1)}"
    return "plugin (não identificado)" if "CLAUDE_PLUGIN_ROOT" in cmd else "settings ou plugin"


def coletar_uso(home, dias):
    raiz = home / ".claude" / "projects"
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    corte_iso = corte.strftime("%Y-%m-%dT%H:%M:%S")
    corte_epoch = corte.timestamp()
    S = defaultdict(lambda: {"proj": "?", "calls": {}, "humanos": [], "hooks": {}, "compact": [],
                             "base": None, "custo": 0.0, "entrada": set(), "imagens": 0, "coladas": 0, "lst": {}})
    ferramentas = defaultdict(lambda: [0, 0, 0, 0])     # vezes, chars, maior, grandes
    skills_carregadas = defaultdict(lambda: [0, 0])     # vezes, chars
    arquivos = lidos = 0
    if not raiz.is_dir():
        return None
    for arq in raiz.rglob("*.jsonl"):
        try:
            if arq.stat().st_mtime < corte_epoch:
                continue
        except OSError:
            continue
        arquivos += 1
        sub_arquivo = arq.parent.name == "subagents"
        sid = arq.parent.parent.name if sub_arquivo else arq.stem
        s = S[sid]
        nomes_tool = {}
        try:
            f = open(arq, "r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with f:
            for linha in f:
                if len(linha) < 20:
                    continue
                try:
                    o = json.loads(linha)
                except Exception:
                    continue
                if not isinstance(o, dict):
                    continue
                lidos += 1
                t = o.get("type")
                ts = o.get("timestamp") or ""
                if o.get("cwd") and s["proj"] == "?" and not sub_arquivo:
                    s["proj"] = Path(str(o["cwd"])).name or "?"
                if o.get("entrypoint"):
                    s["entrada"].add(str(o["entrypoint"]))

                if t == "assistant":
                    m = o.get("message") or {}
                    u = m.get("usage") or {}
                    modelo = m.get("model") or ""
                    if not u or modelo.startswith("<"):
                        continue
                    for b in m.get("content") or []:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            nomes_tool[b.get("id")] = b.get("name") or "?"
                    cc = u.get("cache_creation") or {}
                    cw = u.get("cache_creation_input_tokens") or 0
                    cw1h = cc.get("ephemeral_1h_input_tokens") or 0
                    reg = {"ts": ts, "modelo": modelo, "i": u.get("input_tokens") or 0, "cw": cw, "cw1h": cw1h,
                           "cr": u.get("cache_read_input_tokens") or 0, "o": u.get("output_tokens") or 0,
                           "th": (u.get("output_tokens_details") or {}).get("thinking_tokens") or 0,
                           "sub": bool(sub_arquivo or o.get("isSidechain")), "effort": o.get("effort"),
                           "tools": sum(1 for b in (m.get("content") or [])
                                        if isinstance(b, dict) and b.get("type") == "tool_use")}
                    reg["ctx"] = reg["i"] + reg["cw"] + reg["cr"]
                    mid = m.get("id") or o.get("uuid")
                    ant = s["calls"].get(mid)
                    if ant is not None:          # mesma resposta gravada em varios blocos
                        reg["tools"] += ant["tools"]
                        reg["o"] = max(reg["o"], ant["o"])
                        reg["th"] = max(reg["th"], ant["th"])
                        reg["ts"] = min(reg["ts"], ant["ts"]) if ant["ts"] else reg["ts"]
                    s["calls"][mid] = reg
                    if not reg["sub"] and s["base"] is None and reg["ctx"] > 0:
                        s["base"] = reg["ctx"]

                elif t == "user":
                    if ts < corte_iso:
                        continue
                    c = (o.get("message") or {}).get("content")
                    if isinstance(c, list):
                        for b in c:
                            if not isinstance(b, dict):
                                continue
                            if b.get("type") == "tool_result":
                                chars, img = tamanho_resultado(b.get("content"))
                                nome = nomes_tool.get(b.get("tool_use_id"), "?")
                                if nome.startswith("mcp__"):
                                    nome = "MCP " + nome.split("__")[1]
                                ft = ferramentas[nome]
                                ft[0] += 1
                                ft[1] += chars
                                ft[2] = max(ft[2], chars)
                                ft[3] += chars >= RESULTADO_GRANDE
                                s["imagens"] += img
                            elif b.get("type") == "image":
                                s["coladas"] += 1
                    if not sub_arquivo and eh_humano(o):
                        s["humanos"].append(ts)

                elif t == "attachment":
                    a = o.get("attachment") or {}
                    at = a.get("type")
                    rend = o.get("rendered") or []
                    rchars = sum(len(r.get("content") or "") for r in rend if isinstance(r, dict))
                    if at in ("hook_success", "hook_additional_context"):
                        if ts < corte_iso:
                            continue
                        c = a.get("content")
                        chars = sum(len(x) for x in c if isinstance(x, str)) if isinstance(c, list) else len(c or "")
                        if chars <= 0:
                            continue
                        chave = (a.get("toolUseID"), a.get("hookEvent"))
                        ant = s["hooks"].get(chave)
                        org = origem_hook(a)
                        if ant is None or chars > ant[2]:
                            if ant is not None and org == "settings ou plugin":
                                org = ant[3]
                            s["hooks"][chave] = (ts, a.get("hookEvent") or "?", chars, org)
                    elif sub_arquivo:
                        pass
                    elif at == "skill_listing" and a.get("isInitial"):
                        s["lst"].setdefault("skills", len(a.get("content") or ""))
                        s["lst"].setdefault("skills_qtd", a.get("skillCount") or 0)
                    elif at == "deferred_tools_delta":
                        s["lst"].setdefault("ferramentas", rchars)
                    elif at == "mcp_instructions_delta":
                        s["lst"].setdefault("mcp", rchars)
                    elif at == "instructions":
                        s["lst"].setdefault("memoria", rchars)
                    elif at == "invoked_skills" and ts >= corte_iso:
                        for sk in a.get("skills") or []:
                            if isinstance(sk, dict):
                                r = skills_carregadas[sk.get("name") or "?"]
                                r[0] += 1
                                r[1] += len(sk.get("content") or "")

                elif t == "system" and o.get("subtype") == "compact_boundary":
                    if ts >= corte_iso:
                        cm = o.get("compactMetadata") or {}
                        s["compact"].append((ts, cm.get("trigger") or "?", cm.get("preTokens") or 0))

                elif t == "cost-state":
                    try:
                        s["custo"] = max(s["custo"], float(o.get("totalCostUSD") or 0))
                    except (TypeError, ValueError):
                        pass

    # Mantem so as chamadas dentro da janela
    for s in S.values():
        s["calls"] = sorted((c for c in s["calls"].values() if c["ts"] >= corte_iso), key=lambda c: c["ts"])
    S = {k: v for k, v in S.items() if v["calls"]}
    listagem = {k: [v["lst"][k] for v in S.values() if k in v["lst"]]
                for k in ("skills", "skills_qtd", "ferramentas", "mcp", "memoria")}
    listagem["hooks_inicio"] = [sum(h[2] for h in v["hooks"].values() if h[1] == "SessionStart") for v in S.values()]
    return {"sessoes": S, "ferramentas": ferramentas, "skills_carregadas": skills_carregadas,
            "listagem": listagem, "arquivos": arquivos, "linhas": lidos, "dias": dias}


def peso_call(c):
    pr = preco(c["modelo"])
    cw5 = max(c["cw"] - c["cw1h"], 0)
    return (c["i"] * pr["in"] + cw5 * pr["in"] * ESCRITA_5M + c["cw1h"] * pr["in"] * ESCRITA_1H
            + c["cr"] * pr["cr"] + c["o"] * pr["out"]) / 1e6


def analisar_uso(uso):
    S = uso["sessoes"]
    por_modelo = defaultdict(lambda: {"calls": 0, "i": 0, "cw": 0, "cr": 0, "o": 0, "th": 0, "peso": 0.0, "sub": 0})
    A = {"total_peso": 0.0, "total_ctx": 0, "fixo_ctx": 0, "fixo_peso": 0.0, "longo_peso": 0.0, "longo_calls": 0,
         "calls": 0, "calls_sub": 0, "sub_peso": 0.0, "sub_modelos": Counter(), "effort": Counter(),
         "reescritas": [], "leves": {"turnos": 0, "peso": 0.0, "turnos_topo": 0, "peso_topo": 0.0},
         "hooks": defaultdict(lambda: [0, 0, 0]), "hook_releituras": 0, "compact": [], "imagens": 0,
         "dias_ativos": set(), "bases": [], "sessoes": [], "humanos": 0, "custo": 0.0, "entrada": Counter(),
         "sem_limpar": 0, "coladas": 0, "cedo": [0.0, 0], "topo_peso": 0.0}
    for sid, s in S.items():
        principais = [c for c in s["calls"] if not c["sub"]]
        subs = [c for c in s["calls"] if c["sub"]]
        base = s["base"] or (principais[0]["ctx"] if principais else 0)
        if principais:
            A["bases"].append(base)
        peso_s = 0.0
        pico = 0
        fam = Counter()
        ant = None
        for c in s["calls"]:
            w = peso_call(c)
            peso_s += w
            pm = por_modelo[c["modelo"]]
            pm["calls"] += 1
            for k in ("i", "cw", "cr", "o", "th"):
                pm[k] += c[k]
            pm["peso"] += w
            pm["sub"] += c["sub"]
            if modelo_caro(c["modelo"]):
                A["topo_peso"] += w
            A["dias_ativos"].add(c["ts"][:10])
            if c["effort"]:
                A["effort"][str(c["effort"])] += 1
        for c in subs:
            A["calls_sub"] += 1
            A["sub_peso"] += peso_call(c)
            A["sub_modelos"][familia(c["modelo"])] += 1
        for n, c in enumerate(principais):
            w = peso_call(c)
            fam[familia(c["modelo"])] += w
            A["calls"] += 1
            if n < 10:
                A["cedo"][0] += w
                A["cedo"][1] += 1
            A["total_ctx"] += c["ctx"]
            fixo = min(base, c["ctx"])
            A["fixo_ctx"] += fixo
            A["fixo_peso"] += fixo * preco(c["modelo"])["cr"] / 1e6
            pico = max(pico, c["ctx"])
            if c["ctx"] >= CONTEXTO_LONGO:
                A["longo_peso"] += w
                A["longo_calls"] += 1
            # Reescrita de cache: o contexto inteiro foi regravado em vez de relido
            if ant is not None and c["ctx"] >= 30_000 and c["cw"] >= 0.5 * c["ctx"]:
                d1, d0 = iso(c["ts"]), iso(ant["ts"])
                gap = (d1 - d0).total_seconds() / 60 if d1 and d0 else 0
                motivo = ("troca de modelo" if familia(c["modelo"]) != familia(ant["modelo"])
                          else "pausa de mais de 1 hora" if gap >= 60
                          else "pausa entre 5 e 60 minutos" if gap >= 5 else "outra causa")
                pr = preco(c["modelo"])
                extra = c["cw"] * (pr["in"] * (ESCRITA_1H if c["cw1h"] else ESCRITA_5M) - pr["cr"]) / 1e6
                A["reescritas"].append({"motivo": motivo, "tokens": c["cw"], "extra": extra})
            ant = c
        # Turnos: do envio de uma pessoa ate o proximo envio
        hs = sorted(s["humanos"])
        turnos = defaultdict(list)
        for c in principais:
            i = bisect.bisect_right(hs, c["ts"]) - 1
            turnos[i].append(c)
        A["humanos"] += len(hs)
        for cs in turnos.values():
            w = sum(peso_call(c) for c in cs)
            visivel = sum(max(c["o"] - c["th"], 0) for c in cs)
            ferr = sum(c["tools"] for c in cs)
            topo = any(modelo_caro(c["modelo"]) for c in cs)
            if topo:
                A["leves"]["turnos_topo"] += 1
                A["leves"]["peso_topo"] += w
                if ferr <= 2 and visivel <= 500:
                    A["leves"]["turnos"] += 1
                    A["leves"]["peso"] += w
        # Hooks: entram uma vez e sao relidos em todas as chamadas seguintes
        tss = [c["ts"] for c in principais]
        for (_, evento, chars, org) in s["hooks"].values():
            h = A["hooks"][(evento, org)]
            h[0] += 1
            h[1] += chars
        for (ts_h, evento, chars, org) in s["hooks"].values():
            depois = len(tss) - bisect.bisect_left(tss, ts_h)
            A["hooks"][(evento, org)][2] += tok(chars) * depois
            A["hook_releituras"] += tok(chars) * depois
        for cpt in s["compact"]:
            A["compact"].append(cpt)
        if pico >= CONTEXTO_LONGO and not s["compact"]:
            A["sem_limpar"] += 1
        A["imagens"] += s["imagens"]
        A["coladas"] += s["coladas"]
        A["custo"] += s["custo"]
        for e in s["entrada"]:
            A["entrada"][e] += 1
        A["total_peso"] += peso_s
        ini = s["calls"][0]["ts"]
        fim = s["calls"][-1]["ts"]
        d0, d1 = iso(ini), iso(fim)
        A["sessoes"].append({"proj": s["proj"], "dia": ini[:10], "calls": len(principais), "turnos": len(hs),
                             "pico": pico, "peso": peso_s, "compact": len(s["compact"]),
                             "modelo": fam.most_common(1)[0][0] if fam else "?",
                             "horas": (d1 - d0).total_seconds() / 3600 if d0 and d1 else 0})
    A["por_modelo"] = dict(por_modelo)
    A["sessoes"].sort(key=lambda x: -x["peso"])
    return A


# ---------------------------------------------------------------------------
# 3. Achados: cada um com evidencia, impacto estimado e a correcao indicada
# ---------------------------------------------------------------------------
def achados(cfg, inv, uso, A):
    out = []

    def add(chave, titulo, evidencia, impacto, parcela, correcao):
        out.append({"id": chave, "titulo": titulo, "evidencia": evidencia, "impacto": impacto,
                    "parcela": parcela, "correcao": correcao})

    ef = cfg["efetivo"]
    if cfg["chave_api_definida"]:
        add("chave-api", "ANTHROPIC_API_KEY está definida",
            "Com essa variável definida, o Claude Code cobra da chave de API e não do plano.",
            "Pode gerar cobrança à parte sem você perceber.", None, "correcoes.md#chave-api")

    def origem_provavel(evento, org):
        if org.startswith("plugin ") and "não identificado" not in org:
            return org
        cand = [pl["nome"] for pl in inv["plugins"] if any(h["evento"] == evento for h in pl["hooks"])]
        if any(h["evento"] == evento and h["origem"].startswith("settings") for h in inv["hooks"]):
            cand.append("settings")
        return "provável: " + ", ".join(cand) if cand else "origem não identificada"

    if A:
        T = A["total_peso"] or 1.0
        fator = 1 - PRECOS["sonnet"]["out"] / PRECOS["opus"]["out"]
        topo = pct(A["topo_peso"], T)
        if topo >= 70:
            add("modelo-padrao", "Quase tudo roda no modelo mais caro",
                f"{p(topo)} do custo do período foi em Opus ou Fable. Segundo a documentação, o padrão do Claude Code "
                "nos planos pagos é o Opus, e o Sonnet dá conta da maior parte das tarefas de código.",
                f"A mesma sessão no Sonnet custa cerca de {100 * fator:.0f}% menos. Movendo metade do trabalho, a "
                f"economia seria de cerca de {p(topo * 0.5 * fator)} do total.",
                topo * 0.5 * fator, "correcoes.md#modelo")
        # Modelo caro em tarefas leves
        lv = A["leves"]
        if lv["turnos_topo"] >= 5 and lv["turnos"] >= 3:
            economia = lv["peso"] * fator
            add("modelo-leve", "Tarefas leves rodando no modelo mais caro",
                f"{lv['turnos']} de {lv['turnos_topo']} pedidos feitos em Opus ou Fable usaram até 2 ferramentas e "
                f"tiveram resposta curta. Eles somam {p(pct(lv['peso'], T))} do custo do período.",
                f"Feitos no Sonnet, custariam cerca de {p(pct(economia, T))} a menos do total.",
                pct(economia, T), "correcoes.md#modelo")
        # Raciocinio
        th = sum(m["th"] * preco(k)["out"] / 1e6 for k, m in A["por_modelo"].items())
        saida = sum(m["o"] for m in A["por_modelo"].values()) or 1
        th_tok = sum(m["th"] for m in A["por_modelo"].values())
        altos = sum(v for k, v in A["effort"].items() if k in ("high", "xhigh", "max"))
        tot_e = sum(A["effort"].values())
        if pct(th, T) >= 10 or (tot_e and pct(altos, tot_e) >= 50):
            nivel = ", ".join(f"{k} em {p(pct(v, tot_e))}" for k, v in A["effort"].most_common(3)) if tot_e else "não registrado"
            add("effort", "Raciocínio (effort) alto como padrão",
                f"Nível usado nas chamadas: {nivel}. Raciocínio foi {p(pct(th_tok, saida))} de tudo que o modelo "
                f"escreveu ({fmt(th_tok)} tokens).",
                f"Raciocínio responde por cerca de {p(pct(th, T))} do custo do período. O padrão dos modelos é medium.",
                pct(th, T) * 0.5, "correcoes.md#effort")
        # Conversas longas
        if pct(A["longo_peso"], T) >= 15:
            add("conversa-longa", "Conversas que continuam depois de ficarem grandes",
                f"{A['longo_calls']} chamadas ({p(pct(A['longo_calls'], A['calls']))}) foram feitas com mais de "
                f"{fmt(CONTEXTO_LONGO)} tokens de contexto. {A['sem_limpar']} sessões passaram desse tamanho sem "
                f"nenhuma compactação. Em média, cada chamada releu {fmt(A['total_ctx'] / max(A['calls'], 1))} tokens.",
                f"Essas chamadas somam {p(pct(A['longo_peso'], T))} do custo do período.",
                pct(A["longo_peso"], T) * 0.5, "correcoes.md#conversa-longa")
        # Reescritas de cache
        rs = A["reescritas"]
        if len(rs) >= 3:
            motivos = Counter(r["motivo"] for r in rs)
            extra = sum(r["extra"] for r in rs)
            add("cache", "Contexto regravado em vez de relido do cache",
                f"{len(rs)} vezes o contexto inteiro foi regravado ({fmt(sum(r['tokens'] for r in rs))} tokens). "
                "Motivos: " + ", ".join(f"{m} ({n})" for m, n in motivos.most_common()) + ".",
                f"Cerca de {p(pct(extra, T))} do custo do período foi regravação que dava para evitar.",
                pct(extra, T), "correcoes.md#cache")
        # Carga fixa
        if A["bases"]:
            med = statistics.median(A["bases"])
            lst = uso["listagem"]
            partes = {"listagem de skills": tok(med_de(lst["skills"])),
                      "nomes de ferramentas e conectores": tok(med_de(lst["ferramentas"])),
                      "instruções de servidores MCP": tok(med_de(lst["mcp"])),
                      "arquivos de memória": tok(med_de(lst["memoria"])),
                      "hooks de início de sessão": tok(med_de(lst["hooks_inicio"]))}
            seu = sum(partes.values())
            if med >= CARGA_INICIAL_ALTA and seu >= 4000:
                det = ", ".join(f"{k} {fmt(v)}" for k, v in sorted(partes.items(), key=lambda kv: -kv[1]) if v)
                parte = pct(A["fixo_peso"], T) * min(seu / med, 1.0)
                add("carga-fixa", "Carga inicial alta em toda sessão",
                    f"Cada sessão começa com cerca de {fmt(med)} tokens antes da primeira resposta (mediana). "
                    f"Você controla cerca de {fmt(seu)} deles ({det}). O restante é a base do aplicativo.",
                    f"Reler a carga inicial responde por cerca de {p(pct(A['fixo_peso'], T))} do custo do período; "
                    f"a parte que você controla, por cerca de {p(parte)}.",
                    parte, "correcoes.md#carga-fixa")
        # Hooks
        hk = A["hooks"]
        tot_chars = sum(v[1] for v in hk.values())
        if tot_chars >= 20_000:
            maior = sorted(hk.items(), key=lambda kv: -kv[1][2])[:3]
            det = "; ".join(f"{ev} ({origem_provavel(ev, org)}): {v[0]} vezes, {fmt(tok(v[1]))} tokens"
                            for (ev, org), v in maior)
            parcela = pct(A["hook_releituras"], A["total_ctx"])
            add("hooks", "Hooks injetando texto no contexto",
                f"{det}. Cada injeção fica na conversa e é relida nas chamadas seguintes.",
                f"Somando as releituras, {p(parcela)} de tudo que o modelo leu no período veio de hooks.",
                pct(A["hook_releituras"] * (A["fixo_peso"] / A["fixo_ctx"] if A["fixo_ctx"] else 0), T),
                "correcoes.md#hooks")
        # Saidas grandes de ferramentas
        grandes = sorted(((n, v) for n, v in uso["ferramentas"].items() if v[3]), key=lambda kv: -kv[1][3])
        if sum(v[3] for _, v in grandes) >= 5:
            det = "; ".join(f"{n}: {v[3]} saídas grandes, maior com {fmt(tok(v[2]))} tokens" for n, v in grandes[:4])
            add("saidas-grandes", "Saídas de ferramenta muito grandes",
                f"{sum(v[3] for _, v in grandes)} resultados passaram de {fmt(tok(RESULTADO_GRANDE))} tokens. {det}.",
                "Cada um fica no contexto e é relido até a conversa ser limpa.", None, "correcoes.md#saidas-grandes")
        # Subagentes
        if pct(A["sub_peso"], T) >= 15:
            fam = ", ".join(f"{k} ({p(pct(v, A['calls_sub']))})" for k, v in A["sub_modelos"].most_common(3))
            add("subagentes", "Subagentes rodando no mesmo modelo caro",
                f"Subagentes fizeram {A['calls_sub']} chamadas. Modelos: {fam}. Por padrão eles herdam o modelo da conversa.",
                f"Somam {p(pct(A['sub_peso'], T))} do custo do período.", pct(A["sub_peso"], T) * 0.4,
                "correcoes.md#subagentes")
        # Compactacao tardia
        autos = [c for c in A["compact"] if c[1] == "auto"]
        if autos:
            med = statistics.median([c[2] for c in autos])
            if med >= 300_000:
                add("compactacao", "Compactação só acontece quando o contexto está no limite",
                    f"{len(autos)} compactações automáticas, com mediana de {fmt(med)} tokens no momento da compactação.",
                    "Até lá, cada chamada carrega a conversa inteira.", None, "correcoes.md#conversa-longa")
        if A["imagens"] + A["coladas"] >= 10:
            add("imagens", "Muitas imagens no contexto",
                f"{A['coladas']} imagens coladas por você e {A['imagens']} devolvidas por ferramentas "
                "(capturas de tela, por exemplo).",
                "Cada imagem fica no contexto e é relida até a conversa ser limpa.", None, "correcoes.md#saidas-grandes")

    # Inventario
    sk = inv["skills"]
    usadas = inv.get("skill_uso") or {}
    nunca = [s["nome"] for s in sk if s["origem"] == "usuário" and not usadas.get(s["nome"])]
    lst = uso["listagem"]["skills"] if uso else []
    lst_med = statistics.median(lst) if lst else sum(s["desc_chars"] for s in sk)
    if len(sk) >= 40 or lst_med >= 8_000:
        fam = Counter(s["nome"].split("-")[0] for s in sk)
        grupos = ", ".join(f"{k}-* ({v})" for k, v in fam.most_common(3) if v >= 4)
        add("skills", "Skills demais na listagem",
            f"{len(sk)} skills ativas; a listagem ocupa cerca de {fmt(tok(lst_med))} tokens em toda sessão. "
            f"{len(nunca)} skills de usuário nunca foram usadas." + (f" Maiores grupos: {grupos}." if grupos else ""),
            "O orçamento da listagem é de cerca de 1% da janela de contexto (uns 8 mil caracteres num modelo de "
            f"200 mil tokens) e a sua tem cerca de {fmt(lst_med)} caracteres. Quando estoura, as descrições das "
            "skills menos usadas são cortadas e o Claude deixa de saber quando usá-las.", None, "correcoes.md#skills")
    mem_linhas = max((m["linhas"] for m in inv["memoria"]), default=0)
    mem_chars = sum(m["chars"] for m in inv["memoria"])
    if mem_linhas > LINHAS_CLAUDE_MD or mem_chars >= 12_000:
        add("claude-md", "CLAUDE.md grande",
            f"Arquivos de memória somam cerca de {fmt(tok(mem_chars))} tokens; o maior tem {mem_linhas} linhas "
            f"(a documentação recomenda menos de {LINHAS_CLAUDE_MD}).",
            "Carregado inteiro no início de toda sessão.", None, "correcoes.md#claude-md")
    mcp_u = [m for m in inv["mcp"] if m["escopo"].startswith("usuário")]
    if len(mcp_u) >= 3:
        add("mcp", "Servidores MCP ligados em todas as sessões",
            f"{len(mcp_u)} servidores no escopo de usuário: " + ", ".join(m["nome"] for m in mcp_u[:6]) + ".",
            "Nomes de ferramentas e instruções de cada servidor entram em toda sessão, mesmo sem uso.", None,
            "correcoes.md#mcp")
    por_msg = [h for h in inv["hooks"] if h["evento"] in ("UserPromptSubmit", "PreToolUse", "PostToolUse")]
    if por_msg and not any(a["id"] == "hooks" for a in out):
        det = ", ".join(sorted({f"{h['origem']} ({h['evento']})" for h in por_msg})[:5])
        add("hooks-config", "Hooks que rodam a cada mensagem ou ferramenta",
            f"Configurados hoje: {det}.", "Podem injetar texto no contexto a cada execução; confira com /hooks.",
            None, "correcoes.md#hooks")
    out.sort(key=lambda a: -(a["parcela"] if a["parcela"] is not None else -1))
    return out


# ---------------------------------------------------------------------------
# 4. Relatorio
# ---------------------------------------------------------------------------
def relatorio(cfg, inv, uso, A, ach, anonimo):
    L = []
    w = L.append
    w("# Auditoria de tokens · Claude Code")
    if A:
        w(f"Período: últimos {uso['dias']} dias · {len(A['sessoes'])} sessões · {len(A['dias_ativos'])} dias ativos · "
          f"{A['humanos']} pedidos seus · {A['calls'] + A['calls_sub']} chamadas ao modelo")
        w("")
        w("## 1. Para onde foram os tokens")
        w("| Modelo | Chamadas | Entrada nova | Gravado em cache | Lido do cache | Saída | Raciocínio | Parte do custo |")
        w("|---|---|---|---|---|---|---|---|")
        T = A["total_peso"] or 1.0
        for k, m in sorted(A["por_modelo"].items(), key=lambda kv: -kv[1]["peso"]):
            w(f"| {k} | {m['calls']} | {fmt(m['i'])} | {fmt(m['cw'])} | {fmt(m['cr'])} | {fmt(m['o'])} | "
              f"{fmt(m['th'])} | {p(pct(m['peso'], T))} |")
        w("")
        if A["total_ctx"]:
            fixo = pct(A["fixo_ctx"], A["total_ctx"])
            w(f"- De cada 100 tokens que o modelo leu, {fixo:.0f} eram carga inicial (já existem antes de você "
              f"digitar) e {100 - fixo:.0f} eram conversa (histórico, arquivos e saídas de ferramentas).")
        if A["bases"]:
            w(f"- Carga inicial por sessão: mediana de {fmt(statistics.median(A['bases']))} tokens, "
              f"máxima de {fmt(max(A['bases']))}.")
        lidos = sum(m["cr"] for m in A["por_modelo"].values())
        tudo = sum(m["cr"] + m["cw"] + m["i"] for m in A["por_modelo"].values())
        w(f"- Cache: {p(pct(lidos, tudo))} da leitura veio do cache, que custa de 5% a 10% de uma leitura normal.")
        if A["calls_sub"]:
            w(f"- Subagentes: {A['calls_sub']} chamadas, {p(pct(A['sub_peso'], T))} do custo.")
        w(f"- Equivalente em preço de API: cerca de US$ {T:.0f} no período. Serve de escala: o plano não cobra "
          "assim, mas créditos de uso seguem essa tabela.")
        w("")
    w("## 2. Achados, do maior impacto para o menor")
    if not ach:
        w("Nenhum problema relevante encontrado com os limites atuais do script.")
    for n, a in enumerate(ach, 1):
        w(f"### {n}. {a['titulo']}")
        w(f"- Evidência: {a['evidencia']}")
        w(f"- Impacto: {a['impacto']}")
        w(f"- Correção: {a['correcao']}")
    w("")
    if A:
        w("## 3. Sessões mais pesadas")
        w("| Pasta | Dia | Modelo | Pedidos | Chamadas | Pico de contexto | Compactações | Parte do total |")
        w("|---|---|---|---|---|---|---|---|")
        nomes = {}
        for s in A["sessoes"][:6]:
            nome = s["proj"]
            if anonimo:
                nome = nomes.setdefault(nome, f"projeto-{len(nomes) + 1}")
            elif nome.startswith("scratch-"):
                nome = "(sem pasta)"
            w(f"| {nome} | {s['dia']} | {s['modelo']} | {s['turnos']} | {s['calls']} | {fmt(s['pico'])} | "
              f"{s['compact']} | {p(pct(s['peso'], A['total_peso']))} |")
        w("")
    w("## 4. O que carrega em toda sessão")
    ef = cfg["efetivo"]
    w(f"- Modelo padrão: {ef.get('model', 'não definido (usa o padrão do plano)')} · effortLevel: "
      f"{ef.get('effortLevel', 'não definido')} · por modelo: {ef.get('modelSettings') or 'nada'}")
    if cfg["env"]:
        w("- Variáveis: " + ", ".join(f"{k}={v}" for k, v in sorted(cfg["env"].items())))
    sk = inv["skills"]
    org = Counter(s["origem"].split(" ")[0] for s in sk)
    w(f"- Skills ativas: {len(sk)} (" + ", ".join(f"{v} de {k}" for k, v in org.most_common()) + "); descrições somam "
      f"cerca de {fmt(tok(sum(s['desc_chars'] for s in sk)))} tokens")
    if uso and uso["listagem"]["skills"]:
        w(f"- Listagem de skills medida nas sessões: {fmt(tok(statistics.median(uso['listagem']['skills'])))} "
          f"tokens para {int(statistics.median(uso['listagem']['skills_qtd']))} skills (conta também as embutidas "
          "do aplicativo e as de plugins que estavam ativos no período)")
    w(f"- Agentes personalizados: {len(inv['agentes'])}")
    for m in inv["memoria"]:
        w(f"- Memória: {m['arquivo']} · {m['linhas']} linhas · cerca de {fmt(tok(m['chars']))} tokens")
    ativos = [pl for pl in inv["plugins"] if pl["ativo"]]
    for pl in ativos:
        ev = ", ".join(f"{h['evento']} ({h['comandos']})" for h in pl["hooks"]) or "nenhum"
        w(f"- Plugin ativo: {pl['nome']} · {pl['skills']} skills · {pl['agentes']} agentes · hooks: {ev}")
    inativos = [pl["nome"] for pl in inv["plugins"] if not pl["ativo"]]
    if inativos:
        w("- Plugins instalados e desligados: " + ", ".join(inativos))
    if inv["mcp"]:
        w("- Servidores MCP: " + ", ".join(f"{m['nome']} [{m['escopo']}]" for m in inv["mcp"]))
    if uso and A:
        top = sorted(uso["skills_carregadas"].items(), key=lambda kv: -kv[1][1])[:5]
        if top:
            w("- Skills mais carregadas no período: " +
              ", ".join(f"{n} ({v[0]} vezes, {fmt(tok(v[1]))} tokens)" for n, v in top))
        ft = sorted(uso["ferramentas"].items(), key=lambda kv: -kv[1][1])[:5]
        if ft:
            w("- Ferramentas que mais trouxeram texto: " +
              ", ".join(f"{n} ({v[0]} vezes, {fmt(tok(v[1]))} tokens)" for n, v in ft))
    w("")
    w("## Limites desta auditoria")
    w("- Tokens de uso vêm dos registros do Claude Code. Tamanhos de texto são estimados em 4 caracteres por token.")
    w("- As porcentagens de custo usam os preços públicos da API em 17/11/2026. Elas comparam causas entre si; "
      "não são a conta do plano, cuja fórmula a Anthropic não publica.")
    w("- O script não lê o texto das conversas e não envia nada para fora da máquina.")
    if uso:
        w(f"- Lidos {uso['arquivos']} arquivos de sessão. O Claude Code apaga registros antigos (30 dias por padrão).")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Auditoria de tokens do Claude Code (somente leitura).")
    ap.add_argument("--dias", type=int, default=14, help="janela de análise em dias (padrão: 14)")
    ap.add_argument("--home", default=str(Path.home()), help="pasta do usuário (para testes)")
    ap.add_argument("--projeto", default=os.getcwd(), help="pasta do projeto atual")
    ap.add_argument("--json", dest="saida_json", help="grava os dados completos neste arquivo")
    ap.add_argument("--anonimo", action="store_true", help="troca nomes de pasta por projeto-1, projeto-2...")
    ap.add_argument("--so-config", action="store_true", help="não lê os registros de sessão")
    a = ap.parse_args()
    home, proj = Path(a.home), Path(a.projeto)
    if not (home / ".claude").is_dir():
        print("Não encontrei a pasta .claude em " + str(home) + ". Este script audita o Claude Code. "
              "Para o chat (claude.ai), use o modo chat da skill.")
        return 2
    cfg = coletar_config(home, proj)
    inv = coletar_inventario(home, proj, cfg)
    uso = None if a.so_config else coletar_uso(home, a.dias)
    A = analisar_uso(uso) if uso and uso["sessoes"] else None
    ach = achados(cfg, inv, uso, A)
    print(relatorio(cfg, inv, uso, A, ach, a.anonimo))
    if a.saida_json:
        dados = {"config": cfg, "inventario": inv, "achados": ach}
        if A:
            resumo = {k: v for k, v in A.items() if k not in ("hooks", "dias_ativos", "sub_modelos", "effort", "entrada")}
            resumo["hooks"] = [{"evento": e, "origem": o, "vezes": v[0], "chars": v[1], "releituras": v[2]}
                               for (e, o), v in A["hooks"].items()]
            resumo["dias_ativos"] = sorted(A["dias_ativos"])
            resumo["effort"] = dict(A["effort"])
            resumo["sub_modelos"] = dict(A["sub_modelos"])
            dados["uso"] = resumo
        with open(a.saida_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
