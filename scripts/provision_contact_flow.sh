#!/usr/bin/env bash
set -euo pipefail

# Provisionne le Flow du formulaire de contact public et ses permissions.
cd "$(dirname "$0")/.."
set -a
source .env
set +a
python3 scripts/provision_contact_flow.py
