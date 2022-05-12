#!/usr/bin/python3

import sys
import glob
import csv
import re
import matplotlib.pyplot as plt

plt.rc('font', size=13)

NR_SYSCALLS=334

# How many apps we have data for suite/bench in stub/fake mode
SUITE_APPS=5
BENCH_APPS=8

# Syscalls missing to achieve full compat, order is@
# zephyr, unikraft, graphene, gvisor, hermitux, osv
missing_suite = [129, 65, 34, 3, 90, 77]
missing_bench = [32, 18, 3, 0, 12, 12]
implemented_suite = [42, 106, 137, 168, 81, 94]
implemented_bench = [23, 37, 52, 55, 43, 43]

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
def compute_score(workload, analysis, osdata, usagedata, print_missing,
        print_implemented):

    res = {}

    # compute score for each OS
    for os in osdata:
        score = 0
        for syscall in range(0, 335):
            if osdata[os][syscall]:
                gain = int(usagedata[workload][syscall][analysis])
                score += gain
                if print_implemented:
                    if gain:
                        print("- " + os + " implements syscall " + str(syscall) + \
                            " for " + workload + " " + analysis + " (+" + \
                            str(gain) +")")

            elif print_missing:
                gain = int(usagedata[workload][syscall][analysis])
                if gain:
                    print("- " + os + " is missing syscall " + str(syscall) + \
                            " for " + workload + " " + analysis + " (+" + \
                            str(gain) +")")

        res[os] = score

    # compute max score
    maxscore = 0
    for syscall in range(0, 335):
        syscall_score = int(usagedata[workload][syscall][analysis])
        maxscore += syscall_score

    res["full"] = maxscore

    return res

def plot_fig(data):
    fig, axs = plt.subplots(1, 2)
    fig.tight_layout()
    plt.subplots_adjust(left=0.1, bottom=0.2, right=None, top=0.9) #, wspace=4, hspace=0.6)

    keys = ["Zephyr", "Unikraft", "Graphene", "gVisor", "HermiTux", "OSv"]

    plot_data = dict(data)

    full_coverage = {}
    full_coverage["suite"] = plot_data["suite"]["dyn_stubfake"]["full"]
    full_coverage["bench"] = plot_data["bench"]["dyn_stubfake"]["full"]

    del plot_data["suite"]["dyn_stubfake"]["full"]
    del plot_data["bench"]["dyn_stubfake"]["full"]

    axs[0].set_title("Test suites (" + str(SUITE_APPS)  + " apps)")
    axs[0].set_ylabel("Compatibility score")
    axs[0].hlines(full_coverage["suite"], -1, 6, color="red")
    axs[0].bar(keys, plot_data["suite"]["dyn_stubfake"].values(), zorder=2)
#    for i in range(0, len(keys)):
#        axs[0].text(i, 15, str(-missing_suite[i]), color="white", ha='center')
#        axs[0].text(i, 35, str(implemented_suite[i]), color="white", ha='center')
    axs[0].tick_params(labelrotation=45)
    axs[0].text(-0.5, 390, "Full\ncompatibility", color="red")
    axs[0].grid(zorder=0)

    axs[1].set_title("Benchmarks (" + str(BENCH_APPS) + " apps)")
    axs[1].set_ylabel("Compatibility score")
    axs[1].hlines(full_coverage["bench"], -1, 6, color="red")
    axs[1].bar(keys, plot_data["bench"]["dyn_stubfake"].values(), zorder=2)
#    for i in range(0, len(keys)):
#        axs[1].text(i-0.25, 15, str(-missing_bench[i]), color="white")
#        axs[1].text(i-0.25, 35, str(implemented_bench[i]), color="white")
    axs[1].tick_params(labelrotation=45)
    axs[1].text(-0.5, 160, "Full compatibility", color="red")
    axs[1].grid(zorder=0)

    axs[0].set_ylim([0, 450])
    axs[1].set_ylim([0, 450])

    fig.set_size_inches(8, 4)
    plt.savefig("compatibility-score.pdf")

if __name__ == "__main__":
    print_missing = False
    print_implemented = False

    if len(sys.argv) == 2:
        if sys.argv[1] == "-m":
            print_missing = True
        elif sys.argv[1] == "-i":
            print_implemented = True

    # load os compatibility data
    os = load_os_compatibility_files()

    # load syscall popularity
    usage = load_syscall_usage()

    data = {}
    for workload in ["all", "suite", "bench"]:
        data[workload] = {}
        for analysis in ["staticbinary", "staticsource", "dyn_conservative", "dyn_stubfake"]:
            data[workload][analysis] = compute_score(workload, analysis, os, \
                    usage, print_missing, print_implemented)

    plot_fig(data)
