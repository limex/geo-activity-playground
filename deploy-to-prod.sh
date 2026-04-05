#!/bin/bash
set -euo pipefail

REMOTE_USER="gbosch"
REMOTE_HOST="192.168.1.176"
REMOTE_DIR="~/docker/geo-activity-playground"

rsync \
  --archive \
  --delete \
  --exclude='/playground/' \
  --filter='+ /Dockerfile' \
  --filter='+ /.dockerignore' \
  --filter='+ /docker-compose.yml' \
  --filter='+ /pyproject.toml' \
  --filter='+ /uv.lock' \
  --filter='+ /alembic.ini' \
  --filter='+ /deploy-to-prod.sh' \
  --filter='+ /geo_activity_playground/' \
  --filter='+ /geo_activity_playground/**' \
  --filter='- *' \
  --verbose \
  ./ \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"
