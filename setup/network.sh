if [ ! -z "$HOSTNAME" ]; then
	echo "hostname..."
	hostname "$HOSTNAME"
	cp --parents /etc/hostname $BACKUP_DIR/
	echo "$HOSTNAME" > /etc/hostname
	cp --parents /etc/hosts $BACKUP_DIR/
	# prevents problems with sudo when no dns is available
	LINE="127.0.1.1	$HOSTNAME"
	FILE="/etc/hosts"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
fi

if [ -z "$HOTSPOT" ]; then
	# remove hotspot specific system scripts
	rm /usr/local/sbin/raveberry/enable_tunneling
	rm /usr/local/sbin/raveberry/disable_tunneling
	rm /usr/local/sbin/raveberry/enable_hotspot
	rm /usr/local/sbin/raveberry/disable_hotspot
	rm /usr/local/sbin/raveberry/enable_homewifi
	rm /usr/local/sbin/raveberry/disable_homewifi
	# Without a seperate hotspot, the internet is available on wlan0
	sed -i s/wlan1/wlan0/ /usr/local/sbin/raveberry/connect_to_wifi
else
	systemctl stop dnsmasq
	systemctl stop hostapd

	echo "dhcpcd..."
	cp --parents /etc/dhcpcd.conf $BACKUP_DIR/
	LINE=$(cat setup/dhcpcd.conf)
	FILE="/etc/dhcpcd.conf"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

	echo "dnsmasq..."
	cp --parents /etc/dnsmasq.conf $BACKUP_DIR/
	cat setup/dnsmasq.conf > /etc/dnsmasq.conf
	envsubst < setup/hosts.dnsmasq > /etc/hosts.dnsmasq

	echo "hostapd..."
	envsubst < setup/hostapd_protected.conf > /etc/hostapd/hostapd_protected.conf
	envsubst < setup/hostapd_unprotected.conf > /etc/hostapd/hostapd_unprotected.conf
	cp --parents /etc/default/hostapd $BACKUP_DIR/
	LINE='DAEMON_CONF="/etc/hostapd/hostapd_protected.conf"'
	FILE="/etc/default/hostapd"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

	echo -n "$HOMEWIFI" > config/homewifi
	chown www-data:www-data config/homewifi
	cp setup/homewifi.service /etc/systemd/system/homewifi.service
	envsubst < setup/disable_hotspot_at_home '$SERVER_ROOT' > /usr/local/sbin/raveberry/disable_hotspot_at_home
	chmod +x /usr/local/sbin/raveberry/disable_hotspot_at_home

	echo "forwarding..."
	cp --parents /etc/sysctl.conf $BACKUP_DIR/
	LINE="net.ipv4.ip_forward=1"
	FILE="/etc/sysctl.conf"
	grep -qxF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
	/usr/local/sbin/raveberry/enable_tunneling

	cp --parents /etc/rc.local $BACKUP_DIR/
	LINE="iptables-restore < /etc/iptables.ipv4.nat"
	FILE="/etc/rc.local"
	grep -qxF -- "$LINE" "$FILE" || sed -i "`wc -l < /etc/rc.local`i\\$LINE\\" /etc/rc.local

	rfkill unblock wlan
	service dhcpcd restart
	systemctl daemon-reload
	systemctl restart dhcpcd
	systemctl unmask hostapd.service
	systemctl start hostapd
	systemctl start dnsmasq
fi
