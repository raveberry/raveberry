FROM raveberry/raveberry-dependencies

RUN apt-get install -y mopidy-spotify dumb-init &&\
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
 && chown mopidy:audio -R $HOME /entrypoint.sh \
 && chmod go+rwx -R $HOME /entrypoint.sh

# Runs as mopidy user by default.
USER mopidy

EXPOSE 6680

ENTRYPOINT ["/usr/bin/dumb-init", "/entrypoint.sh"]
CMD ["/usr/bin/mopidy", "--config", "/config/mopidy.conf"]
