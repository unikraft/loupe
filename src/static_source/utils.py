# SPDX-License-Identifier: BSD-3-Clause
#
# Authors:  Gaulthier Gain <gaulthier.gain@uliege.be>
#           Benoit Knott <benoit.knott@student.uliege.be>
#
# Copyright (c) 2020-2023, University of Liège. All rights reserved.
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

"""Contains analysis global parameters and helper functions"""

import argparse

DEBUG = False
log_dir_path = "../logs/"

# global variables
# Beware that these may NOT be reflective of the default values. To modify the
# default value, look inside `static_analyser.py`
verbose = True
app = "redis-server-static"
use_log_file = True
logging = False
skip_data = False
max_backtrack_insns = 20
# For debug purpose
cur_depth = -1


def print_verbose(msg, indent=0):
    """Prints msg with the specified indentation into the standard output if
    verbose is True.

    Parameters
    ----------
    msg : str
        msg to print
    file_name : str
        name of the log file to add the message to
    indent: int
        number of tabs to add before the msg
    """
    if verbose:
        print(indent * "\t" + msg)

def print_debug(msg):
    """Used for debugging purposes only. Print debug messages"""

    if DEBUG:
        log(msg, "debug.log")

def log(msg, file_name, indent=0):
    """Logs msg with the specified indentation into the log file, or to the
    standard output if `use_log_file` is set to False.

    The msg is added at the end of the file.

    Parameters
    ----------
    msg : str
        msg to print
    file_name : str
        name of the log file to add the message to
    indent: int
        number of tabs to add before the msg
    """

    if not logging:
        return

    if use_log_file:
        with open(log_dir_path + file_name, "a", encoding="utf-8") as f:
            f.write(indent * " " + msg + "\n")
    else:
        print(indent * "\t" + msg)

def clean_logs():
    """Empties the content of the log files."""

    with open(log_dir_path + "backtrack.log", "w", encoding="utf-8") as f:
        f.truncate()
    with open(log_dir_path + "lib_functions.log", "w", encoding="utf-8") as f:
        f.truncate()
    if DEBUG:
        with open(log_dir_path + "debug.log", "w", encoding="utf-8") as f:
            f.truncate()

def is_hex(s):
    """Returns True if the given string represents an hexadecimal number.

    Parameters
    ----------
    s : str
        string to check

    Returns
    -------
    is_hex : bool
        True if `s` is an hexadecimal number
    """
    if not s or len(s) < 3:
        return False

    return s[:2] == "0x" and all(c.isdigit()
                                 or c.lower() in ('a', 'b', 'c', 'd', 'e', 'f')
                                 for c in s[2:])

def str2bool(v):
    """Returns the boolean value represented in the parameter given.

    Parameters
    ----------
    v : bool or str
        value representing a boolean value

    Raises
    ------
    arg_error : ArgumentTypeError
        If the given value does not correspond to a boolean

    Returns
    -------
    boolean : bool
        the boolean value that `v` represents
    """

    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    if v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    raise argparse.ArgumentTypeError('Boolean value expected.')

def f_name_from_path(path):
    """Returns the file name from a full path (after the last slash)

    Parameters
    ----------
    path: str
        unix-like path of a file
    """

    return path.split("/")[-1]
