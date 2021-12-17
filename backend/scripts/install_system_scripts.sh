#!/bin/bash
if [ "$EUID" -ne 0 ]
then echo "Please run as root"
	exit
fi
mkdir -p /usr/local/sbin/raveberry
cp scripts/system/* /usr/local/sbin/raveberry/
