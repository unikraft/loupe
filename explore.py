#!/usr/bin/python3

# SPDX-License-Identifier: BSD-3-Clause
#
# Authors: Hugo Lefeuvre <hugo.lefeuvre@manchester.ac.uk>
#
# Copyright (c) 2020-2022, The University of Manchester. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import datetime
import os, sys, signal, re, argparse, pathlib, time, subprocess
import src.common as common
from src.common import *

# ==============
# SCRIPT OPTIONS

ENABLE_SEQUENTIAL = False

ENABLE_FASTSCAN = True

PARTIAL_SUPPORT_ANALYSIS = False

SPECIAL_FILES_ANALYSIS = False

PERFORMANCE_ANALYSIS = False
# set this to fit your system;
# it's important for the performance comparison part
TASKSET_CPU = 5
# how many times to warmup before running baseline
WARMUP_ROUNDS = 5
# how many runs to average
NO_RUNS_AVG = 4

LIMIT_RETRIES = 2

BEAUTIFY_PERF_OUTPUT = True

WAIT_STARTUP_TIME = 0.40

# NOTE: adapt timeout depending on how long your script takes...
TEST_TIMEOUT = 4

ZBINARY = None

HOME_PATH = os.path.abspath(os.path.dirname(__file__))
SECCOMPRUN_PATH = os.path.join(HOME_PATH, "src", "seccomp-run")

SMART_WAIT_REPEAT = 1

# =========
# CONSTANTS

ERRNO_ENOSYS = 38

# edit this if you want to use strace from another location
STRACE_BINARY = "strace"

SYSCALL_FLAGS = {
# syscall  : position of the flags argument
    "mmap" : 3,
    "mprotect" : 2,
    "madvise" : 2,
    "arch_prctl" : 0,
    "accept4" : 3,
    "prlimit64" : 1,
    "setrlimit" : 0,
    "getrlimit" : 0,
    "fcntl" : 1,
    "clock_nanosleep" : 0,
    "ioctl" : 1
}

SYSCALL_FLAGS_FILES = {
    "open" : 0,
    "openat" : 1
}

INITIAL_SCAN_STDERR = "/tmp/dynsystmp"
INITIAL_SCAN_STDOUT = "/tmp/dynsystmp-stdout"

# ============
# USAGE CHECKS

testscript_path = ""
binary_path = ""
binary_options = []

# =============
# OPTION CHECKS

def strace_recent_enough():
    cmd = [STRACE_BINARY, "-n", "who"]
    ps = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ps.communicate()[0]
    if "strace: invalid option -- 'n'" in str(output):
        return False
    return True

if not strace_recent_enough():
    print("WARN: strace is old on this system and does not support -n")
    print("      without support for this option, the scan will be MUCH slower")
    print("      you can get a proper recent strace from https://strace.io/")
    input("[ press ENTER to continue, or kill me to abort (CTRL-C) ]")
    ENABLE_FASTSCAN = False

# =======
# HELPERS

def smart_wait(process, logfs):
    ret = -1

    logf = pathlib.Path(logfs)
    loghash = get_file_hash(logf)
    for i in range(SMART_WAIT_REPEAT):
        try:
            ret = process.wait(timeout=TEST_TIMEOUT)
        except(subprocess.TimeoutExpired):
            newhash = get_file_hash(logf)
            if (loghash != newhash):
                loghash = newhash
            else:
                break
    return ret

def cleanup():
    # make sure to have a clean system
    os.system("killall -9 %s > /dev/null 2>&1" % binary_path)
    os.system("pkill -9 %s > /dev/null 2>&1" % binary_path)

