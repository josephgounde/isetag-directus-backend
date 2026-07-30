#!/usr/bin/env bash
set -euo pipefail

# Ouvre la lecture publique du contenu du site (catalogue, actualités, etc.) et
# crée le dossier "Public" servant d'allowlist pour les fichiers publiquement
# lisibles. À rejouer après chaque `directus schema apply` sur un environnement
# neuf (staging/prod) — permissions et dossier ne sont pas capturés par le
# snapshot de schéma.
cd "$(dirname "$0")/.."
set -a
source .env
set +a
python3 scripts/provision_public_read.py
