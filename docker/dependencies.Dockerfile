FROM python:3

COPY common.txt .
RUN apt-get update &&\
	apt-get install -y ffmpeg atomicparsley wget gnupg &&\
	apt-get clean &&\
	pip install -r common.txt &&\
	rm -rf ~/.cache/pip
