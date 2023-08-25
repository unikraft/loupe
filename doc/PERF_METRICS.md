# Loupe Analysis of Performance Metrics

For illustration purposes, we provide raw data as returned by Loupe for a
number of applications, particularly as covered in the ASPLOS'24 paper.

:warning: This is a non-exhaustive list. Results are provided for demonstration
purposes, see the paper for a comprehensive list.

**Nginx (wrk)**

*Stubbing*

| System call  | Performance | FD Usage | Memory Usage |
|--------------|-------------|----------|--------------|
| 1            | **1.15**    | 1.0      | 1.0          |
| 11           | 1.0         | 1.0      | 1.0          |
| 12           | 1.01        | 1.0      | **1.17**     |
| 14           | 1.01        | 1.0      | 1.0          |
| 21           | 1.01        | 1.0      | 1.0          |
| 42           | 1.0         | 1.0      | 1.0          |
| 92           | 1.0         | 1.0      | 1.0          |
| 107          | 1.01        | 1.0      | 1.0          |
| 110          | 1.0         | 1.0      | 1.0          |
| 116          | 1.01        | 1.0      | 1.0          |
| 130          | **0.87**    | 1.0      | 1.0          |
| 157          | 0.99        | 1.0      | 1.0          |
| 218          | 1.02        | 1.0      | 1.0          |
| 273          | 1.0         | 1.0      | 1.0          |
| 288          | 1.0         | 1.0      | 1.0          |
| 290          | 1.01        | 1.0      | 1.0          |
| 318          | 1.0         | 1.0      | 1.0          |
| 334          | 1.01        | 1.0      | 1.0          |

*Faking*

| System call  | Performance | FD Usage | Memory Usage |
|--------------|-------------|----------|--------------|
| 1            | **1.14**    | 1.0      | 1.0          |
| 8            | 1.0         | 1.0      | 1.0          |
| 10           | 1.0         | 1.0      | 1.0          |
| 11           | 1.01        | 1.0      | 1.0          |
| 12           | 1.0         | 1.0      | **1.17**     |
| 13           | 1.0         | 1.0      | 1.0          |
| 14           | 1.0         | 1.0      | 1.0          |
| 16           | 1.01        | 1.0      | 1.0          |
| 21           | 1.0         | 1.0      | 1.0          |
| 33           | 1.01        | 1.0      | 1.0          |
| 39           | 1.01        | 1.0      | 1.0          |
| 42           | 1.01        | 1.0      | 1.0          |
| 56           | 1.01        | 1.0      | **1.1**      |
| 63           | 1.0         | 1.0      | 1.0          |
| 72           | 1.0         | 1.0      | 1.0          |
| 83           | 1.0         | 1.0      | 1.0          |
| 92           | 1.02        | 1.0      | 1.0          |
| 105          | 1.01        | 1.0      | 1.0          |
| 106          | 1.02        | 1.0      | 1.0          |
| 107          | 1.01        | 1.0      | 1.0          |
| 110          | 1.01        | 1.0      | 1.0          |
| 116          | 1.01        | 1.0      | 1.0          |
| 130          | **0.62**    | 1.0      | 1.0          |
| 157          | 1.0         | 1.0      | 1.0          |
| 218          | 1.01        | 1.0      | 1.0          |
| 273          | 0.99        | 1.0      | 1.0          |
| 290          | 1.02        | 1.0      | 1.0          |
| 302          | 1.0         | 1.0      | 1.0          |
| 318          | 1.01        | 1.0      | 1.0          |
| 334          | 1.01        | 1.0      | 1.0          |

Generally no performance impact (error margin, <3%), apart from (as described in the paper):
- 1: `write` (14-15% faster, because logs are not written anymore, fine)
- 130: `sigsuspend` (~38% slower, because the master process polls for signals, fine)

Generally no resource usage impact (error margin, <1%), apart from (as described in the paper):
- 12: `brk` (17% increased memory footprint, due to `mmap` fallback in early GLIBC allocator, fine)
- 56: `clone` (10% increased memory footprint, results in the master process executing the worker loop, works but fragile)

Note on 130 (`sigsuspend`): there is a bug in Loupe that prevents it from
automatically performing measurements for 130. We are working on solving it.
Meanwhile, we conducted the measurements for 130 manually (calling
`seccomp-run` manually). Unlike other system calls, the performance impact of
stubbing/faking this feature shows a lot of variance, which explains the
difference of results between stubbing and faking.

**Redis (redis-benchmark)**

Note: The Redis experiment is much less stable (than, e.g., Nginx), so make
sure to keep a low-noise system, pin properly, repeat and average.

*Stubbing*

