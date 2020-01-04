echo "*** Installing apt Dependencies ***"
apt-get update
packagelist=(
	python3-pip #python package management
	dnsmasq hostapd #wifi access point
	ffmpeg #audio conversion
	atomicparsley #thumbnail embedding
	nginx #webserver
	mpd #player
	postgresql libpq-dev #postgresql-contrib #database
	redis-server #channel layer
	autossh #remote connection
	curl #key fetching
)
apt-get install -y ${packagelist[@]} || exit 1
# Install bluetooth backend. Not required, thus as extra command that may fail
apt-get install -y bluealsa

# force system wide reinstall even if packages are present for the user by using sudo -H
sudo -H pip3 install -r requirements.txt || exit 1

echo "*** Installing yarn ***"
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" > /etc/apt/sources.list.d/yarn.list
apt-get update
apt-get install -y yarn

if [ ! -z "$SCREEN_VISUALIZATION" ]; then
	echo "*** Installing pi3d and dependencies ***"
	pip3 install pi3d # OpenGL Framework
	packagelist=(
		python3-numpy # heavyer computation; pip installs too new version
		python3-pil # image texture loading
		mesa-utils libgles2-mesa-dev # graphics drivers
		xorg # X is needed for displaying
	)
	apt-get install -y ${packagelist[@]} || exit 1
fi

if [ ! -z "$LED_VISUALIZATION" ]; then
	echo "*** Installing cava ***"
	cd /opt
	git clone https://github.com/karlstav/cava
	cd cava
	apt-get install -y libfftw3-dev libasound2-dev libncursesw5-dev libpulse-dev libtool m4 automake libtool
	./autogen.sh
	./configure
	make
	make install
	cd $SERVER_ROOT
fi

if [ ! -z "$AUDIO_NORMALIZATION" ]; then
	echo "*** Installing aacgain ***"
	apt-get install -y libtool

	mkdir -p /opt/aacgain
	cd /opt/aacgain
	wget https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/mp4v2/mp4v2-1.9.1.tar.bz2
	tar -jxf mp4v2-1.9.1.tar.bz2
	rm mp4v2-1.9.1.tar.bz2

	wget http://downloads.sourceforge.net/sourceforge/faac/faad2-2.7.tar.bz2
	tar -jxf faad2-2.7.tar.bz2
	rm faad2-2.7.tar.bz2

	git clone https://github.com/elfchief/mp3gain
	git clone https://aur.archlinux.org/aacgain-cvs.git

	rm -rf mp4v2 faad2
	mv mp4v2-1.9.1 mp4v2
	mv faad2-2.7 faad2
	mv mp3gain mp3gain-tree
	mv mp3gain-tree/aacgain ./
	mv mp3gain-tree/mp3gain ./
	cd aacgain

	patch -d ../ -p1 <mp4v2.patch
	cd ../mp4v2
	patch -p0 <../aacgain-cvs/fix_missing_ptr_deref.patch
	./configure
	make libmp4v2.la

	cd ../faad2
	./configure
	cd libfaad
	make

	cd ../../aacgain/linux
	sed "s/patch -p0 -N <mp3gain.patch/patch -d ..\/..\/ -p2 -N <mp3gain.patch/" -i prepare.sh
	chmod +x prepare.sh
	./prepare.sh
	rm -rf build
	mkdir build
	cd build
	../../../configure --prefix=/usr
	make
	cp aacgain/aacgain /usr/bin
	cd $SERVER_ROOT
fi

echo "*** Installing System Scripts ***"
scripts/install_system_scripts.sh
