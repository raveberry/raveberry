FROM raveberry/raveberry

RUN pip3 install bs4 &&\
	rm -rf ~/.cache/pip

COPY tests /opt/raveberry/tests
