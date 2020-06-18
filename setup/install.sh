# this needs to be done before apt installation, so mopidy is on the newest version
echo "*** Installing libspotify ***"
wget -q -O - https://apt.mopidy.com/mopidy.gpg | apt-key add -
wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list
sudo apt-get update
apt-get install -y libspotify-dev

echo "*** Installing apt Dependencies ***"
apt-get update
packagelist=(
	python3-pip #python package management
	ffmpeg #audio conversion
	atomicparsley #thumbnail embedding
	nginx #webserver
	mopidy pulseaudio #player
	mopidy-spotify mopidy-soundcloud # mopidy extensions
	pulseaudio-module-bluetooth # bluetooth playback
	libglib2.0-dev libgirepository1.0-dev libcairo2-dev # PyGObject dependencies
	gstreamer1.0-plugins-bad # m4a playback
	postgresql libpq-dev #database
	redis-server #channel layer
	autossh #remote connection
	curl #key fetching
)
apt-get install -y ${packagelist[@]} || exit 1

# force system wide reinstall even if packages are present for the user by using sudo -H
sudo -H pip3 install -r requirements.txt || exit 1

if [ ! -z "$HOTSPOT" ]; then
	apt-get install -y dnsmasq hostapd #wifi access point
fi

if [ ! -z "$SCREEN_VISUALIZATION" ]; then
	echo "*** Installing pi3d and dependencies ***"
	sudo -H pip3 install pi3d # OpenGL Framework
	packagelist=(
		python3-numpy # heavier computation; pip installs too new version
		python3-scipy # gaussian filtering
		python3-pil # image texture loading
		mesa-utils libgles2-mesa-dev # graphics drivers
		xorg # X is needed for displaying
	)
	apt-get install -y ${packagelist[@]} || exit 1
fi

if [ ! -z "$LED_VISUALIZATION" ]; then
	echo "*** Installing dependencies for led control ***"
	sudo -H pip3 install -r requirements/ledvis.txt || exit 1
fi

if [[ ( ! -z "$LED_VISUALIZATION" || ! -z "$SCREEN_VISUALIZATION" ) ]] && ! type cava > /dev/null 2>&1; then
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

if [ ! -z "$AUDIO_NORMALIZATION" ] && ! type rganalysis > /dev/null 2>&1 ; then
	echo "*** Installing rganalysis ***"
	apt-get install -y python3-dev bzip2 gcc make

	cd /opt
	wget https://downloads.sourceforge.net/project/audiotools/audiotools/3.1.1/audiotools-3.1.1.tar.gz
	tar -xf audiotools-3.1.1.tar.gz
	rm audiotools-3.1.1.tar.gz
	cd audiotools-3.1.1
	python3 setup.py build
	python3 setup.py install

	# install faad to analyze aac files
	cd /opt
	wget http://downloads.sourceforge.net/sourceforge/faac/faad2-2.7.tar.bz2
	tar -jxf faad2-2.7.tar.bz2
	rm faad2-2.7.tar.bz2
	cd faad2-2.7
	./configure
	make install

	sudo -H pip3 install https://github.com/DarwinAwardWinner/rganalysis/archive/master.zip

	cd $SERVER_ROOT
fi

echo "*** Installing System Scripts ***"
scripts/install_system_scripts.sh