def start_seccomp_run(errno, syscall, logf, prefix=[], opts=[]):
    cleanup()

    runcmd = []
    runcmd.extend(prefix)
    runcmd.extend([SECCOMPRUN_PATH, "-e", errno, "-n", "1", str(syscall)])
    if ZBINARY is not None:
        runcmd.extend(["-y", str(ZBINARY)])
    runcmd.extend(opts)
    runcmd.extend(["--", str(binary_path)])
    runcmd.extend(binary_options)

    ret = subprocess.Popen(runcmd, stderr=logf, stdout=logf,
        preexec_fn=os.setsid)

    # small sleep in case the program needs time to initialize
    time.sleep(WAIT_STARTUP_TIME)

    return ret

def start_test_cmd(log):
    if testscript_path is None:
        time.sleep(TEST_TIMEOUT)
        return 0
    testcmd = [testscript_path, log]
    ret = 0
    try:
        ret = subprocess.call(testcmd, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=TEST_TIMEOUT)
    except(subprocess.TimeoutExpired):
        ret = 1
    return ret

# return (is used, success)
def analyze_one_pass(errno, syscall, log, errs, prefix=[], opts=[]):
    with open(log, 'wb') as logf:
        process = start_seccomp_run(errno, syscall, logf)
        process_ok = True
        if ENABLE_SEQUENTIAL:
            process_ret = smart_wait(process, log)
            if process_ret:
                process_ok = False

        ret = start_test_cmd(log)

        if (not ret and process_ok):
            # the program works without this syscall
            success = (True,True,errs)
        elif (ret != 200):
            success = (False,True,errs)
        elif (ret == 200 and errs == LIMIT_RETRIES):
            # see the comment below (in explore_perf) regarding retries
            success = (False,True,errs)
        else:
            cleanup()
            time.sleep(10)
            success = (False,False,errs + 1)

        if not ENABLE_SEQUENTIAL:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    return success

# ===========
# EXPLORATION

FEATURE_TRANSLATIONS = {}

# this scanning approach is much faster to detect all system calls
# executed by the application. It uses strace underneath, but the
# version has to be very recent, potentially compiled from source.
def initial_strace_scan():
    def generate_regex_feature(syscall, position, comment=False):
        farg = "(?:{[^}]*}|[^{][^,]*)"
        regex = syscall + "\("
        if position > 0:
            for i in range(position):
                regex += "%s, " % farg
        if not comment:
            regex += "([a-zA-Z0-9_]+)"
        else:
            regex += "([a-zA-Z0-9_]+) /\* ([^\*]+) \*/"
        return regex

    def generate_regex_files(syscall, position):
        farg = "[^,]+"
        regex = syscall + "\("
        if position > 0:
            for i in range(position):
                regex += "%s, " % farg
        regex += "\"([^\"]+)\""
        return regex

    cleanup()

    # --status=successful,failed greatly simplifies the output of strace for us to parse
    # and should not impact the number of system calls that we see or their arguments, only
    # their relative ordering, which doesn't matter to us.
    runcmd = [STRACE_BINARY, "-tfnX", "verbose",  "--status=successful,failed", str(binary_path)]
    runcmd.extend(binary_options)

    process = None
    success = False
    tries = 0

    while (not success):
        with open(INITIAL_SCAN_STDERR, "w") as stderr:
            with open(INITIAL_SCAN_STDOUT, "w") as stdout:
                process = subprocess.Popen(runcmd, stderr=stderr,
                                            stdout=stdout,
                                            preexec_fn=os.setsid)

        time.sleep(WAIT_STARTUP_TIME)

        traced_program_ok = True
        traced_program_ret = -1
        if ENABLE_SEQUENTIAL:
            try:
                traced_program_ret = process.wait(timeout=TEST_TIMEOUT)
            except(subprocess.TimeoutExpired):
                pass
            if traced_program_ret:
                traced_program_ok = False

        ret = start_test_cmd(INITIAL_SCAN_STDOUT)

        if not ENABLE_SEQUENTIAL:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)

        if ret == 0 and traced_program_ok:
            success = True
        elif tries == LIMIT_RETRIES:
            error("Error: cannot run initial scan. The program doesn't seem to work.")
            info("Program stdout/err logs are located at " + INITIAL_SCAN_STDERR)
            exit(1)
        else:
            debug("Initial strace scan attempt failed, traced program returned %d, test returned %d" % (traced_program_ret, ret))
            cleanup()
            time.sleep(10)
            tries += 1

    rets = []
    features = {}
    files = {}
    with open(INITIAL_SCAN_STDERR) as logf:
        full = logf.read()
        regex = re.compile("\[\s+(\d+)\]")
        rets = list(set(regex.findall(full)))

        # parse used features
        for syscall in SYSCALL_FLAGS.keys():
            regex = re.compile(generate_regex_feature(syscall,
                               SYSCALL_FLAGS[syscall]))
            features[syscall] = list(set(regex.findall(full)))
            features[syscall] = list(map(lambda i: int(i[2:], 16)
                    if i[:2] == "0x" else int(i), features[syscall]))

            FEATURE_TRANSLATIONS[syscall] = {}
            regex = re.compile(generate_regex_feature(syscall,
                               SYSCALL_FLAGS[syscall], comment=True))
            matches = regex.findall(full)
            for m in matches:
                if len(m) == 2:
                    if m[0][:2] == "0x":
                        FEATURE_TRANSLATIONS[syscall][int(m[0][2:], 16)] = m[1]
                    else:
                        FEATURE_TRANSLATIONS[syscall][int(m[0])] = m[1]

        # parse used files
        for syscall in SYSCALL_FLAGS_FILES.keys():
            regex = re.compile(generate_regex_files(syscall,
                               SYSCALL_FLAGS_FILES[syscall]))
            files[syscall] = list(set(regex.findall(full)))

    return ([int(e) for e in rets if int(e) <= MAX_SYSCALL],
            {k:v for (k,v) in features.items() if len(v) > 0},
            {k:v for (k,v) in files.items() if len(v) > 0})

