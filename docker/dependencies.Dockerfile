FROM debian:buster

COPY common.txt youtube.txt spotify.txt soundcloud.txt prod.txt docker.txt ./

RUN apt-get update &&\
	apt-get install -y python3-pip ffmpeg atomicparsley wget gnupg audiotools libfaad2 libpq-dev &&\
	apt-get clean

RUN if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
		echo "downloading amd" &&\
		wget -O /tmp/faad2.deb http://launchpadlibrarian.net/335256796/faad_2.7-8+deb7u1build0.14.04.1_amd64.deb; \
	elif [ "$(dpkg --print-architecture)" = "armhf" ]; then \
		echo "downloading arm" &&\
		wget -O /tmp/faad2.deb http://launchpadlibrarian.net/335256808/faad_2.7-8+deb7u1build0.14.04.1_armhf.deb; \
	else \
		exit 1; \
	fi; \
	dpkg -i /tmp/faad2.deb &&\
	rm /tmp/faad2.deb

RUN pip3 install -U pip

# add piwheels index to avoid compiling cryptography with rust
RUN pip3 install --extra-index-url https://www.piwheels.org/simple -r docker.txt &&\
	rm -rf ~/.cache/pip
