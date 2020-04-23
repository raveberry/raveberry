FROM python:3

COPY common.txt .
RUN apt-get install -y wget gnupg &&\
	wget -q -O - https://apt.mopidy.com/mopidy.gpg | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn apt-key add - &&\
	wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list &&\
	apt-get update &&\
	apt-get install -y mopidy ffmpeg atomicparsley libspotify-dev libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad &&\
	apt-get clean &&\
	pip install -r common.txt &&\
	rm -rf ~/.cache/pip
