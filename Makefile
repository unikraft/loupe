.PHONY: docker

seccomp-run:
	gcc seccomp-run.c -o seccomp-run

docker:
	docker build --tag loupe-base -f docker/Dockerfile.loupe-base .

all: seccomp-run docker