# given an errno and a list of system calls, return the list of system
# calls that worked
def explore_works(errno, syscalls):
    unused = set()
    for i in syscalls:
        progress(i, max(syscalls))
        log = get_temp_file()

        s = False
        errs = 0

        while (not s):
            (u, s, errs) = analyze_one_pass(errno, i, log, errs)
            if (u):
                # the program works without feature j in syscall i
                unused.add(i)
    progress_end()
    return unused

def syscall_name_to_int(syscall):
    for (s,n) in syscall_mapping.items():
        if (s == syscall):
            return n

def explore_works_partial(errno, features):
    retval = dict()
    numfeatures = len([i for subl in features.values() for i in subl])
    t = 1
    for i in features.keys():
        retval[i] = set()
        for j in features[i]:
            progress(t, numfeatures)
            log = get_temp_file()

            success = False
            errs = 0

            while (not success):
                (used, success, errs) = analyze_one_pass(errno, syscall_name_to_int(i), log, errs,
                        opts=["-p", str(SYSCALL_FLAGS[i]), str(j)])
                if (used):
                    # the program works without feature j in syscall i
                    retval[i].add(j)
            t += 1
    progress_end()
    return retval

def explore_works_specialfiles(errno, files):
    retval = dict()
    numfeatures = len([i for subl in files.values() for i in subl])
    t = 1
    for i in files.keys():
        retval[i] = set()
        for j in files[i]:
            progress(t, numfeatures)
            log = get_temp_file()

            success = False
            errs = 0

            while (not success):
                (used, success, errs) = analyze_one_pass(errno, syscall_name_to_int(i), log, errs,
                        opts=["-t", str(SYSCALL_FLAGS_FILES[i]), j])
                if (used):
                    # the program works without feature j in syscall i
                    retval[i].add(j)
            t += 1
    progress_end()
    return retval

def open_fds(pid):
    files = os.listdir("/proc/%s/fd/" % str(pid))
    return len(files)

