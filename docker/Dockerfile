FROM raveberry/raveberry-dependencies

WORKDIR /opt/raveberry

RUN pip install -U youtube-dl &&\
	rm -rf ~/.cache/pip &&\
	mkdir logs

# copying multiple directories in one layer is not easily doable
COPY core /opt/raveberry/core
COPY config /opt/raveberry/config
COPY main /opt/raveberry/main
COPY templates /opt/raveberry/templates
COPY AUTHORS LICENSE manage.py VERSION /opt/raveberry/
COPY docker/entrypoint.sh /entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/local/bin/daphne", "--bind", "0.0.0.0", "--port", "9000", "main.asgi:application"]