| System call  | Performance | FD Usage | Memory Usage |
|--------------|-------------|----------|--------------|
| 2            | 1.01        | 1.0      | 1.0          |
| 8            | 0.99        | 1.0      | 1.0          |
| 11           | 1.0         | 1.0      | **1.19**     |
| 12           | 1.0         | 1.0      | **1.02**     |
| 13           | 1.02        | 1.0      | 1.0          |
| 14           | 0.97        | 1.0      | **0.85**     |
| 16           | 1.01        | 1.0      | 1.0          |
| 21           | 1.01        | 1.0      | 1.0          |
| 28           | 1.0         | 1.0      | 1.0          |
| 39           | 0.97        | 1.0      | 1.0          |
| 89           | 0.99        | 1.0      | 1.0          |
| 95           | 0.99        | 1.0      | 1.0          |
| 99           | 0.99        | 1.0      | 1.0          |
| 157          | 1.03        | 1.0      | 1.0          |
| 218          | 0.98        | 1.0      | 1.0          |
| 302          | 0.98        | 1.0      | 1.0          |
| 293          | 1.0         | 1.0      | **0.66**     |
| 318          | 1.0         | 1.0      | 1.0          |
| 334          | 1.0         | 1.0      | 1.0          |

*Faking*

| System call  | Performance | FD Usage | Memory Usage |
|--------------|-------------|----------|--------------|
| 3            | 1.02        | **7.97** | 1.0          |
| 8            | 1.0         | 1.0      | 1.0          |
| 11           | 0.98        | 1.0      | **1.19**     |
| 12           | 0.98        | 1.0      | **1.02**     |
| 13           | 0.98        | 1.0      | 1.0          |
| 14           | 1.0         | 1.0      | 1.0          |
| 16           | 0.97        | 1.0      | 1.0          |
| 21           | 1.02        | 1.0      | 1.0          |
| 28           | 0.99        | 1.0      | 1.0          |
| 39           | 1.0         | 1.0      | 1.0          |
| 56           | 0.99        | 1.0      | 1.0          |
| 89           | 0.96        | 1.0      | 1.0          |
| 95           | 1.02        | 1.0      | 1.0          |
| 99           | 1.0         | 1.0      | 1.0          |
| 157          | 0.98        | 1.0      | 1.0          |
| 202          | **0.33**    | **1.94** | 1.0          |
| 218          | 0.97        | 1.0      | 1.0          |
| 273          | 0.98        | 1.0      | 1.0          |
| 293          | 0.96        | **0.75** | 1.0          |
| 318          | 1.03        | 1.0      | 1.0          |
| 334          | 1.0         | 1.0      | 1.0          |

Generally no performance impact (error margin, <3%), apart from (as described in the paper):
- 202: `futex` (66% slower, inconsistent synchronization, breaking)

Generally no resource usage impact (error margin, <1%), apart from (as described in the paper):
- 3: `close` (8x increased FD usage, FDs are not closed anymore, fine to a certain extent)
- 11: `munmap` (19% increased memory footprint, regions are not disposed anymore, fine to a certain extent)
- 12: `brk` (2% increased memory footprint, due to `mmap` fallback in early GLIBC allocator, fine)
- 14: `rt_sigprocmask` (15% lower memory footprint, when stubbing only, prevents creation of jemalloc background threads, resulting in memory being freed earlier/synchronously, fine)
- 202: `futex` (94% more FD usage, inconsistent synchronization, breaking)
- 293: `pipe2` (25% lower FD usage, because pipes are not created anymore, persistence may not work properly, fine depending on feature targets)

**iPerf3 (iPerf3 client)**

*Stubbing*

| System call  | Performance | FD Usage | Memory Usage |
|--------------|-------------|----------|--------------|
| 11           | 1.0         | 1.0      | 1.0          |
| 12           | 1.0         | 1.0      | **1.11**     |
| 13           | 0.97        | 1.0      | 1.0          |
| 21           | 0.99        | 1.0      | 1.0          |
| 72           | 0.99        | 1.0      | 1.0          |
| 98           | 1.0         | 1.0      | 1.0          |
| 218          | 0.99        | 1.0      | 1.0          |
| 228          | 0.98        | 1.0      | 1.0          |
| 273          | 1.0         | 1.0      | 1.0          |
| 302          | 1.0         | 1.0      | 1.0          |
| 318          | 1.0         | 1.0      | 1.0          |
| 334          | 0.97        | 1.0      | 1.0          |

*Faking*

| System call  | Performance | FD Usage | Memory Usage |
|--------------|-------------|----------|--------------|
| 10           | 1.01        | 1.0      | 1.0          |
| 11           | 1.0         | 1.0      | 1.0          |
| 12           | 1.0         | 1.0      | **1.11**     |
| 13           | 1.01        | 1.0      | 1.0          |
| 21           | 1.0         | 1.0      | 1.0          |
| 51           | 1.02        | 1.0      | 1.0          |
| 52           | 1.02        | 1.0      | 1.0          |
| 55           | 1.03        | 1.0      | 1.0          |
| 72           | 1.02        | 1.0      | 1.0          |
| 87           | 1.01        | 1.0      | 1.0          |
| 98           | 1.0         | 1.0      | 1.0          |
| 218          | 1.01        | 1.0      | 1.0          |
| 228          | 1.03        | 1.0      | 1.0          |
| 273          | 1.02        | 1.0      | 1.0          |
| 302          | 1.03        | 1.0      | 1.0          |
| 318          | 0.97        | 1.0      | 1.0          |
| 334          | 1.01        | 1.0      | 1.0          |

Generally no performance impact (error margin, <3%).

Generally no resource usage impact (error margin, <1%), apart from (as described in the paper):
- 12: `brk` (11% increased memory footprint, due to `mmap` fallback in early GLIBC allocator, fine)
