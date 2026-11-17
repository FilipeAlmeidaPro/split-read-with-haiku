#!/usr/bin/env bash
# Remove o ajudante no Haiku, a nota do CLAUDE.md e o aviso com números.
# Com --tudo, remove também a skill de auditoria.
set -euo pipefail
aqui="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then py=python3; else py=python; fi
"$py" "$aqui/configurar.py" remover "$@"
