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
if [[ ! -d static/libs ]]; then
	echo "Installing frontend libraries"
	HOME= yarn install
fi
if [[ ! -f static/scss/dark.css ]]; then
	echo "Compiling SCSS Files"
	DJANGO_MOCK=1 python3 manage.py compilescss
fi

if [ "$ADMIN_PASSWORD" == "admin" ]; then
  echo 1>&2
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
  echo "! Warning! Default admin password used, please consider changing it! !" 1>&2
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
  echo 1>&2
fi
