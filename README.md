# Raveberry

Raveberry is a multi user music server that allows democratic selection of songs.

It provides an intuitive interface for requesting songs and changing their order according to the rating that users have made.

![](docs/showcase.gif "Showcase Gif")

## Installation

Raveberry is meant to be installed on a Raspberry Pi. Then it works as a portable music server which you can take with you wherever you are. I used a Raspberry Pi 3B for development and testing of the software, but Raveberry should work on any Debian based Linux.

Raveberry is available on PyPi:
```
sudo apt-get install -y python3-pip ffmpeg atomicparsley mpd redis-server
pip3 install raveberry
raveberry run
```
Depending on your distribution, you may need to write `~/.local/bin/raveberry run` or add that to your PATH. `raveberry run` will start a basic version of Raveberry that can be tested on `http://localhost:8000/` (The server is running if you see `Quit the server with CONTROL-C.`).

If you want to install Raveberry system wide and make it fully featured, you can use the following command:
```
raveberry system-install
```

This assumes you have a working system with root access. If you need help setting up your Raspberry Pi, consider visiting [this guide](https://projects.raspberrypi.org/en/projects/raspberry-pi-setting-up).

You can customize your installation with the config file at [`config/raveberry.ini`](config/raveberry.ini). (Or at the location the installer tells you)

Although everything *should* work fine, I recommend taking a backup of your system. On a Raspberry Pi this is easily done by creating a copy of its SD card.

During installation you will be asked to provide a password for the admin user. This user is allowed to modify the database and change the system configuration, so choose a sensible password.

The installation will take at most 30 minutes, most of which is spent on installing/updating packages. You might need to reboot afterwards for all changes to take effect.

After the installation has finished `http://raveberry/` is up and ready to play music (go ahead and try now!). You can visit `http://raveberry/login/` and log in as the `admin` user with your provided admin password. If you take a look at `http://raveberry/settings` (which is also linked from the dropdown) you can see various configuration possibilities. For more information about these settings and privileges in general refer to [`docs/privileges.md`](docs/privileges.md).

An introduction to basic functionality can be found in [`docs/functionality.md`](docs/functionality.md). Or just visit `http://raveberry/` and find out for yourself ; )

## Features

* **Live Updates**:
Web page content is updated instantly using websockets.

* **Complementary App**:
[Shareberry](https://github.com/raveberry/shareberry/) lets you share songs directly from your phone to Raveberry.

* **Hotspot**:
Provides a WiFi network for access in areas without proper infrastructure. Can double as a repeater.

* **Remote URL**:
Specify a domain to make your Raveberry accessible from the world wide web.

* **Privilege Levels**:
Grant users additional permissions like playback control.

* **Youtube as a Database**:
With `youtube-dl` as a media provider, all of Youtube is available to play.

* **Graphical Admin Interface**:
Raveberry features a convenient way of modifying the behavior of the server, like hotspot configuration or download limitation.

* **Bluetooth support**
Use your bluetooth speakers with Raveberry, removing the need of an aux cable.

* **Screen visualization**:
With the tool [`cava`](https://github.com/karlstav/cava), the current music is split into its frequencies and visualized on a connected screen. (See screenshot below)

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

## Uninstall

During installation a backup folder is created. It contains all files that were overwritten outside of the `raveberry/` folder. To undo installation, move these files back to their respective locations using the following command. Take care of changes you made in the meantime!
```
sudo cp -r backup_{timestamp}/* / 
```
To remove files created during the setup run
```
sudo scripts/uninstall.sh
```

## More Information

Feel free to visit [`docs/`](docs/) for more information about usage, resources etc.

Don't hesitate to mail me for feedback or open an issue if you experience any problems.
