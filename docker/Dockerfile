FROM raveberry/raveberry-dependencies

RUN pip3 install psycopg2 &&\
	rm -rf ~/.cache/pip

# persist raveberry (build context) in container
# TODO: change with pip
COPY . /opt/raveberry
WORKDIR /opt/raveberry
