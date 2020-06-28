FROM alpine:latest

RUN addgroup -S icecast &&\
    adduser -S icecast
    
RUN apk add --update icecast mailcap &&\
    rm -rf /var/cache/apk/*

COPY icecast.xml /etc/icecast.xml

COPY icecast-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY silence.mp3 /usr/share/icecast/web/silence.mp3

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD icecast -c /etc/icecast.xml
