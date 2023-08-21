# Static Analyser Tool (sources-level)

The static source analyser is a tool designed to detect system calls by analysing the source files of an application. This tool requires [Clang](https://pypi.org/project/clang/) and [Beautifulsoup4](https://pypi.org/project/beautifulsoup4/) as third-parties libraries.

The analyser is based on two methods to discover system calls:

1. **Source files analysis (required)**:
    - It uses the Clang library to build an AST (Abstract Syntax Tree) of all the different functions present in the source files of a specific application (path to the source code).
    - It traverses this AST in order to detect the system calls called in the application code.
2. **RTL files analysis (*optional* but more accurate analysis)**:
    - For this analysis, the application sources must be compiled with the `-fdump-rtl-expand` (see [RTL files analysis](#rtl-files-analysis) for further information). Using this flag allows the compiler to generate an intermediate representation ([RTL](https://gcc.gnu.org/onlinedocs/gccint/RTL.html)).
    - The tool will then iterate through an "expand/" (must be created and populated) folder which contains the RTL representation and parse this intermediate representation in order to create an interdependency graph of all the functions.
    - It will then detect the system calls (ind)direclty called in the application by traversing this graph.

The analyser can also be used with coverage information (see [Coverage section](#coverage-information-experimental) for further information).

### Requirements

In order to execute the static source analyser, it is necessary to install Clang and update the path of the shared libraries. For *Mac* users, the Clang library is by default set by the `MAC_CLANG` variable. On Linux, this can be done via the following operations:

```bash
cd /usr/lib/x86_64-linux-gnu/
sudo ln -s libclang-X.Y.so.1 /usr/lib/x86_64-linux-gnu/libclang.so #(X.Y the version number)
```

It is also necessary to install Clang (bindings) and Beautifulsoup4. Both can be installed by executing the following commands:

```bash
pip install -r requirements.txt
```

### Getting started

The static source analyser can be used with the following syntax:

```bash
usage: source_analyser.py [-h] --folder FOLDER [--coverage COVERAGE] [--aggregate [AGGREGATE]]
                          [--savehtml [SAVEHTML]] [--unique [UNIQUE]] [--maxdisplay MAXDISPLAY]
                          [--verbose [VERBOSE]] [--display [DISPLAY]] [--csv [CSV]] [--generatePdf [GENERATEPDF]]
                          [--generateDot [GENERATEDOT]] [--exclude REGEX] [--no-externs] [--no-warnings]
                          [--max-depth DEPTH]

optional arguments:
  -h, --help            show this help message and exit
  --folder FOLDER, -f FOLDER
                        Path to the folder (source files) of the application to analyse (required)
  --coverage COVERAGE   [EXPERIMENTAL] Type of coverage (can be: None,-coverage-benchmark/or-coverage-suite/)
  --aggregate [AGGREGATE], -a [AGGREGATE]
                        Aggregate results into a single aggregated file (log_aggregated)
  --savehtml [SAVEHTML], -s [SAVEHTML]
                        Save intermediate results as .html (when coverage is used)
  --unique [UNIQUE]     Count only functions once in an aggregated unique file (when coverage is used)
  --maxdisplay MAXDISPLAY
                        Max referenced files to show in the aggregate unique file (default: 10, when coverage is used)
  --verbose [VERBOSE], -v [VERBOSE]
                        Verbose mode
  --display [DISPLAY], -d [DISPLAY]
                        Display system call
  --csv [CSV], -c [CSV]
                        Save system call as CSV
  --generatePdf [GENERATEPDF]
                        Generate PDF files (when coverage is used)
  --generateDot [GENERATEDOT]
                        Generate dot files (when coverage is used)
  --exclude REGEX       RegEx for functions to exclude (when coverage is used)
  --no-externs          Do not show external functions (when coverage is used)
  --no-warnings         Do not show warnings on the console (when coverage is used)
  --max-depth DEPTH     Maximum tree depth traversal, default no depth (when coverage is used)
```

As an example, the static source analyser can be executed with the following syntax:

```bash
./source_analyser.py -f [folder_path] --csv=true --display=false --verbose=false
```

### Shared Libraries

For both analyses, only the application source code is analysed (*without shared libraries*). If you want to analyse the shared libraries, you must include the sources within the application directory. There are two possible options:

1. Include the raw sources of the shared libraries: in this case, all the system calls directly used by the shared libraries will be detected, which may greatly overestimate the number of system calls used by the application.
2. Include RTL files (`*.expand`) from shared libraries: in this case, the interdependency graph can be used to reduce the number of system calls (functions called by the application code only). The larger and more complex the graph is, the longer the analysis takes.

Note that glibc parsing is not supported and requires manual sanitisation.

### RTL files analysis

If you want a more accurate analysis, it is required to compile your application with the `-fdump-rtl-expand` flags (only for gcc). You can either override the `CFLAGS` variable in the Makefile or compile the application with `make CFLAGS+=-fdump-rtl-expand`.

When the compilation is complete, you need to move all the RTL files into a `expand/` folder. This can be done via the following command:

```bash
mkdir expand/ && find . -type f -name "*.expand"  -exec mv -t expand {} +
```

For shared libraries, RTL files must also be included in the application's `expand/` folder (either in subdirectories or in the root directory).

### Coverage information (EXPERIMENTAL)

The tool is also able to detect which system call is really called when testing an application (via benchmark or testsuite). In order to use this feature, you need to install [gcov](https://gcc.gnu.org/onlinedocs/gcc/Gcov.html)and compile your application with the `-fprofile-arcs -ftest-coverage` or `--coverage` flags (only for gcc). As previously, you can also override the `CFLAGS` variable.

When the compilation is complete, you need to generate a lcov report:

```bash
lcov --capture --directory . --output-file cov.info
genhtml cov.info --output-directory "coverage-suite" \
    --demangle-cpp --legend \
    --title "Coverage type"
```

When the HTML folder (called either `coverage-benchmark` or `coverage-suite`) is generated, you can use the source analyser with the `--coverage [coverage-benchmark|coverage-suite]` keyword to analyse the coverage information. The tool can generate dot and pdf files for each system call (which contains the call trace). For this option, `graphviz` must be installed.

### Architecture

The current implementation is organized into eight different files. There are three main files that contain the logic of the source analyser: `source_analyser.py`, `process_call.py`, and `parser_clang.py`. The remaining four files contain helper functions, classes or data: `syscalls_list.py`, `utility.py`, `classes.py`, `check_syscall.py` and `output_html.py`.

- The code for scanning syscall from source files (clang AST) is in `parser_clang.py`.
- The code for detecting syscalls from the RTL representation is in `source_analyser.py` and `process_call.py`.
- The code for parsing and generating HTML folder/results is in `source_analyser.py` and `output_html.py`.
- The code for manipulating the syscalls map is in `syscalls_list.py`.
- Finally, all the helper functions that are not directly related to the source analyser have been moved to `utility.py`.

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
