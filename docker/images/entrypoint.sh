#!/bin/bash
set -e

cd /app

# Start celery worker in background
make start-celery &

# Start celery beat in background
make start-celery-beat &

# Start Django server in foreground (runs migrations and collectstatic)
exec make run
