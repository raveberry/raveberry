FROM debian:buster

COPY common.txt prod.txt docker.txt ./

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

RUN wget https://downloads.sourceforge.net/project/audiotools/audiotools/3.1.1/audiotools-3.1.1.tar.gz &&\
	tar -xf audiotools-3.1.1.tar.gz &&\
	rm audiotools-3.1.1.tar.gz &&\
	cd audiotools-3.1.1 &&\
	python3 setup.py build &&\
	python3 setup.py install &&\
	cd .. &&\
	rm -rf audiotools-3.1.1
