echo "Performing Migrations"
DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py migrate
echo "Creating Users"
DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py shell <<-EOF
	from django.contrib.auth.models import User
	User.objects.create_superuser('admin', email='', password='admin')
	User.objects.create_user('mod', password='mod')
	User.objects.create_user('pad', password='pad')
EOF
if [[ ! -d static/libs ]]; then
	echo "Installing frontend libraries"
	HOME= yarn install
fi
echo "Compiling SCSS Files"
DJANGO_MOCK=1 DJANGO_DEBUG=1 python3 manage.py compilescss
