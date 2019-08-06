# Raveberry

Raveberry is a multi user music server that allows democratic selection of songs.

It provides an intuitive interface for requesting songs and changing their order according to the rating that users have made.

![](docs/showcase.gif "Showcase Gif")

## Installation

Raveberry is meant to be installed on a Raspberry Pi. Then it works as a portable music server which you can take with you wherever you are. I used a Raspberry Pi 3B for development and testing of the software, but Raveberry should work on any Debian based Linux.

You can customize your installation with the config file at [`config/raveberry.ini`](config/raveberry.ini).

Although everything *should* work fine, I recommend taking a backup of your system. On a Raspberry Pi this is easily done by taking a copy of its SD card.

Installing Raveberry is very simple:
```
git clone
cd raveberry
nano config/raveberry.ini
sudo ./setup.py
```
This assumes you have a working system with root access. If you need help setting up your Raspberry Pi, consider visiting [this guide](https://projects.raspberrypi.org/en/projects/raspberry-pi-setting-up).

During installation you will be asked to provide a password for the admin user. This user is allowed to modify the database and change the system configuration, so choose a sensible password.

After the installation you should login to the admin page (URL `/admin`) and change the passwords of the other users. For more information about privileges take a look at [`docs/privileges.md`](docs/privileges.md).

The installation will take at most 30 minutes, most of which is spent on installing/updating packages. You might need to reboot for all changes to take effect.

For an introduction to basic functionality refer to [`docs/functionality.md`](docs/functionality.md). Or just visit `http://raveberry/` and find out for yourself ; )

## Features

* **Live Updates**:
Web page content is updated instantly using websockets.

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

* **Audio normalization**:
Raveberry uses `aacgain` to analyze the volume of songs and prevent sharp volume transitions.

* **Audio visualization**:
With the tool [`cava`](https://github.com/karlstav/cava), the music currently playing is split into its frequencies and mapped to the color spectrum. Connected LEDs then flash to the rhythm of the music. 


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
