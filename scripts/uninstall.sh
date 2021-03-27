echo "Uninstalling..."
echo "cava"
if [ -d /opt/cava ]; then
        cd /opt/cava
        make uninstall
        cd -
fi
rm -rf /opt/cava
rm -rf /usr/bin/cava
echo "system scripts"
rm -rf /usr/local/sbin/raveberry
echo "configs"
rm -rf /etc/hostapd/hostapd_protected.conf
rm -rf /etc/hostapd/hostapd_unprotected.conf
rm -rf /etc/nginx/sites-available/raveberry-events
rm -rf /etc/nginx/sites-available/raveberry-static
rm -rf /etc/nginx/sites-enabled/raveberry-events
rm -rf /etc/nginx/sites-enabled/raveberry-static
echo "services"
rm -rf /etc/systemd/system/daphne.service
rm -rf /etc/systemd/system/gunicorn.service
rm -rf /etc/systemd/system/homewifi.service
rm -rf /etc/systemd/system/pulseaudio.service
rm -rf /etc/systemd/system/remote.service
rm -rf /etc/systemd/system/xinit.service
echo "Done!"
echo "You may now delete this directory"
