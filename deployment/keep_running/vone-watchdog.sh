#!/bin/bash
# Vishakha One watchdog: restarts the application (or nginx) if it stops answering.
# Runs once a minute from vone-watchdog.timer. Safe to run by hand.
SERVICE="${VONE_SERVICE:-vishakha-one}"
URL="${VONE_HEALTH_URL:-http://127.0.0.1:8101/healthz/}"
STATE=/run/vone-watchdog.fails
LIMIT=3

fails=$(cat "$STATE" 2>/dev/null || echo 0)

if curl -fsS --max-time 8 -o /dev/null "$URL"; then
  echo 0 > "$STATE"
else
  fails=$((fails + 1))
  echo "$fails" > "$STATE"
  logger -t vone-watchdog "health check failed ($fails/$LIMIT): $URL"
  if [ "$fails" -ge "$LIMIT" ]; then
    logger -t vone-watchdog "restarting $SERVICE"
    systemctl restart "$SERVICE"
    echo 0 > "$STATE"
  fi
fi

# the web server in front must be running too
if ! systemctl is-active --quiet nginx; then
  logger -t vone-watchdog "nginx was not running - starting it"
  systemctl restart nginx
fi
