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

## Dependencies

- Docker
- python 3, with [python-git](https://pypi.org/project/python-git/)
- a recent-enough Linux kernel to support seccomp and ptrace

## Gathering Data

`loupe generate` takes care of analyzing the system call usage of your
application.

### Example 1: Dynamic system call usage analysis of Nginx

*TODO*

## Retrieving and Processing Data

`loupe search` takes care of analyzing the data in the database.
