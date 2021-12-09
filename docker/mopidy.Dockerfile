FROM python:3


RUN wget -q -O - https://apt.mopidy.com/mopidy.gpg | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn apt-key add - &&\
	wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list &&\
	apt-get update &&\
	apt-get install -y mopidy mopidy-spotify mopidy-soundcloud ffmpeg libspotify-dev libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad dumb-init python3-pip&&\
	apt-get clean

RUN /usr/bin/pip3 install Mopidy-Jamendo &&\
	rm -rf ~/.cache/pip &&\
	mkdir -p /opt/raveberry/config/sounds

# Start helper script.
COPY docker/mopidy-entrypoint.sh /entrypoint.sh

# Default configurations.
COPY docker/mopidy.conf /config/mopidy.conf

# Copy the pulse-client configuration.
COPY docker/pulse-client.conf /etc/pulse/client.conf

COPY config/sounds/alarm.m4a /opt/raveberry/config/sounds/

# Allows any user to run mopidy, but runs by default as a randomly generated UID/GID.
ENV HOME=/var/lib/mopidy
RUN set -ex \
 && usermod -G audio,sudo mopidy \
 && chown mopidy:audio -R $HOME /entrypoint.sh /config \
 && chmod go+rwx -R $HOME /entrypoint.sh /config

# Runs as mopidy user by default.
USER mopidy

EXPOSE 6680

ENTRYPOINT ["/usr/bin/dumb-init", "/entrypoint.sh"]
CMD ["/usr/bin/mopidy", "--config", "/config/mopidy.conf"]
