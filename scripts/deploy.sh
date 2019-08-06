#!/bin/bash
git push
git checkout master
git merge dev
git push
git checkout dev
cd /opt/raveberry/
git pull
