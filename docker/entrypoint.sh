#!/bin/bash

set -e

DJANGO_MOCK=1 python manage.py migrate --noinput
scripts/create_users.sh

echo "Starting: ${@}"
exec "${@}"
