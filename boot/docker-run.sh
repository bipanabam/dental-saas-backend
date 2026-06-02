#!/bin/sh

echo "Starting Dental SaaS Backend"
echo "Time: $(date)"

cd /code

exec gunicorn \
  -k uvicorn.workers.UvicornWorker \
  --workers ${WORKERS:-4} \
  --timeout 120 \
  --forwarded-allow-ips="*" \
  --bind 0.0.0.0:${PORT:-8000} \
  app.main:app
