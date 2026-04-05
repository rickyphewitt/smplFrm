#!/bin/bash
set -e

cd /app/src/smplfrm

# Run migrations and collect static files
python3.14 manage.py migrate
python3.14 manage.py collectstatic --noinput

# Start celery worker in background
python3.14 -m celery -A smplfrm worker -E -l info &

# Start celery beat in background
python3.14 -m celery -A smplfrm beat -l info &

# Start Django server in foreground
exec python3.14 manage.py runserver 0.0.0.0:8321
