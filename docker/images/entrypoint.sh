#!/bin/bash
set -e

cd /app

# Fix ownership on mounted volumes (may be root-owned from prior runs)
chown -R smplfrm:smplfrm /app/src/smplfrm/db

# Generate version file from git info
gosu smplfrm ./scripts/generate_version.sh

# Start celery worker in background
gosu smplfrm make start-celery &

# Start celery beat in background
gosu smplfrm make start-celery-beat &

# Start Django server in foreground (runs migrations and collectstatic)
exec gosu smplfrm make run
