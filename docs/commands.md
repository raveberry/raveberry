# Commands
This file contains some useful commands to deal with Ravberry's administration.

## Setting Volume
By default, alsa devices are not set to 100% percent volume. In this case, Raveberry cannot use the full volume range. Raveberry sets the volume of the built in PCM audio output by itself (using `amixer sset PCM 100%`). If you are using different device configure it like this:
```
aplay -l # find the card number of your device
amixer -c <card_number> scontrols # list available controls for this card
amixer -c <card_number> sset <control> 100% # Change volume. Probably something like 'Master' or 'Speaker'
```
You can test your configuration with `aplay -D<alsa_device> <soundfile>`

## Connecting to a WiFi Network
Raveberry uses a script to allow connection to WiFi networks from the interface. You can also use it from the command line:
```
sudo iwlist wlan1 scan # find out SSID
sudo scripts/system/connect_to_wifi # interactively create wpa_supplicant entry
```

## Managing bluetooth
Raveberry uses the `bluetoothctl` tool to manage bluetooth connections. It can also be used for manual configuration.

## The `scripts/` directory

In the `scripts` directory you can find a collection of useful scripts for developing.

* `scripts/compilescss.sh` creates a new `styles.css`. Necessary if you changed a `.scss` file.
* `scripts/deploy.sh` pushes changes from the current development directory and pulls them in the production directory.
* `scripts/install_system_scripts.sh` moves the content of `scripts/system` to `/usr/local/sbin/raveberry`
* `scripts/runserver.sh [user]` runs the debug server under the specified user or www-data if no user was given.
* `scripts/set_permissions.sh` grants www-data necessary permissions to run Raveberry.
* `scripts/system/` contains a number of configuration scripts used by Raveberry to control the system.
* `scripts/uninstall.sh` removes files created by Raveberry.
