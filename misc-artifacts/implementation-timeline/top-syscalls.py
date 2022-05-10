#!/usr/bin/python3

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

# syscalls present in ALL top-x
def get_top_all(data, top):
    res = []
    already_seen = []

    for os in data:
        for syscall in sorted(data[os], key=data[os].get)[0:top]:
            if syscall not in already_seen:
                already_seen.append(syscall)
                present = True
                for os2 in data:
                    if os2 != os and syscall not in sorted(data[os2], key=data[os2].get)[0:top]:
                        present = False
                        break
                if present:
                    res.append(syscall)
    return res


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: " + sys.argv[0] + " <google doc csv>")
        sys.exit()

    data = load_data(sys.argv[1])

    print("syscalls present in ALL top-x:")
    for top in [10, 25, 50, 100]:
        topdata = get_top_all(data, top)
        print("top " + str(top) + ": " + str(topdata) + " (total " + \
                str(len(topdata)) + ")")








