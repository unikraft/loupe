# Writing Good Loupe Dockerfiles

TODO: make this a little bit more reader-friendly.

- Ensure that your workload really represents what you would like to support down the line.
- Build the application *and* the benchmarking tool (if relevant) from source instead of using APT repositories to ensure that application version and configuration remain fixed.
- Prefer static builds over dynamically linked builds to better fix dependencies.
- Use the full span of Loupe features, particularly `--final-check`
