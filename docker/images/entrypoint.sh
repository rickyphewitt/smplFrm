#!/bin/bash
set -e

cd /app

# Generate version file from git info
./scripts/generate_version.sh

# Start celery worker in background
make start-celery &

# Start celery beat in background
make start-celery-beat &

# Start Django server in foreground (runs migrations and collectstatic)
exec make run
