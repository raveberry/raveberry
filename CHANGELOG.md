# Changelog

## 0.7.8 - 2021-01-17

- A backup stream can be provided in the settings that is played whenever the queue is empty
- There should be no more notifications about updates when none are available (sorry)

## 0.7.7 - 2020-11-16

- Remove CSRF checks for voting methods, as the Discord bot needs to access them.

## 0.7.6 - 2020-11-16

- Stick to django channels 2.2
- youtube-dl struggles with playlist downloading

## 0.7.5 - 2020-09-20

- IP of the hotspot is shown in `/network_info`.

## 0.7.4 - 2020-09-20

- The admin is informed about new versions.
- `/network_info` now shows info for both networks if the hotspot is enabled.
- The button that toggles repeat mode is not hidden in voting mode.

## 0.7.3 - 2020-08-20

- Added two new options in the settings that modify search behavior.
	- Additional keywords can be specified that are added to every query.
	- A list of keywords can be given that will be used to filter results. No song containing any of these words will be enqueued (Only for Spotify and Soundcloud).

## 0.7.2 - 2020-08-20

- Added a "new music only" mode. No suggestions are given and only songs that have never been played are accepted.
- Added local music as a new platform, so local songs can be searched for.
- All superusers act as admin, regardless of username.

## 0.7.1 - 2020-08-06

- Added a necessary dependency for cava install.
- Fixed install when no hotspot ssid is given.

## 0.7.0 - 2020-08-02

- Add WLED support.
- Removed the pad.
- Overwrite Youtube's cookie file if it is empty.
- Less verbose CSRF error.
- Add `--local` option to `raveberry` command to use a local raveberry copy instead of the installed package.
- Hide shuffle and repeat buttons in voting mode as they have no effect anyway when voting.

## 0.6.15 - 2020-07-16
- Added the `/network_info` page that shows wifi and ip information and allows people to connect with the shown qr codes.
- Swapped the pad icon with the qr icon linking to the new page.
- Accessing the `/settings` without being logged in redirects you to the login page.
- Light mode works on every page, not just `/musiq`.
- Added a shutdown button in `/settings`.
- Hide all passwords in `/settings`.

## 0.6.14 - 2020-07-02
- Fixed a bug where migrations where not performed during install, making it impossible to run Raveberry.
- Credentials can now be passed to the mopidy container via environment variables.
- Disabling stream authentication is now simpler in the docker setup.

## 0.6.13 - 2020-06-28
- Javascript files are copied into the nginx container. This removes the need of the shared static folder.
- `DJANGO_MOCK` always uses the debug database, unless otherwise specified with `DJANGO_POSTGRES`. It also mocks all url patterns instead of just faking them.

## 0.6.12 - 2020-06-28

- Clicking the current songs shows further information as well (like it does for songs in the queue)
- Since the little cross at the right end of the input field is a little small, the cursor now moves to the right of the text when tapped. Then, the text can be deleted with the keyboard.

## 0.6.11 - 2020-06-25

- In voting mode, the voting buttons are now shown to logged in users as well.
- Allow users to upgrade from a config where no hotspot ssid was specified.

## 0.6.10 - 2020-06-24

- settings.py (the previously largest file) was split into smaller files.
- player.py was split into playback.py and controller.py
- In suggestions, playcount is fetched from the database to avoid presenting stale information.
- Code was made more mypy and pylint compliant.
- The number of suggestions that is shown when searching can be customized.
- The number of online suggestions can be changed for each service individually.
- The name of the WiFi created by Raveberry can be changed in the config file.

## 0.6.9 - 2020-06-18
- Due to a bug in youtube-dl, it currently crashes during thumbnail embedding. Thus, it was temporarily disabled.

## 0.6.8 - 2020-06-18

- The config file is persisted during system installation. Now a custom config can be used during upgrade.
- css files are published, removing the need of building them on device.
- Dependencies were cleaned up.
	- Packages that control leds are not required anymore (as one of them caused a segfault).
	- libsass was removed, speeding up the docker build.

## 0.6.7 - 2020-06-10

- Users can vote 10 times in 30 seconds instead of once every 5 seconds
- Unavailable options are greyed out in settings

## 0.6.6 - 2020-06-11

- Requesting archived musiq also toggles the upvote button
- If more than one backend is configured, only one online suggestion per service is displayed
- [watson](https://github.com/etianen/django-watson) is used to search the database for suggestions

## 0.6.5 - 2020-06-08

- Bump django to 2.2.13

## 0.6.4 - 2020-05-20

- Started keeping this changelog.
- Songs are now upvoted automatically after requesting.  
This required removing the placeholders as a special queue instance. Now, every request results in a persisted queue entry that is removed on error. The db-key of this queue entry is handed back to the client for upvoting.  
As a side effect, the new placeholders can be reordered, voted for and even removed. This required some refactoring, but now the request process is a little less convoluted.
- Decreased the number of votes required to kick a song to 2, as every song starts out with 1 now.
- `module-bluetooth-policy` is loaded on boot, which is needed by some devices.
- Added version information in the settings.
- Added option to upgrade raveberry in the settings.
