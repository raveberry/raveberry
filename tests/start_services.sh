#!/bin/bash
service postgresql start
service mopidy start
service redis-server start
sudo -u postgres psql -c "CREATE USER raveberry WITH PASSWORD 'raveberry';"
sudo -u postgres psql -c "CREATE DATABASE raveberry;"
# allow raveberry user to create databases (only for tests)
sudo -u postgres psql -c "ALTER USER raveberry CREATEDB";
# run parameters in new shell
/bin/bash -c "$@"
