cp --parents /boot/config.txt $BACKUP_DIR/
if [ ! -z "$SCREEN_VISUALIZATION" ]; then
	echo "*** Configuring Screen Visualization ***"
	echo "hdmi..."
	echo "hdmi_force_hotplug=1" >> /boot/config.txt
	echo "X11..."
	# allow non-root users to start an X server
	sed -i s/console/anybody/ /etc/X11/Xwrapper.config
	# without access to renderD128 another slow method is used
	# to access it, add www-data to the 'render' group
	adduser www-data render 2>/dev/null
fi

if [ ! -z "$LED_VISUALIZATION" ]; then
	echo "*** Configuring LEDs ***"
	echo "i2c..."
	echo "dtparam=i2c_arm=on" >> /boot/config.txt
	echo "spi..."
	echo "dtparam=spi=on" >> /boot/config.txt
	if [[ `cat /proc/device-tree/model` == "Raspberry Pi 4"* ]]; then
		echo "core_freq=500" >> /boot/config.txt
		echo "core_freq_min=500" >> /boot/config.txt
	else
		echo "core_freq=250" >> /boot/config.txt
	fi
fi

echo "*** Configuring MPD ***"
cp --parents /etc/mpd.conf $BACKUP_DIR/
envsubst < setup/mpd.conf > /etc/mpd.conf
amixer -q sset PCM 100%
systemctl restart mpd

echo "*** Configuring Cache Directory ***"
if [[ ! -z "$CACHE_DIR" ]]; then
	mkdir -p "$CACHE_DIR"
	chown www-data:www-data "$CACHE_DIR"
fi
if [[ ! -z "$CACHE_MEDIUM" ]]; then
	if [[ -z "$CACHE_DIR" ]]; then
		CACHE_DIR="/mnt/$CACHE_MEDIUM"
	fi
	mkdir -p "$CACHE_DIR"
	eval $(blkid --match-token LABEL="$CACHE_MEDIUM" -o export | grep UUID)
	cp --parents /etc/fstab $BACKUP_DIR/
	echo "UUID=$UUID /mnt/$CACHE_MEDIUM vfat auto,nofail,noatime,rw,dmask=002,fmask=0113,gid=$(id -g www-data),uid=$(id -u www-data)" >> /etc/fstab
	mount -a
fi
echo "$CACHE_DIR" > config/cache_dir

echo "*** Granting www-data necessary Privileges ***"
echo "groups"
# leds
adduser www-data spi 2>/dev/null
adduser www-data gpio 2>/dev/null
adduser www-data i2c 2>/dev/null
# bluetoothctl
adduser www-data bluetooth 2>/dev/null
echo "/var/www"
mkdir -p /var/www
chown www-data:www-data /var/www
echo "$SERVER_ROOT"
chown -R www-data:www-data .
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
