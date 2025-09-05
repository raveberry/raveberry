# Changelog

## 0.11.5 - 2025-12-10

- Use virtualenv instead of modifying system packages
- Disable pipewire services during installation
- Use newer ansible version that is compatible with python 3.12
- Added aarch64 to possible architectures for volume normalization package

## 0.11.4 - 2024-12-10

- Adapt mopidy-spotify installation according to https://github.com/mopidy/mopidy-spotify
- Volume normalization: install arm64 package for aarch64 architecture during install

## 0.11.3 - 2024-08-01

- Update mopidy repository to debian bullseye
- Allow pip to install system packages
- Hide color indicator when voting indicators are disabled

## 0.11.2 - 2024-03-21

- Voting behavior is indicated
- Users are represented by different colors
- Users can override their assigned color
- Needs to be enabled in settings

- Requested songs from random suggestion for unavailable platforms are no longer discarded
- Instead they are searched for in available platforms
- Fake player no longer relies on mopidy

## 0.11.1 - 2023-12-15

- nginx port can be customized
- "Max Playlist Length" setting honored for Spotify playlists

## 0.11.0 - 2023-12-09

- New Spotify feature: device playback
- Any logged in Spotify app can be used as playback device
- Local playback is still possible, can switch between the two
- Credentials are checked for both local and device mode
- Added documentation on how to provide credentials
- Abstraction for two different players: mopidy and spotify

- Youtube Music is used for searches
- music.youtube.com links are parsed correctly
- Client streaming for Youtube did not work reliably, was removed
- Sound outputs have more descriptive names and are grouped
- Docker setup also logs low severity messages
- Too frequent alarms are prevented
- Storing dark/light theme preferences does not clash with django's


## 0.10.7 - 2022-10-30

- Check whether Jamendo songs are streamable before enqueuing them

## 0.10.6 - 2022-06-23

- Docker setup works with arbitrary container names
- Simplified client streaming settings
- Client streaming configurable from docker setup
- Playlists are not suggested if the platform is not available
- Fixed apt dependencies during install
- Don't crash the install when admin files are already present

## 0.10.5 - 2022-04-22

- Different Levels of interactivity can be set in the settings: Full Control, Full Voting, Upvotes only, No Control
- Added option to enqueue songs at the top of the queue rather than the bottom
- Fixed a bug where the main page could not be loaded when no song provider was enabled
- Dynamic streaming possible with Youtube songs

## 0.10.4 - 2022-02-12

- Added song cooldown option that prevents a song from being enqueued again for a given time
- Added buzzer success probability option. Custom sounds can be provided in `resources/sounds/yes` and `resources/sounds/no`.
- Dropdown icons have descriptions
- Removed link to /stream from dropdown
- Added button to send feedback
- Moved "Delete Current Song" button to Queue Control, which is available on docker setup
- Visualization correctly works on big screens. Previously, a scaling would lead to an only partially visible visualization.
- Prevent hashtag scrolling for distances < 1 pixel
- Fixed bug where the is-service-active check would crash for uninstalled services
- Do nothing if the currently active task strategy is requested

## 0.10.3 - 2022-01-23

- Hotspot status shows whether it would start without homewifi instead of whether it is currently enabled
- Changed message when no online suggestions are returned
- Each section in settings can be collapsed, making them much more usable
- PYTHONOPTIMIZE set to 1. pycparser has problems with level 2.

## 0.10.2 - 2022-01-22

- Refactoring: mypy and pylint run without complaining
* Simplified control flow, added type hints, sorted imports, etc.
* Added instructions to CONTRIBUTING.md

