FROM ubuntu:focal

# have tzdata install without userinput
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y wget gnupg postgresql libpq-dev iputils-ping sudo
RUN wget -q -O - https://apt.mopidy.com/mopidy.gpg | apt-key add -
RUN wget -q -O - https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" > /etc/apt/sources.list.d/yarn.list
RUN apt-get update
RUN apt-get install -y python3-pip ffmpeg atomicparsley mopidy redis-server libspotify-dev libglib2.0-dev libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad yarn

# persist raveberry (build context) in container
RUN mkdir -p /opt/raveberry
COPY . /opt/raveberry

WORKDIR /opt/raveberry
RUN yarn install
RUN pip3 install -r requirements.txt
RUN pip3 install bs4

ENTRYPOINT ["./tests/start_services.sh"]
CMD ["bash"]
