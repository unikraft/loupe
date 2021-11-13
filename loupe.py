#!/usr/bin/python3

# SPDX-License-Identifier: BSD-3-Clause
#
# Authors: Hugo Lefeuvre <hugo.lefeuvre@manchester.ac.uk>
#
# Copyright (c) 2020-2021, The University of Manchester. All rights reserved.
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

import os
import hashlib
import argparse
import pathlib
import shutil
import git
import re
import common
import subprocess
from common import *

def open_syscall_file(path):
    with open(path, "r") as f:
        l = list(set([e for e in f.read().split("\n") if len(e) > 1]))
        l = format_syscall_list_to_num(l)
        l.sort()
        return l

# init a fresh database
def init_db(path):
    if (not os.path.isdir(path)):
        os.mkdir(path)
    g = git.cmd.Git(path)
    g.init()

# check that the db is sane
def db_check(path):
    # it must exist and be in a git repo
    try:
        git_repo = git.Repo(path, search_parent_directories=True)
    except git.exc.NoSuchPathError:
        error("Database %s does not exist" % path)
        create = input("Create it? [y/n] ")
        if create.lower() == 'yes' or create.lower() == 'y':
            init_db(path)
            return True
        else:
            return False
    except git.exc.InvalidGitRepositoryError:
        error("Database %s is not a git repository" % path)
        return False

    # it may not have uncommited changes
    git_repo = git.Repo(path, search_parent_directories=True)
    if (git_repo.is_dirty() or len(git_repo.untracked_files) != 0):
        error("Database %s is dirty; commit your changes before running this tool." % path)
        return False

    return True

# return an in-memory representation of the DB:
# {
#   # first level: applications
#   redis : {
#     # second level: workloads
#     benchmark : [
#       # third level: individual measurements
#       [[0, 'Y', 'N', 'Y'], [1, 'N', 'N', 'N'], ...],
#       [[0, 'Y', 'N', 'Y'], [1, 'Y', 'Y', 'Y'], ...]
#     ]
#     testsuite : [
#       [[0, 'Y', 'N', 'Y'], [1, 'N', 'N', 'N'], ...]
#     ]
#   }
# }
def db_load(path):
    db = dict()

    # iterate over apps
    for a in [e for e in path.iterdir() if e.is_dir()]:
        if os.path.basename(a)[0] == ".":
            continue

        app = dict()

        # iterate over workloads
        for w in [e for e in a.iterdir() if e.is_dir()]:
            bench_workload = list()
            suite_workload = list()

            # iterate over measurements
            for m in [e for e in w.iterdir() if e.is_dir()]:
                ml = list()

                # iterate over the CSV file
                with open(os.path.join(str(m), "data", "dyn.csv"), "r") as f:
                    for line in f:
                        if (line[0] == '#'):
                            continue
                        ml.append(re.sub(r"[\n\t\s]*", '', line).split(","))

                if (os.path.basename(w).startswith("benchmark")):
                    bench_workload.append(ml)
                else:
                    suite_workload.append(ml)

            app["benchmark"] = bench_workload
            app["testsuite"] = suite_workload

        db[os.path.basename(a)] = app

    return db

def process_cumulative(db, applist, bench=False, suite=False):
    assert(bench or suite)

    if "*" in applist and len(applist) > 1:
        warning("* in the application list but other entries are specified: " + str(applist))
        warning("Ignoring them.")
        applist = db.keys()
    elif "*" in applist:
        applist = db.keys()

    cumulative_required = {}
    cumulative_executed = {}

    # prepopulate
    for i in range(0, MAX_SYSCALL + 1):
        cumulative_required[i] = 0
        cumulative_executed[i] = 0

    n = 0
    for app in applist:
        n += 1
        workloads = []
        if bench:
            workloads.extend(db[app]["benchmark"])
        if suite:
            workloads.extend(db[app]["testsuite"])
        for i in range(0, MAX_SYSCALL + 1):
            exe = False
            req = False
            for w in workloads:
                if w[i][1] == "Y":
                    exe = True
                    if w[i][2] == "N" and w[i][3] == "N" and w[i][4] == "N":
                        req = True
            if exe:
                cumulative_executed[i] += 1
            if req:
                cumulative_required[i] += 1

    # convert to percentages
    for i in range(0, MAX_SYSCALL + 1):
        cumulative_required[i] /= n
        cumulative_required[i] *= 100
        cumulative_executed[i] /= n
        cumulative_executed[i] *= 100

    return (cumulative_required, cumulative_executed)

