#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
UMASK="${UMASK:-022}"
DATA_DIR="${DATA_DIR:-/app/data}"

# ── Create app group and user with desired IDs ──────────────
if ! getent group appuser >/dev/null 2>&1; then
    addgroup --gid "$PGID" appuser
fi

if ! getent passwd appuser >/dev/null 2>&1; then
    adduser --uid "$PUID" --ingroup appuser --disabled-password --gecos "" --no-create-home appuser
fi

# ── Apply umask ─────────────────────────────────────────────
umask "$UMASK"

# ── Ensure data directory exists and is owned by appuser ────
mkdir -p "$DATA_DIR"
chown -R "$PUID:$PGID" "$DATA_DIR"

# ── Run migrations as appuser ───────────────────────────────
cd /app/backend
echo "Running database migrations..."
su -s /bin/sh appuser -c "umask $UMASK && PATH=/app/backend/.venv/bin:\$PATH alembic upgrade head"

# ── One-time data seeds (marker file prevents re-runs) ──────
SEED_MARKER="$DATA_DIR/.seed_store_aliases_done"
if [ ! -f "$SEED_MARKER" ]; then
    echo "Running one-time store alias seed..."
    su -s /bin/sh appuser -c "umask $UMASK && cd /app/backend && PATH=/app/backend/.venv/bin:\$PATH python -m scripts.seed_store_aliases" \
        && touch "$SEED_MARKER" \
        && chown "$PUID:$PGID" "$SEED_MARKER"
fi

# ── Inject user= into supervisord programs ──────────────────
CONF=/etc/supervisor/conf.d/supervisord.conf
sed -i "s|^\(\[program:backend\]\)|\1\nuser=appuser|" "$CONF"
sed -i "s|^\(\[program:worker\]\)|\1\nuser=appuser|" "$CONF"
sed -i "s|^\(\[program:redis\]\)|\1\nuser=appuser|" "$CONF"

echo "Starting supervisord (appuser UID=$PUID GID=$PGID UMASK=$UMASK)..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
