#!/bin/sh
set -e

# Entry point runs migrations and collectstatic, then executes the supplied CMD.
# It is safe to call on every container start; migrations/collectstatic are idempotent.

echo "Starting entrypoint: waiting for DB & running migrations if available..."

# Wait for the DB to be ready (best effort). Honor DATABASE_URL or try until connection.
# Simple loop: try to run migrate; if it fails, wait and retry a few times.
RETRIES=30
DELAY=2
count=0
until [ $count -ge $RETRIES ]
do
  python manage.py migrate --noinput && break
  count=$((count+1))
  echo "Migration attempt $count/$RETRIES failed — retrying in ${DELAY}s..."
  sleep $DELAY
done

# Collect static files
python manage.py collectstatic --noinput || true

# Create logs dir if missing
mkdir -p logs

# Execute the container CMD
echo "Launching process: $@"
exec "$@"
