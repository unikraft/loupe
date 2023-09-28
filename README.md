# :mag: Loupe: Syscall Usage Analysis Tool

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
more than a git repository with a [particular
layout](https://github.com/unikraft/loupe/blob/staging/doc/DATABASE_FORMAT.md).
We offer an online, open [database](https://github.com/unikraft/loupedb)
maintained by the community.  Feel free to pull request your analysis results!

### Loupe is not your regular strace!

- Loupe supports stubbing/faking analysis (Loupe is not a *passive* observer)
- Loupe goes beyond system call granularity
- Loupe supports replication to obtain results stable across runs
- Loupe offers an infrastructure for reproducibility and sharing of results

### ASPLOS'24 Paper

Loupe is the result of a collaboration between The University of Manchester,
Liège Université, University Politehnica of Bucharest, and Unikraft.io. It has
been accepted to appear in [ASPLOS'24](https://www.asplos-conference.org/asplos2024/).

> **Abstract**: Supporting mainstream applications is fundamental for a new OS to have impact, and is generally achieved by developing a layer of compatibility such that applications developed for a mainstream OS like Linux can work, unmodified, on the new OS. Building such a layer, as we will show, results in large inefficiencies in terms of engineering effort due to the lack of efficient methods to precisely measure the OS features required by a set of applications.
>
> We propose Loupe, a novel method based on dynamic analysis that determines the OS features that need to be implemented in a prototype OS to bring support for a target set of applications and workloads.
> Loupe guides and boosts OS developers as they build compatibility layers, prioritizing which features to implement in order to quickly support many applications as early as possible. We apply our methodology to 100+ applications and several OSes currently under development, demonstrating high engineering effort savings vs. existing approaches: for example, for the 62 applications supported by the OSv kernel, we show that using Loupe, would have required implementing only 37 system calls vs. 92 for the non-systematic process followed by OSv developers.
>
> We further study our measurements and extract several novel key insights. Overall, we show that the burden of building compatibility layers is significantly less than what previous works suggest: in some cases, only as few as 20% of system calls reported by static analysis, and 50% of those reported by naive dynamic analysis need an implementation for an application to successfully run standard benchmarks.

Information on Loupe can also be found in Vlad-Radu Schiller's [3rd year project report](https://github.com/SchillV/unikraft-test-suite/blob/main/Investigating%20Application%20Compatibility%20in%20Prototype%20Operating%20Systems:%20Vlad-Radu%20Schiller.pdf).

## 0. Table of Contents & Links

If at all possible, please read through this entire document before installing
or using Loupe. This document is best read on
[GitHub](https://github.com/unikraft/loupe), with a Markdown viewer, or
Markdown editor.

- [1. Hardware Dependencies](#1-hardware-dependencies)
- [2. Dependencies & Install](#2-dependencies--install)
- [3. Gathering Data](#3-gathering-data)
- [4. Retrieving and Processing Data](#4-retrieving-and-processing-data)
- [5. Advanced Features](#5-advanced-features)
- [6. Troubleshooting](#6-troubleshooting)
- [7. Additional Documentation](#7-additional-documentation)
- [8. Zenodo Artifact, Tags, and ASPLOS'24 Artifact Evaluation](#8-zenodo-artifact-tags-and-asplos24-artifact-evaluation)
- [9. Contributing](#9-contributing)
- [10. Disclaimer](#10-disclaimer)
- [11. Acknowledgements](#11-acknowledgements)

**Link to the Loupe ASPLOS'24 paper data set: [[ASPLOS'24 Data Set]](https://github.com/unikraft/loupedb)**

## 1. Hardware Dependencies

Any x86 machine should do the trick - non-x86 might cause technical issues
because of our Docker containers.

We recommend (but do not require) > 8 CPU cores to obtain stable performance
numbers.

## 2. Dependencies & Install

Loupe has been tested on Debian 12. While this is not a hard requirement (it
will likely work on any Linux distribution), we have not tested other
environments. Please do report an issue if Loupe does not run on your
Linux-based system.

- [Docker](https://docs.docker.com/engine/install/)
- python3 (should work with any version of Python 3, known to work with at least 3.10.5)
- [python-git](https://pypi.org/project/python-git/) (`pip3 install gitpython`, known to work with at least 3.1.27)
- a recent-enough Linux kernel to support seccomp and ptrace (i.e., if your Linux kernel doesn't support them, you really seriously should update your setup :innocent:)

Once these dependencies have been installed, the setup is very simple: `make
all`

## 3. Gathering Data

`loupe generate` takes care of analyzing the system call usage of your
application.

### Example 1: Dynamic + Static System Call Usage Analysis of Nginx

Loupe considers two types of workloads: benchmarks and test suites. Both
measurements are independent. In this example, we'll illustrate both for Nginx.

#### Benchmark workload

Let's take a look at benchmarks first.

**Step 0**: first you'll need to generate the `loupe-base` container image as
follows (in loupe's root directory):

	$ make docker

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

### Notes

In practice, you likely want to write your Docker containers a little bit more carefully to ensure that the analysis remains stable and reproducible over time. We provide recommendations in [`GOOD_DOCKERFILES.md`](https://github.com/unikraft/loupe/blob/staging/doc/GOOD_DOCKERFILES.md).

## 4. Retrieving and Processing Data

Once the analysis completed, you can check the database (`loupedb` in the
previous examples). You will see a number of uncommitted changes - they are the
results of the analysis. The database is formatted in a custom text-based
layout documented [here](https://github.com/unikraft/loupe/blob/staging/doc/DATABASE_FORMAT.md).

As a user, you do not need to understand this format; `loupe search` takes care
of analyzing the data in the database for you.

### Extracting Data

Loupe can simply output the database's raw data:

```
$ ./loupe search --show-usage -db ../loupedb -a "nginx" -w benchmark
[I] Checking database...
Required:
[0, 3, 9, 17, 18, 20, 41, 45, 49, 50, 53, 54, 59, 158, 213, 232, 233, 257, 262]
Can be stubbed:
[8, 10, 13, 16, 33, 39, 56, 63, 72, 83, 105, 106, 302]
Can be faked:
[288]
Can be both stubbed or faked:
[1, 11, 12, 14, 21, 40, 42, 92, 107, 110, 116, 157, 218, 273, 290, 318, 334]
```

- You can replace `nginx` with any other application name, list of names (comma-separated), or a `*` for all.
- You can replace `benchmark` with `suite` to obtain data for the test-suite, or `*` for both.

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

## 5. Advanced Features

Here we describe advanced features supported by Loupe.

:warning: Some of the features below may not be fully integrated in the `loupe`
main wrapper, and may not be stable.

### Integration with debhelper

We provide a script that integrates Loupe with [`debhelper`](https://man7.org/linux/man-pages/man7/debhelper.7.html). 
Our script automatically downloads the debian sources of a package, builds it and then runs the test suite with loupe (if supported by the package).
We use `dh_test_auto` to run the testsuite. `dh_test_auto` returns 0 if the test suite executed successfully.

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

Or if you would want to run loupe manually from the container:

```
sudo docker container run --rm --privileged -e "BINARY=memcached-debug" -e "APP=memcached" -it loupe-dbhelper /bin/bash
```

TODO: We can get from the automatic build all the binaries being buit, and such we could pass them to `BINARY` without user input.

Although we did not deploy this at a large scale, it is known to work with, at least: LigHTTPd, webfsd, Memcached.

### Performance & Resource Usage Impact Analysis

Loupe can analyze, for each system call stubbed/faked, the impact on
performance and resource usage.

For that...
- the test script must be extended to support benchmarking (usually very simple!);
- and `explore.py` must be called with particular arguments.

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

You can find other examples of scripts that support performance measurement [here](https://github.com/unikraft/loupedb/blob/staging/iperf3/benchmark-iperf3-client/b4d7816051b0a4f6d70569b2bde09104/dockerfile_data/iperf3-test.sh) and [here](https://github.com/unikraft/loupedb/blob/staging/redis/benchmark-redis-benchmark/e068cbf1d0f3b508f42a2507f9a2e437/dockerfile_data/redis-test.sh).

**Step 2**: We now want to call `explore.py` as following:

```
$ /root/explore.py --perf-analysis -t /root/nginx-test.sh -b /root/nginx/objs/nginx -- -p /root/nginx -g "daemon off;"
```

Note that support is not integrated in the `loupe` main program. In order to
run this, manually start the Docker contain built previously while running the
analysis, and manually run:

```
$ docker run -it docker.io/library/nginx-loupe bash
$ /root/explore.py --perf-analysis -t /root/nginx-test.sh -b /root/nginx/objs/nginx -- -p /root/nginx -g "daemon off;"
```

This will output the performance and resource usage impact detailed analysis per-system call.

TODO: Integrate performance and resource usage analysis in the main `loupe` wrapper.

**Results**: We provide a set of example raw results obtained with Nginx,
Redis, and iPerf3 [here](doc/PERF_METRICS.md).

### Generating Coverage

You may be wondering what portion of the code a particular workload is exercising under a full Loupe analysis. Here is how to obtain a precise report.

**Step 1**: Check the Dockerfile of the application. If it already contains a
version of the software built with coverage, then proceed to step 2. Otherwise,
build the software (or a copy of it if performance measurements are planned)
with CFLAGS `-fprofile-arcs -ftest-coverage` and LDFLAGS `-lgcov`. An example
is visible [here](https://github.com/unikraft/loupedb/blob/87439475881b64de0203d9c142ddc01b1071698d/nginx/benchmark-wrk/7883824b5cbef4f66dd1c9bdcf7d6185/Dockerfile.nginx).

**Step 2**: Build the application container, e.g., for nginx:
```
$ ./loupe generate -b -db ../loupedb -a "nginx" -w "wrk" -d ./Dockerfile.nginx --only-build-docker
```
We don't need to perform the actual system call measurement, we only need the
container to be built, so we pass `--only-build-docker`.

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

## 6. Troubleshooting

This is a list of known issues, along with their solution. If your issue is not
in this list, feel free to open a bug report and [contribute a
fix](https://github.com/unikraft/loupe#8-contributing). This README is not exhaustive,
before opening a bug report, please check the help feature of the relevant binary or
script with `-h`.

**Issue 1:** You want to rebuild the base container, but running `make docker` doesn't do anything.

Solution: You can use `make rebuild-docker` instead of `make docker`.

**Issue 2:** Loupe fails with the following error message:
```
[E] Database /home/hle/Development/loupedb is dirty; commit your changes before running this tool.
```
Solution: You should either commit your changes to the database, or ignore the changes with `--allow-dirty-db`

**Issue 3:** The container hangs while building, with the following error:
```
Please select the geographic area in which you live. Subsequent configuration
questions will narrow this down by presenting a list of cities, representing
the time zones in which they are located.

  1. Africa      4. Australia  7. Atlantic  10. Pacific  13. Etc
  2. America     5. Arctic     8. Europe    11. SystemV
  3. Antarctica  6. Asia       9. Indian    12. US
Geographic area:
```
Solution: We likely forgot to add `ARG DEBIAN_FRONTEND=noninteractive` in the Dockerfile. Try to add it, it should address the issue.

**Issue 4:** Performance measurement shows with the following error:
```
[E] Bug here! Failed to determine VmPeak.
```
...and the value for the memory usage of one or more system calls is -1.

Solution: It is likely that the program is crashing during performance analysis, and that Loupe is consequently unable to measure the peak process memory usage. You should assume that those system calls cannot be faked or stubbed.

**Issue 5:** Performance measurement shows with the following error:
```
[E] Bug here! VmPeak not in kB:${something}
```
...and the value for the memory usage of one or more system calls is -1.

Solution: This is a bug in Loupe. Please submit a bug report.

**Issue 6:** I cannot reproduce certain measurements, despite of running the
reproduce command as instructed in the
[README.md](https://github.com/unikraft/loupe/tree/staging#example-2-reproducing-existing-runs).

Solution: Although infrequently happening, this is a known issue. The reason
varies; it can be due to the Loupe code having changed since the run was
performed, to the Docker container not being perfectly reproducible (e.g.,
versions of the application, shared libraries not being fixed properly), to the
kernel having changed, etc.

Loupe has been developed over a span of 3 years, during which we generated
various results, not all taking advantage of the full set of features that
Loupe offers in its current state.

We are working on implementing [best practices](https://github.com/unikraft/loupe/blob/staging/doc/GOOD_DOCKERFILES.md) over the data set.

**Issue 7:** Loupe fails to build the Docker container with `404 Not Found` errors on an APT command.

Solution: The APT command is likely missing a `apt-get update -q -y &&` prefix - however you do not necessarily need to modify the Docker container. You can simply rebuild the base container with `make rebuild-docker` and re-run Loupe.

## 7. Additional Documentation

In addition to this README, interested readers may want to take a look at...

- [`STRUCTURE.md`](https://github.com/unikraft/loupe/blob/staging/doc/STRUCTURE.md), which describes the structure of this repository
- [`DATABASE_FORMAT.md`](https://github.com/unikraft/loupe/blob/staging/doc/DATABASE_FORMAT.md), which describes the structure of a Loupe database
- [`GOOD_DOCKERFILES.md`](https://github.com/unikraft/loupe/blob/staging/doc/GOOD_DOCKERFILES.md), which provides advice on writing Dockerfiles for reproducible Loupe analysis

## 8. Zenodo Artifact, Tags, and ASPLOS'24 Artifact Evaluation

In addition to this repository, we have archived this artifact on Zenodo. In
order to make the Zenodo artifact as self-contained as possible, we included a
copy of the [Loupe database](https://github.com/unikraft/loupedb) along with
this repository. These are provided for the main purpose of archival. You can
generate a new snapshot with `make zenodo`.

We tagged both repositories with `asplos24-ae-v1` before submission. Future
iterations on the artifact will be tagged with `-v2`, etc.

We did not apply for the [reproduced badge](https://www.acm.org/publications/policies/artifact-review-badging) because the cost (in time and resources) of reproducing our data set goes beyond what can be expected from ASPLOS'24 artifact evaluators.

## 9. Contributing

We welcome contributions from anyone. This is [free
software](https://github.com/unikraft/loupe/blob/staging/COPYING.md).

To contribute to this repository, please fork and submit a Pull-Request. If you
introduce a new file, make sure to add an SPDX license header. If you do
significant-enough changes, consider adding yourself to `COPYING.md`.

Here are a few ideas of contributions to get started:
- Add support to convert Loupe databases to SQLite.
- Fix [open bug reports](https://github.com/unikraft/loupe/issues).

## 10. Disclaimer

This artifact is the first release of a research proof-of-concept for Loupe.
Like any research prototype, it contains hacks, bugs, and TODOs. Please use it
with a critical eye. We hope that it will be useful!

## 11. Acknowledgements

This artifact would not exist without the infrastructure and hard work of the
Unikraft community.  We encourage interested researchers to visit the project's
[web page](https://unikraft.org/) and [GitHub](https://github.com/unikraft/).
