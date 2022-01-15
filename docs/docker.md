# Docker

After running `docker-compose up -d`, Raveberry is now accessible at `http://localhost/` or `http://<your hostname>/` for other devices in the network. To use a different password for the `admin` user than the default password `admin`, set it in the `.env` file.

If there is no sound and your user has a UID other than 1000, you need to provide your UID an GID for pulse to work: `UID=$(id -u) GID=$(id -g) docker-compose up -d`.
For the visualization, you would also need to change the UID of `pulse_user` in the docker container, either by live-patching or with a new Dockerfile.

If you intend to use Raveberry for a longer period, it is recommended to map the database into your filesystem in order to persist it. Uncomment the corresponding line in the `db` service of the `docker-compose.yml`.

To use local files from your system, specify the path to the desired folder in the volumes section of the file. The folder will be visible in as `/Music/raveberry`, which is the path you need to use when scanning the library.

In order to use Spotify, you need to provide your credentials in the `.env` file.


### Streaming

If you want to use the remote streaming feature, uncomment the corresponding line in the .env file (the one containing `MOPIDY_OUTPUT`).

You can also set a different password for the remote stream in the `.env` file. To disable authentication, set `STREAM_NOAUTH=1`.

### Visualization

To run the visualization from the docker setup, you need to grant permissions to open a Window on the host:
```
xhost +si:localuser:www-data
```
Now you can set a screen program on the `/lights` page.
