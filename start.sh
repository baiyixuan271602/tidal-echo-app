#!/usr/bin/env bash
set -u
PORT="${PORT:-10000}"
DATA=/data
mkdir -p "$DATA/uploads"

echo "[boot] PORT=$PORT"
echo "[boot] restoring data from backup (if any)..."
python3 /app/scripts/boot_restore.py || true

# brain: route PWA messages straight to the local API loop (no desktop channel here)
printf 'loop' > "$DATA/brain_target"
export RELAY_BRAIN_FILE="$DATA/brain_target"

# ---- relay ----
cd /app/backend
uvicorn app:app --host 127.0.0.1 --port 3011 --log-level warning &
echo "[boot] relay up (pid $!)"

# ---- api loop (the AI brain) ----
cd /app/loop
LOOP_PORT=3020 RELAY_URL=http://127.0.0.1:3011 python3 api_loop.py &
echo "[boot] loop up (pid $!)"

# ---- backup loop ----
python3 /app/scripts/backup_loop.py &
echo "[boot] backup loop up (pid $!)"

# ---- nginx (foreground) ----
envsubst '${PORT}' < /app/nginx.conf.tpl > /etc/nginx/conf.d/default.conf
echo "[boot] starting nginx on :$PORT"
exec nginx -g 'daemon off;'
