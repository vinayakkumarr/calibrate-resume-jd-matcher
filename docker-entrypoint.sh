#!/bin/bash
set -e

# ==============================================================================
# Calibrate AI — Production Container Entrypoint & Retention Supervisor
# Supervises Apache in foreground and runs automated retention daemon
# ==============================================================================

# Spawn background retention worker inheriting full container environment variables
(
  echo "[RETENTION_DAEMON] Automated retention daemon initialized (30-minute interval)."
  # Initial 5-minute grace period before first sweep to allow service warm-up
  sleep 300
  while true; do
    echo "[RETENTION_DAEMON] Running scheduled retention sweep: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    php /var/www/html/cron/cleanup.php 2>&1 || true
    sleep 1800
  done
) &

# Execute main container command (apache2-foreground) under tini supervision
exec "$@"
