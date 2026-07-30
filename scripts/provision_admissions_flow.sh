#!/usr/bin/env bash
set -euo pipefail

# Crée (ou met à jour, de façon idempotente) le Flow de pré-inscription publique
# et ses permissions. À rejouer après chaque `directus schema apply` sur un
# environnement neuf (staging/prod) — les flows et permissions ne sont pas
# capturés par le snapshot de schéma.
cd "$(dirname "$0")/.."
set -a
source .env
set +a
python3 scripts/provision_admissions_flow.py
