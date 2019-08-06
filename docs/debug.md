# Debugging

Here you can find some hints on how to debug Raveberry if not everything works as intended.  
Raveberry uses `systemd` services to provide its functionality.
Services used are:
* `nginx`: webserver, serves static files and proxys requests to `daphne`
* `daphne`: webserver, runs all the python code
* `mpd.service`: Music Player Daemon, plays the songs
* `mpd.socket`: provides a socket interface to communicate with `mpd`
* `hostapd`: runs the hotspot (if configured)
* `dnsmasq`: handles DNS for the hotspot (if configured)
* `remote`: connects to a remote URL (if configured)
* `homewifi`: disables the hotspot in the homewifi (if configured)

You can check if they are running with
```
systemctl status <service>
```
For a log of the service, use
```
journalctl -xe -u <service>
```
Only `daphne` writes its logs to `/var/log/syslog`. In general, inspecting the syslog might help:
```
less /var/log/syslog
```
Sometimes a restart is required.
```
sudo systemctl restart <service>
```

If you notice that some features do not work at all, they may have been installed incorrectly. Then you might have to trace the scripts in `setup/` and check if all steps executed correctly.
