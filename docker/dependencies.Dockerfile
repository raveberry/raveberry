FROM debian:buster

COPY common.txt prod.txt docker.txt ./

RUN apt-get update &&\
	apt-get install -y python3-pip ffmpeg atomicparsley wget gnupg audiotools libfaad2 libpq-dev &&\
	apt-get clean

# cryptography install failed even with rust installed. don't use rust for now
RUN CRYPTOGRAPHY_DONT_BUILD_RUST=1 pip install -r docker.txt &&\
	rm -rf ~/.cache/pip

RUN wget https://downloads.sourceforge.net/project/audiotools/audiotools/3.1.1/audiotools-3.1.1.tar.gz &&\
	tar -xf audiotools-3.1.1.tar.gz &&\
	rm audiotools-3.1.1.tar.gz &&\
	cd audiotools-3.1.1 &&\
	python3 setup.py build &&\
	python3 setup.py install &&\
	cd .. &&\
	rm -rf audiotools-3.1.1
