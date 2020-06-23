#!/bin/sh

sed -i "s/<admin-password>[^<]*<\/admin-password>/<admin-password>$ICECAST_ADMIN_PASSWORD<\/admin-password>/g" /etc/icecast.xml

if [ -z "${STREAM_NOAUTH}" ]; then
	USER=${STREAM_USERNAME:=raveberry}
	PASS=${STREAM_PASSWORD:=raveberry}
	HASH=$(echo -n ${PASS} | md5sum | awk '{ print $1 }')
	echo "${USER}:${HASH}" > /usr/share/icecast/.htaccess
	chown icecast:icecast /usr/share/icecast/.htaccess

	sed -i -e 's#<!-- <authentication#<authentication#' \
		-e 's#</authentication> -->#</authentication>#' /etc/icecast.xml
fi

exec "$@"
