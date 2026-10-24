#!/bin/sh
set -eu
python manage.py migrate --run-syncdb --noinput
python manage.py collectstatic --noinput
if [ "${SEED_DEMO:-true}" = "true" ]; then python manage.py seed_demo; fi
exec gunicorn eventbase.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-3}" --timeout 60 --access-logfile - --error-logfile -
