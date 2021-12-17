#!/bin/bash
if (( $# == 0 )); then
	DJANGO_DEBUG=1 python3 manage.py migrate
	DJANGO_DEBUG=1 python3 manage.py runserver 0:8080
elif (( $# == 1 )); then
	user=$1
	sudo -u $user DJANGO_DEBUG=1 python3 manage.py migrate
	sudo -u $user DJANGO_DEBUG=1 python3 manage.py runserver 0:8080
else
	echo "$0 [user]"
	exit 1
fi
