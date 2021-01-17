# Raveberry

[![Build Status](https://travis-ci.org/raveberry/raveberry.svg?branch=master)](https://travis-ci.org/raveberry/raveberry)
[![PyPI](https://img.shields.io/pypi/v/raveberry)](https://pypi.org/project/raveberry/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Subreddit subscribers](https://img.shields.io/reddit/subreddit-subscribers/raveberry?style=social)](https://www.reddit.com/r/raveberry/)

Raveberry is a multi user music server that allows democratic selection of songs.

It provides an intuitive interface for requesting songs and changing their order according to the rating that users have made. It supports Youtube, Spotify, Soundcloud and local files as sources for music.

![](docs/showcase.gif "Showcase Gif")

## Installation

### Docker

If you just want it to work, you can use [docker-compose](https://docs.docker.com/compose/install/):
```
wget https://raw.githubusercontent.com/raveberry/raveberry/master/docker-compose.yml
docker-compose up -d
```
If you want to use the remote streaming feature, instead run:
```
wget https://raw.githubusercontent.com/raveberry/raveberry/master/icecast.docker-compose.yml
docker-compose -f icecast.docker-compose.yml up -d
```

Raveberry is now accessible at `http://localhost/` or `http://<your hostname>/` for other devices in the network. To use a different password for the `admin` user than the default password `admin`, set an environment variable `ADMIN_PASSWORD`. Similarly, `STREAM_PASSWORD` sets the password to access the remote stream, `STREAM_NOAUTH=1` disables password protection.

If there is no sound, you might need to provide your UID an GID for pulse to work: `UID=$(id -u) GID=$(id -g) docker-compose up -d`

To use local files from your system, specify the path to the desired folder in the volumes section of the file. The folder will be visible in as `/Music/raveberry`, which is the path you need to use when scanning the library.

In order to use Spotify, you need to provide your credentials to Raveberry via the `/settings` page and to mopidy via environment variables. Find out which environment variables in the docker compose file.

Note: Playback and voting should work as expected, but additional features like visualization or the hotspot are not supported (yet).

### Manual

Raveberry is meant to be installed on a Raspberry Pi. Then it works as a portable music server which you can take with you wherever you are. To gain access to all features of Raveberry you need to perform a manual system installation.

Install the dependencies and download Raveberry from PyPi:
```
wget -q -O - https://apt.mopidy.com/mopidy.gpg | sudo apt-key add -
sudo wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list
sudo apt-get update
sudo apt-get install -y python3-pip ffmpeg atomicparsley mopidy redis-server libspotify-dev libglib2.0-dev libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad

pip3 install raveberry
raveberry run
```
Depending on your distribution, you may need to write `~/.local/bin/raveberry run` or add that to your PATH. `raveberry run` will start a basic version of Raveberry that can be tested on `http://localhost:8080/` (The server is running if you see `Quit the server with CONTROL-C.`).

If you want to install Raveberry system wide and make it fully featured, you can use the following command:
```
raveberry system-install
```

This assumes you have a working system with root access. If you need help setting up your Raspberry Pi, consider visiting [this guide](https://projects.raspberrypi.org/en/projects/raspberry-pi-setting-up).

You can customize your installation with the config file at [`config/raveberry.ini`](config/raveberry.ini). (Or at the location the installer tells you)

Although everything *should* work fine, I recommend taking a backup of your system. On a Raspberry Pi this is easily done by creating a copy of its SD card.

During installation you will be asked to provide a password for the admin user. This user is allowed to modify the database and change the system configuration, so choose a sensible password.

The installation will take at most 30 minutes, most of which is spent on installing/updating packages. You might need to reboot afterwards for all changes to take effect.

## First Steps

After the installation has finished `http://raveberry/` is up and ready to play music (go ahead and try now!). You can visit `http://raveberry/login/` and log in as the `admin` user with your provided admin password. If you take a look at `http://raveberry/settings` (which is also linked from the dropdown) you can see various configuration possibilities. For more information about these settings and privileges in general refer to [`docs/privileges.md`](docs/privileges.md).

An introduction to basic functionality can be found in [`docs/functionality.md`](docs/functionality.md). Or just visit `http://raveberry/` and find out for yourself ; )

## Updating

### Docker
Just update all of your containers in the docker-compose file:
```
docker-compose pull
```

### Manual Installation
Updating an existing installation is easy. Just update the PyPi package and rerun the system installation.
```
pip3 install -U raveberry
raveberry system-install
```
Your database will be preserved, unless you specify a database backup in your config file.

## Features

* **Live Updates**:
Web page content is updated instantly using websockets.

* **Streaming Support**:
With `icecast`, it is possible to remotely listen to Raveberry. See [`docs/streaming.md`](docs/streaming.md).

* **Bluetooth Support**:
Use your bluetooth speakers with Raveberry, removing the need of an aux cable.

* **Hotspot**:
Provides a WiFi network for access in areas without proper infrastructure. Can double as a repeater.

* **Remote URL**:
Specify a domain to make your Raveberry accessible from the world wide web.

* **Local Files Support**:
Play all the files you already have in your local filesystem. Various filetypes supported.

* **Youtube Support**:
With `youtube-dl` as a media provider, all of Youtube is available to play.

* **Spotify Support**:
Raveberry's music player `mopidy` can play songs from Spotify, if you to log in with your account. Spotify Premium is required.

* **Privilege Levels**:
Grant users additional permissions like playback control.

* **Graphical Admin Interface**:
Raveberry features a convenient way of modifying the behavior of the server, like hotspot configuration or download limitation.

* **Complementary App**:
[Shareberry](https://github.com/raveberry/shareberry/) lets you share songs directly from your phone to Raveberry.

* **Audio normalization**:
Raveberry uses replaygain to analyze the volume of songs and prevent sharp volume transitions.

* **Screen visualization**:
With the tool `cava`, the current music is split into its frequencies and visualized on a connected screen. Can also be configured to run in [user mode](#user_visualization). (See screenshot below)

* **Audio visualization**:
Using the same tool, Raveberry can also make connected LEDs flash to the rhythm of the music.

![](docs/visualization.png "Visualization")

## Optional Hardware Additions

Some of Raveberry's features rely on additional hardware. If you want to use all of them, consider upgrading your Raspberry Pi with one of these one of items:

* **WiFi Dongle**:
To provide a WiFi network for users to connect, you have to set up a second network interface. If disabled, your users have to be in the same network as the Raveberry, or you have to configure an external URL.

* **LEDs**:
For audio visualization, Raveberry uses the `i2c` and `spi` protocols to control connected LEDs. They will automatically be used if they are detected at server startup. For more information see [`docs/leds.md`](docs/leds.md).

* **USB Sound Card**:
The quality of the internal Raspberry Pi sound card varies from model to model. For a better music experience I recommend using a small USB sound card. If you use one, edit the config file accordingly.

* **USB Stick**:
If you don't want to use the Raspberry Pi's internal filesystem, you can insert an external medium like a USB stick. Its label can be specified in the config file and is then used to cache the songs.

## <a name="tested_hardware"></a> Tested Hardware

Raveberry is known to work on the following Hardware:
* Raspberry Pi 4
* Raspberry Pi 3B+
* Raspberry Pi Zero W

If you have something to add to the list, please let me know!

Although it is possible to install and run Raveberry on the original Raspberry Pi (after a very long installation), the hardware is just to weak for audio decoding and can not provide a pleasant experience at all.

### A Note about Ubuntu 18.04
Mopidy 3.0 requires Python 3.7, while Ubuntu 18.04 ships with Python 3.6. It is possible to install it nevertheless, but it is not trivial. Refer to [this guide](https://mopidy.com/blog/2019/12/27/mopidy-3-faq/#what-about-mopidy-3-on-ubuntu-1804-lts) for instructions.

## Uninstall

During installation a backup folder is created. It contains all files that were overwritten outside of the `raveberry/` folder. To undo installation, move these files back to their respective locations using the following command. Take care of changes you made in the meantime!
```
sudo cp -r backup_{timestamp}/* / 
```
To remove files created during the setup run
```
sudo scripts/uninstall.sh
```

## FAQ

### <a name="user_visualization"></a> I want to use the visualization without doing a system install.

Install the required python packages
```
pip3 install raveberry[screenvis]
```
Install cava (Instructions from [the repository](https://github.com/karlstav/cava))
```
sudo apt-get install git libfftw3-dev libasound2-dev libncursesw5-dev libpulse-dev libtool automake libiniparser-dev
export CPPFLAGS=-I/usr/include/iniparser
git clone https://github.com/karlstav/cava
cd cava
./autogen.sh
./configure
make
cp cava ~/.local/bin  # or add the binary to your PATH
```
comment out the following line in the used cava config (probably something like `nano ~/.local/lib/python3.7/site-packages/raveberry/config/cava.config`) (add the `#`:
```
# source = cava.monitor
```
Now you should be able to start the server with `raveberry run`, login with admin:admin at `localhost:8080/login` and enable the visualization at `localhost:8080/lights`.

### There is an error during installation while `building wheel for cryptography`.

You are probably missing some build dependencies on your system. This has been reported to happen on the Raspberry Pi Zero. Install them using `sudo apt-get install build-essential libssl-dev libffi-dev python-dev`.

### "Connect Failed" when trying to connect to a bluetooth device.

This is a permission issue from before v0.5.  
Run `sudo adduser pulse bluetooth` or upgrade Raveberry. Afterwards reboot and it should work again.

### Where are my Youtube files?

If you specified a path in your config file before installing, you will find them there. If no path was given, it will default to `~/Music/raveberry`. If you run it as `pi` using `raveberry run`, this will be `/home/pi/Music/raveberry`. If Raveberry was installed on the system, the process is running as `www-data` and you will find the directory at `/var/www/Music/raveberry`.

### `django.db.utils.DataError: value too long for type character varying(200)`

You will encounter this when scanning your local files if they have long paths. Version 0.5.10 fixed this. If you installed your version before, update your database with:
```
sudo -u www-data DJANGO_MOCK=1 python3 /opt/raveberry/manage.py migrate
```
You will not lose any data. If running a docker setup, this will be done automatically.

## Special Thanks

* All the awesome people that created [Mopidy](https://mopidy.com/) for this incredibly versatile music player.
* Especially [Mopidy-Spotify](https://github.com/mopidy/mopidy-spotify), without which I could not have added Spotify support.
* [django](https://www.djangoproject.com/), for providing one of the best documentations I have ever encountered.
* [@karlstav](https://github.com/karlstav) for his audio visualizer [`cava`](https://github.com/karlstav/cava).
* [`youtube-dl`](https://github.com/ytdl-org/youtube-dl/) for greatly simplifying the interaction with Youtube.
* [Steven van Tetering](https://www.tikveel.nl/) for writing [the shader](https://www.shadertoy.com/view/llycWD) I based my visualization on.
* All my friends for constantly beta testing this project.

## More Information

Feel free to visit [`docs/`](docs/) for more information about usage, resources etc.

Don't hesitate to mail me for feedback or open an issue if you experience any problems.
