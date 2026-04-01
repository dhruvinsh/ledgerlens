#!/bin/sh
set -e
DATA_DIR="${DATA_DIR:-/app/data}"
mkdir -p "$DATA_DIR"
cd /app/backend
echo "Running database migrations..."
alembic upgrade head
echo "Starting supervisord..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
