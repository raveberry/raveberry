FROM python:3


RUN mkdir -p /etc/apt/keyrings &&\
	wget -q -O /etc/apt/keyrings/mopidy-archive-keyring.gpg https://apt.mopidy.com/mopidy.gpg &&\
	wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/bullseye.list &&\
	apt-get update &&\
	apt-get install -y mopidy mopidy-soundcloud ffmpeg libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad dumb-init python3-pip &&\
	apt-get clean

# dependencies for https://github.com/mopidy/mopidy-spotify
RUN cd /tmp &&\
	arch=$(uname -m) &&\
	( [ "$arch" = "x86_64" ] && wget https://github.com/kingosticks/gst-plugins-rs-build/releases/download/gst-plugin-spotify_0.14.0-alpha.1-1/gst-plugin-spotify_0.14.0.alpha.1-1_amd64.deb -O gst-plugin-spotify.deb || :) &&\
	( [ "$arch" = "armv7l" ] && wget https://github.com/kingosticks/gst-plugins-rs-build/releases/download/gst-plugin-spotify_0.14.0-alpha.1-1/gst-plugin-spotify_0.14.0.alpha.1-1_armhf.deb -O gst-plugin-spotify.deb || :) &&\
	dpkg -i gst-plugin-spotify.deb

# downgrade libshout in order to make streaming work.
# TODO: fails due to missing libssl1.1
# either make streaming work with newer libshout again or install old libssl versions manually
#RUN cd /tmp &&\
#	arch=$(uname -m) &&\
#	( [ "$arch" = "x86_64" ] && wget http://mirrors.kernel.org/ubuntu/pool/main/libs/libshout/libshout3_2.4.1-2build1_amd64.deb -O libshout.deb || :) &&\
#	( [ "$arch" = "armv7l" ] && wget http://raspbian.raspberrypi.org/raspbian/pool/main/libs/libshout/libshout3_2.4.1-2_armhf.deb -O libshout.deb || :) &&\
#	dpkg -i /tmp/libshout.deb &&\
#	apt-mark hold libshout3

RUN /usr/bin/pip3 install --break-system-packages Mopidy-Spotify==5.0.0a3 Mopidy-Jamendo &&\
	rm -rf ~/.cache/pip &&\
	mkdir -p /opt/raveberry/

COPY docker/mopidy-entrypoint.sh /entrypoint.sh
COPY docker/mopidy.conf /config/mopidy.conf
COPY docker/pulse-client.conf /etc/pulse/client.conf
COPY backend/resources /opt/raveberry/resources

# Allows any user to run mopidy
ENV HOME=/var/lib/mopidy
RUN set -ex &&\
	usermod -G audio,sudo mopidy &&\
	chown mopidy:audio -R $HOME /entrypoint.sh /config &&\
	chmod go+rwx -R $HOME /entrypoint.sh /config

USER mopidy

EXPOSE 6680

ENTRYPOINT ["/usr/bin/dumb-init", "/entrypoint.sh"]
CMD ["/usr/bin/mopidy", "--config", "/config/mopidy.conf"]
