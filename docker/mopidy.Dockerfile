FROM python:3


RUN wget -q -O - https://apt.mopidy.com/mopidy.gpg | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn apt-key add - &&\
	wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list &&\
	apt-get update &&\
	apt-get install -y mopidy mopidy-spotify mopidy-soundcloud ffmpeg atomicparsley libspotify-dev libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad dumb-init &&\
	apt-get clean

# Start helper script.
COPY mopidy-entrypoint.sh /entrypoint.sh

# Default configurations.
COPY mopidy.conf /config/mopidy.conf
COPY mopidy_icecast.conf /config/mopidy_icecast.conf

# Copy the pulse-client configuratrion.
COPY pulse-client.conf /etc/pulse/client.conf

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
