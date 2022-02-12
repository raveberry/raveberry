# Privileges

(Urls like `/login` refer to Raveberry's pages, so enter `http://raveberry.local/login` to access them.)

Complementing Raveberry's [base functionality](functionality.md), additional features are available to logged in users. By visiting the `/login` page, multiple privilege levels can be obtained. Since logins tend to happen quite rarely, this page is not linked from the main page. You can log in with one of the following users and the respective passwords you assigned to them. The default passwords for the `mod` user is `mod`. If you want to change it (you should), login to django's administration page at `/admin` and click on 'Users', then 'mod' and then the small link below the password hash. There you can set a new password.

## Mod
The `mod` user is able to change the playback. They can change the volume, seek the current song or skip it. They are also allowed to remove songs from the queue regardless of their score. Mods can also control the LEDs.

With mod privileges, playlists can be requested as well. A new icon appears next to the dice that enables playlist mode. Subsequent searches will then lead to each song of the playlist being added after one another. Additionally, a robot icon will appear that can be used to add Youtube's recommendations for the currently playing song.

## Admin
The `admin` user has full access to the page. This user is automatically the superuser for the webframework. By visiting `/admin` they can edit the database and change user passwords. In addition to all previously mentioned permissions, this user can access `/settings`. On this page, the following settings can be changed:

* The voting system can be enabled or disabled. If disabled, all users can freely modify the order of upcoming songs.

* Logging can be toggled. If enabled, Raveberry logs the user requests and which songs were played.

* You can define the number of active users that are necessary to switch on the alarm and the probability with which it is triggered after every song.

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

* **Streaming**:
Configures whether audio should be made available at `/stream`. See [base functionality](streaming.md) for further information.

* **Hotspot**:
Configures whether the raveberry casts its own WiFi network.

* **Hotspot Protection**:
Configures whether a password is needed to connect to the hotspot.

* **Tunneling**:
Configures whether network traffic is forwarded from the hotspot to the other interfaces i.e. whether the devices connected to the hotspot have internet access. Internally uses `iptables`.

* **Remote**:
Configures whether Raveberry is reachable through a remote URL. Uses a reverse ssh tunnel to connect to a worldwide accessible server controlled by you. See [remote.md](remote.md) for a guide on how to setup this feature.

* **Reboot**: You can also reboot the webserver and the system from the settings page.
