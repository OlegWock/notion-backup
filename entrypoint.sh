#!/bin/sh
set -e

# Create a user with the specified UID/GID to match host permissions
groupadd -g "${PGID}" appgroup 2>/dev/null || true
useradd -u "${PUID}" -g "${PGID}" -M -s /bin/sh appuser 2>/dev/null || true
chown -R "${PUID}:${PGID}" /app

RUN_CMD="su -s /bin/sh appuser -c 'cd /app && /bin/uv run --no-sync main.py'"

if [ -n "$CRON_SCHEDULE" ]; then
    # Dump env vars for cron to source (cron doesn't inherit container env)
    printenv | grep -v 'no_proxy' > /app/.cronenv
    chown "${PUID}:${PGID}" /app/.cronenv

    cat > /etc/cron.d/notion-backup <<EOF
SHELL=/bin/sh
$CRON_SCHEDULE . /app/.cronenv; $RUN_CMD >> /proc/1/fd/1 2>&1
EOF
    chmod 0644 /etc/cron.d/notion-backup
    crontab /etc/cron.d/notion-backup

    echo "Running initial backup..."
    eval "$RUN_CMD"
    echo "Starting cron with schedule: $CRON_SCHEDULE"
    exec cron -f
else
    exec su -s /bin/sh appuser -c "cd /app && /bin/uv run --no-sync main.py"
fi
