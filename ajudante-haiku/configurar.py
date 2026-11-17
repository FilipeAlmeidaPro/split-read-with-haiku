#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
configurar.py - Instala e remove o kit de economia de tokens no Claude Code.

  python3 configurar.py instalar                 # skill + ajudante + nota + aviso com números
  python3 configurar.py instalar --sem-resumo    # sem o aviso com números (não toca no settings.json)
  python3 configurar.py instalar --so-auditoria  # só a skill de auditoria
  python3 configurar.py remover                  # tira o ajudante, a nota e o aviso
  python3 configurar.py remover --tudo           # tira também a skill de auditoria
  python3 configurar.py estado                   # mostra o que está instalado

O que a instalação completa mexe, e nada além disso:
  ~/.claude/skills/auditoria-de-tokens/     pasta nova
  ~/.claude/agents/ajudante-haiku.md        arquivo novo
  ~/.claude/kit-economia-de-tokens/         pasta nova (scripts e backups)
  ~/.claude/CLAUDE.md                       um bloco marcado, no fim do arquivo
  ~/.claude/settings.json                   um hook "Stop"

Antes de alterar CLAUDE.md e settings.json, uma cópia vai para
~/.claude/kit-economia-de-tokens/backups/. O modelo da conversa não é alterado.
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

CLAUDE = Path.home() / ".claude"
KIT = CLAUDE / "kit-economia-de-tokens"
BACKUPS = KIT / "backups"
SKILL = CLAUDE / "skills" / "auditoria-de-tokens"
AGENTE = CLAUDE / "agents" / "ajudante-haiku.md"
MEMORIA = CLAUDE / "CLAUDE.md"
SETTINGS = CLAUDE / "settings.json"
INICIO = "<!-- kit-economia-de-tokens:inicio -->"
FIM = "<!-- kit-economia-de-tokens:fim -->"
MARCA = "kit-economia-de-tokens"
COMANDO = 'python3 "$HOME/.claude/kit-economia-de-tokens/resumo_do_pedido.py" --hook'
BLOCO = re.compile(r"\n*" + re.escape(INICIO) + r".*?" + re.escape(FIM) + r"\n?", re.S)


def backup(arq):
    if arq.is_file():
        BACKUPS.mkdir(parents=True, exist_ok=True)
        destino = BACKUPS / f"{arq.name}.{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(arq, destino)
        return destino
    return None


def ler_settings():
    """Devolve (dados, erro). Não tenta consertar um arquivo inválido."""
    if not SETTINGS.is_file():
        return {}, None
    try:
        dados = json.loads(SETTINGS.read_text(encoding="utf-8"))
        return (dados, None) if isinstance(dados, dict) else (None, "o arquivo não é um objeto JSON")
    except Exception as e:
        return None, str(e)


def tem_hook(dados):
    for grupo in (dados.get("hooks") or {}).get("Stop") or []:
        for h in (grupo.get("hooks") or []) if isinstance(grupo, dict) else []:
            if MARCA in str(h.get("command", "")):
                return True
    return False


def por_hook():
    dados, erro = ler_settings()
    if erro:
        print(f"  ! Não mexi no settings.json porque ele não está em JSON válido ({erro}). O aviso com números ficou de fora.")
        return
    if tem_hook(dados):
        print("  = aviso com números: já estava configurado")
        return
    copia = backup(SETTINGS)
    dados.setdefault("hooks", {}).setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": COMANDO, "timeout": 10}]})
    SETTINGS.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  + aviso com números ao fim de cada resposta (hook Stop no settings.json)" +
          (f"; cópia do original em {copia}" if copia else ""))


def tirar_hook():
    dados, erro = ler_settings()
    if erro or not dados or not tem_hook(dados):
        return False
    backup(SETTINGS)
    grupos = []
    for grupo in dados["hooks"]["Stop"]:
        if isinstance(grupo, dict):
            grupo["hooks"] = [h for h in grupo.get("hooks") or [] if MARCA not in str(h.get("command", ""))]
            if not grupo["hooks"]:
                continue
        grupos.append(grupo)
    if grupos:
        dados["hooks"]["Stop"] = grupos
    else:
        del dados["hooks"]["Stop"]
        if not dados["hooks"]:
            del dados["hooks"]
    SETTINGS.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def por_nota(texto):
    atual = MEMORIA.read_text(encoding="utf-8") if MEMORIA.is_file() else ""
    copia = backup(MEMORIA)
    base = BLOCO.sub("\n", atual).rstrip("\n")
    MEMORIA.parent.mkdir(parents=True, exist_ok=True)
    MEMORIA.write_text((base + "\n\n" if base else "") + texto.strip("\n") + "\n", encoding="utf-8")
    print("  + nota no CLAUDE.md (bloco marcado, no fim do arquivo)" + (f"; cópia do original em {copia}" if copia else ""))