def peak_memsize(pid):
    size = ""
    regex = "VmPeak:(.*)$"
    with open("/proc/%s/status" % str(pid)) as f:
        for line in f:
            result = re.match(regex, line)
            if result is not None:
                size = result.group(1).strip()
    if (size == ""):
        error("Bug here! Failed to determine VmPeak.")
        exit(1)
    if (size[-3:] != " kB"):
        error("Bug here! VmPeak not in kB:%s" % size[-3:])
        exit(1)
    return int(size[:-3])

# given an errno and a list of system calls, return a mapping of system calls
# and resulting performance
def explore_perf(errno, syscalls):
    perf = dict()
    for i in syscalls:

        if len(syscalls) > 1:
            # no progress bar when doing baseline
            progress(i, max(syscalls))

        # (average performance, average no. of open FDs, average peak memory usage in KB)
        perf[i] = {"perf": 0, "openfds": 0, "memusage": 0}
        errs = 0

        for j in range(NO_RUNS_AVG):
            log = get_temp_file()

            success = False
            while (not success):
                with open(log, 'wb') as logf:
                    process = start_seccomp_run(errno, i, logf,
                        prefix=["taskset", "-c", str(TASKSET_CPU)])

                    testcmd = [testscript_path, log, "benchmark"]

                    try:
                        out = subprocess.check_output(testcmd).decode(sys.stdout.encoding)
                        perf[i]["perf"] += float(out)
                        perf[i]["openfds"] += float(open_fds(process.pid))
                        perf[i]["memusage"] += float(peak_memsize(process.pid))
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        success = True
                    except(subprocess.CalledProcessError):
                        # in theory, this shouldn't happen
                        # in practice, it happens because ports don't get freed in
                        # time between the starting and stopping of nginx
                        # in this case we just want to wait a bit and retry
                        # if it happens to many time in a row, just abort, it's bad.
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        errs += 1
                        if (errs >= LIMIT_RETRIES):
                            print()
                            error("Error: syscall " + str(i) + " does not actually seem " +
                                  "to work with errno " + str(errno) + " OR test script " +
                                  "doesn't support performance benchmark mode.")
                            error("Cause: CalledProcessError")
                            exit(1)
                        else:
                            cleanup()
                            time.sleep(10)
                    except(ValueError):
                        print()
                        error("Error: syscall " + str(i) + " does not actually seem " +
                              "to work with errno " + str(errno) + " OR test script " +
                              "doesn't support performance benchmark mode.")
                        error("Cause: ValueError")
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        exit(1)
        perf[i]["perf"] /= NO_RUNS_AVG
        perf[i]["openfds"] /= NO_RUNS_AVG
        perf[i]["memusage"] /= NO_RUNS_AVG

    if len(syscalls) > 1:
        progress_end()

    return perf

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
        help="enable debug output")
parser.add_argument("-q", "--quiet", action="store_true", dest="quiet",
        help="disable any non-error output")
parser.add_argument("--no-strace", action="store_true", dest="nostrace",
        help="perform initial scan without strace (slower!)")
parser.add_argument("--output-sys-names", action="store_true", dest="outputnames",
        help="output system call names instead of numbers")
parser.add_argument("--output-csv", action="store_true", dest="outputcsv",
        help="output data as CSV")
parser.add_argument("--partial-support", action="store_true",
        help="enable partial support analysis", dest="partialsupport")
parser.add_argument("--perf-analysis", action="store_true",
        help="enable performance and resource usage analysis", dest="perfanalysis")
parser.add_argument("--timeout", type=int,
        help="test timeout (default %ds)" % TEST_TIMEOUT, dest="timeout")
parser.add_argument("--smart-wait-repeat", type=int,
        help="enable smart wait (if you don't know what this does, don't enable it)", dest="smartwait")
parser.add_argument("--test-sequential", action="store_true",
        help="run the binary first, then the test script with the binary's output", dest="seq")
