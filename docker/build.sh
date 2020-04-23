#!/bin/bash
docker build -f docker/dependencies.Dockerfile -t raveberry/raveberry-dependencies requirements/
docker build -f docker/nginx.Dockerfile -t raveberry/raveberry-nginx docker/
echo "Publish using:"
echo "docker push raveberry/raveberry-dependencies"
echo "docker push raveberry/raveberry-nginx"
