#!/bin/bash
if [ "$EUID" -ne 0 ]
then echo "Please run as root"
	exit
fi

declare -a modify=("."
			"db.sqlite3"
			".yarnrc"
			"config"
			"config/cava.config"
			"core/migrations"
			"static"
			"static/scss"
			"logs"
			"logs/info.log"
			"logs/error.log")

for file in "${modify[@]}"; do
	echo "$file"
	chown www-data:www-data "$file"
	chmod g+w "$file"
done
