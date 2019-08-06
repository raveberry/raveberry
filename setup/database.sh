echo "*** Creating Postgres Database ***"
sudo -u postgres psql -c "CREATE USER raveberry WITH PASSWORD 'raveberry';"
sudo -u postgres psql -c "CREATE DATABASE raveberry;"
if [[ -z "$DB_BACKUP" ]]; then
	echo "Performing Migrations"
	sudo -u www-data DJANGO_MOCK=1 python3 manage.py migrate
	echo "Creating admin user"
	echo "Please create a password for admin"
	sudo -u www-data DJANGO_MOCK=1 python3 manage.py createsuperuser --username admin --email ''
	echo "Creating other users"
	sudo -u www-data DJANGO_MOCK=1 python3 manage.py shell <<-EOF
		from django.contrib.auth.models import User
		user=User.objects.create_user('mod', password='mod')
		user.is_superuser=False
		user.is_staff=False
		user.save()
		user=User.objects.create_user('pad', password='pad')
		user.is_superuser=False
		user.is_staff=False
		user.save()
	EOF
else
	echo "Restoring Backup"
	sudo -u postgres psql raveberry < $DB_BACKUP
fi

if [ ! -z "$DEV_USER" ]; then
	echo "*** Creating Debug Database ***"
	echo "Performing Migrations"
	sudo -u www-data DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py migrate
	echo "Creating admin user"
	sudo -u www-data DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py createsuperuser --username admin --email ''
	echo "Creating other users"
	sudo -u www-data DJANGO_DEBUG=1 DJANGO_MOCK=1 python3 manage.py shell <<-EOF
		from django.contrib.auth.models import User
		user=User.objects.create_user('mod', password='mod')
		user.is_superuser=False
		user.is_staff=False
		user.save()
		user=User.objects.create_user('pad', password='pad')
		user.is_superuser=False
		user.is_staff=False
		user.save()
	EOF
fi
