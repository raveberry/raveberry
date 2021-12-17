FROM raveberry/raveberry-dependencies

WORKDIR /opt/raveberry

RUN pip install -U -r /youtube.txt &&\
	rm -rf ~/.cache/pip &&\
	mkdir logs

# copying multiple directories in one layer is not easily doable
COPY backend/core /opt/raveberry/core
COPY backend/config /opt/raveberry/config
COPY backend/main /opt/raveberry/main
COPY backend/templates /opt/raveberry/templates
COPY AUTHORS LICENSE backend/manage.py backend/VERSION /opt/raveberry/
COPY docker/entrypoint.sh /entrypoint.sh

RUN mkdir -p /Music/raveberry
RUN chown -R www-data:www-data /opt/raveberry /Music/raveberry
EXPOSE 9000

USER www-data

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/local/bin/daphne", "--bind", "0.0.0.0", "--port", "9000", "main.asgi:application"]
