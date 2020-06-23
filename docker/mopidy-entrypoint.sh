#!/bin/bash

if [ -z "$PULSE_COOKIE_DATA" ]; then
    echo -ne $(echo $PULSE_COOKIE_DATA | sed -e 's/../\\x&/g') >$HOME/pulse.cookie
    export PULSE_COOKIE=$HOME/pulse.cookie
fi

# substitute potentially set environment variables
for KEY in SPOTIFY_USERNAME SPOTIFY_PASSWORD SPOTIFY_CLIENT_ID SPOTIFY_CLIENT_SECRET SOUNDCLOUD_AUTH_TOKEN; do
    [ -z "$(printenv ${KEY})" ] && continue
    SHORT=$(echo ${KEY#*_} | tr A-Z a-z)
    sed -i "s/^.* # ${KEY}/${SHORT} = $(printenv ${KEY})/" /config/mopidy.conf /config/mopidy_icecast.conf
done

exec "$@"
