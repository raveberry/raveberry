# Privileges

(Urls like `/login` refer to Raveberry's pages, so enter `http://raveberry/login` to access them.)

Complementing Raveberry's [base functionality](functionality.md), additional features are available to logged in users. By visiting the `/login` page, multiple privilege levels can be obtained. Since logins tend to happen quite rarely, this page is not linked from the main page. You can log in with one of the following users and the respective passwords you assigned to them. The default passwords for the `mod` and the `pad` user are `mod` and `pad`. If you want to change these (you should), login to djangos administration page at `/admin` and click on 'Users', the name of the user you want to change and then the small link below the password hash. There you can set a new password.

## Mod
The `mod` user is able to change the playback. They can change the volume, seek the current song or skip it. They are also allowed to remove songs from the queue regardless of their score. Mods can also control the LEDs.

With mod privileges, playlists can be requested as well. A new icon appears next to the dice that enables playlist mode. Subsequent searches will then lead to each song of the playlist being added after one another. Additionally, a robot icon will appear that can be used to add Youtube's recommendations for the currently playing song.

## Pad
The `pad` user has all the privileges the `mod` user has. Additionally, they have access to `/pad`. This page features a simple text area to store plaintext. Useful for sharing links, contact information etc.

## Admin
The `admin` user has full access to the page. This user is automatically the superuser for the webframework. By visiting `/admin` they can edit the database and change user passwords. In addition to all previously mentioned permissions, this user can access `/settings`. On this page, the following settings can be changed:

* The voting system can be enabled or disabled. If disabled, all users can freely modify the order of upcoming songs.

* Logging can be toggled. If enabled, Raveberry logs the user requests and which songs were played.

* You can define the number of active users that are necessary to switch on the alarm and the probability with which it is triggered after every song. The sound file `alarm.mp3` was taken from [soundbible.com](http://soundbible.com/2176-Submarine-Diving.html), original by Daniel Simion, used under CC BY / slightly modified.

* The number of negative votes needed to remove a song can be changed.

* You can set a download limit for new songs. Useful when Raveberry is connected to a metered connection. Users requesting larger songs receive an appropriate error message.

* The number of songs that are downloaded when adding a playlist is customizable.

* The internet connection can be checked.

* Usually the count of active users updates at most once every minute, but you can also force an update.

* It is possible to scan for bluetooth devices and subsequently connect to one of them. After the initial connection, Raveberry will automatically connect to this device again.

* You can also connect to WiFi networks from this page. This is especially useful if you have a WiFi dongle, because then you can access the Raveberry's settings page from its own WiFi and connect to available networks.

* You can set a home WiFi network. In this network, Raveberry will not activate its hotspot.

* There is a small analysis tool available. It lists the most frequently played song and the most active device for a specified period of time. The playlist for that period can also be exported. Only works if logging is enabled.

At the bottom of the settings page, the system can be configured in various ways:

* **Events**:
Configures whether live updates with websockets are active. Internally this option changes the deployment between `daphne` (websockets suported) and `gunicorn` (websockets disabled). Since websockets require a lot of computation on server side, disabling them can reduce strain on the CPU. However, this also diminishes user experience significantly.

* **Hotspot**:
Configures whether the raveberry casts its own WiFi network.

* **Hotspot Protection**:
Configures whether a password is needed to connect to the hotspot.

* **Tunneling**:
Configures whether network traffic is forwarded from the hotspot to the other interfaces i.e. whether the devices connected to the hotspot have internet access. Internally uses `iptables`.

* **Remote**:
Configures whether Raveberry is reachable through a remote URL. Uses a reverse ssh tunnel to connect to a worldwide accessible server controlled by you. See `raveberry-remote` for an example nginx configuration file.

* **Reboot**: You can also reboot the webserver and the system from the settings page.
