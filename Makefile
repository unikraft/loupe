.PHONY: docker

src/seccomp-run:
	gcc src/seccomp-run.c -o src/seccomp-run

docker:
	docker build --tag loupe-base -f docker/Dockerfile.loupe-base .

clonedb:
	git clone git@github.com:unikraft/loupedb.git ../loupedb

cleanfigs:
	rm -rf *.svg *.dat

clean: cleanfigs
	rm -rf src/seccomp-run

paperplots: cleanfigs
	mkdir -p paperplots
	# syscall usage histogram
	./loupe -v search --paper-histogram-plot -db ../loupedb
	# syscall usage heatmaps
	./loupe -v search --heatmap-plot -db ../loupedb -a "*" -w bench
	# syscall usage cumulative
	./loupe -v search --cumulative-plot -db ../loupedb -a "*" -w suite
	mv *.svg paperplots

all: clean clonedb src/seccomp-run docker
