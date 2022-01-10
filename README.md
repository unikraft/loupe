# Loupe: Syscall Usage Analysis Tool

Loupe is a tool designed to help you analyze the system call usage of your
application.

Loupe can do primarily two things: (1) collect data about the system call usage
of your application(s), and (2) analyze the data collected for your
application(s). It can tell you what system calls you need to run them, and
visualize these numbers in a variety of plots.

Loupe is based on *dynamic* analysis, but it is also able to gather static
analysis data.  We put the emphasis on *reproducible* analysis: measurements
are made in a Docker container.

Loupe stores analysis results in a custom database. A Loupe database is nothing
more than a git repository with a particular layout. If necessary, Loupe is
also able to convert this database to SQLite. We offer an online, open
[database]() maintained by the community. Feel free to pull request your
analysis results!

## Dependencies & Install

- Docker
- python3, with [python-git](https://pypi.org/project/python-git/)
- a recent-enough Linux kernel to support seccomp and ptrace

The setup is very simple: `make all`

## Gathering Data

`loupe generate` takes care of analyzing the system call usage of your
application.

### Example 1: Dynamic system call usage analysis of Nginx

Loupe considers two types of workloads: benchmarks and test suites. Both
measurements are independent. In this example, we'll measure the dynamic system
call analysis for Nginx.

Let's take a look at benchmarks first.

#### Benchmark workload

**Step 1**: identify a benchmarking tool that we can use to benchmark Nginx.

Here we'll go for [wrk](https://github.com/wg/wrk).

**Step 2**: write a *test script* that uses wrk. Test scripts are used by Loupe
to determine whether or not the application (here Nginx) works. Test scripts return
0 if the application works, 1 if it doesn't.

In the case of Nginx, our test script looks like the following:

	#!/bin/bash

	# nginx command: ./objs/nginx -p $(pwd) -g 'daemon off;'

	b=$(${WRK_PATH} http://localhost:8034/index.html -d3s)

	nl=$(echo ${bench} | grep -P "Transfer/sec:\s*\d+(?:\.\d+)MB" | wc -l)
	if [ "$nl" -eq "1" ]; then
	    exit 0
	fi

	exit 1

This is a very simple script. We first start a 3s benchmark on port 8034 with
`wrk`.  Then we parse the output for a chain of characters that typically
indicate success (here the throughput, which is absent if the benchmark fails).
We return 0 if it is present, and 1 otherwise.

**Step 3**: create a Docker container that build nginx and wrk, and performs
the system call analysis using Loupe. Use `loupe-base` as basis for your Docker
container.

In our case, the Dockerfile looks like the following:

	FROM loupe-base:latest

	# Install wrk
	RUN apt install -y wrk

	# Nginx related instructions
	RUN apt build-dep -y nginx
	RUN wget https://nginx.org/download/nginx-1.20.1.tar.gz
	RUN tar -xf nginx-1.20.1.tar.gz
	RUN cd nginx-1.20.1 && ./configure \
		--sbin-path=$(pwd)/nginx \
		--conf-path=$(pwd)/conf/nginx.conf \
		--pid-path=$(pwd)/nginx.pid
	RUN cd nginx-1.20.1 && make -j && mkdir logs
	RUN cd nginx-1.20.1 && sed -i "s/listen       80/listen       8034/g" conf/nginx.conf

	COPY dockerfile_data/nginx-test.sh /root/nginx-test.sh
	RUN chmod a+x /root/nginx-test.sh
	RUN sed -i "s/\/root\/hle\/pub\/wrk\///g" /root/nginx-test.sh

	CMD /root/explore.py --output-csv -t /root/nginx-test.sh \
                             -b /root/nginx-1.20.1/objs/nginx -- \
                             -p /root/nginx-1.20.1 -g "daemon off;"

This is a simple container. We install `wrk`, build Nginx and set the port to
8034 (not stricly necessary). Finally, we start `explore.py`. The arguments are
quite important:

 - `--output-csv` is necessary to enable parsing by Loupe
 - `-t /root/nginx-test.sh` indicates our test script
 - `-b /root/nginx-1.20.1/objs/nginx` indicates our binary
 - `--` denotes arguments that are passed on to nginx (remember that we want to call `objs/nginx -p $(pwd) -g 'daemon off;'`

**Step 4**: start the analysis using the following command:

	$ ./loupe.py generate -b -db ../loupedb -a "nginx" -w "wrk" -d ./Dockerfile.nginx

The arguments are important too:

 - `-b` tells Loupe that you are running a benchmark, not a test suite, and `-w` defines the name of the benchmark.
 - `-db` tells Loupe where the database is
 - `-a` tells Loupe the name of the software that we are benchmarking
 - and `-d ./Dockerfile.nginx` passes our Dockerfile from Step 3

#### Test-suite workload

Gathering data for a test suite is not fundamentally different from a benchmark.

**Step 1**: identify the test suite. In many cases it will be in the same
repository as the software itself, but the case of Nginx it is located in a
[separate repository](https://github.com/nginx/nginx-tests.git).

**Step 2**: write a *test script* that parses the output of the test suite and
determines whether it is a success or a failure. It is generally a very simple
task: run it once manually, and search for a string that indicates success.

In the case of Nginx, our test script looks like the following:

	#!/bin/bash

	nl=$(cat $1 | grep -P "All tests successful." | wc -l)
	if [ "$nl" -eq "1" ]; then
	    exit 0
	fi

	exit 1

**Step 3**: create a Docker container that build nginx and wrk, and performs
the system call analysis using Loupe. Use `loupe-base` as basis for your Docker
container.

This Dockerfile will be very similar to the one you wrote for the benchmark.

In our case, the Dockerfile looks like the following:

	FROM loupe-base:latest

	RUN apt build-dep -y nginx

	# needed to run the test suite
	RUN apt install -y prove6

	COPY dockerfile_data/nginx-test.sh /root/nginx-test.sh
	RUN chmod a+x /root/nginx-test.sh

	# the test suite cannot be run as root - don't ask me why
	RUN useradd -ms /bin/bash user
	USER user
	RUN mkdir /tmp/nginx
	WORKDIR /tmp/nginx

	# Nginx related instructions
	RUN wget https://nginx.org/download/nginx-1.20.1.tar.gz
	RUN tar -xf nginx-1.20.1.tar.gz
	RUN cd nginx-1.20.1 && ./configure \
		--sbin-path=$(pwd)/nginx \
		--conf-path=$(pwd)/conf/nginx.conf \
		--pid-path=$(pwd)/nginx.pid
	RUN cd nginx-1.20.1 && make -j && mkdir logs
	RUN cd nginx-1.20.1 && sed -i "s/listen       80/listen       8034/g" conf/nginx.conf
	# necessary for the test suite
	RUN mv nginx-1.20.1 nginx

	# test suite
	RUN git clone https://github.com/nginx/nginx-tests.git

	CMD cd /tmp/nginx/nginx-tests && /root/explore.py --output-csv \
			     --only-consider /tmp/nginx/nginx/objs/nginx \
			     --timeout 600 --test-sequential -t /root/nginx-test.sh \
			     -b /usr/bin/prove -- -m .

**Step 4**: start the analysis using the following command:

	$ ./loupe.py generate -s -db ../loupedb -a "nginx" -d ./Dockerfile.nginx

As you can see, the only difference is the `-s` and the absence of workload name.

## Retrieving and Processing Data

`loupe search` takes care of analyzing the data in the database.

More documentation will come here.
