FROM raveberry/raveberry-dependencies

RUN pip install -U youtube-dl &&\
	rm -rf ~/.cache/pip

COPY . /opt/raveberry
COPY docker/entrypoint.sh /entrypoint.sh

WORKDIR /opt/raveberry

EXPOSE 9000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/local/bin/daphne", "--bind", "0.0.0.0", "--port", "9000", "main.asgi:application"]
