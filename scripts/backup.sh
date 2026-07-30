#!/usr/bin/env bash
set -euo pipefail

# Sauvegarde de la base PostgreSQL et des médias Directus (uploads).
# Usage : ./scripts/backup.sh [staging|prod]   (défaut: prod)
#
# À planifier sur le VPS via cron, ex. tous les jours à 3h du matin :
#   0 3 * * * cd ~/isetag && ./scripts/backup.sh prod >> /var/log/isetag-backup.log 2>&1
#
# Conserve les 7 derniers jours de sauvegardes (rotation automatique).

ENVIRONMENT="${1:-prod}"
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "Usage: $0 [staging|prod]" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

POSTGRES_CONTAINER="isetag-postgres-$ENVIRONMENT"
ENV_FILE=".env.$ENVIRONMENT"
UPLOADS_DIR="cms/uploads"
[[ "$ENVIRONMENT" == "staging" ]] && UPLOADS_DIR="cms/uploads-staging"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier $ENV_FILE introuvable." >&2
  exit 1
fi

DB_USER=$(grep -m1 '^DB_USER=' "$ENV_FILE" | cut -d= -f2)
DB_DATABASE=$(grep -m1 '^DB_DATABASE=' "$ENV_FILE" | cut -d= -f2)

BACKUP_DIR="backups/$ENVIRONMENT"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

echo ">> Dump PostgreSQL ($ENVIRONMENT)..."
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DB_USER" "$DB_DATABASE" \
  | gzip > "$BACKUP_DIR/db-$TIMESTAMP.sql.gz"

echo ">> Archive des médias ($UPLOADS_DIR)..."
tar -czf "$BACKUP_DIR/uploads-$TIMESTAMP.tar.gz" "$UPLOADS_DIR"

echo ">> Rotation (7 jours)..."
find "$BACKUP_DIR" -name '*.gz' -mtime +7 -delete

echo ">> Sauvegarde $ENVIRONMENT terminée : $BACKUP_DIR/{db,uploads}-$TIMESTAMP.*.gz"
