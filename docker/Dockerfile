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
COPY backend/resources /opt/raveberry/resources
COPY AUTHORS LICENSE backend/manage.py backend/VERSION /opt/raveberry/
COPY docker/entrypoint.sh /entrypoint.sh

COPY docker/pulse-client.conf /etc/pulse/client.conf
COPY docker/cava_wrapper /cava_wrapper

# create a user with the UID 1000, so it can access the host's pulse server
# this user needs write access on its config, so add it to the www-data group
# in order to transparently run cava as this new user,
# wrap cava in a script that calls sudo as the new user
# add the corresponding sudoers entry so no password is asked
RUN mkdir -p /Music/raveberry &&\
	chown -R www-data:www-data /opt/raveberry /Music/raveberry &&\
	sed -i -r -e "s|(^source = .*)|#\1|" /opt/raveberry/config/cava.config &&\
	useradd -mu 1000 -g 33 pulse_user &&\
    echo "www-data ALL=(pulse_user) NOPASSWD:/usr/bin/orig_cava" >> /etc/sudoers &&\
	mv /usr/bin/cava /usr/bin/orig_cava &&\
	mv /cava_wrapper /usr/bin/cava &&\
	chmod +x /usr/bin/cava

EXPOSE 9000

USER www-data

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/local/bin/daphne", "--bind", "0.0.0.0", "--port", "9000", "main.asgi:application"]
