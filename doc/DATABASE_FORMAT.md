# Loupe Database Format

The Loupe database uses a human-readable, text-based format, as described below.

## Directory Tree

Overall, the database is structured around the distinction between *applications*, *workloads*, and *distinct run environments*:

- Each application has exactly one directory at the root, named after the application, e.g., [`redis`](https://redis.io/), or [`aio-stress`](https://www.vi4io.org/tools/benchmarks/aio-stress).
- All *files* at the root of the database directory (e.g., [`README.md`](https://github.com/unikraft/loupedb/blob/staging/README.md) or [`OSv.syscalls`](https://github.com/unikraft/loupedb/blob/staging/Osv.syscalls)) are ignored.
  - In the ASPLOS'24 dataset, we just stored a README, the paper appendix, and OS syscall support descriptions.
- Each application directory contains exactly one folder per workload.
  - These folders follow the following convention: if the workload is the official test suite, it must be called `suite`; if it is a benchmark called `$X`, it must be called `benchmark-$X`.
  - Loupe does not currently support multiple alternative test suites, although support for this could be trivially added following the benchmark model (`suite-$X` for any alternative suite called `$X`).
- Each workload directory contains one folder per *run environment*.
  - Runs are identified by the hash of the Dockerfile that describes the run environment.
- Each run environment folder contains three files (`Dockerfile.$appname`, `cmd.txt`, `explore.logs`) and two folders (`data` and `dockerfile_data`, the latter optional).
  - `Dockerfile.$appname` is the [Dockerfile](https://docs.docker.com/engine/reference/builder/) used to build the test environment of the application and start the Loupe analysis. If the Dockerfile is [carefully constructed](doc/GOOD_DOCKERFILES.md), reproducing this measurement will almost always yield the same results; this is why the Dockerfile is used as identifier for the directory.
  - `cmd.txt` describes the Loupe command which was used to generate the results, to help users reproduce the run.
  - `explore.logs` contains the logs of explore.py for debugging and reproducibility purposes.
  - `dockerfile_data` are any files required to build `Dockerfile.$appname`, e.g., the application test script.
  - `data` is the folder containing analysis results (whose formats are documented [further down below](https://github.com/unikraft/loupe/blob/staging/doc/DATABASE_FORMAT.md#format-of-analysis-data)):
    - `dyn.csv` for Loupe analysis;
    - `static_binary.csv` for static binary analysis;
    - and `static_sources.csv` for static source analysis ([not automatically generated](https://github.com/unikraft/loupe/tree/staging/src/static-source-analyser)).

Here is an abbreviated example of the directory tree of the ASPLOS'24 data set:

```
loupdb $ tree
.
├── activemq
│   └── benchmark-activemq-test
│       └── 5578a88feb2192cf502ad3888cf4c1fe
│           ├── cmd.txt
│           ├── data
│           │   ├── dyn.csv
│           │   └── static_binary.csv
│           ├── Dockerfile.activemq
│           └── dockerfile_data
│               └── activemq-test.sh
├── aio-stress
│   └── benchmark-aio-stress
│       └── 25e14aafbc675e9891a7e12627e2f86b
│           ├── cmd.txt
│           ├── data
│           │   ├── dyn.csv
│           │   └── static_binary.csv
│           ├── Dockerfile.aio-stress
│           └── dockerfile_data
│               └── null-test.sh
├── aircrack-ng
│   └── benchmark-aircrack-ng
│       └── 29003849b92adf731ef959965de436db
│           ├── cmd.txt
│           ├── data
│           │   ├── dyn.csv
│           │   └── static_binary.csv
│           ├── Dockerfile.aircrack-ng
│           └── dockerfile_data
│               └── null-test.sh
├── akka
│   └── benchmark-akka-test
│       └── imported
│           ├── cmd.txt
│           ├── data
│           │   └── dyn.csv
│           ├── Dockerfile.akka
│           └── dockerfile_data
│               └── akka-test.sh
├── amg
│   └── benchmark-amg-test
│       └── 62971a011f7d0f20607bdc3de1cfce17
│           ├── cmd.txt
│           ├── data
│           │   ├── dyn.csv
│           │   └── static_binary.csv
│           ├── Dockerfile.amg
│           └── dockerfile_data
│               └── null-test.sh
├── aobench
│   └── benchmark-aobench-test
│       └── 7d83a19d5ce32c7666e61b39f530ab4a
│           ├── cmd.txt
│           ├── data
│           │   ├── dyn.csv
│           │   └── static_binary.csv
│           ├── Dockerfile.aobench
│           └── dockerfile_data
│               └── null-test.sh
├── ASPLOS24-supp.pdf
├── blackscholes
│   └── benchmark-blackscholes
│       └── c8e8f2de3aa0451718b21bc6b4b470ae
│           ├── cmd.txt
│           ├── data
│           │   ├── dyn.csv
│           │   └── static_binary.csv
│           ├── Dockerfile.blackscholes
│           └── dockerfile_data
│               ├── blackscholes.patch
│               └── blackscholes-test.sh
├── blogbench
│   └── benchmark-blogbench-test
│       └── 6005be59c2177cd1b3f7e773766801db
│           ├── cmd.txt
│           ├── data
│           │   ├── dyn.csv
│           │   └── static_binary.csv
│           ├── Dockerfile.blogbench
│           └── dockerfile_data
│               └── blogbench-test.py
├── Browsix.syscalls
├── ... (abbreviated)
├── lighttpd
│   ├── benchmark-wrk
│   │   └── 681bd60a89599a42b6b2b79957152ea6
│   │       ├── cmd.txt
│   │       ├── data
│   │       │   ├── dyn.csv
│   │       │   ├── static_binary.csv
│   │       │   └── static_sources.csv
│   │       ├── dockerfile_data
│   │       │   ├── lighttpd.conf
│   │       │   └── lighttpd-test.sh
│   │       └── Dockerfile.lighttpd
│   └── suite
│       └── imported
│           └── data
│               └── dyn.csv
└── ... (abbreviated)
```

In this data set, you can also see runs identified by `imported`, which is clearly not a Dockerfile hash. These contain data imported from runs of Loupe that predate this data base format.

Not all entries feature `explore.logs` as it was introduced recently.

## Format of Analysis Data

### Dynamic Analysis

The format of `dyn.csv` is as following:

- The first line contains an explanatory comment on the format.
- Then, each line in CSV format contains:
  - The system call number (`0`, `1`, `2`, ...)
  - Followed by four booleans (`Y` or `N`) indicating whether or not...
    - the analysis determined that the system call is used.
    - the analysis determined that the system call can be faked.
    - the analysis determined that the system call can be stubbed.
    - the analysis determined that the system call can be faked and stubbed.

Here is an abbreviated example from the ASPLOS'24 data set:
```
$ cat loupedb/lighttpd/benchmark-wrk/681bd60a89599a42b6b2b79957152ea6/data/dyn.csv
# syscall, used, works faked, works stubbed, works both
0,Y,N,N,N
1,Y,N,N,N
2,N,N,N,N
3,Y,Y,N,N
... (abbreviated)
```

### Static Analysis

The format of static analysis files (`static_binary.csv`, `static_sources.csv`) is as following:

- The first line contains an explanatory comment on the format.
- Then, each line in CSV format contains:
  - The system call number (`0`, `1`, `2`, ...)
  - Followed by a boolean (`Y` or `N`) indicating whether or not the analysis determined that the system call is used.

Here is an abbreviated example from the ASPLOS'24 data set:
```
$ cat loupedb/lighttpd/benchmark-wrk/681bd60a89599a42b6b2b79957152ea6/data/static_binary.csv
# syscall, used
0,Y
1,Y
2,Y
3,Y
```