- Reordering songs works from mobile devices
- The host that is used to check internet connectivity can be configured
- New music only mode: removed suggestions for playlists, no "Error" suggestions are shown
- manage.py celery is now manage.py startcelery
- celery module renamed, update your docker-compose.yml. systemd service is updated automatically
- Sites other than `/musiq` are not tracked for user activity anymore
- Filepaths are quoted, allowing for more obscure filenames in the local library (#126)
- PYTHONOPTIMIZE is set in production, stripping docstrings and skipping asserts

## 0.10.1 - 2022-01-15

- Include resources folder in PyPi package

## 0.10.0 - 2022-01-15

- Big visualization rework:
* Visualization is more robust and more performant
* A Pi 4 can comfortably render HD@30fps, before performance always degraded significantly
* Switched library from [pi3d](https://github.com/tipam/pi3d/tree/master/pi3d) (Python) to [glium](https://github.com/glium/glium) (Rust)
* Moved the code into its own repository: [https://github.com/raveberry/visualization](https://github.com/raveberry/visualization)
* Optimized for tile-based GPUs: render directly to framebuffer, smaller and less complex shaders, less draw calls, moved computation to the CPU
* Programs are loaded dynamically, new shaders will show up as new programs
* UPS and resolution can be can be configured in `/lights`
* X resolution is adjusted to adapt to performance fluctuations
* Instead of a white xterm, the Raveberry logo is shown when no screen program is active
* Added new screen program that loops through a colored Raveberry logo
* Removed old code and dependencies
* Hide programs that require cava if it is not installed

- Raveberry exits explicitly when restarting. Sometimes, it needed to wait for a timeout, now restarts are much faster.
- Task strategy can be switched between celery and threads for low memory devices

- Visualization is possible from docker setup
- Added environment variable for docker setup to deal with CSRF issue
- Host and IP for all services can be set via environment variables
- Merged `icecast.docker-compose.yml` and `docker-compose.yml`, only the latter one exists now
- `MOPIDY_OUTPUT` can now contain slashes, e.g. for paths of filesinks

- Created dedicated resources folder for images/videos/sounds
- `raveberry system-install` is now just `raveberry install`
- Added `raveberry install --use-default-password-i-promise-ill-change-it` to allow easier scripted installs
- Move to actively developed PCA library for the led strip
- Problematic python dependencies are forced to be install from wheels, speeding up installation
- Install cava from apt instead of building from source, speeding up installation
- Simplified cava config
- Changed message when there are no hashtags
- Removed unused scripts
- Buzzer cooldown is a float
- Ansible warning silenced

## 0.9.10 - 2021-12-18

- Restructured code into a backend folder to clean up the root folder
- Added link to new discord server into readme
- Debug setup uses threads instead of celery, speeding up reload significantly
- Docker images are tagged with the version
- Lights worker flushes the settings cache before loading settings. Program changes apply immediately.

## 0.9.9 - 2021-12-09

- Big suggestion improvements:
* Trigram similarity is used instead of full text search
* Now Raveberry can provide suggestions for substrings, stop words (and, a, the etc.) and typos
* This is slower, but GIN indexes and config tweaking minimize overhead

- Song metadata is cached in the database. Suggestions are now faster than before, despite the slower query.
- Directly after the update, durations are shown incorrectly. Either wait until metadata is synced automatically overnight, or run:
- `sudo -u www-data python3 /opt/raveberry/manage.py syncsongmetadata`

- Upgraded to Django 4.0. This was necessary to use functional indexes.
- Django 2.2 would be out of support soon anyway, so now was a good time.
- Python 3.8 or higher is now required.
- The main reason for not upgrading was that multiple asgi-requests could not be processed in parallel since Django 3.0.
- In 4.0, context-aware `sync_to_async` removes this issue, finally allowing the upgrade without usability impact.

- When checking whether voting is allowed on server side, a redis transaction is used to reduce performance impact.
- Settings are cached for a short time, removing load from tasks that query settings often when they change very rarely.
- Only some instead of all urls are used to measure activity (page loads, voting and musiq requests) to decrease performance impact.

- Switched from youtube-dl to yt-dlp, significantly increasing download speed.

## 0.9.8 - 2021-12-01

- Fixed bug where color definitions got lost in the css minification process
- Tapping an "error" suggestion does nothing
- Buttons for queue control are further apart (and thus harder to mis-select)

## 0.9.6 - 2021-11-27

- Suggestions are much more responsive:
* The first line (the query itself) is shown immediately
* Offline suggestions are shown as soon as they are ready and don't wait for the online suggestions
* Placeholders for online suggestions until they are available
* Different platforms (e.g. Youtube and Spotify) are queried in parallel

- Increase dhcp ip range for hotspot
- Bluetooth scanning and connecting does not spit a huge error anymore. Cause was that requests were sent twice.
- Song duration is shown in song info modal. Current song duration can now be determined
- Ring visualization improved
- The Raspberry Pi's internal pwr led (red) is disabled when the ring is active
- The internal act led (green) indicates active Raveberry requests

## 0.9.5 - 2021-10-18

- Add option for server-side vote duplication checking by IP
- Use session keys instead of IPs to link requests logs
- Most active device entry is sorted correctly in analysis section
- Page does not scroll on mobile after clearing the input field
- Old hashtag doesn't start scrolling when adding a new one
- Correct QR code is shown for hotspot wifi on `/network-info`
- Improve documentation for remote feature
- Pin postgres version in docker-compose files
- Admin page in docker container looks fine now

## 0.9.4 - 2021-10-06

- Frontend files are shipped with the pypi package
- Long modals are scrollable (e.g. changelog, upgrade confirmation dialog)

## 0.9.3 - 2021-09-27

- Bind address can be specified for reverse ssh tunnel
- If specified, remote ssh key is always overwritten, even if one already exists (#118)
- Allowed discord bot to receive the queue key of requested songs
- System install is tested in CI

## 0.9.2 - 2021-09-24

- Database is registered correctly in celery workers. New songs will directly appear in suggestions again.
- Current song can be deleted in settings to help recover from disconnection problems (#116)
- Add donation link to readme
- Moved from travis to github actions
- Songs with identical suggestions show their duration for disambiguation in suggestions
- Arrow to insert suggestion into search input field is only shown for online suggestions
- Clearing the song input field is easier, the x has a bigger interaction area
- Analysis results are shown again
- Error message when there are no songs to analyze
- Red and blue colors are more prominent in rainbow LED visualization

## 0.9.1 - 2021-09-16

- Fix installation issue by quoting rsync argument and pinning ansible (#115).
- Mopidy container also loads jamendo client id from environment.

## 0.9.0 - 2021-07-27

- _Big_ Architecture rewrite: 
- State is not kept in a single god-object, but stored in Redis and the database
- Celery is used for long-running tasks
- As a result, playback starts with the server, not with the first request
- redis-server is required for the development server (`raveberry run`) as well

- Pause times are stored in the database, resulting in less mopidy queries
- Additionally, restarting the server after seeking a song now correctly resumes playback

- Voting and lights setting changes are possible during alarm
- Renamed internal name of voting mode, needs to be set again in settings
- Got rid of `DJANGO_MOCK` and `DJANGO_POSTGRES` environment variables. Only "runserver" and "daphne" start Raveberry, other commands don't need extra env vars anymore.
- After login, users are redirected to the page they tried to access
- Login errors are less ugly
- Player errors are indicated. Player can be restarted in settings.
- Removed gunicorn, wasn't supported for a long time anyway
- Docker container does not run as root
- Adjusting the screen temporarily stops visualization, because it restarts the worker task
- Daphne (finally) does not log into syslog anymore
- Smaller audio files are used for testing

## 0.8.13 - 2021-07-05

- Big performance improvement: reverted a dependency upgrade that made the server effectively single-threaded

## 0.8.12 - 2021-06-30

- The embedded speaker icon can now provide `/stream` as well
- Pin psycopg2 (fixes #111)

## 0.8.11 - 2021-06-23

- Made new config key optional

## 0.8.10 - 2021-06-21

- New feature: the alarm can be triggered anytime by connecting two pins on the Pi, e.g. with a buzzer. Enable in raveberry.yaml with "buzzer" key.
- Fixed youtube autoplay
- Queue updates show instantly instead of after an animation. Updates sometimes got lost when no animation was triggered. Some songs seemed to be downloading forever.
- Added option to disable duplicating audio into cava (only takes effect if any visualization is installed). Due to the large buffer size the playback sometimes gliched.
- Placeholders are correctly linked
- All `/lights` settings are stored in the database

## 0.8.9 - 2021-05-02

- Migrate databases during setup
- Failing to applay homewifi does not stop setup
- Script that sets output during setup is provided with all credentials
- Voting correctly uses the key of a queued song

## 0.8.6 - 2021-05-02

- Introducing [https://raveberry.party/](https://raveberry.party/)
- Jamendo support
- Added option to limit queue length
- Added option to not show hashtags by default
- Added option to embed the stream in the mainpage, clients stream the music directly from the service (currently only Jamendo)
- Cleaned up docker-compose file
- No more snake&#95case for frontend: camelCase for js and kebab-case for css and html
- Fixed shareberry link

## 0.8.5 - 2021-04-19

- New shuffle all button for the admin that reorders the whole queue (Finally generically implementing reordering animations pays off) (#80)
- Playlists can be created from songs played during a given time span (#106)
- [snapcast](https://github.com/badaix/snapcast) support
- icecast and snapcast can be selected as a sound output
- As a side effect, icecast streaming is not reset to be disabled every mopidy config update
- The Shareberry endpoint tries to extract a url from the received query, fixing Spotify and Soundcloud sharing
- Disconnected banner does not show when reloading or leaving the page
- Only one state update handler is registered per page (instead of every handler on every page)
- The base state is not updated twice every update
- Disable timer based scheduling in pulseaudio (fixes hdmi sound quality issues, #104)
- Made documentation regarding system install clearer
- Reactive lighting starts on a different offset on the LED ring (it was remounted)

- Removed a lot of code duplication, making new functions a lot easier to implement (hopefully):
* Url patterns are generated dynamically from backend functions
* Ajax endpoints are injected into the html via templating
* Default behavior is added to html elements corresponding to ajax endpoints
* These elements are also generically updated during state updates

## 0.8.4 - 2021-04-07

- Raveberry is upgraded by a system service, making it finish reliably
- Remove false positives for new versions (pip changed its interface)
- Testing in CI is done in a separate folder, .pyc files are not packaged anymore
- Search engine is only initialized in new databases, speeding up installation
- Due to issues during pairing, devices are connected to directly
- Tested HiFiBerry (it works)
- Config file can be specified in remote installs
- Log to console when testing

## 0.8.3 - 2021-04-05

- Use svg graphics
- Use localStorage instead of cookies
- Removed some unnecessary state updates

## 0.8.2 - 2021-04-03

- Youtube playlists, radio and autoplay work again
- Spotify can play albums and artist's top tracks
- Download limit applies to spotify songs
- Keyword filter is applied to artist and in suggestions, instead of only to the title
- Keyword filter is applied to youtube and local requests
- Tools for normalization are installed from packages instead of built from source (speeds up system installation)
- Docker version can normalize m4a files
- Dependencies container uses piwheels, significantly speeding up cross-architecture buidl

## 0.8.1 - 2021-03-27

- python3 is used by bin/raveberry, even without ansible.cfg

## 0.8.0 - 2021-03-27

- _Big_ installation rewrite: ansible is used
- Update through the webinterface is possible, but it will take some time. See the log in `/var/www`.
- Config is now in .yaml format. Your old config is automatically migrated.

- Dependencies: Package size reduced.
* Spotify, YouTube and Soundcloud can be specified during install.
* Unavailable platforms are marked in /settings.
* Install and run dependencies separated.

- mopidy config is not overwritten during install. Spotify credentials are kept across updates.
- homewifi is respected during install.
- CSS is minified.
- QR codes are readable again (styles are not purged anymore).
- Bluetooth scanning happens in a background thread, server does not hang anymore.
- Icecast is enabled even if not configured during its install.
- Key for remote access is stored in a static location.
- `raveberry run` waits for mopidy before starting.

- Visualization:
* Can be installed on systems with desktop environment, open a window.
* The window is closable. Closing will disable the screen program.

## 0.7.12 - 2021-03-22

- Checking the latest version does not prevent websockets from being opened
- Songs are sortable again when not voting (library was missing)
- Menu slide and modal background are not stripped from css anymore
- Thumbnails of songs from youtube are embedded again

## 0.7.11 - 2021-03-09

- Linted typescript code
- Reduced size of frontend bundle
* Use less and smaller js libraries
* Only ship used css and fonts
- gzip enabled in nginx
- docker: only nginx contains frontend code

## 0.7.10 - 2021-02-15
- Bugfix: state was only updated on musiq page

## 0.7.9 - 2021-02-15
- Huge frontend rework
* Migration to Typescript
* Testing
* Reduced the size of the raveberry package
- The total time of the queue is shown to users with moderator privileges.
- A default favicon is specified, eliminating a 404.

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
* Additional keywords can be specified that are added to every query.
* A list of keywords can be given that will be used to filter results. No song containing any of these words will be enqueued (Only for Spotify and Soundcloud).

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
* Packages that control leds are not required anymore (as one of them caused a segfault).
* libsass was removed, speeding up the docker build.

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
- Songs are now upvoted automatically after requesting. This required removing the placeholders as a special queue instance. Now, every request results in a persisted queue entry that is removed on error. The db-key of this queue entry is handed back to the client for upvoting. As a side effect, the new placeholders can be reordered, voted for and even removed. This required some refactoring, but now the request process is a little less convoluted.
- Decreased the number of votes required to kick a song to 2, as every song starts out with 1 now.
- `module-bluetooth-policy` is loaded on boot, which is needed by some devices.
- Added version information in the settings.
- Added option to upgrade raveberry in the settings.
