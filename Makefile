# SPDX-License-Identifier: BSD-3-Clause
#
# Authors: Hugo Lefeuvre <hugo.lefeuvre@manchester.ac.uk>
#
# Copyright (c) 2020-2023, The University of Manchester. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

WORKDIR ?= $(CURDIR)
GITHUB_PREFIX ?= "https://github.com/"

src/seccomp-run:
	gcc src/seccomp-run.c -o src/seccomp-run

.PHONY: docker
docker:
	docker build --tag loupe-base -f docker/Dockerfile.loupe-base .

rebuild-docker:
	docker build --no-cache --tag loupe-base -f docker/Dockerfile.loupe-base .

clonedb:
	git clone git@github.com:unikraft/loupedb.git ../loupedb

cleanfigs:
	rm -rf *.svg *.dat

clean: cleanfigs
	rm -rf src/seccomp-run

properclean: clean
	rm -rf Dockerfile.* dockerfile_data

paperplots: cleanfigs
	mkdir -p paperplots
	# syscall usage histogram
	./loupe -v search --paper-histogram-plot -db ../loupedb
	# syscall usage heatmaps
	./loupe -v search --static-source --heatmap-plot -db ../loupedb -a "*" -w bench
	# syscall usage cumulative
	./loupe -v search --static-source --cumulative-plot -db ../loupedb -a "*" -w bench
	mv *.svg paperplots

# Prepare the Zenodo archive
zenodo:
	mkdir -p $(WORKDIR)/repositories
	# clone all repos in the conffuzz organization
	cd $(WORKDIR)/repositories && git clone $(GITHUB_PREFIX)/unikraft/loupe.git
	cd $(WORKDIR)/repositories && git clone $(GITHUB_PREFIX)/unikraft/loupedb.git
	find $(WORKDIR)/repositories/* -name '.git' | xargs rm -rf
	cd $(WORKDIR) && tar -cvzf ../loupe-artifact.tar.gz repositories/
	rm -rf $(WORKDIR)/repositories

all: clean clonedb src/seccomp-run docker