parser.add_argument("arg_binary", nargs='*',
        help="additional arguments to pass to the test binary")
parser.add_argument("-t", dest="testscript",
        type=pathlib.Path, required=False, help="path to the test script")
parser.add_argument("--only-consider", dest="zbinary",
        type=pathlib.Path, help="only consider a given binary in the analysis")

required_args = parser.add_argument_group('required arguments')
required_args.add_argument("-b", dest="testbinary",
        type=pathlib.Path, required=True, help="path to the test binary")

required_args = parser.add_argument_group('debug arguments')
required_args.add_argument("--maxsys", dest="maxsys",
        type=int, help="maximum number of system calls to consider")

args = parser.parse_args()

# setup according to command line arguments
ENABLE_SEQUENTIAL = args.seq
ENABLE_FASTSCAN = (args.nostrace is False)
PARTIAL_SUPPORT_ANALYSIS = (args.partialsupport is True)
PERFORMANCE_ANALYSIS = (args.perfanalysis is True)
OUTPUT_CSV = (args.outputcsv is True)
common.OUTPUT_NAMES = (args.outputnames is True)
common.ENABLE_VERBOSE = (args.verbose is True)
common.ENABLE_QUIET = (args.quiet is True)
if args.maxsys is not None:
    MAX_SYSCALL = args.maxsys

if args.smartwait is not None and args.smartwait > 1:
    SMART_WAIT_REPEAT = args.smartwait

ZBINARY = args.zbinary
if ZBINARY is not None:
    ENABLE_FASTSCAN = False

if common.ENABLE_VERBOSE and common.ENABLE_QUIET:
    error("--verbose and --quiet incompatible.")
    exit(1)

if common.ENABLE_VERBOSE and OUTPUT_CSV:
    error("--verbose and --csv incompatible.")
    exit(1)

if OUTPUT_CSV:
    common.ENABLE_QUIET = True

if args.timeout is not None:
    TEST_TIMEOUT = args.timeout

if TEST_TIMEOUT < 1:
    warning("Test timeout is very low, this might cause invalid test results!")

if not args.testscript and PERFORMANCE_ANALYSIS:
    error("Performance analysis requires a test script.")
    exit(1)

binary_path = args.testbinary
binary_options = args.arg_binary
testscript_path = args.testscript

debug("Full test binary command: %s %s" % (binary_path, " ".join(binary_options)))

all_syscalls = range(0, MAX_SYSCALL + 1)

if not OUTPUT_CSV and (PARTIAL_SUPPORT_ANALYSIS or PERFORMANCE_ANALYSIS):
    error("CSV formatting not available with performance or partial analysis.")
    exit(1)

if not ENABLE_FASTSCAN and PARTIAL_SUPPORT_ANALYSIS:
    error("Partial system call support exploration only " +
          "available with strace (and --no-strace was passed).")
    exit(1)

# start analysis
info("Finding used system calls...")

used = []
features = []
files = []
if ENABLE_FASTSCAN:
    start_time = time.time()
    ret = initial_strace_scan()
    end_time = time.time()

    used = ret[0]
    features = ret[1]
    files = ret[2]
    info("Fast scan done!")
    info("Traced %d syscalls, estimated total (worst case) test time: %s" % (len(ret[0]), str(datetime.timedelta(seconds=end_time-start_time)*len(ret[0]*2))))
else:
    unused = explore_works("crash", all_syscalls)
    used = list(set(all_syscalls) - unused)
used.sort()

info("Finding system calls that work with ENOSYS...")

probably_works_stubbed = list(explore_works(str(ERRNO_ENOSYS), used))
probably_works_stubbed.sort()

info("Finding system calls that work when we fake (errno = 0)...")

probably_works_lying = list(explore_works("0", used))
probably_works_lying.sort()

require_impl = list(((set(used)) - set(probably_works_stubbed)) - set(probably_works_lying))
require_impl.sort()