# FIXME has a lot of duplicated code
def used_by_apps(db, applist, bench=False, suite=False):
    assert(bench or suite)

    if "*" in applist and len(applist) > 1:
        warning("* in the application list but other entries are specified: " + str(applist))
        warning("Ignoring them.")
        applist = db.keys()
    elif "*" in applist:
        applist = db.keys()

    def _used_by_app(app):
        if app not in db.keys():
            error("%s not in the database." % app)
            error("Valid entries are: " + str(db.keys()))
            exit(1)

        req  = []
        stub = []
        fake = []
        both = []

        # collect all relevant measurements
        workloads = []
        if bench:
            workloads.extend(db[app]["benchmark"])
        if suite:
            workloads.extend(db[app]["testsuite"])

        # populate req, stub, fake
        for i in range(0, MAX_SYSCALL + 1):
            isr = None
            iss = None
            isf = None
            isb = None

            for w in workloads:
                if (w[i][1] == "N"):
                    continue
                elif ((w[i][2] == "Y" and w[i][3] == "Y") or
                      (w[i][4] == "Y")):
                    # can be stubbed and faked
                    if (iss is not None or isf is not None):
                        continue
                    isr = False
                    iss = True
                    isf = True
                    isb = True
                elif (w[i][2] == "Y" and w[i][3] == "N"):
                    # can be stubbed
                    isf = False
                    isb = False
                    if (iss is not None):
                        continue
                    isr = False
                    iss = True
                elif (w[i][2] == "N" and w[i][3] == "Y"):
                    # can be faked
                    iss = False
                    isb = False
                    if (isf is not None):
                        continue
                    isr = False
                    isf = True
                elif (w[i][2] == "N" and w[i][3] == "N" and w[i][4] == "N"):
                    # required
                    isr = True
                    iss = False
                    isf = False
                    isb = False
                    break

            if isr:
                req.append(i)
            elif isb:
                both.append(i)
            elif iss:
                stub.append(i)
            elif isf:
                fake.append(i)

        return {"required": req, "stubbed": stub, "faked": fake, "both": both}

    pdb = dict()
    for a in applist:
        pdb[a] = _used_by_app(a)

    req  = []
    stub = []
    fake = []
    both = []

    for i in range(0, MAX_SYSCALL + 1):
        isr = None
        iss = None
        isf = None
        isb = None

        for a in applist:
            if (i in pdb[a]["both"]):
                if (iss is not None or isf is not None):
                    continue
                isr = False
                iss = True
                isf = True
                isb = True
            elif (i in pdb[a]["stubbed"]):
                # can be stubbed
                isf = False
                isb = False
                if (iss is not None):
                    continue
                isr = False
                iss = True
            elif (i in pdb[a]["faked"]):
                # can be faked
                iss = False
                isb = False
                if (isf is not None):
                    continue
                isr = False
                isf = True
            elif (i in pdb[a]["required"]):
                # required
                isr = True
                iss = False
                isf = False
                isb = False
                break

        if isr:
            req.append(i)
        elif isb:
            both.append(i)
        elif iss:
            stub.append(i)
        elif isf:
            fake.append(i)

    return {"required": req, "stubbed": stub, "faked": fake, "both": both}

def container_exists(name):
    runcmd = ["docker", "images"]
    out = subprocess.check_output(runcmd).decode('utf-8')
    return re.search("^%s" % name, out, re.MULTILINE) is not None

def remove_container(name):
    info("Removing stale container...")
    runcmd = ["docker", "container", "rm", name]
    process = subprocess.Popen(runcmd)
    process.wait()

