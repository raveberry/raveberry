#!/bin/bash
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
echo "Performing Migrations"
DJANGO_MOCK=1 python3 manage.py migrate
echo "Creating Users"
DJANGO_MOCK=1 python3 manage.py shell <<-EOF
	from django.contrib.auth.models import User
	User.objects.create_superuser('admin', email='', password='$ADMIN_PASSWORD')
	User.objects.create_user('mod', password='mod')
EOF
if [[ ! -f static/bundle.js ]]; then
	echo "building frontend"
	yarn --cwd frontend install
	yarn --cwd frontend build
fi

if [ "$ADMIN_PASSWORD" == "admin" ]; then
  echo 1>&2
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
  echo "! Warning! Default admin password used, please consider changing it! !" 1>&2
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
  echo 1>&2
fi
