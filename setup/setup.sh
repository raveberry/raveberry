#!/bin/bash
if [ "$EUID" -ne 0 ]
then echo "Please run as root"
	exit
fi

export SERVER_ROOT=$PWD
echo "*** Using this directory ($SERVER_ROOT) as install directory ***"

export BACKUP_DIR="backup_$(date +%Y-%m-%d-%H:%M:%S)"
mkdir $BACKUP_DIR

echo "***** Installing Dependencies *****"
setup/install.sh || { echo "Could not install required dependencies"; exit 1; }

echo "***** Configuring Network *****"
setup/network.sh

echo "***** Configuring System *****"
setup/system.sh

echo "***** Configuring Database *****"
setup/database.sh

echo "***** Configuring Webserver *****"
setup/server.sh

echo ""
echo "***** Finished *****"
echo ""
echo "Raveberry was installed on this system!"
echo "You can now visit http://raveberry/"
echo "A reboot might be necessary for the system to be reachable under this name."
