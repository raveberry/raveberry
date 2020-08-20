cp --parents /boot/config.txt $BACKUP_DIR/
if [ ! -z "$SCREEN_VISUALIZATION" ]; then
	echo "*** Configuring Screen Visualization ***"
	echo "hdmi..."
	LINE="hdmi_force_hotplug=1"
	FILE="/boot/config.txt"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	echo "X11..."
	xhost +si:localuser:www-data

	if [[ -f /proc/device-tree/model && `cat /proc/device-tree/model` == "Raspberry Pi 4"* ]]; then
		# start x on boot, but only for raspberry pi 4
		cp setup/xinit.service /etc/systemd/system/xinit.service
		systemctl daemon-reload
		systemctl enable xinit
	fi

	# without access to renderD128 another slow method is used
	# to access it, add www-data to the 'render' group
	adduser www-data render 2>/dev/null
	if [ ! -z $DEV_USER ]; then
		echo "Granting $DEV_USER rendering privileges"
		adduser $DEV_USER render 2>/dev/null
	fi
fi

if [ ! -z "$LED_VISUALIZATION" ]; then
	echo "*** Configuring LEDs ***"
	echo "i2c..."
	LINE="dtparam=i2c_arm=on"
	FILE="/boot/config.txt"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	echo "spi..."
	LINE="dtparam=spi=on"
	FILE="/boot/config.txt"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	if [[ `cat /proc/device-tree/model` == "Raspberry Pi 4"* ]]; then
		LINE="core_freq=500"
		FILE="/boot/config.txt"
		grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
		LINE="core_freq_min=500"
		grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	else
		LINE="core_freq=250"
		FILE="/boot/config.txt"
		grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	fi
fi

echo "*** Configuring Sound Output ***"
cp setup/pulseaudio.service /etc/systemd/system/pulseaudio.service

cp --parents /etc/pulse/system.pa $BACKUP_DIR/
LINE=$(cat <<-EOF
	load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1
	load-module module-bluetooth-policy
	load-module module-bluetooth-discover
EOF
)
FILE="/etc/pulse/system.pa"
grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

adduser mopidy www-data
cp --parents /etc/mopidy/mopidy.conf $BACKUP_DIR/

if [[ ( ! -z "$LED_VISUALIZATION" || ! -z "$SCREEN_VISUALIZATION" ) ]]; then
	LINE=$(cat <<-EOF
		load-module module-null-sink sink_name=cava
		update-sink-proplist cava device.description="virtual sink for cava"
		set-default-sink 0
	EOF
	)
	FILE="/etc/pulse/system.pa"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	envsubst < setup/mopidy_cava.conf > /etc/mopidy/mopidy.conf
else
	envsubst < setup/mopidy.conf > /etc/mopidy/mopidy.conf
fi

amixer -q sset PCM 100%
# also set volume of external sound card
amixer -q -c 1 sset Speaker 100%

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

	LINE="UUID=$UUID /mnt/$CACHE_MEDIUM ntfs auto,nofail,noatime,rw,dmask=002,fmask=0113,gid=$(id -g www-data),uid=$(id -u www-data)"
	FILE="/etc/fstab"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	mount -a
fi
echo "$CACHE_DIR" > config/cache_dir

echo "*** Granting www-data necessary Privileges ***"
echo "groups"
# leds
adduser www-data spi 2>/dev/null
adduser www-data gpio 2>/dev/null
adduser www-data i2c 2>/dev/null
# pulseaudio
adduser www-data audio 2>/dev/null
adduser www-data pulse 2>/dev/null
adduser www-data pulse-access 2>/dev/null
# bluetoothctl
adduser www-data bluetooth 2>/dev/null
adduser pulse bluetooth 2>/dev/null
echo "/var/www"
mkdir -p /var/www
chown www-data:www-data /var/www
echo "$SERVER_ROOT"
chown -R www-data:www-data .
echo "/usr/local/sbin/raveberry/"
echo 'www-data ALL=NOPASSWD:/usr/local/sbin/raveberry/*' | EDITOR='tee -a' visudo
if [ ! -z $DEV_USER ]; then
	echo "Granting $DEV_USER user privileges"
	adduser $DEV_USER bluetooth
	adduser $DEV_USER www-data
fi

systemctl enable pulseaudio
systemctl restart pulseaudio
systemctl enable mopidy
systemctl restart mopidy

echo "periodic youtube-dl updates..."
crontab -l > $BACKUP_DIR/crontab
LINE="0 6 * * * /usr/bin/sudo -H /usr/bin/pip3 install -U youtube-dl"
crontab -l | grep -qxF "$LINE" || (crontab -l ; echo "$LINE") | crontab -

if [ ! -z "$BACKUP_COMMAND" ]; then
	echo "*** Activating Backup Cronjob ***"
	LINE="0 5 * * * $BACKUP_COMMAND"
	crontab -l | grep -qxF "$LINE" || (crontab -l ; echo "$LINE") | crontab -
fi
