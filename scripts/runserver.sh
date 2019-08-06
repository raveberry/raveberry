#!/bin/bash
if (( $# == 0 )); then
	user=www-data
elif (( $# == 1 )); then
	user=$1
else
	echo "$0 <user>"
	exit 1
fi
sudo -u $user DJANGO_DEBUG=1 python3 manage.py runserver 0:8000
