#!/usr/bin/python3

import sys
import glob
import csv
import re
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import pprint

NR_SYSCALLS=334

def load_syscall_usage():
    usage = {}

    print("loading syscall usage data...")

    for workload in ["all", "suite", "bench"]:
        usage[workload] = []
        with open("generated-data/" + workload + ".csv") as f:
            reader =  csv.DictReader(f)
            for row in reader:
                del row["Syscall#"]
                usage[workload].append(row)

    return usage

def load_os_compatibility_files():
    os = {}

    print("loading os compatibility files...")

    os_comp_files = glob.glob("google-csvs/*.csv")
    for os_comp_file in os_comp_files:

        # Get OS name
        os_name = ""
        r = re.search("/(.*)\.csv", os_comp_file)
        if r:
            os_name = r.group(1)
        else:
            print("ERROR: can't get os name for " + os_comp_file + ", stopping")
            sys.exit(-1)

        os[os_name] = []
        for i in range(0, NR_SYSCALLS+1):
            os[os_name].append(False)
        with open(os_comp_file) as f:
            print(" - loading " + os_comp_file)
            reader =  csv.DictReader(f)
            for row in reader:
                status = row["Status"]
                if status == "Implemented" or status == "implemented" or \
                        status == "partially implemented" or \
                        status == "Stubbed" or status == "faked" or \
                        status == "stubbed":
                    os[os_name][int(row["Syscall N#"])] = True
                elif status == "not implemented" or status == "" or \
                        status == "Not implemented":
                    os[os_name][int(row["Syscall N#"])] = False
                else:
                    print("ERROR: cant understand status: \"" + status + "\"")
                    sys.exit(-1)
    return os

# workload = all/suite/bench
# analysis = staticbinary/staticsource/dyn_conservative/dyn_stubfake
def compute_score(workload, analysis, osdata, usagedata):

    res = {}

    # compute score for each OS
    for os in osdata:
        score = 0
        for syscall in range(0, 335):
            if osdata[os][syscall]:
                score += int(usagedata[workload][syscall][analysis])
        res[os] = score

    # compute max score
    maxscore = 0
    print("computing max score for " + workload + " " + analysis)
    for syscall in range(0, 335):
        syscall_score = int(usagedata[workload][syscall][analysis])
        if syscall_score:
            print(" - " + str(syscall) + ": " + str(syscall_score))
        maxscore += syscall_score

    res["full"] = maxscore

    return res

def plot_fig(data):
    fig, axs = plt.subplots(2, 4)
    fig.tight_layout()
    plt.subplots_adjust(left=0.1, bottom=None, right=None, top=0.9, wspace=0.3, hspace=0.4)

    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(data)

    keys = ["Z", "U", "G", "g", "H", "O", "F"]
    apps = {"suite": 5, "bench": 8}

    workloads = {0: "suite", 1: "bench"}
    analyses = {0: "staticbinary", 1: "staticsource", 2: \
                "dyn_conservative", 3: "dyn_stubfake"}

    plot_data = data.copy()
    for workload in workloads:
        for analysis in analyses:
            #full_compat = data[workloads[workload]][analyses[analysis]]["full"]

            #for os in plot_data[workloads[workload]][analyses[analysis]].keys():
            #    plot_data[workloads[workload]][analyses[analysis]][os] /= full_compat

            #del plot_data[workloads[workload]][analyses[analysis]]["full"]

            axs[workload, analysis].bar(keys, \
                plot_data[workloads[workload]][analyses[analysis]].values())

            axs[workload][analysis].set_title(workloads[workload] + \
                    " (" + str(apps[workloads[workload]]) + " apps)\n" + analyses[analysis])

            if analysis == 0:
                axs[workload][analysis].set_ylabel("Compatibility score")

            #axs[workload][analysis].yaxis.set_major_formatter(FormatStrFormatter('%.1f'))

#axs[workload, analysis].bar(data[workloads[workload]][analyses[analysis]].keys(), \
    plt.savefig("out.pdf")

if __name__ == "__main__":

    # load os compatibility data
    os = load_os_compatibility_files()

    # load syscall popularity
    usage = load_syscall_usage()

    data = {}
    for workload in ["all", "suite", "bench"]:
        data[workload] = {}
        for analysis in ["staticbinary", "staticsource", "dyn_conservative", "dyn_stubfake"]:
            data[workload][analysis] = compute_score(workload, analysis, os, usage)

    plot_fig(data)
