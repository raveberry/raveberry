FROM python:3


RUN wget -q -O - https://apt.mopidy.com/mopidy.gpg | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn apt-key add - &&\
	wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list &&\
	apt-get update &&\
	apt-get install -y mopidy mopidy-spotify mopidy-soundcloud ffmpeg libspotify-dev libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad dumb-init python3-pip &&\
	apt-get clean

# downgrade libshout in order to make streaming work
RUN cd /tmp &&\
	arch=$(uname -m) &&\
	( [ "$arch" = "x86_64" ] && wget http://mirrors.kernel.org/ubuntu/pool/main/libs/libshout/libshout3_2.4.1-2build1_amd64.deb -O libshout.deb || :) &&\
	( [ "$arch" = "armv7l" ] && wget http://raspbian.raspberrypi.org/raspbian/pool/main/libs/libshout/libshout3_2.4.1-2_armhf.deb -O libshout.deb || :) &&\
	dpkg -i libshout.deb &&\
	apt-mark hold libshout3

RUN /usr/bin/pip3 install Mopidy-Jamendo &&\
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
