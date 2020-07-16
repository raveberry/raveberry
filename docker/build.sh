#!/bin/bash
# build for the current architecture only
#docker build -f docker/dependencies.Dockerfile -t raveberry/raveberry-dependencies requirements/
#docker build -f docker/mopidy.Dockerfile -t raveberry/raveberry-mopidy docker/
#docker build -f docker/nginx.Dockerfile -t raveberry/raveberry-nginx .
#docker build -f docker/icecast.Dockerfile -t raveberry/raveberry-icecast docker/
#docker build -f docker/Dockerfile -t raveberry/raveberry .
# build for both x64 and arm. Also pushes to dockerhub.
docker buildx build --platform linux/amd64,linux/arm/v7 --output type=registry -f docker/dependencies.Dockerfile -t raveberry/raveberry-dependencies requirements/
docker buildx build --platform linux/amd64,linux/arm/v7 --output type=registry -f docker/mopidy.Dockerfile -t raveberry/raveberry-mopidy docker/
docker buildx build --platform linux/amd64,linux/arm/v7 --output type=registry -f docker/nginx.Dockerfile -t raveberry/raveberry-nginx .
docker buildx build --platform linux/amd64,linux/arm/v7 --output type=registry -f docker/icecast.Dockerfile -t raveberry/raveberry-icecast docker/
docker buildx build --platform linux/amd64,linux/arm/v7 --output type=registry -f docker/Dockerfile -t raveberry/raveberry .
echo "Publish using:"
echo "docker push raveberry/raveberry-dependencies"
echo "docker push raveberry/raveberry-mopidy"
echo "docker push raveberry/raveberry-nginx"
echo "docker push raveberry/raveberry-icecast"
echo "docker push raveberry/raveberry"