def run_tests(path_db, application, workload, path_dockerfile):
    info("Checking database...")
    if not db_check(path_db):
        error("Problem with the database, exiting.")
        return False

    info("Building container...")
    if not path_dockerfile.exists():
        error("Dockerfile %s does not exist" % str(path_dockerfile))
        return False

    containername = "%s-loupe" % application

    # build container in /tmp to at least any reference to a local directory
    # that could be needed
    tmpbuild = get_temp_dir()
    shutil.copyfile(path_dockerfile, os.path.join(tmpbuild, "Dockerfile.%s" % application))
    if (pathlib.Path("./dockerfile_data").exists()):
        shutil.copytree("./dockerfile_data", os.path.join(tmpbuild, "dockerfile_data"))

    cwd = os.getcwd()
    os.chdir(tmpbuild)
    runcmd = ["docker", "build", "--tag", containername, "-f", str(path_dockerfile), "."]
    process = subprocess.Popen(runcmd)

    process.wait()
    os.chdir(cwd)

    ret = process.returncode
    if (ret != 0):
        error("Problem building the container? Error code %d" % ret)
        return False

    if (not container_exists(containername)):
        error("Problem building the container?")
        return False

    info("Running container...")

    runcmd = ["docker", "container", "run", "--rm", "--privileged", containername]
    out = ""
    try:
        out = subprocess.check_output(runcmd).decode('utf-8')
    except subprocess.CalledProcessError as e:
        out  = str(e.output)

    # sanitize a bit, make sure that the output is sane
    info("Sanitizing output...")
    l = 0
    for line in out.splitlines():
        if (len(re.sub("[^,]", "", line)) != 4):
            error("Line %d of the test output seems corrupted. Dumping." % l)
            print(out)
            return False
        l += 1
    if (l != MAX_SYSCALL + 2):
        error("Somehow this file does not have the right size... " +
              "Expected %d lines, got %d. Dumping." % (MAX_SYSCALL, l))
        print(out)
        return False

    # write to the db
    info("Writing to the database...")
    hashdf = ""
    with open(path_dockerfile, "rb") as df:
        data = df.read()
        hashdf = hashlib.md5(data).hexdigest()

    runpath = os.path.join(path_db, application, workload, hashdf)
    if not os.path.exists(runpath):
        os.makedirs(runpath)
    if not os.path.exists(os.path.join(runpath, "data")):
        os.makedirs(os.path.join(runpath, "data"))
    shutil.copyfile(path_dockerfile, os.path.join(runpath, "Dockerfile.%s" % application))
    if (pathlib.Path("./dockerfile_data").exists()):
        shutil.copytree("./dockerfile_data", os.path.join(runpath, "dockerfile_data"))
    with open(os.path.join(runpath, "data", "dyn.csv"), "a+") as outf:
        outf.write(out)

    info("Done!")
    print(" -- Make sure to commit the changes to the database :-)")

    return True

def support_plan(applist, supported):
    print("Step by step support plan:")
    if applist == "*":
        applist = db.keys()

    per_app_syscalls = {}
    for app in applist:
        per_app_syscalls[app] = {}
        per_app_syscalls[app]["required"] = used_by_apps(db, [app], benchmark, testsuite)["required"]
        per_app_syscalls[app]["faked"] = used_by_apps(db, [app], benchmark, testsuite)["faked"]
        per_app_syscalls[app]["stubbed"] = used_by_apps(db, [app], benchmark, testsuite)["stubbed"]
        per_app_syscalls[app]["both"] = used_by_apps(db, [app], benchmark, testsuite)["both"]

    already_supported = []
    for app in per_app_syscalls:
        if set(per_app_syscalls[app]["required"]).issubset(supported):
            already_supported.append(app)
    if already_supported:
        print("- Supported without changes: ", end="")
        print(already_supported)
        for app in already_supported:
            per_app_syscalls.pop(app)

    step = 1
    while per_app_syscalls:
        next_app = list(per_app_syscalls.keys())[0]
        next_app_impl = set(per_app_syscalls[next_app]["required"]).difference(set(supported))
        for app in per_app_syscalls:
            impl_required = set(per_app_syscalls[app]["required"]).difference(set(supported))
            if len(impl_required) < len(next_app_impl):
                next_app = app
                next_app_impl = impl_required

        stub_needed = (set(per_app_syscalls[next_app]["stubbed"])\
                .union(set(per_app_syscalls[next_app]["both"]))).difference(set(supported))
        fake_needed = set(per_app_syscalls[next_app]["faked"]).difference(set(supported))
        print("- Step " + str(step) + " - to support " + next_app)
        if next_app_impl:
            print("  - implement " + str(next_app_impl))
        if stub_needed:
            print("  - stub " + str(stub_needed))
        if fake_needed:
            print("  - fake " + str(fake_needed))
        supported = supported.union(next_app_impl)
        del per_app_syscalls[next_app]
        step += 1


