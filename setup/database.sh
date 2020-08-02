echo "*** Creating Postgres Database ***"
# create user and database if they do not exist already
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "raveberry"; then
	db_exists=true
fi
if [[ ! $db_exists = true ]]; then
	sudo -u postgres psql -c "CREATE USER raveberry WITH PASSWORD 'raveberry';"
	sudo -u postgres psql -c "CREATE DATABASE raveberry;"
fi

if [[ -z "$ADMIN_PASSWORD" ]]; then
	ADMIN_PASSWORD=admin
fi

if [[ -z "$DB_BACKUP" ]]; then
	if [[ ! $db_exists = true ]]; then
		echo "Performing migrations"
		sudo -Hu www-data DJANGO_MOCK=1 DJANGO_POSTGRES=1 python3 manage.py migrate
		echo "Creating Users"
		if [[ "$ADMIN_PASSWORD" == "admin" ]]; then
			echo "!!! Warning! Using default admin password 'admin' !!!"
			echo "!!!     change this later in the webinterface     !!!"
			echo "!!!           at http://raveberry/admin           !!!"
		fi
		sudo -Hu www-data DJANGO_MOCK=1 DJANGO_POSTGRES=1 python3 manage.py shell <<-EOF
			from django.contrib.auth.models import User
			User.objects.create_superuser('admin', email='', password='$ADMIN_PASSWORD')
			User.objects.create_user('mod', password='mod')
		EOF
	fi
else
	echo "Restoring Backup"
	systemctl stop daphne
	sudo -u postgres pg_dump raveberry > $BACKUP_DIR/dbbackup
	sudo -u postgres psql -c "DROP DATABASE raveberry;"
	sudo -u postgres psql -c "CREATE DATABASE raveberry;"
	sudo -u postgres psql raveberry < $DB_BACKUP
fi
echo "Initializing search engine"
sudo -Hu www-data DJANGO_MOCK=1 DJANGO_POSTGRES=1 python3 manage.py migrate
sudo -Hu www-data DJANGO_MOCK=1 DJANGO_POSTGRES=1 python3 manage.py installwatson
sudo -Hu www-data DJANGO_MOCK=1 DJANGO_POSTGRES=1 python3 manage.py buildwatson

if [ ! -z "$DEV_USER" ] && [ ! -f db.sqlite3 ]; then
	echo "*** Creating Debug Database ***"
	echo "Performing Migrations"
	sudo -Hu www-data DJANGO_MOCK=1 python3 manage.py migrate
	echo "Creating Users"
	if [[ "$ADMIN_PASSWORD" == "admin" ]]; then
		echo "!!! Warning! Using default admin password 'admin' !!!"
		echo "!!!     change this later in the webinterface     !!!"
		echo "!!!        at http://raveberry:8000/admin         !!!"
	fi
	sudo -Hu www-data DJANGO_MOCK=1 python3 manage.py shell <<-EOF
		from django.contrib.auth.models import User
		User.objects.create_superuser('admin', email='', password='$ADMIN_PASSWORD')
		User.objects.create_user('mod', password='mod')
	EOF
else
	echo "Debug database already exists, no migration needed"
fi
