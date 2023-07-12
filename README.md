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

### Loupe is not your regular strace!

- Loupe supports stubbing/faking analysis (Loupe is not a *passive* observer)
- Loupe goes beyond system call granularity
- Loupe supports replication to obtain results stable across runs
- Loupe offers an infrastructure for reproducibility and sharing of results

## Hardware Dependencies

Any x86 machine with more than 8 CPU cores should do the trick (non-x86 might
cause issues because of our Docker containers).

## Dependencies & Install

- Docker
- python3, with [python-git](https://pypi.org/project/python-git/)
  (`pip3 install gitpython`)
- a recent-enough Linux kernel to support seccomp and ptrace

The setup is very simple: `make all`

## Gathering Data

`loupe generate` takes care of analyzing the system call usage of your
application.

### Example 1: Dynamic + Static System Call Usage Analysis of Nginx

Loupe considers two types of workloads: benchmarks and test suites. Both
measurements are independent. In this example, we'll measure the dynamic system
call analysis for Nginx.

Let's take a look at benchmarks first.

#### Benchmark workload

**Step 0**: first you'll need to generate the `loupe-base` container image as
follows (in loupe's root directory):

	$ docker build -f docker/Dockerfile.loupe-base --tag=loupe-base .

**Step 1**: identify a benchmarking tool that we can use to benchmark Nginx.

Here we'll go for [wrk](https://github.com/wg/wrk).

**Step 2**: write a *test script* that uses wrk. Test scripts are used by Loupe
to determine whether or not the application (here Nginx) works. Test scripts return
0 if the application works, 1 if it doesn't.

In the case of Nginx, our test script looks like the following:

	#!/bin/bash

	# nginx command: ./objs/nginx -p $(pwd) -g 'daemon off;'

	bench=$(wrk http://localhost:80/index.html -d3s)

	nl=$(echo ${bench} | grep -P "Transfer/sec:\s*\d+(?:\.\d+)MB" | wc -l)
	if [ "$nl" -eq "1" ]; then
	    exit 0
	fi

	exit 1

This is a very simple script. We first start a 3s benchmark on port 80 with
`wrk`.  Then we parse the output for a chain of characters that typically
indicates success (here the throughput, which is absent if the benchmark fails).
We return 0 if it is present, and 1 otherwise.

**Step 3**: create a Docker container that build nginx and wrk, and performs
the system call analysis using Loupe. Use `loupe-base` as basis for your Docker
container.

In our case, the Dockerfile looks like the following (slightly modified to
exclude coverage, which is not necessary here):

	FROM loupe-base:latest

	# Install wrk
	RUN apt update
	RUN apt install -y wrk

	# Nginx related instructions
	RUN apt build-dep -y nginx
	RUN wget https://nginx.org/download/nginx-1.20.1.tar.gz
	RUN tar -xf nginx-1.20.1.tar.gz
	RUN mv nginx-1.20.1 nginx

	RUN cd nginx && ./configure \
		--sbin-path=$(pwd)/nginx \
		--conf-path=$(pwd)/conf/nginx.conf \
		--pid-path=$(pwd)/nginx.pid
	RUN cd nginx && make -j
	RUN mkdir /root/nginx/logs

	# Copy test script
	COPY dockerfile_data/nginx-test.sh /root/nginx-test.sh
	RUN chmod a+x /root/nginx-test.sh

	# Run command (without coverage)
	CMD /root/explore.py --output-csv -t /root/nginx-test.sh \
			     -b /root/nginx/objs/nginx \
			     -- -p /root/nginx -g "daemon off;"

This is a simple container. We install `wrk`, and configure and build Nginx.
Finally, we start `explore.py`. The arguments are quite important:

 - `--output-csv` is necessary to enable parsing by Loupe
 - `-t /root/nginx-test.sh` indicates our test script
 - `-b /root/nginx-1.20.1/objs/nginx` indicates our binary
 - `--` denotes arguments that are passed on to nginx (remember that we want to call `objs/nginx -p $(pwd) -g 'daemon off;'`)

**Step 4**: start the analysis using the following command:

	$ ./loupe generate -b -db ../loupedb -a "nginx" -w "wrk" -d ./Dockerfile.nginx

The arguments are important too:

 - `-b` tells Loupe that you are running a benchmark, not a test suite, and `-w` defines the name of the benchmark.
 - `-db` tells Loupe where the database is
 - `-a` tells Loupe the name of the software that we are benchmarking
 - `-d ./Dockerfile.nginx` passes our Dockerfile from Step 3

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

	$ ./loupe generate -s -db ../loupedb -a "nginx" -w "nginx-tests" -d ./Dockerfile.nginx

As you can see, the only difference is the `-s` instead of `-b` to indicate
that this is a testsuite.

Note: for test suites, `-w` can be empty.

### Example 2: Reproducing Existing Runs

Existing runs can be easily reproduced. In order to reproduce [Example 1](https://github.com/unikraft/loupe#benchmark-workload):

```
$ cd loupedb/nginx/benchmark-wrk/7883824b5cbef4f66dd1c9bdcf7d6185
$ loupe generate -b -db ../../../../loupedb -a "nginx" -w "wrk" -d ./Dockerfile.nginx
```

`git diff` can then be used to visualize changes.

## Retrieving and Processing Data

`loupe search` takes care of analyzing the data in the database.

### Generating Plots

Loupe can generate the paper's plot using information from the database.

#### Cumulative Plot

Simply run
```
$ ./loupe search --cumulative-plot -db ../loupedb -a "*" -w suite
```
to output a cumulative plot of the database's content for test-suites and all applications.

#### Heatmap Plot

Similarly, run
```
$ ./loupe search --heatmap-plot -db ../loupedb -a "*" -w suite
```
to output a heatmap plot for the same data set.

#### Paper Histogram Plot

Similarly, run
```
$ ./loupe search --paper-histogram-plot -db ../loupedb
```
to output the histogram plot of the paper.

#### OS Support Plan

To get an optimized order of syscall implementation/faking/stubbing for a
given OS (characterized by a set of already-supported system calls) towards
a particular set of applications:
```
$ ./loupe search -db ../loupedb --guide-support <already supported syscalls> --applications <apps> --workloads <workload>
```

Here, `<already supported syscalls>` is a newline-separated list of syscalls
already supported by the target OS (see the `*.syscalls` files at the root
of `loupedb` for examples), `<apps>` is the list of application to target,
and `<workload>` is `bench` or `suite`.

### Generating the Paper's Plots

Run:

```
$ make paperplots
```

Generated plots will be located under `paperplots`.

## Advanced Features

Here we describe advanced features supported by Loupe.

:warning: this section is temporary and might get outdated. Some of the
features may not be fully integrated in the `loupe` main wrapper, and may not
be stable.

### Integration with debhelper

We provide a script that integrates Loupe with [`debhelper`](https://man7.org/linux/man-pages/man7/debhelper.7.html). 
Our script automatically downloads the debian sources of a package, builds it and then runs the test suite with loupe.
We use `dh_test_auto` to run the testsuite. `dh_test_auto` returns 0 if the test suite executed succesfully.

Example of usage with memcached:

```
sudo docker build --tag loupe-dbhelper --build-arg APP=memcached --build-arg BINARY=memcached-debug  -f debhelper/Dockerfile.debhelper .
```

Note the two variables passed, `APP` and `BINARY`.

- `APP` is the identifier for the debian package that we are targeting, in this case `memcached`.
- `BINARY` is the resulting binary that we will be analysing, in this case `memcached-debug` is being run by the memcached suite automatically.

The next step is to run loupe:

```
sudo docker container run --rm --privileged -e "BINARY=memcached-debug" -e "APP=memcached" -it loupe-dbhelper
```

Or if you would want to run loupe manually from the conainter:

```
sudo docker container run --rm --privileged -e "BINARY=memcached-debug" -e "APP=memcached" -it loupe-dbhelper /bin/bash
```

TODO: We can get from the automatic build all the binaries being buit, and such we could pass them to `BINARY` without user input.

### Performance & Resource Usage Impact Analysis

Loupe can analyze, for each system call stubbed/faked, the impact on
performance and resource usage. For that, the test script must be extended to
support benchmarking (usually very simple!), and `explore.py` must be called
with particular arguments.

**Step 1**: Add support to the test script. The test script may be passed an
argument. If the value of the argument is `benchmark`, then the script is asked
to output a performance number to stdout. If it doesn't, the performance
evaluation will fail. Taking the previous example with Nginx and `wrk`, we obtain:

```
#!/bin/bash

# nginx command: ./objs/nginx -p $(pwd) -g 'daemon off;'

WRK_PATH=wrk
PORT=80

test_works() {
  bench=$(${WRK_PATH} http://localhost:${PORT}/index.html -d3s)

  failure=$(echo ${bench} | grep -P "unable to connect to localhost" | wc -l)
  if [ "$failure" -eq "1" ]; then
      exit 200
  fi

  nl=$(echo ${bench} | grep -P "Transfer/sec:\s*\d+(?:\.\d+)MB" | wc -l)
  if [ "$nl" -eq "1" ]; then
      exit 0
  fi

  exit 1
}

benchmark() {
  taskset -c 6 ${WRK_PATH} http://localhost:${PORT}/index.html -d10s | \
          grep -P "Requests/sec:\s*\d+(?:\.\d+)" | grep -Po "\d+(?:\.\d+)"
  exit $?
}

if [ "$2" == "benchmark" ]; then
  benchmark
else
  test_works
fi
```

No need to modify the script to support resource usage analysis, this is done
automatically.

**Step 2**: We now want to call `explore.py` as following:

```
$ /root/explore.py --perf-analysis -t /root/nginx-test.sh -b /root/nginx/ob^C/nginx -- -p /root/nginx -g "daemon off;"
```

Note that support is not integrate in the `loupe` main program, so, in order to
run this, manually start the Docker contain built previously while running the
analysis and manually run:

```
$ docker run -it docker.io/library/nginx-loupe bash
$ /root/explore.py --perf-analysis -t /root/nginx-test.sh -b /root/nginx/ob^C/nginx -- -p /root/nginx -g "daemon off;"
```

This will output the performance and resource usage impact detailed analysis per-system call.

TODO: Integrate performance and resource usage analysis in the main `loupe` wrapper.

#### Known Results (paper submission)

**Nginx (wrk)**

```
[I] Determining baseline...
Baseline: perf openfds memusage
Baseline: 51333.21 8.0 4612.0

[I] Gathering data for stubbing...
[============================================================] 100.0%
syscall: perf openfds memusage (relative to the baseline)
1: 59073.05 8.0 4612.0 (1.15,1.0,1.0)
11: 51121.13 8.0 4632.0 (1.0,1.0,1.0)
12: 51841.67 8.0 5376.0 (1.01,1.0,1.17)
14: 51806.57 8.0 4612.0 (1.01,1.0,1.0)
21: 51889.43 8.0 4612.0 (1.01,1.0,1.0)
40: 0.0 8.0 4612.0 (0.0,1.0,1.0)
42: 51446.93 8.0 4612.0 (1.0,1.0,1.0)
92: 51401.59 8.0 4612.0 (1.0,1.0,1.0)
107: 52085.92 8.0 4612.0 (1.01,1.0,1.0)
110: 51576.41 8.0 4612.0 (1.0,1.0,1.0)
116: 52016.96 8.0 4612.0 (1.01,1.0,1.0)
157: 51904.9 8.0 4612.0 (1.01,1.0,1.0)
218: 52266.61 8.0 4612.0 (1.02,1.0,1.0)
273: 51326.91 8.0 4612.0 (1.0,1.0,1.0)
288: 51263.03 8.0 4612.0 (1.0,1.0,1.0)
290: 51685.32 8.0 4612.0 (1.01,1.0,1.0)
318: 51462.09 8.0 4612.0 (1.0,1.0,1.0)
334: 52216.86 8.0 4612.0 (1.02,1.0,1.0)

[I] Gathering data for faking...
[============================================================] 100.0%
syscall: perf openfds memusage (relative to the baseline)
1: 58673.37 8.0 4612.0 (1.14,1.0,1.0)
8: 51453.42 8.0 4612.0 (1.0,1.0,1.0)
10: 51287.55 8.0 4612.0 (1.0,1.0,1.0)
11: 51602.4 8.0 4632.0 (1.01,1.0,1.0)
12: 51314.54 8.0 5376.0 (1.0,1.0,1.17)
13: 51754.21 8.0 4612.0 (1.01,1.0,1.0)
14: 51690.4 8.0 4612.0 (1.01,1.0,1.0)
16: 51618.22 8.0 4612.0 (1.01,1.0,1.0)
21: 51466.88 8.0 4612.0 (1.0,1.0,1.0)
33: 52060.56 8.0 4612.0 (1.01,1.0,1.0)
39: 51909.32 8.0 4612.0 (1.01,1.0,1.0)
40: 0.0 8.0 4612.0 (0.0,1.0,1.0)
42: 51787.95 8.0 4612.0 (1.01,1.0,1.0)
56: 51755.31 8.0 5052.0 (1.01,1.0,1.1)
63: 51495.91 8.0 4612.0 (1.0,1.0,1.0)
72: 51440.13 8.0 4612.0 (1.0,1.0,1.0)
83: 51181.87 8.0 4612.0 (1.0,1.0,1.0)
92: 52168.04 8.0 4612.0 (1.02,1.0,1.0)
105: 51685.38 8.0 4612.0 (1.01,1.0,1.0)
106: 52673.1 8.0 4612.0 (1.03,1.0,1.0)
107: 51847.52 8.0 4612.0 (1.01,1.0,1.0)
110: 51861.8 8.0 4612.0 (1.01,1.0,1.0)
116: 51689.33 8.0 4612.0 (1.01,1.0,1.0)
157: 51549.74 8.0 4612.0 (1.0,1.0,1.0)
218: 51659.52 8.0 4612.0 (1.01,1.0,1.0)
273: 51967.1 8.0 4612.0 (1.01,1.0,1.0)
290: 52170.69 8.0 4612.0 (1.02,1.0,1.0)
302: 51486.21 8.0 4612.0 (1.0,1.0,1.0)
318: 51907.57 8.0 4612.0 (1.01,1.0,1.0)
334: 52031.13 8.0 4612.0 (1.01,1.0,1.0)
```

Generally no impact (error margin), apart from `sendfile` (breaks Nginx),
`read` (makes it faster because we don't read requests anymore, breaks it as
well), as described in the paper.

### Generating Coverage

**Step 1**: Check the Dockerfile of the application. If it already contains a
version of the software built with coverage, then proceed to step 2. Otherwise,
build the software (or a copy of it if performance measurements are planned)
with CFLAGS `-fprofile-arcs -ftest-coverage` and LDFLAGS `-lgcov`. An example
is visible [here](https://github.com/unikraft/loupedb/blob/87439475881b64de0203d9c142ddc01b1071698d/nginx/benchmark-wrk/7883824b5cbef4f66dd1c9bdcf7d6185/Dockerfile.nginx).

**Step 2**: Build the application container, e.g., for nginx:
```
$ ./loupe generate -b -db ../loupedb -a "nginx" -w "wrk" -d ./Dockerfile.nginx
```
We don't need to perform the actual system call measurement, we only need the
container to be built, so you can kill this command (CTRL+C) as soon as the
container is built. In the future we'll extend Loupe with an option to only do
that.

**Step 3**: Enter the container and generate coverage. It's as simple as running
the instrumented software. For example, with Nginx:
```
$ docker run -it nginx-loupe:latest /bin/bash
root@b0ef11e440d0:~# # we're in the container, generate coverage data
root@b0ef11e440d0:~# /root/explore.py --output-csv -t /root/nginx-test.sh \
                                      -b /root/nginx-coverage/objs/nginx \
                                      -- -p /root/nginx -g "daemon off;"
root@b0ef11e440d0:~# # done. check the coverage data:
root@b0ef11e440d0:~# ls nginx-coverage/objs/src/core/
[ shows a number of .gcda and .gcno files ]
```

**Step 4**: Generate an lcov report. Example with Nginx, still in the same container:
```
root@b0ef11e440d0:~/nginx-coverage# lcov --capture --directory . --output-file cov.info
[shows files considered, if you get WARNINGs, investigate, they might be
invalid files considered in the coverage, like autotest.gcda at the root.
You can safely remove them.]
root@b0ef11e440d0:~/nginx-coverage# genhtml cov.info --output-directory out_html \
                                            --demangle-cpp --legend \
                                            --title "Nginx coverage wrk"
[...]
Overall coverage rate:
  lines......: 13.0% (5291 of 40728 lines)
  functions..: 20.1% (282 of 1405 functions)
root@b0ef11e440d0:~/nginx-coverage# ls out_html/
amber.png    event      http               index.html  snow.png
core         gcov.css   index-sort-f.html  os          updown.png
emerald.png  glass.png  index-sort-l.html  ruby.png    usr
```

The resulting html report is there.
