# Debugging

Here you can find some hints on how to debug Raveberry if not everything is working as intended.  
The logs of Raveberry can be found at `/opt/raveberry/logs`.
Raveberry uses `systemd` services to provide its functionality.
Services used are:
* `nginx`: webserver, serves static files and proxys requests to `daphne`
* `daphne`: webserver, runs all the python code
* `gunicorn`: alternative to daphne without websockets (usually disabled)
* `mopidy`: music player, plays the songs
* `pulseaudio`: runs a pulseaudio system server
* `xinit`: starts the X-server (if visualization is configured)
* `hostapd`: runs the hotspot (if hotspot is configured)
* `dnsmasq`: handles DNS for the hotspot (if hotspot is configured)
* `homewifi`: disables the hotspot at home (if is configured)
* `remote`: connects to a remote server (if remote is configured)

You can check if they are running with
```
systemctl status <service>
```
For a log of the service, use
```
journalctl -xe -u <service>
```
Sometimes a restart is required.
```
sudo systemctl restart <service>
```

If you notice that some features do not work at all, they may have been installed incorrectly. Then you might have to trace the scripts in `setup/` and check if all steps executed correctly.
