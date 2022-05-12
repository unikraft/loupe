.PHONY: docker

src/seccomp-run:
	gcc src/seccomp-run.c -o src/seccomp-run

docker:
	docker build --tag loupe-base -f docker/Dockerfile.loupe-base .

clean:
	rm -rf *.svg *.dat src/seccomp-run

all: src/seccomp-run docker
