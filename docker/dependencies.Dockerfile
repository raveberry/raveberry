FROM python:3

COPY common.txt .
RUN apt-get update &&\
	apt-get install -y ffmpeg atomicparsley wget gnupg audiotools &&\
	apt-get clean &&\
	pip install -r common.txt &&\
	ln -s /usr/lib/python3/dist-packages/audiotools /usr/local/lib/python3.8/site-packages &&\
	rm -rf ~/.cache/pip
