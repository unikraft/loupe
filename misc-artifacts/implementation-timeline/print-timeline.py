#!/usr/bin/python3

# SPDX-License-Identifier: BSD-3-Clause
#
# Authors: Pierre Olivier <pierre.olivier@manchester.ac.uk>
#
# Copyright (c) 2020-2023, The University of Manchester. All rights reserved.
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

import sys, csv, datetime, argparse

name_to_id = {}
id_to_name = {}

def load_data(csv_file):
    data = []
    with open(csv_file) as f:
        reader = csv.reader(f)
        for row in reader:
            data.append(row)

    res = {}
    res["fuchsia"] = {}
    res["kerla"] = {}
    res["hermitux"] = {}
    res["unikraft"] = {}

    for entry in data:
        try:
            number = int(entry[0])
            name = entry[1]

            id_to_name[number] = name
            name_to_id[name] = number

            if entry[2]:
                res["fuchsia"][name] = \
                        datetime.datetime.strptime(entry[2], '%a %b %d %H:%M:%S %Y %z')
            if entry[3]:
                res["kerla"][name] = \
                        datetime.datetime.strptime(entry[3], '%a %b %d %H:%M:%S %Y %z')
            if entry[4]:
                res["hermitux"][name] = \
                        datetime.datetime.strptime(entry[4], '%a %b %d %H:%M:%S %Y %z')
            if entry[5]:
                res["unikraft"][name] = \
                        datetime.datetime.strptime(entry[5], '%a %b %d %H:%M:%S %Y %z')

        except Exception as e:
            pass # headers, etc.

    return res


# Compute priority scores based on order of implementation
def get_scores_order(os_data):
    scores = {}
    total_syscalls = len(os_data)

    print("total: " + str(total_syscalls))

    syscall_list = sorted(os_data, key=os_data.get)
    for s in syscall_list:
        scores[s] = (syscall_list.index(s) * 100)/total_syscalls

    # Because of a first big commit with 40 syscalls implemented in fuchsia,
    # we can't go at a finer granularity than 0-25%
#     print("0-25%:")
    # for s in scores:
        # if scores[s] <= 25:
            # print(s + ", ", end="")
    # print()

    # print("25-50%:")
    # for s in scores:
        # if scores[s] > 25 and scores[s] <= 50:
            # print(s + ", ", end="")
    # print()

    # print("50-75%:")
    # for s in scores:
        # if scores[s] > 50 and scores[s] <= 75 :
            # print(s + ", ", end="")
    # print()

    # print("75-100%:")
    # for s in scores:
        # if scores[s] > 75 and scores[s] <= 100 :
            # print(s + ", ", end="")
    # print()


    return scores

# Compute priority scores based on time of implementation
def get_scores_in_time(os_data):
    scores = {}

    # compute total duration
    start = os_data[sorted(os_data, key=os_data.get)[0]]
    stop = os_data[sorted(os_data, key=os_data.get)[len(os_data)-1]]
    duration = stop-start

    duration_ts = duration.total_seconds()
    start_ts = start.timestamp()

    for s in os_data:
        scores[s] = ((os_data[s].timestamp() - start_ts) * 100)/duration_ts

#     print("0-10%:")
    # for s in scores:
        # if scores[s] <= 10:
            # print(s + ", ", end="")
    # print()

    # print("10-25%:")
    # for s in scores:
        # if scores[s] > 10 and scores[s] <= 25:
            # print(s + ", ", end="")
    # print()

    # print("25-50%:")
    # for s in scores:
        # if scores[s] > 25 and scores[s] <= 50:
            # print(s + ", ", end="")
    # print()

    # print("50-75%:")
    # for s in scores:
        # if scores[s] > 50 and scores[s] <= 75 :
            # print(s + ", ", end="")
    # print()

    # print("75-100%:")
    # for s in scores:
        # if scores[s] > 75 and scores[s] <= 100 :
            # print(s + ", ", end="")
    # print()

    return scores


def print_timeline(os_data, scores):

    last_date_printed = None
    for syscall in sorted(os_data, key=os_data.get):
        if last_date_printed == os_data[syscall]:
            print(", " + syscall + " (" + str("{:.2f}".format(scores[syscall])) + ")", end="")
        else:
            date = os_data[syscall]
            print(("\n" if last_date_printed else "") + str(date) + ": " + \
                    syscall + " (" + str("{:.2f}".format(scores[syscall])) + ")", end="")
            last_date_printed = date
    print()

def time_to_reach(os_data, syscall_num):
    syscall_list = sorted(os_data, key=os_data.get)

    start_date = os_data[syscall_list[0]]
    end_date = os_data[syscall_list[syscall_num-1]]

    # Iterate over the range of commits in question and check for periods of
    # inactivity ( 1 week+ between two subsequent commits touching
    # syscalls-related files

    inactivity = datetime.timedelta(0)
    last_commit_date = os_data[syscall_list[0]]
    for i in range(1, syscall_num):
        commit_delta = os_data[syscall_list[i]] - last_commit_date
        if commit_delta > datetime.timedelta(weeks=1):
            inactivity += (commit_delta - datetime.timedelta(weeks=1))
        last_commit_date = os_data[syscall_list[i]]

    return (end_date - start_date) - inactivity


if __name__ == "__main__":
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("usage: " + sys.argv[0] + " <google doc csv> [os]")
        sys.exit()

    data = load_data(sys.argv[1])
    scores = {}

    if len(sys.argv) == 3:
        os = sys.argv[2]
        scores[os] = get_scores_in_time(data[os])
        print_timeline(data[os], scores[os])
        print("total syscalls implemented: " + str(len(data[os])))
        for first in [10, 25, 50, 100]:
            if(first < len(data[os])):
                print("Time to implement the first " + str(first) + \
                        " syscalls:" + str(time_to_reach(data[os], first)))

    else:
        for os in data:
            print("----------- " + os + " below -----------")
            scores[os] = get_scores_in_time(data[os])
            print_timeline(data[os], scores[os])

