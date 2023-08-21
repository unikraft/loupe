# Static Analyser Tool (binary-level)

The static binary analyser is a tool designed to detect system calls by analysing a static binary of an application. This tool handles both statically and dynamically-linked (it handles the plt/got sections) binaries. The static analyser requires [Capstone](https://pypi.org/project/capstone/) and [Lief](https://pypi.org/project/lief/) as third-parties libraries.

### Requirements

In order to execute the static analyser, it is necessary to install Capstone and Lief. Both can be installed by executing the following commands:

```bash
pip install -r requirements.txt
```

### Getting started

The static analyser can be used with the following syntax:

```bash
usage: static_analyser.py [-h] --app APP [--verbose [VERBOSE]] [--display [DISPLAY]] [--csv [CSV]] [--log [LOG]] [--log-to-stdout [LOG_TO_STDOUT]] [--max-backtrack-insns [MAX_BACKTRACK_INSNS]]
                          [--skip-data [SKIP_DATA]]

optional arguments:
  -h, --help            show this help message and exit
  --app APP, -a APP     Path to application (required)
  --verbose [VERBOSE], -v [VERBOSE]
                        Verbose mode (default: True)
  --display [DISPLAY], -d [DISPLAY]
                        Display syscalls (default: True)
  --csv [CSV], -c [CSV]
                        Output csv (default: True)
  --log [LOG], -l [LOG]
                        Log mode into a backtrack.log and lib_functions.log files (default: False)
  --log-to-stdout [LOG_TO_STDOUT], -L [LOG_TO_STDOUT]
                        Print logs to the standard output
  --max-backtrack-insns [MAX_BACKTRACK_INSNS], -B [MAX_BACKTRACK_INSNS]
                        Maximum number of instructions to check before a syscall instruction to find its id (default: 20)
  --skip-data [SKIP_DATA], -s [SKIP_DATA]
                        Automatically skip data in code and try to find the next instruction (default: False - [EXPERIMENTAL] may lead to errors)
```

As an example, the static analyser is directly executed by the  `explore.py` script with the following syntax:

```bash
./static_analyser.py -a [app_path] --csv=true --display=false --verbose=false
```

The output gives the syscalls discovered in a CSV format with each line formatted as follows: `<syscall_number, Y|N>`.

### Architecture

The current implementation is organized into seven different files. There are three main files that contain the logic of the static analyser: `static_analyser.py`, `code_analyser.py`, and `library_analyser.py`. The remaining four files contain helper functions, classes or data: `syscalls.py`, `utils.py`, `elf_analyser.py`, and `custom_exception.py`.

- The code for scanning syscall instructions (+ backtracking) is in `code_analyser.py`.
- The code for detecting syscalls from symbolic information is in `elf analyser.py`.
- The code for manipulating the syscalls map is in  `syscalls.py`.
- Finally, all the helper functions that are not directly related to the static analyser have been moved to `utils.py`.

A summary of the content of the code and the interactions between the different files is explained on the following figure:

[<img src="https://people.montefiore.uliege.be/gain/public/syscalls_architecture.png">](https://people.montefiore.uliege.be/gain/public/syscalls_architecture.png/)

### Contributing

We welcome contributions from anyone. This is [free
software](https://github.com/unikraft/loupe/blob/staging/COPYING.md).

To contribute to this repository, please fork and submit a Pull-Request. If you
introduce a new file, make sure to add an SPDX license header. If you do
significant-enough changes, consider adding yourself to `COPYING.md`.

We included a
[description](https://github.com/unikraft/loupe/blob/staging/STRUCTURE.md) of
the structure of this repository, which you may find useful to get started.

Here are a few ideas of contributions to get started:

- Add support to convert Loupe databases to SQLite.
- Fix [open bug reports](https://github.com/unikraft/loupe/issues).
