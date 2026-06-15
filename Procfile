web: gunicorn config.wsgi:application --chdir backend --bind 0.0.0.0:$PORT
worker: celery -A config worker --loglevel=info --workdir backend --pool=solo
