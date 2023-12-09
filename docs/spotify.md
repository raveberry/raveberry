# Spotify

You have two options to use Spotify with Raveberry. Local playback and device playback. For both, Spotify premium is required.

## Device Playback
Raveberry uses the Spotify API to play songs on any of your devices (e.g. your phone).
In this mode, your Raveberry instance can be anywhere, as long as it's connected to the internet. Playing songs from other sources like Youtube is not possible.

Setup:
* Enable your account for https://developer.spotify.com/
* Create a new App in your [dashboard](https://developer.spotify.com/dashboard)
* In Redirect URIs, add `http://localhost`
* Copy the client id and client secret
* Open the `/settings` of your Raveberry instance
* Go to the Spotify section for device playback
* Provide the client id, client secret and redirect uri from the app in your Spotify dashboard
* Click the link that appears
* Authenticate with your Spotify Account
* Copy the link that you are redirected to from the address bar of your browser
* Provide this link to "Auth Url"
* Click "Set Credentials"
* Enable Spotify (checkbox at the top of the settings section)
* Make sure your desired output device is active (e.g. by playing any song on your phone)
* In the "Sound Output" section, click the dropdown for Output
* Choose your Spotify device (Spotify devices are marked with "`[spotify]`")

Now Raveberry should be able to see and control your devices.
Test it by queuing any Spotify song from the main page. You might need to restart Raveberry.

The requested permissions and their uses are:
* `user-read-playback-state`: list devices, currently playing
* `user-modify-playback-state`: play songs, pause, seek, volume
* `playlist-read-private, playlist-read-collaborative, user-library-read`: suggest private playlists and songs in search

## Local Playback
Alternatively, you can have Raveberry play the Spotify songs directly. You can mix Spotify songs with songs from different sources like Youtube.
In this mode, seeking does not work. You can combine this mode with streaming or snapcast.

Setup:
* Install the newest `mopidy-spotify` extension: `sudo pip3 install https://github.com/mopidy/mopidy-spotify/archive/master.zip`
* Go to https://mopidy.com/ext/spotify/#authentication
* Authenticate with your Spotify account
* Copy the client_id and client_secret
* Open the `/settings` of your Raveberry instance
* Go to the Spotify section for local playback
* Provide your Spotify username and password and the client id and client secret you copied previously
* Click "Set Credentials"
* Enable Spotify (checkbox at the top of the settings section)
* In the "Sound Output" section, click the dropdown for Output
* Choose your desired local output method

Now Raveberry should be able to play Spotify songs.
Test it by queuing any Spotify song from the main page. You might need to restart Raveberry or mopidy.