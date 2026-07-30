#!/usr/bin/env bash
set -euo pipefail

# Crée (ou vérifie, de façon idempotente) les rôles internes "Service
# Admissions" et "Service Communication". À rejouer avant
# provision_admissions_flow.sh / provision_contact_flow.sh sur un
# environnement neuf (staging/prod) — les rôles/policies ne sont pas
# capturés par le snapshot de schéma.
cd "$(dirname "$0")/.."
set -a
source .env
set +a
python3 scripts/provision_roles.py
