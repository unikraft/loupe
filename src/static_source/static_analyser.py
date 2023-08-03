#!/usr/bin/python3

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

"""
Main file of the program.

Parses the input, calls the elf and code analyser and prints the results.
"""

import sys
import argparse
import lief

import utils
from syscalls import get_inverse_syscalls_map, syscalls_map
from code_analyser import CodeAnalyser
from elf_analyser import get_syscalls_from_symbols, is_valid_binary
from custom_exception import StaticAnalyserException

CSV = "data.csv"

def main():
    """Parse the arguments, starts the analysis and print the results"""

    parser = argparse.ArgumentParser()
    parser.add_argument('--app','-a', help='Path to application',required=True,
                        default=utils.app)
    parser.add_argument('--verbose', '-v', type=utils.str2bool, nargs='?',
                        const=True, help='Verbose mode', default=True)
    parser.add_argument('--display', '-d', type=utils.str2bool, nargs='?',
                        const=True, help='Display syscalls', default=True)
    parser.add_argument('--csv', '-c', type=utils.str2bool, nargs='?',
                        const=True, help='Output csv', default=True)
    parser.add_argument('--log', '-l', type=utils.str2bool, nargs='?',
                        const=True, help='Log mode', default=False)
    parser.add_argument('--log-to-stdout', '-L', type=utils.str2bool,
                        nargs='?', const=True, help='Print logs to the '
                        'standard output', default=False)
    parser.add_argument('--max-backtrack-insns', '-B', type=int, nargs='?',
                        const=True, help='Maximum number of instructions to '
                        'check before a syscall instruction to find its id',
                        default=20)
    parser.add_argument('--skip-data', '-s', type=utils.str2bool, nargs='?',
                        const=True, help='Automatically skip data in code and '
                        'try to find the next instruction (may lead to '
                        'errors)', default=False)
    args = parser.parse_args()

    utils.verbose = args.verbose
    utils.app = args.app
    utils.use_log_file = not args.log_to_stdout
    utils.logging = args.log if args.log_to_stdout is False else True
    if utils.logging and utils.use_log_file:
        utils.clean_logs()
    utils.skip_data = args.skip_data
    utils.max_backtrack_insns = args.max_backtrack_insns

    try:
        binary = lief.parse(utils.app)
        if not is_valid_binary(binary):
            raise StaticAnalyserException("The given binary is not a CLASS64 "
                                          "ELF file.")

        utils.print_verbose("Analysing the ELF file. This may take some "
                            "times...")

        syscalls_set = set()
        get_syscalls_from_symbols(binary, syscalls_set)

        code_analyser = CodeAnalyser(utils.app)

        inv_syscalls_map = get_inverse_syscalls_map()
        code_analyser.get_used_syscalls_text_section(syscalls_set,
                                                     inv_syscalls_map)
    except StaticAnalyserException as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(1)

    if args.display:
        for k,v in syscalls_map.items():
            if k in syscalls_set:
                print(f"{k} : {v}")

    utils.print_verbose("Total number of syscalls: " + str(len(syscalls_set)))

    if args.csv:
        print("# syscall, used")
        for k,v in syscalls_map.items():
            value = "N"
            if k in syscalls_set:
                value = "Y"
            print(f"{v},{value}")

if __name__== "__main__":
    main()
