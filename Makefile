all:
	gcc seccomp-run.c -o seccomp-run

docker:
	sudo docker build -t loup-img .
