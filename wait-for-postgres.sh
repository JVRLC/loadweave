#!/bin/sh
set -e

# Use environment variables for database connection
host="${DB_HOST}"
port="${DB_PORT}"
user="${DB_USER}"
db="${DB_NAME}"
password="${DB_PASSWORD}"

# Remaining arguments are the command to execute
cmd="$@"

echo "Waiting for Postgres at $host:$port..."
until PGPASSWORD=$password psql -h "$host" -p "$port" -U "$user" -d "$db" -c '\q'; do
  echo "Postgres is unavailable - sleeping"
  sleep 2
done

echo "Postgres is available! Starting application..."
exec $cmd