# parse arguments and launch the right option
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='cmd')
parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
        help="enable debug output")
parser.add_argument("-q", "--quiet", action="store_true", dest="quiet",
        help="disable any non-error output")

run_parser = subparsers.add_parser("generate",
        help="run system call usage analysis for an application")

run_parse_req_args = run_parser.add_argument_group('required arguments')
run_parse_req_args.add_argument("-db", "--database", dest="dbpath", type=pathlib.Path, required=True,
        help="path to the database")
run_parse_req_args.add_argument("-a", "--application-name", type=str, required=True,
        help="name of the application to be analyzed (e.g., nginx)", dest="application")
run_parse_req_args.add_argument("-w", "--workload-name", type=str, required=True,
        help="name of the workload (e.g., wrk)", dest="workload")
run_parse_req_args.add_argument("-d", "--dockerfile", type=pathlib.Path, required=True,
        help="path to the dockerfile that performs the analysis")

run_parse_other_args = run_parser.add_argument_group('classifier arguments')
run_parse_other_args.add_argument("-b", action="store_true", dest="isbenchmark",
        help="consider this workload as a benchmark")
run_parse_other_args.add_argument("-s", action="store_true", dest="issuite",
        help="consider this workload as a testsuite")

search_parser = subparsers.add_parser("search",
        help="retrieve and analyze data from the database")

required_args = search_parser.add_argument_group('required arguments')
required_args.add_argument("-db", "--database", dest="dbpath", type=pathlib.Path, required=True,
        help="path to the database")
required_args.add_argument("-a", "--applications", dest="applist", type=str, required=True,
        help="comma-separated list of apps to consider, e.g., 'redis,nginx', '*' for all")
required_args.add_argument("-w", "--workloads", dest="wllist", type=str, required=True,
        help="comma-separated list of workloads to consider, e.g., 'bench,suite', '*' for all")

action_args = search_parser.add_argument_group('action arguments')
action_args.add_argument("--show-usage", dest="showusage", action="store_true",
        help="output a list of required/stubbed/faked system calls for this set")
action_args.add_argument("--guide-support", dest="supportfile", type=pathlib.Path,
        help="given the path to a newline separated file of supported system calls, " +
        "output the remaining system calls to implement to support this set")
action_args.add_argument("--cumulative-plot", action="store_true", dest="cumulativeplot",
        help="output a cumulative support plot for this set")
action_args.add_argument("--heatmap-plot", action="store_true",
        help="output a heatmap support plot for this set")
action_args.add_argument("--export-sqlite", action="store_true",
        help="export the DB as SQLite database")

opt_args = search_parser.add_argument_group('optional arguments')
opt_args.add_argument("--static-binary", action="store_true",
        help="also include static binary analysis data", dest="sbinary")
opt_args.add_argument("--static-source", action="store_true",
        help="also include static source analysis data", dest="ssource")
opt_args.add_argument("--output-sys-names", action="store_true", dest="outputnames",
        help="output system call names instead of numbers")

args = parser.parse_args()

common.ENABLE_VERBOSE = (args.verbose is True)
common.ENABLE_QUIET = (args.quiet is True)

if (args.cmd is None):
    parser.print_help()

