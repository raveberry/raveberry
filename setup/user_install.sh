echo "Performing Migrations"
DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py migrate
echo "Creating Users"
DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py shell <<-EOF
	from django.contrib.auth.models import User
	User.objects.create_superuser('admin', email='', password='admin')
	User.objects.create_user('mod', password='mod')
	User.objects.create_user('pad', password='pad')
EOF
echo "Configuring mpd"
mkdir -p ~/.mpd
cat setup/user_mpd.conf > ~/.mpd/mpd.conf
echo "Compiling SCSS Files"
DJANGO_MOCK=1 DJANGO_DEBUG=1 python3 manage.py compilescss
