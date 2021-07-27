#!/bin/bash

set -e

# initialize the database if the container is run with django related commands
if [[ "$1" == *"daphne" || "${@}" == *"manage.py"* ]]; then

	python3 manage.py migrate --noinput

	# create users in the database
	python3 manage.py shell <<EOF
from django.contrib.auth.models import User
User.objects.all().delete()
User.objects.create_superuser('admin', email='', password='$ADMIN_PASSWORD')
User.objects.create_user('mod', password='$MOD_PASSWORD')

from core.settings import storage
if '$SPOTIFY_USERNAME' or '$SPOTIFY_PASSWORD' or '$SPOTIFY_CLIENT_ID' or '$SPOTIFY_CLIENT_SECRET':
	storage.set('spotify_username', '$SPOTIFY_USERNAME')
	storage.set('spotify_password', '$SPOTIFY_PASSWORD')
	storage.set('spotify_client_id', '$SPOTIFY_CLIENT_ID')
	storage.set('spotify_client_secret', '$SPOTIFY_CLIENT_SECRET')
	storage.set('spotify_enabled', True)
if '$SOUNDCLOUD_AUTH_TOKEN':
	storage.set('soundcloud_auth_token', '$SOUNDCLOUD_AUTH_TOKEN')
	storage.set('soundcloud_enabled', True)
if '$JAMENDO_CLIENT_ID':
	storage.set('jamendo_client_id', '$JAMENDO_CLIENT_ID')
	storage.set('jamendo_enabled', True)
EOF

	if [ "$ADMIN_PASSWORD" == "admin" ]; then
		echo 1>&2
		echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
		echo "! Warning! Default admin password used, change it! !" 1>&2
		echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
		echo 1>&2
	fi
fi

exec "${@}"
