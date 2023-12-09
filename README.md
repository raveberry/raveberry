# Raveberry

[![Build Status](https://img.shields.io/github/actions/workflow/status/raveberry/raveberry/publish.yml)](https://github.com/raveberry/raveberry/actions/workflows/publish.yml)
[![PyPI](https://img.shields.io/pypi/v/raveberry)](https://pypi.org/project/raveberry/)
[![Subreddit subscribers](https://img.shields.io/reddit/subreddit-subscribers/raveberry?style=social)](https://www.reddit.com/r/raveberry/)
[![Discord](https://img.shields.io/badge/-discord?style=social&logo=discord&label=Chat%20on%20Discord)](https://discord.gg/dy7Jxvjj9H)

Raveberry is a multi user music server that allows democratic selection of songs.

It provides an intuitive interface for requesting songs and changing their order according to the rating that users have made. It supports YouTube, Spotify and local files as sources for music.

A live demo is available at https://demo.raveberry.party/.

![](docs/showcase.gif "Showcase Gif")

## Installation

### Try it out!

You can test a slim version of Raveberry like this:
```
sudo apt-get install -y python3-pip mopidy redis-server ffmpeg gstreamer1.0-plugins-bad
pip3 install raveberry[run]
raveberry run
```
You might need to write `~/.local/bin/raveberry run` instead. Now you can visit `http://localhost:8080/` and play a song of your choice.

This method uses a development server, with limited performance and a restricted feature set.

### Installation

In order to gain access to all features of Raveberry, install it:
```
pip3 install raveberry[install]
raveberry install
```

If you get `raveberry: command not found` you need to run `export PATH="$HOME/.local/bin:$PATH"`.
Raveberry was developed for the Raspberry Pi. If you need help setting yours up up, visit [this guide](https://projects.raspberrypi.org/en/projects/raspberry-pi-setting-up).

The installer will ask you to confirm the config file it uses. The default install supports YouTube and local files. To customize (e.g. to use Spotify), cancel the installation, edit the config at the provided path and rerun `raveberry install`.

Although everything *should* work fine, I recommend taking a backup of your system. On a Raspberry Pi this can be done by creating a copy of its SD card.

The installation will take at most 30 minutes, most of which is spent on installing/updating packages. You might need to reboot afterwards for all changes to take effect.

### Docker

Alternatively, you can use [docker-compose](https://docs.docker.com/compose/install/):
```
wget https://raw.githubusercontent.com/raveberry/raveberry/master/docker/docker-compose.yml
wget https://raw.githubusercontent.com/raveberry/raveberry/master/docker/.env
docker-compose up -d
```

For more information, consult [`docs/docker.md`](docs/docker.md).

### Remote Installation

You can also install Raveberry on a remote machine you have ssh access to:
```
pip3 install raveberry[install]
cd "$(pip3 show raveberry | grep Location: | sed 's/.*: //')/raveberry"
ansible-playbook --user <user> --key-file <private_key> -i <ip>, -e "config_file=/path/to/raveberry.yaml" setup/system_install.yaml
```
If omitted, `config_file` defaults to `backend/config/raveberry.yaml`. `--user` and `--key-file` can be omitted if the target host is configured in your ssh config.

Passwordless sudo is default on a Raspberry Pi. For most other systems, sudo requires a password, then you have to add `--ask-become-pass`.

## First Steps

After the installation has finished `http://raveberry.local/` is up and ready to play music (go ahead and try now!). If this does not take you to the musiq landing page, use the IP of the device (`hostname -I` to find out).

You can visit `http://raveberry.local/login/` and log in as the `admin` user with your provided admin password. If you take a look at `http://raveberry.local/settings` (which is also linked from the dropdown) you can see various configuration possibilities. For more information about these settings and privileges in general refer to [`docs/privileges.md`](docs/privileges.md).

An introduction to basic functionality can be found in [`docs/functionality.md`](docs/functionality.md). Or just visit the website and find out for yourself ; )

## Updating

### Webinterface

At the bottom of the `/settings` page, click "Upgrade Raveberry".
A Log will be written to `/var/www`. 

### Manual

Update the PyPi package and rerun the installation.
```
pip3 install -U raveberry[install]
raveberry install
```
Your database will be preserved, unless you specify a database backup in your config file.

### Docker
Update all of your containers in the docker-compose file:
```
docker-compose pull
```

## Features

* **Live Updates**:
Web page content is updated instantly across all clients using websockets.

* **Remote Streaming**:
With `icecast`, it is possible to remotely listen to Raveberry. See [`docs/streaming.md`](docs/streaming.md).

* **Bluetooth Support**:
Use your bluetooth speakers with Raveberry, removing the need for an audio cable.

* **HiFiBerry Support**:
Attach your [HiFiBerry](https://www.hifiberry.com/) board for a high quality audio experience.

* **Hotspot**:
Provides a WiFi network for access in areas without proper infrastructure. Can double as a repeater.

* **Remote URL**:
Specify a domain to make your Raveberry accessible from the world wide web.

* **Local Files Support**:
Play all the files you already have in your local filesystem. Various filetypes supported.

* **YouTube Support**:
With `yt-dlp` as a media provider, all of YouTube is available to play.

* **Spotify Support**:
Raveberry's music player `mopidy` can play songs from Spotify, if you to log in with your account. Spotify Premium is required.

* **Soundcloud Support**:
Songs from Soundcloud are also available for you to play. ([currently broken](https://github.com/raveberry/raveberry/issues/117))

* **Privilege Levels**:
Grant people additional permissions like playback control.

* **Graphical Admin Interface**:
Raveberry features a convenient way of modifying the behavior of the server, like hotspot configuration or download limitation.

* **Complementary App**:
[Shareberry](https://github.com/raveberry/shareberry/) lets you share songs directly from your phone to Raveberry.

* **Discord Integration**:
Control your Raveberry instance from the discord chat with the [Raveberry bot](https://github.com/raveberry/shareberry/)

* **Audio normalization**:
Raveberry uses replaygain to analyze the volume of songs and prevent sharp volume transitions.

* **Screen visualization**:
With the tool `cava`, the current music is split into its frequencies and visualized on a connected screen (See screenshot below). Code in [separate Repository](https://github.com/raveberry/visualization).

* **Audio visualization**:
Using the same tool, Raveberry can also make connected LEDs flash to the rhythm of the music.

![](docs/visualization.png "Visualization")

## Optional Hardware Additions

Some of Raveberry's features rely on additional hardware. If you want to use all of them, consider upgrading your Raspberry Pi with one of these one of items:

* **WiFi Dongle**:
To provide a WiFi network for users to connect, you have to set up a second network interface. If disabled, your users have to be in the same network as Raveberry, or you have to configure an external URL.

* **LEDs**:
For audio visualization, Raveberry uses the `i2c` and `spi` protocols to control connected LEDs. They will automatically be used if they are detected at server startup. For more information see [`docs/leds.md`](docs/leds.md).

* **USB Sound Card**:
The quality of the internal Raspberry Pi sound card varies from model to model. For a better music experience I recommend using a small USB sound card.

* **USB Stick**:
If you don't want to use the Raspberry Pi's internal filesystem, you can insert an external medium like a USB stick. Its label can be specified in the config file and is then used to cache the songs.

## Tested Hardware

Raveberry is known to work on the following Hardware:
* Raspberry Pi 4
* Raspberry Pi 3B+
* Raspberry Pi Zero W

If you have something to add to the list, please let me know!

Although it is possible to install and run Raveberry on the original Raspberry Pi (after a very long installation), the hardware is just to weak for audio decoding and can not provide a pleasant experience at all.

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

### The current song is displayed in red and there is no sound
Red text means that Raveberry can't communicate with the player anymore. Either the player crashed or the interfacing library can't reconnect.

To fix this, first restart the player (`/settings` in "Sound Output") and wait a few seconds. If it still does not work, restart the server (`/settings` at the bottom).

### How do I use Spotify?
To enable Spotify support, install Raveberry with `spotify: true` in `raveberry.yaml`. Read how to enter your credentials [here](docs/spotify.md).

### During installation I get `error: externally-managed-environment`
Solution: `sudo mv /usr/lib/python3.11/EXTERNALLY-MANAGED /usr/lib/python3.11/EXTERNALLY-MANAGED.old`  
With debian bookworm, system-wide installation of python packages is strongly discouraged. While this is a noble approach, Raveberry is very integrated and needs to be installed system-wide. An installation in a virtualenv will not work for the full install.  
Note that this will allow system-wide installation for all packages, not only `raveberry`.

### I can't log in, it always says "Please reload"
You ran into CSRF protection. This happens when you host Raveberry behind a proxy and the protocols don't match up, e.g. `http://demo.raveberry.party` vs `https://demo.raveberry.party`.

Avoid this by providing your url either in the `raveberry.yaml` (install) or in the `.env` file (docker).

### Where are my YouTube files?

If you specified a path in your config file before installing, you will find them there. If no path was given, it will default to `~/Music/raveberry`. If you run it as `pi` using `raveberry run`, this will be `/home/pi/Music/raveberry`. If Raveberry was installed, the process is running as `www-data` and you will find the directory at `/var/www/Music/raveberry`.

### Streaming doesn't work (there is only silence)

This is a known issue on Ubuntu 20.04 and Debian Bullseye.
To fix it, downgrade `libshout3`:
```
cd /tmp
# for x86_64
wget http://mirrors.kernel.org/ubuntu/pool/main/libs/libshout/libshout3_2.4.1-2build1_amd64.deb -O libshout.deb
# for armhf (Raspberry Pi)
wget http://raspbian.raspberrypi.org/raspbian/pool/main/libs/libshout/libshout3_2.4.1-2_armhf.deb -O libshout.deb
sudo dpkg -i libshout.deb
sudo apt-mark hold libshout3
```

### I want to use the visualization without doing an install.

Install the required packages
```
sudo apt-get install cava
pip3 install raveberry[screenvis]
```
If `cava` is not available on apt, you need to [build it from source](https://github.com/karlstav/cava#from-source).

Then comment out the following line in the used cava config (add the `#`):
```
# source = cava.monitor
```
Now you can start the server with `raveberry run`, login with admin:admin at `localhost:8080/login` and enable the visualization at `localhost:8080/lights`.

## Special Thanks

* All the awesome people that created [Mopidy](https://mopidy.com/) for this incredibly versatile music player.
    * Especially [Mopidy-Spotify](https://github.com/mopidy/mopidy-spotify) for their continued efforts to keep Spotify playback possible.
* [django](https://www.djangoproject.com/) for providing one of the best documentations I have ever encountered.
* [@karlstav](https://github.com/karlstav) for his audio visualizer [`cava`](https://github.com/karlstav/cava).
* [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for greatly simplifying the interaction with YouTube.
* [Glium](https://github.com/glium/glium) for making OpenGL a lot less painful.
* [Steven van Tetering](https://www.tikveel.nl/) for writing [the shader](https://www.shadertoy.com/view/llycWD) I based my visualization on.
* All my friends for constantly beta testing this project.

## More Information

The [`docs/`](docs/) folder contains more information about usage, resources etc.

Don't hesitate to mail me for feedback or open an issue if you experience any problems. There is also a Reddit and a Discord community:
* Reddit: https://www.reddit.com/r/raveberry/
* Discord: https://discord.gg/dy7Jxvjj9H 

If you like this project, you can support me here:  
[![](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=ZUPUUHFQMZNQQ)
