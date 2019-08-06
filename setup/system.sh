if [ ! -z "$AUDIO_VISUALIZATION" ]; then
	echo "*** Configuring LEDs ***"
	cp --parents /boot/config.txt $BACKUP_DIR/
	echo "i2c..."
	echo "dtparam=i2c_arm=on" >> /boot/config.txt
	echo "spi..."
	echo "dtparam=spi=on" >> /boot/config.txt
	echo "core_freq=250" >> /boot/config.txt
fi

echo "*** Configuring MPD ***"
cp --parents /etc/mpd.conf $BACKUP_DIR/
envsubst < setup/mpd.conf > /etc/mpd.conf
amixer -q sset PCM 100%
systemctl restart mpd

echo "*** Configuring Cache Directory ***"
mkdir -p "$CACHE_DIR"
if [[ -z "$CACHE_MEDIUM" ]]; then
	mkdir "$CACHE_DIR/songs"
	chown www-data:www-data "$CACHE_DIR/songs"
else
	eval $(blkid --match-token LABEL="$CACHE_MEDIUM" -o export | grep UUID)
	cp --parents /etc/fstab $BACKUP_DIR/
	echo "UUID=$UUID /mnt/Music vfat auto,nofail,noatime,rw,dmask=002,fmask=0113,gid=$(id -g www-data),uid=$(id -u www-data)" >> /etc/fstab
	mount -a
fi

echo "*** Granting www-data necessary Privileges ***"
echo "groups"
adduser www-data spi 2>/dev/null
adduser www-data gpio 2>/dev/null
adduser www-data i2c 2>/dev/null
echo "/var/www"
mkdir -p /var/www
chown www-data:www-data /var/www
echo "$SERVER_ROOT"
scripts/set_permissions.sh > /dev/null 2>&1
echo "/usr/local/sbin/raveberry/"
echo 'www-data ALL=NOPASSWD:/usr/local/sbin/raveberry/*' | EDITOR='tee -a' visudo
if [ ! -z $DEV_USER ]; then
	echo "Granting $DEV_USER user privileges to $SERVER_ROOT"
	adduser $DEV_USER www-data
fi

if [ ! -z "$BACKUP_COMMAND" ]; then
	echo "*** Activating Backup Cronjob ***"
	crontab -l > $BACKUP_DIR/crontab
	(crontab -l ; echo "0 5 * * * $BACKUP_COMMAND") | crontab -
fi
