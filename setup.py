#!/usr/bin/env python3
import configparser
import subprocess
import os

config = configparser.ConfigParser()
config.read('config/raveberry.ini')
for section_name, section in config.items():
    for key, value in section.items():
        try:
            enabled = config.getboolean(section_name, key)
        except ValueError:
            enabled = True
        if enabled:
            os.environ[key.upper()] = value

subprocess.call(['/bin/bash', 'setup/setup.sh'])
