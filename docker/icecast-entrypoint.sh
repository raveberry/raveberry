#!/bin/sh

sed -i "s/<admin-password>[^<]*<\/admin-password>/<admin-password>$ICECAST_ADMIN_PASSWORD<\/admin-password>/g" /etc/icecast.xml

USER=raveberry
PASS="$STREAM_PASSWORD"
HASH=$(echo -n $PASS | md5sum | awk '{ print $1 }')
ENTRY="$USER:$HASH"
echo "$ENTRY" > /usr/share/icecast/.htaccess
chown icecast:icecast /usr/share/icecast/.htaccess

exec "$@"