probably_works_stubbed_and_lying_and_impled = list(set(probably_works_stubbed).intersection(
                                                   set(probably_works_lying)))
probably_works_stubbed_and_lying_and_impled.sort()

probably_works_stubbed_and_impled = list(set(probably_works_stubbed) -
                                         set(probably_works_lying))
probably_works_stubbed_and_impled.sort()

probably_works_lying_and_impled = list(set(probably_works_lying) -
                                       set(probably_works_stubbed))
probably_works_lying_and_impled.sort()

if not OUTPUT_CSV:
    print_header("Usage analysis")

    print("Used system calls: " + str(len(used)))
    if (len(used)):
        print(format_syscall_list(used))

    print()
    print("[NOTE] The following categories are all non overlapping!")

    print("System calls that require an implementation: " + str(len(require_impl)) +
              "/" + str(len(used)))
    if (len(require_impl)):
        print(format_syscall_list(require_impl))

    print("System calls that seem to work stubbed (but NOT lying): " + str(len(probably_works_stubbed_and_impled)) +
              "/" + str(len(used)))
    if (len(probably_works_stubbed_and_impled)):
        print(format_syscall_list(probably_works_stubbed_and_impled))

    print("System calls that seem to work lying (but NOT stubbed): " + str(len(probably_works_lying_and_impled)) +
              "/" + str(len(used)))
    if (len(probably_works_lying_and_impled)):
        print(format_syscall_list(probably_works_lying_and_impled))

    print("System calls that seem to work stubbed AND lying: " + str(len(probably_works_stubbed_and_lying_and_impled)) +
              "/" + str(len(used)))
    if (len(probably_works_stubbed_and_lying_and_impled)):
        print(format_syscall_list(probably_works_stubbed_and_lying_and_impled))
else:
    print("# syscall, used, works faked, works stubbed, works both")
    for sys in all_syscalls:
        isused = "N"
        if sys in used:
            isused = "Y"
        canfake = "N"
        if sys in probably_works_lying_and_impled:
            canfake = "Y"
        canstub = "N"
        if sys in probably_works_stubbed_and_impled:
            canstub = "Y"
        canboth = "N"
        if sys in probably_works_stubbed_and_lying_and_impled:
            canboth = "Y"
        print("%s,%s,%s,%s,%s" % (
                str(format_syscall_list([sys])[0]),
                isused, canfake, canstub, canboth))

info("\nFinding used system calls using static analysis...")

if (OUTPUT_CSV):
    print()

print("# syscall, used")
runcmd = [str(os.path.join(os.path.realpath(os.path.dirname(__file__)),
        "src/static_source/static_analyser.py")), "-a", str(binary_path),
        "--csv=true", "--display=false", "--verbose=false"]
print(subprocess.check_output(runcmd).decode('utf-8'))


def print_set(s, printer):
    keys = list(s.keys())
    keys.sort()
    for syscall in keys:
        print(syscall + ": ", end="")
        printer(s, syscall)
    print()

