#!/usr/bin/env bash
set -e
CMD=(uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}")
# Drop root before serving: fix ownership of the (root-owned) Fly volume,
# then exec as the unprivileged `app` user.
if [ "$(id -u)" = "0" ] && command -v setpriv >/dev/null 2>&1 && id app >/dev/null 2>&1; then
  mkdir -p /database /app/tts_cache /app/backups
  chown -R app:app /database /app/tts_cache /app/backups 2>/dev/null || true
  exec setpriv --reuid=app --regid=app --init-groups "${CMD[@]}"
fi
exec "${CMD[@]}"
