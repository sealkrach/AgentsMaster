#!/usr/bin/env bash
# Crée un nouveau skill à partir du template.
#   ./scripts/new_skill.sh mon-skill
set -euo pipefail

NAME="${1:-}"
if [[ -z "$NAME" ]]; then
  echo "Usage: ./scripts/new_skill.sh <nom-du-skill>"; exit 1
fi
if [[ ! "$NAME" =~ ^[a-z0-9-]+$ ]]; then
  echo "Nom invalide : minuscules, chiffres et tirets uniquement."; exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/skills/$NAME"

if [[ -d "$DEST" ]]; then
  echo "Le skill '$NAME' existe déjà : $DEST"; exit 1
fi

mkdir -p "$DEST/references" "$DEST/scripts"
sed "s/REPLACE-WITH-skill-name/$NAME/g" "$ROOT/skills/_TEMPLATE/SKILL.md" > "$DEST/SKILL.md"

echo "✅ Skill créé : skills/$NAME/SKILL.md"
echo "   1. Édite la 'description' (c'est elle qui décide du déclenchement)."
echo "   2. Écris les instructions étape par étape."
echo "   3. Relance le runtime (make up) et teste dans l'UI."