if PARTIAL_SUPPORT_ANALYSIS:
    def print_values(l, sys):
        def print_value(f, e):
            if f in FEATURE_TRANSLATIONS[sys]:
                print("0x{:x} (%s)".format(f) % FEATURE_TRANSLATIONS[sys][f], end = e)
            else:
                print("0x{:x}".format(f), end = e)
        if not len(l):
            print ("-")
            return
        for f in l[:-1]:
            print_value(f, ", ")
        print_value(l[-1], "\n")

    def lengthof(d):
        return len([i for subl in d.values() for i in subl])

    print_header("Partial support analysis")

    print("Note: considering only the following system calls:")
    keys = list(SYSCALL_FLAGS.keys())
    keys.sort()
    for syscall in keys[:-1]:
        print(syscall + " (arg #%d)" % SYSCALL_FLAGS[syscall], end =", ")
    print(keys[-1] + " (arg #%d)" % SYSCALL_FLAGS[keys[-1]])
    print()

    info("Finding partial system call features that work with ENOSYS...")
    works_partial_stubbed = explore_works_partial(str(ERRNO_ENOSYS), features)

    info("Finding partial system call features that work faking...")
    works_partial_faked = explore_works_partial("0", features)

    assert len(works_partial_stubbed.keys()) == len(works_partial_faked.keys())

    works_partial_only_impled = {}
    for syscall in features.keys():
        works_partial_only_impled[syscall] = []
        for f in features[syscall]:
            if (f not in works_partial_stubbed[syscall] and
                f not in works_partial_faked[syscall]):
                works_partial_only_impled[syscall].append(f)

    works_partial_stubbed_and_faked = {}
    for syscall in works_partial_stubbed.keys():
        works_partial_stubbed_and_faked[syscall] = []
        for f in works_partial_stubbed[syscall]:
            if f in works_partial_faked[syscall]:
                works_partial_stubbed_and_faked[syscall].append(f)

    works_partial_stubbed_but_not_faked = {}
    for syscall in works_partial_stubbed.keys():
        works_partial_stubbed_but_not_faked[syscall] = []
        for f in works_partial_stubbed[syscall]:
            if f not in works_partial_faked[syscall]:
                works_partial_stubbed_but_not_faked[syscall].append(f)

    works_partial_faked_but_not_stubbed = {}
    for syscall in works_partial_stubbed.keys():
        works_partial_faked_but_not_stubbed[syscall] = []
        for f in works_partial_faked[syscall]:
            if f not in works_partial_stubbed[syscall]:
                works_partial_faked_but_not_stubbed[syscall].append(f)

    print()
    print("Used features (%d):" % lengthof(features))
    print_set(features, print_values)

    print("Features that *must* be implemented (%d/%d):" %
            (lengthof(works_partial_only_impled), lengthof(features)))
    print_set(works_partial_only_impled, print_values)

    print("Features that may be stubbed but not faked (%d/%d):" %
            (lengthof(works_partial_stubbed_but_not_faked), lengthof(features)))
    print_set(works_partial_stubbed_but_not_faked, print_values)

    print("Features that may be faked but not stubbed (%d/%d):" %
            (lengthof(works_partial_faked_but_not_stubbed), lengthof(features)))
    print_set(works_partial_faked_but_not_stubbed, print_values)

    print("Features that may be faked and stubbed (%d/%d):" %
            (lengthof(works_partial_stubbed_and_faked), lengthof(features)))
    print_set(works_partial_stubbed_and_faked, print_values)

if PERFORMANCE_ANALYSIS:
    def print_perf(p, baseline):
        if BEAUTIFY_PERF_OUTPUT:
            print("syscall: perf openfds memusage (relative to the baseline)")
            for k, v in p.items():
                print(str(format_syscall_list([k])[0]) + ": %s %s %s (%s,%s,%s)" %
                        (str(round(v["perf"], 2)),
                        str(round(v["openfds"], 2)),
                        str(round(v["memusage"], 2)),
                        str(round(v["perf"] / baseline_perf["perf"], 2)),
                        str(round(v["openfds"] / baseline_perf["openfds"], 2)),
                        str(round(v["memusage"] / baseline_perf["memusage"], 2))))
            print()
        else:
            print({format_syscall_list([k])["perf"]: v for k, v in p.items()})

    print_header("Performance analysis")

    info("Determining baseline...")
    # this is NOT a copy and paste error, do it three times to warm up
    # this has a significant impact on performance
    baseline_raw = []
    for i in range(WARMUP_ROUNDS): # = WARMUP_ROUNDS + 1 runs
        baseline_raw = explore_perf(str(ERRNO_ENOSYS), [317])
    baseline_perf = baseline_raw[317]

    if BEAUTIFY_PERF_OUTPUT:
        print("Baseline: perf openfds memusage")
        print("Baseline: %s %s %s" % (str(round(baseline_perf["perf"], 2)),
                                     str(round(baseline_perf["openfds"], 2)),
                                     str(round(baseline_perf["memusage"], 2))))
        print()

    info("Gathering data for stubbing...")
    stubbing_perf = explore_perf(str(ERRNO_ENOSYS), probably_works_stubbed)
    print_perf(stubbing_perf, baseline_perf)

    info("Gathering data for faking...")
    faking_perf = explore_perf("0", probably_works_lying)
    print_perf(faking_perf, baseline_perf)

