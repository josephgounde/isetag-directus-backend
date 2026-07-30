#!/usr/bin/env bash
set -euo pipefail

# Peuple les 5 pôles et les 27 filières dans Directus.
cd "$(dirname "$0")/.."
set -a
source .env
set +a
python3 scripts/seed_data.py
