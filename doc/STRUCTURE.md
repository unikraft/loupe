# Structure of the Loupe repository

The following information is true as of ASPLOS'24 release:

**Makefile**

- Provides rules to build Loupe and all environment Docker images.
- Usage is documented in the main [README.md](https://github.com/unikraft/loupe/blob/staging/README.md).

**loupe**

- Main Loupe wrapper: provides DB management, container building and orchestration, reproducibility features, search and visualization features.
- Under the hood, relies on `explore.py` for the system call analysis/exploration, and on Gnuplot scripts (`resources`) for plotting.
- Usage is documented with `./loupe -h` and in the main [README.md](https://github.com/unikraft/loupe/blob/staging/README.md).
- More help can be obtained for each of the subcommands, e.g., `./loupe generate -h`.

**explore.py**

- Loupe system call exploration module.
- Performs the bulk of the system call exploration as described in the ASPLOS'24 paper.
- Under the hood, relies on `seccomp-run` (in `src`) to interpose with ptrace and seccomp.
- Usage is documented via `./explore.py -h`, and partially in the main [README.md](https://github.com/unikraft/loupe/blob/staging/README.md).

**src/seccomp-run.c**

- Performs system call interposition using ptrace and seccomp.
- You should not have to build this manually. If necessary, you can do it via `make src/seccomp-run`.
- You should not have to call this manually. If necessary, usage is documented visa `./seccomp-run -h`.

**src/static-{binary|source}-analyser**

- Contains the static binary and source analysis tools.
- Documented separately in the corresponding folder.

**resources/**

- Contains Gnuplot scripts used by Loupe to visualize the database.
- You should not have to call these manually.

**misc-artifacts/**

- Contains all OS compatibility score and implementation plans code, as described in the paper.

**docker/**

- Contains Dockerfiles used to build the Loupe base container and the plotting container.
- Can be built with `make docker` or `make docker-rebuild`.

**debhelper/**

- Contains debhelper integration module. This includes a new docker image derived from the base one,
and a set of wrapper scripts over the debhelper tool.
- Automates the build process of the target application.
- Automates the running of Loupe on the test suite of the app (EXPERIMENTAL)

**doc/**

- Contains additional documentation on Loupe.
