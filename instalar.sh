#!/usr/bin/env bash
# Instala a skill auditoria-de-tokens no Claude Code (macOS e Linux).
# Copia a pasta para ~/.claude/skills/. Nao altera nenhuma configuracao.
set -euo pipefail

origem="$(cd "$(dirname "$0")" && pwd)/auditoria-de-tokens"
destino="$HOME/.claude/skills/auditoria-de-tokens"

if [ ! -f "$origem/SKILL.md" ]; then
  echo "Não encontrei a pasta auditoria-de-tokens ao lado deste script."
  exit 1
fi

mkdir -p "$HOME/.claude/skills"
if [ -e "$destino" ]; then
  # Fora da pasta skills, para a versao antiga nao ser carregada como uma segunda skill.
  mkdir -p "$HOME/.claude/skills-anteriores"
  copia="$HOME/.claude/skills-anteriores/auditoria-de-tokens-$(date +%Y%m%d-%H%M%S)"
  mv "$destino" "$copia"
  echo "Já havia uma versão instalada. Ela foi movida para: $copia"
fi

cp -R "$origem" "$destino"
echo "Instalada em: $destino"
echo "Abra uma sessão nova do Claude Code e peça: audite meus tokens"
