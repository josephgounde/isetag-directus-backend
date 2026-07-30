#!/usr/bin/env bash
set -euo pipefail

# Génère cms/snapshots/current.yaml depuis l'instance Directus en cours d'exécution.
cd "$(dirname "$0")/.."
MSYS_NO_PATHCONV=1 docker exec isetag-directus-dev npx directus schema snapshot /directus/snapshots/current.yaml --yes
