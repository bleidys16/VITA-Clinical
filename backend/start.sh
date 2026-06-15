#!/bin/bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

celery -A config worker --loglevel=info --pool=solo &

exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
