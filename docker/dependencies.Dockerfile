FROM python:3

COPY common.txt docker.txt ./

RUN apt-get update &&\
	apt-get install -y ffmpeg atomicparsley wget gnupg &&\
	apt-get clean &&\
	pip install -r docker.txt &&\
	rm -rf ~/.cache/pip

RUN wget https://downloads.sourceforge.net/project/audiotools/audiotools/3.1.1/audiotools-3.1.1.tar.gz &&\
	tar -xf audiotools-3.1.1.tar.gz &&\
	rm audiotools-3.1.1.tar.gz &&\
	cd audiotools-3.1.1 &&\
	python3 setup.py build &&\
	python3 setup.py install &&\
	cd .. &&\
	rm -rf audiotools-3.1.1
