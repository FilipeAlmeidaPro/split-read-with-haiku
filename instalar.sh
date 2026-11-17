#!/usr/bin/env bash
# Instala o kit de economia de tokens no Claude Code (macOS e Linux).
#
#   bash instalar.sh                 skill de auditoria + ajudante no Haiku + nota + aviso com números
#   bash instalar.sh --sem-resumo    sem o aviso com números (não toca no settings.json)
#   bash instalar.sh --so-auditoria  só a skill de auditoria
#
# Para remover depois: bash ~/.claude/kit-economia-de-tokens/desinstalar.sh
# No Windows: python ajudante-haiku\configurar.py instalar
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  py=python3
elif command -v python >/dev/null 2>&1; then
  py=python
else
  echo "O instalador precisa do Python 3, que não foi encontrado."
  echo "Sem ele, copie a pasta auditoria-de-tokens para ~/.claude/skills/ e o arquivo"
  echo "ajudante-haiku/ajudante-haiku.md para ~/.claude/agents/, e cole o conteúdo de"
  echo "ajudante-haiku/nota-claude-md.md no fim do seu ~/.claude/CLAUDE.md."
  exit 1
fi

"$py" "$aqui/ajudante-haiku/configurar.py" instalar "$@"
