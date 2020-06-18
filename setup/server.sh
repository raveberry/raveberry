echo "nginx..."
cp --parents /etc/nginx/sites-enabled/default $BACKUP_DIR/ 2>/dev/null
rm -f /etc/nginx/sites-enabled/default
envsubst < setup/raveberry-events '$SERVER_ROOT' > /etc/nginx/sites-available/raveberry-events
envsubst < setup/raveberry-static '$SERVER_ROOT' > /etc/nginx/sites-available/raveberry-static

echo "daphne..."
envsubst < setup/daphne.service '$SERVER_ROOT' > /etc/systemd/system/daphne.service

echo "gunicorn..."
envsubst < setup/gunicorn.service '$SERVER_ROOT' > /etc/systemd/system/gunicorn.service

if [ ! -z "$REMOTE_KEY" ] && [ ! -z "$REMOTE_IP" ] && [ ! -z REMOTE_PORT ] && [ ! -z "$REMOTE_URL" ]; then
	echo "remote..."
	if [ "${REMOTE_KEY:0:1}" = "/" ]; then
		export KEY_LOCATION=$REMOTE_KEY
	else
		export KEY_LOCATION="$SERVER_ROOT/$REMOTE_KEY"
	fi
	cp setup/remote.service /etc/systemd/system/remote.service
	envsubst < setup/connect_to_remote '$REMOTE_IP $REMOTE_PORT $KEY_LOCATION' > /usr/local/sbin/raveberry/connect_to_remote
	chmod +x /usr/local/sbin/raveberry/connect_to_remote
	cp --parents /root/.ssh/known_hosts $BACKUP_DIR/ 2>/dev/null
	mkdir -p /root/.ssh
	ssh-keygen -F $REMOTE_IP > /dev/null || ssh-keyscan -H $REMOTE_IP >> /root/.ssh/known_hosts
fi

systemctl daemon-reload
/usr/local/sbin/raveberry/enable_events
