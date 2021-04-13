# Streaming

Raveberry can stream its audio output via [icecast](https://icecast.org/).

In order to enable streaming, you can go to the settings page (`http://raveberry.local/settings`) when logged in as admin and select "icecast" as sound output.
Note that you need to have the `icecast2` package installed. Raveberry will tell you to do this, but not perform the installation automatically.
On Raspbian, run `sudo apt-get install icecast2`. You will be prompted to set an admin password during installation. Although recommended, it is not required for Raveberry to stream.

After enabling streaming in the `/settings` page, icecast will be configured and started. Mopidy will be configured to output to the icecast stream instead of the local speakers.

The stream is available at `http://raveberry.local:8000/stream` (original icecast stream) and `http://raveberry.local/stream` (routed to icecast by nginx).

Since ogg streams have been reported to [cause problems](https://github.com/mopidy/mopidy/issues/1623), an mp3 stream is used.

As recommended by [mopidy's documentation](https://docs.mopidy.com/en/latest/icecast/), a fallback stream to a soundfile with 10 seconds of silence is used. This will be activated if you pause Raveberry or no songs are played. After playing music again, streams take about 30 seconds to move to the primary stream again. Alternatively, reload the stream to instantly reconnect.

As streaming relies on system services, it will not work when using `raveberry run`.



### Authentication

By default, the stream is password protected with these credentials:  
Username: `raveberry`
Password: `raveberry`
You can change this through icecast's admin interface at `http://raveberry.local:8000/admin`. Note that the stream needs to be playing for you to be able to configure it.

When sharing a link you can integrate the credentials directly like this:  
`https://raveberry:raveberry@raveberry.local/stream`

### Disabling Authentication

If you want to disable authentication completely, you need to edit icecast's config file located at `/etc/icecast2/icecast.xml` and remove the four lines of the `authentication` tag at the end of the file. For more information consult [icecast's documentation](https://www.icecast.org/docs/icecast-2.4.1/auth.html).
