FROM raveberry/raveberry-deps

# persist raveberry (build context) in container
COPY . /opt/raveberry
WORKDIR /opt/raveberry

RUN yarn install &&\
	scripts/clean_libs.sh

ENTRYPOINT ["./tests/start_services.sh"]
CMD ["bash"]
