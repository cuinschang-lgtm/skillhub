#!/bin/bash
set -e

echo "Starting FastAPI on port 8001..."
uvicorn app.main:app --host 0.0.0.0 --port 8001 &

echo "Starting Next.js on port ${PORT:-8000}..."
cd /app/web
export SKILLHUB_API_HOSTPORT=localhost:8001
export HOSTNAME=0.0.0.0
exec node server.js
