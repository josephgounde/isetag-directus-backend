#!/usr/bin/env bash
set -euo pipefail

# Déploiement vers le VPS unique (build -> ghcr.io -> pull -> up -d -> apply snapshot).
# Appelé par .github/workflows/deploy.yml via SSH, ou manuellement depuis le VPS :
#   ./scripts/deploy.sh staging
#   ./scripts/deploy.sh prod
#
# Prérequis sur le VPS (une seule fois) :
#   docker network create isetag_edge
#   .env.staging (ou .env.prod) rempli à partir de .env.staging.example / .env.prod.example

ENVIRONMENT="${1:-}"
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "Usage: $0 <staging|prod>" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker/$ENVIRONMENT/docker-compose.yml"
ENV_FILE=".env.$ENVIRONMENT"
DIRECTUS_CONTAINER="isetag-directus-$ENVIRONMENT"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier $ENV_FILE introuvable. Le créer à partir de .env.$ENVIRONMENT.example." >&2
  exit 1
fi

echo ">> Pull des images ($ENVIRONMENT)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

echo ">> Redémarrage de la stack ($ENVIRONMENT)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo ">> Attente de la disponibilité de Directus..."
for _ in $(seq 1 30); do
  if docker exec "$DIRECTUS_CONTAINER" wget -qO- http://localhost:8055/server/ping >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo ">> Application du schéma Directus (cms/snapshots/current.yaml)..."
docker exec "$DIRECTUS_CONTAINER" npx directus schema apply --yes /directus/snapshots/current.yaml

echo ">> Provisionnement des rôles, Flows et de la lecture publique (non couverts par le snapshot de schéma)..."
if command -v python3 >/dev/null 2>&1; then
  set -a
  source "$ENV_FILE"
  set +a
  python3 scripts/provision_roles.py
  python3 scripts/provision_admissions_flow.py
  python3 scripts/provision_contact_flow.py
  python3 scripts/provision_public_read.py
else
  echo "   python3 introuvable sur cet hôte — à lancer manuellement : make provision-roles provision-flows provision-contact-flow provision-public-read" >&2
fi

echo ">> Déploiement $ENVIRONMENT terminé."