if SPECIAL_FILES_ANALYSIS:
    def print_values(l, x): # x is ignored
        if not len(l):
            print ("-")
            return
        for f in l[:-1]:
            print(f, end=", ")
        print(l[-1], end="\n")

    def lengthof(d):
        return len([i for subl in d.values() for i in subl])

    print_header("Special files analysis")

    print("Note: considering only the following system calls:")
    keys = list(SYSCALL_FLAGS_FILES.keys())
    keys.sort()
    for syscall in keys[:-1]:
        print(syscall + " (arg #%d)" % SYSCALL_FLAGS_FILES[syscall], end =", ")
    print(keys[-1] + " (arg #%d)" % SYSCALL_FLAGS_FILES[keys[-1]])
    print()

    info("Finding special files that work with ENOSYS...")
    works_partial_stubbed = explore_works_specialfiles(str(ERRNO_ENOSYS), files)

    info("Finding special files that work faking...")
    works_partial_faked = explore_works_specialfiles("0", files)

    assert len(works_partial_stubbed.keys()) == len(works_partial_faked.keys())

    works_partial_only_impled = {}
    for syscall in files.keys():
        works_partial_only_impled[syscall] = []
        for f in files[syscall]:
            if (f not in works_partial_stubbed[syscall] and
                f not in works_partial_faked[syscall]):
                works_partial_only_impled[syscall].append(f)

    works_partial_stubbed_and_faked = {}
    for syscall in works_partial_stubbed.keys():
        works_partial_stubbed_and_faked[syscall] = []
        for f in works_partial_stubbed[syscall]:
            if f in works_partial_faked[syscall]:
                works_partial_stubbed_and_faked[syscall].append(f)

    works_partial_stubbed_but_not_faked = {}
    for syscall in works_partial_stubbed.keys():
        works_partial_stubbed_but_not_faked[syscall] = []
        for f in works_partial_stubbed[syscall]:
            if f not in works_partial_faked[syscall]:
                works_partial_stubbed_but_not_faked[syscall].append(f)

    works_partial_faked_but_not_stubbed = {}
    for syscall in works_partial_stubbed.keys():
        works_partial_faked_but_not_stubbed[syscall] = []
        for f in works_partial_faked[syscall]:
            if f not in works_partial_stubbed[syscall]:
                works_partial_faked_but_not_stubbed[syscall].append(f)

    print()
    print("Used files (%d):" % lengthof(files))
    print_set(files, print_values)

    print("Files that *must* be implemented (%d/%d):" %
            (lengthof(works_partial_only_impled), lengthof(features)))
    print_set(works_partial_only_impled, print_values)

    print("Files that may be stubbed but not faked (%d/%d):" %
            (lengthof(works_partial_stubbed_but_not_faked), lengthof(features)))
    print_set(works_partial_stubbed_but_not_faked, print_values)

    print("Files that may be faked but not stubbed (%d/%d):" %
            (lengthof(works_partial_faked_but_not_stubbed), lengthof(features)))
    print_set(works_partial_faked_but_not_stubbed, print_values)

    print("Files that may be faked and stubbed (%d/%d):" %
            (lengthof(works_partial_stubbed_and_faked), lengthof(features)))
    print_set(works_partial_stubbed_and_faked, print_values)
