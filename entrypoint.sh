#!/bin/bash
# Docker entrypoint, runs everything trunk-player needs in one container.
# Pass a command to run it instead, e.g.
#   docker compose run --rm app ./manage.py createsuperuser
set -e

if [ -n "$1" ]; then
  exec "$@"
fi

# Use the redis bundled in the image unless REDIS_URL points somewhere else
case "${REDIS_URL:-redis://127.0.0.1:6379}" in
  redis://127.0.0.1*|redis://localhost*)
    echo "Starting redis"
    redis-server --daemonize yes --save "" --appendonly no
    ;;
esac

case "${MIGRATE_DB,,}" in
  1|true|yes)
    echo "Updating database"
    if [[ "$SQL_ENGINE" == *postgresql* ]]; then
      python utility/trunk-player/db_check_create.py
    fi
    python manage.py migrate --noinput
    ;;
esac

# Create the admin account on first start
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  export DJANGO_SUPERUSER_EMAIL="${DJANGO_SUPERUSER_EMAIL:-admin@example.com}"
  python manage.py createsuperuser --noinput >/dev/null 2>&1 \
    && echo "Created admin user $DJANGO_SUPERUSER_USERNAME" \
    || echo "Admin user $DJANGO_SUPERUSER_USERNAME already exists"
fi

python manage.py collectstatic --noinput -v0

echo "Starting nginx"
nginx

echo "Starting daphne"
exec daphne trunk_player.asgi:application --port 7055 --bind 127.0.0.1 \
  --access-log /var/log/trunk-player/daphne_main.log \
  --ping-interval 3 --ping-timeout 12 --proxy-headers
