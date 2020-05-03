FROM raveberry/raveberry-dependencies

RUN apt-get update &&\
	wget -q -O - https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - &&\
	echo "deb https://dl.yarnpkg.com/debian/ stable main" > /etc/apt/sources.list.d/yarn.list &&\
	apt-get update &&\
	apt-get install -y yarn &&\
	apt-get clean &&\
	pip3 install -U youtube-dl &&\
	pip3 install psycopg2 bs4 &&\
	rm -rf ~/.cache/pip

# persist raveberry (build context) in container
COPY . /opt/raveberry
WORKDIR /opt/raveberry

RUN yarn install &&\
	scripts/clean_libs.sh