def tirar_nota():
    if not MEMORIA.is_file():
        return False
    atual = MEMORIA.read_text(encoding="utf-8")
    if INICIO not in atual:
        return False
    backup(MEMORIA)
    resto = BLOCO.sub("\n", atual).strip("\n")
    MEMORIA.write_text(resto + "\n" if resto else "", encoding="utf-8")
    return True


def instalar(args):
    origem = Path(__file__).resolve().parent
    raiz = origem.parent
    print("Instalando o kit de economia de tokens:")
    fonte_skill = raiz / "auditoria-de-tokens"
    if fonte_skill.is_dir():
        if SKILL.exists():
            antigos = CLAUDE / "skills-anteriores"
            antigos.mkdir(parents=True, exist_ok=True)
            shutil.move(str(SKILL), str(antigos / f"auditoria-de-tokens-{time.strftime('%Y%m%d-%H%M%S')}"))
        SKILL.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(fonte_skill, SKILL, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        print(f"  + skill de auditoria em {SKILL}")
    if "--so-auditoria" in args:
        print('Pronto. Abra uma sessão nova e peça: "audite meus tokens".')
        return 0
    KIT.mkdir(parents=True, exist_ok=True)
    for nome in ("configurar.py", "resumo_do_pedido.py", "nota-claude-md.md", "desinstalar.sh"):
        fonte = origem / nome if (origem / nome).is_file() else raiz / nome
        if fonte.is_file() and fonte.resolve() != (KIT / nome).resolve():
            shutil.copy2(fonte, KIT / nome)
    AGENTE.parent.mkdir(parents=True, exist_ok=True)
    if AGENTE.is_file():
        backup(AGENTE)
    shutil.copy2(origem / "ajudante-haiku.md", AGENTE)
    print(f"  + ajudante de leitura em {AGENTE} (roda no Haiku; só lê)")
    por_nota((origem / "nota-claude-md.md").read_text(encoding="utf-8"))
    if "--sem-resumo" in args:
        print("  - aviso com números: não instalado, a pedido")
    else:
        por_hook()
    print()
    print("O modelo da sua conversa não foi alterado.")
    print("Vale a partir da próxima sessão do Claude Code.")
    print("Para remover: bash ~/.claude/kit-economia-de-tokens/desinstalar.sh")
    return 0


def remover(args):
    print("Removendo o kit de economia de tokens:")
    if AGENTE.is_file():
        AGENTE.unlink()
        print("  - ajudante de leitura")
    if tirar_nota():
        print("  - nota do CLAUDE.md")
    if tirar_hook():
        print("  - aviso com números (hook Stop)")
    if "--tudo" in args and SKILL.exists():
        shutil.rmtree(SKILL)
        print("  - skill de auditoria")
    if KIT.is_dir():
        for item in KIT.iterdir():
            if item.name != "backups":
                item.unlink() if item.is_file() else shutil.rmtree(item)
        if BACKUPS.is_dir():
            print(f"As cópias de segurança continuam em {BACKUPS}. Pode apagar a pasta quando quiser.")
        else:
            KIT.rmdir()
    print("Pronto. Vale a partir da próxima sessão do Claude Code.")
    return 0


def estado(_args):
    dados, erro = ler_settings()
    nota = MEMORIA.is_file() and INICIO in MEMORIA.read_text(encoding="utf-8")
    print(f"skill de auditoria:  {'instalada' if SKILL.exists() else 'ausente'}")
    print(f"ajudante no Haiku:   {'instalado' if AGENTE.is_file() else 'ausente'}")
    print(f"nota no CLAUDE.md:   {'presente' if nota else 'ausente'}")
    print(f"aviso com números:   {'ligado' if dados and tem_hook(dados) else 'desligado'}" + (f" (settings.json inválido: {erro})" if erro else ""))
    return 0


def main():
    acoes = {"instalar": instalar, "remover": remover, "estado": estado}
    if len(sys.argv) < 2 or sys.argv[1] not in acoes:
        print(__doc__)
        return 1
    return acoes[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
