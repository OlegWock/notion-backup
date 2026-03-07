#!/bin/sh
set -e

if [ -n "$CRON_SCHEDULE" ]; then
    # Dump env vars for cron to source (cron doesn't inherit container env)
    printenv | grep -v 'no_proxy' > /app/.cronenv

    cat > /etc/cron.d/notion-backup <<EOF
SHELL=/bin/sh
$CRON_SCHEDULE . /app/.cronenv; cd /app && /bin/uv run --no-sync main.py >> /proc/1/fd/1 2>&1
EOF
    chmod 0644 /etc/cron.d/notion-backup
    crontab /etc/cron.d/notion-backup

    echo "Running initial backup..."
    uv run --no-sync main.py
    echo "Starting cron with schedule: $CRON_SCHEDULE"
    exec cron -f
else
    exec uv run --no-sync main.py
fi
