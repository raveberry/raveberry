#!/bin/bash
DJANGO_MOCK=1 python3 manage.py shell <<-EOF
	from django.contrib.auth.models import User
	User.objects.all().delete()
	User.objects.create_superuser('admin', email='', password='$ADMIN_PASSWORD')
	User.objects.create_user('mod', password='$MOD_PASSWORD')
	User.objects.create_user('pad', password='$PAD_PASSWORD')
EOF

if [ "$ADMIN_PASSWORD" == "admin" ]; then
  echo 1>&2
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
  echo "! Warning! Default admin password used, please consider changing it! !" 1>&2
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" 1>&2
  echo 1>&2
fi
