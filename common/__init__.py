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

import tempfile, os, sys, re

# =========
# CONSTANTS

SYSCALL_MAPPING_FILE = "/usr/include/x86_64-linux-gnu/asm/unistd_64.h"

# get it from /usr/include/x86_64-linux-gnu/asm/unistd_64.h
MAX_SYSCALL = 334

# =======
# HELPERS

ENABLE_VERBOSE = False
ENABLE_QUIET = False
OUTPUT_NAMES = False

def error(string):
    print("[E] " + string)

def warning(string):
    if not ENABLE_QUIET:
        print("[W] " + string)

def info(string):
    if not ENABLE_QUIET:
        print("[I] " + string)

def debug(string):
    if ENABLE_VERBOSE:
        print("[D] " + string)

def print_header(s):
    if not ENABLE_QUIET:
        print()
        print("-"*len(s))
        print(s)
        print("-"*len(s))
        print()

def get_sysnum_to_sysname():
    with open(SYSCALL_MAPPING_FILE) as headerf:
        header = headerf.read()
        regex = re.compile("#define __NR_([a-zA-Z1-9_]+)\s(\d+)")
        return dict([(s, int(n)) for (s, n) in regex.findall(header)])

syscall_mapping = get_sysnum_to_sysname()

def format_syscall_list_to_num(syscall_list):
    out = []
    for syscall in syscall_list:
        for (s,n) in syscall_mapping.items():
            if (s == syscall):
                out.append(n)
    return out

def format_syscall_list_to_names(syscall_list):
    out = []
    for syscall in syscall_list:
        for (s,n) in syscall_mapping.items():
            if (n == syscall):
                out.append(s)
    return out

def format_syscall_list(syscall_list):
    isn = True
    for e in syscall_list:
        if (not isinstance(e, int) and re.search('[a-zA-Z]', e)):
            isn = False

    if not OUTPUT_NAMES and isn:
        return syscall_list
    elif not OUTPUT_NAMES and not isn:
        return format_syscall_list_to_num(syscall_list)
    elif OUTPUT_NAMES and not isn:
        return syscall_list
    elif OUTPUT_NAMES and isn:
        return format_syscall_list_to_names(syscall_list)

def progress(count, total):
    if ENABLE_QUIET:
        return

    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s\r' % (bar, percents, '%'))
    sys.stdout.flush()

def progress_end():
    if not ENABLE_QUIET:
        print()

def get_temp_file():
    return os.path.join("/tmp", next(tempfile._get_candidate_names())) + ".log"

def get_temp_dir():
    d = os.path.join("/tmp", next(tempfile._get_candidate_names()))
    os.mkdir(d)
    return d
