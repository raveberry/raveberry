FROM raveberry/raveberry-dependencies

RUN pip install psycopg2 &&\
	pip install raveberry --no-deps --target /opt &&\
	rm -rf ~/.cache/pip

WORKDIR /opt/raveberry