if (args.cmd == "search"):
    common.OUTPUT_NAMES = (args.outputnames is True)
    if args.sbinary is True or args.ssource is True:
        warning("Not implemented yet.")
        exit(0)

    usage = []

    if (args.showusage is True or
       args.cumulativeplot is True or
       args.supportfile is not None):
        db = db_load(args.dbpath)

        benchmark = False
        testsuite = False
        if "*" in args.wllist and len(args.wllist) > 1:
            warning("* in the workload list but other entries are specified: " + str(args.wllist))
            warning("Ignoring them.")
            benchmark = True
            testsuite = True
        elif "*" in args.wllist:
            benchmark = True
            testsuite = True
        elif "benchmark" in args.wllist or "bench" in args.wllist:
            benchmark = True
        elif "testsuite" in args.wllist or "suite" in args.wllist:
            testsuite = True

        usage = used_by_apps(db, args.applist.split(","), bench=benchmark, suite=testsuite)

    if (args.showusage is True):
        print("Required:")
        print(format_syscall_list(usage["required"]))
        print("Can be stubbed:")
        print(format_syscall_list(usage["stubbed"]))
        print("Can be faked:")
        print(format_syscall_list(usage["faked"]))
        print("Can be both stubbed or faked:")
        print(format_syscall_list(usage["both"]))
    elif (args.cumulativeplot is True):
        # build plot container
        info("Building plot container")
        runcmd = ["docker", "build", "--tag", "loupe-plot", "-f", "docker/Dockerfile.loupe-plot", "."]
        process = subprocess.Popen(runcmd)
        process.wait()

        # process data
        info("Processing data")
        cumulative = process_cumulative(db, args.applist.split(","), bench=benchmark, suite=testsuite)

        # generate data.dat
        req = "# x\tdyn-req\n" + "\n".join(["%s\t%s" % (k,v) for (k,v) in cumulative[0].items()])
        exe = "# x\tdyn-exe\n" + "\n".join(["%s\t%s" % (k,v) for (k,v) in cumulative[1].items()])
        with open(os.path.join("./data.dat"), "a") as outf:
            outf.write(exe)
            outf.write("\n\n\n")
            outf.write(req)

        info("Building plot")
        cwd = os.getcwd()
        runcmd = ["docker", "run", "-it", "--rm", "-v", cwd+ ":/mnt", "loupe-plot", "gnuplot", "/mnt/resources/cumulative-plot.gnu"]
        print(" ".join(runcmd))
        process = subprocess.Popen(runcmd)
        process.wait()

        # remove data file
        #os.remove("./data.dat")

        # notify user
        print("Plot: ./cumulative-plot.svg")
    elif args.supportfile is not None:
        supported = set(format_syscall_list(open_syscall_file(args.supportfile)))
        required  = set(format_syscall_list(usage["required"]))
        stubbed   = set(format_syscall_list(usage["stubbed"]))
        faked     = set(format_syscall_list(usage["faked"]))
        print("Missing a full implementation:")
        print(list(required.difference(supported)))
        print("Missing a stub:")
        print(list(stubbed.difference(supported)))
        print("Missing a fake:")
        print(list(faked.difference(supported)))

        support_plan(args.applist, supported)

    else:
        warning("Not implemented yet.")
        exit(0)

if (args.cmd == "generate"):
    wl = args.workload
    if (args.isbenchmark is True) and (args.issuite is True):
        error("Workload cannot be both a benchmark (-b) and a test suite (-s)")
        exit(1)
    elif (args.isbenchmark is True):
        wl = "benchmark-" + wl
    elif (args.issuite is True):
        wl = "suite-" + wl
    else:
        ans = str(input("Is this workload a benchmark or a testsuite? [bench/suite] "))
        if ans.lower() == "b" or ans.lower() == "benchmark" or ans.lower() == "bench":
            wl = "benchmark-" + wl
        elif ans.lower() == "s" or ans.lower() == "testsuite" or ans.lower() == "suite":
            wl = "suite-" + wl
        else:
            error("Cannot understand that answer ('%s')." % ans)
            exit(1)

    ex = run_tests(args.dbpath, args.application, wl, args.dockerfile)
    if not ex:
        exit(1)
    exit(0)
