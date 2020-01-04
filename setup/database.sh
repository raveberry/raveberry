echo "*** Creating Postgres Database ***"
sudo -u postgres psql -c "CREATE USER raveberry WITH PASSWORD 'raveberry';"
sudo -u postgres psql -c "CREATE DATABASE raveberry;"

if [[ -z "$ADMIN_PASSWORD" ]]; then
	ADMIN_PASSWORD=admin
fi

if [[ -z "$DB_BACKUP" ]]; then
	echo "Performing Migrations"
	sudo -Hu www-data DJANGO_MOCK=1 python3 manage.py migrate
	echo "Creating Users"
	if [[ "$ADMIN_PASSWORD" == "admin" ]]; then
		echo "!!! Warning! Using default admin password 'admin' !!!"
		echo "!!!     change this later in the webinterface     !!!"
		echo "!!!           at http://raveberry/admin           !!!"
	fi
	sudo -Hu www-data DJANGO_MOCK=1 python3 manage.py shell <<-EOF
		from django.contrib.auth.models import User
		User.objects.create_superuser('admin', email='', password='$ADMIN_PASSWORD')
		User.objects.create_user('mod', password='mod')
		User.objects.create_user('pad', password='pad')
	EOF
else
	echo "Restoring Backup"
	sudo -u postgres psql raveberry < $DB_BACKUP
fi

if [ ! -z "$DEV_USER" ]; then
	echo "*** Creating Debug Database ***"
	echo "Performing Migrations"
	sudo -Hu www-data DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py migrate
	echo "Creating Users"
	if [[ "$ADMIN_PASSWORD" == "admin" ]]; then
		echo "!!! Warning! Using default admin password 'admin' !!!"
		echo "!!!     change this later in the webinterface     !!!"
		echo "!!!        at http://raveberry:8000/admin         !!!"
	fi
	sudo -Hu www-data DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py shell <<-EOF
		from django.contrib.auth.models import User
		User.objects.create_superuser('admin', email='', password='$ADMIN_PASSWORD')
		User.objects.create_user('mod', password='mod')
		User.objects.create_user('pad', password='pad')
	EOF
fi
