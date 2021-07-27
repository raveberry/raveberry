# Docker

After running `docker-compose up -d`, Raveberry is now accessible at `http://localhost/` or `http://<your hostname>/` for other devices in the network. To use a different password for the `admin` user than the default password `admin`, set it in the `.env` file.

If there is no sound, you might need to provide your UID an GID for pulse to work: `UID=$(id -u) GID=$(id -g) docker-compose up -d`

To use local files from your system, specify the path to the desired folder in the volumes section of the file. The folder will be visible in as `/Music/raveberry`, which is the path you need to use when scanning the library.

In order to use Spotify, you need to provide your credentials in the `.env` file.

Note: Playback and voting should work as expected, but additional features like visualization or the hotspot are not supported (yet).


### Streaming

If you want to use the remote streaming feature, use the separate docker-compose file:
```
wget https://raw.githubusercontent.com/raveberry/raveberry/master/icecast.docker-compose.yml
docker-compose -f icecast.docker-compose.yml up -d
```

The setting in the admin page does not toggle streaming. You can provide a custom icecast configuration in `icecast.docker-compose.yml` to tweak it.

You can set a different password for the remote stream in the `.env` file. To disable authentication, set `STREAM_NOAUTH=1`.
