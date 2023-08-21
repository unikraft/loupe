#!/usr/bin/python3
# SPDX-License-Identifier: BSD-3-Clause
#
# Author:   Gaulthier Gain <gaulthier.gain@uliege.be>
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

"""Processes the source code of an application to detect syscalls via Clang AST."""

import getopt
import os
import sys
import json
import clang.cindex
import clang
import argparse
import platform
from utility import *
from clang.cindex import CursorKind
from collections import defaultdict

from syscalls_list import syscall_list, alias_syscalls_list

MAC_CLANG = "/Applications/Xcode.app/Contents/Frameworks/libclang.dylib"

verbose = False # Change it to verbose mode

global_funcs = defaultdict(list)
global_calls = defaultdict(list)

# Check if a path is a directory or a file
def check_input_path(path, includePaths):
    if os.path.isdir(path):
        iterate_root_folder(path, includePaths)
    elif os.path.isfile(path):
        check_type_file(path, includePaths)
    else:
        sys.stderr("[WARNING] Unable to analyse this file: " + path)

def get_include_paths(rootdir):
    subfolders = get_all_folders_and_subfolders(rootdir)
    paths = []
    for s in subfolders:
        path = '-isystem ' + s.replace('\n', '')
        paths.append(path)
    return ' '.join(paths)

# Check type/extension of a given file
def check_type_file(filepath, includePaths):
    cplusplusOptions = '-x c++ --std=c++11'
    cOptions = ''

    if includePaths is not None:
        cplusplusOptions = cplusplusOptions + ' ' + includePaths
        cOptions = cOptions + ' ' + includePaths

    if filepath.endswith(".cpp") or filepath.endswith(".hpp") or filepath.endswith(".cc"):
        parse_file(filepath, cplusplusOptions)
    elif filepath.endswith(".c") or filepath.endswith(".h") or filepath.endswith(".hh"):
        parse_file(filepath, cOptions)

# Iterate through a root folder
def iterate_root_folder(rootdir, includePaths):
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            filepath = subdir + os.sep + file
            check_type_file(filepath, includePaths)

# Print info about symbols (verbose mode)
def display_info_function(funcs, calls):
    for f in funcs:
        print(fully_qualified(f), f.location)
        for c in calls:
            if is_function_call(f, c):
                print('-', c.location)
        print()

# Parse a given file to generate a AST
def parse_file(filepath, arguments):
    print_verbose("Gathering symbols of " + filepath, verbose)
    idx = clang.cindex.Index.create()
    args = arguments.split()
    tu = idx.parse(filepath, args=args)
    funcs, calls = find_funcs_and_calls(tu)
    if verbose:
        display_info_function(funcs, calls)
        print(list(tu.diagnostics))


# Retrieve a fully qualified function name (with namespaces)
def fully_qualified(c):
    if c is None:
        return ''
    elif c.kind == CursorKind.TRANSLATION_UNIT:
        return ''
    else:
        res = fully_qualified(c.semantic_parent)
        if res != '':
            return res + '::' + c.spelling
    return c.spelling

# Determine where a call-expression cursor refers to a particular
# function declaration
def is_function_call(funcdecl, c):
    defn = c.get_definition()
    return (defn is not None) and (defn == funcdecl)

# Filter name to take only the function name (remove "(args)")
def filter_func_name(displayname):
    if "(" in displayname:
        return displayname.split('(')[0]
    return displayname

# Retrieve lists of function declarations and call expressions in a
#translation unit
def find_funcs_and_calls(tu):
    filename = tu.cursor.spelling
    calls = []
    funcs = []

    exception_file=None
    for c in tu.cursor.walk_preorder():
        try:
            exception_file=filename
            expr = c.kind
        except:
            print("[WARNING] Clang error when parsing: " + exception_file)
            continue

        if c.location.file is None:
            pass
        elif c.location.file.name != filename:
            pass
        elif expr == CursorKind.CALL_EXPR:
            calls.append(c)
            # filter name to take only the name if necessary
            funcName = filter_func_name(c.displayname)

            #increment counter
            if funcName not in global_calls:
                global_calls[funcName].append(1)
            else:
                global_calls[funcName][0] +=1

            #add path to file
            if c.location.file.name not in global_calls[funcName]:
                global_calls[funcName].append(c.location.file.name)

        elif expr == CursorKind.FUNCTION_DECL:
            funcs.append(c)
            # filter name to take only the name if necessary
            funcName = filter_func_name(c.displayname)
            
            #increment counter
            if funcName not in global_funcs:
                global_funcs[funcName].append(1)
            else:
                global_funcs[funcName][0] +=1

            #add path to file
            if c.location.file.name not in global_funcs[funcName]:
                global_funcs[funcName].append(c.location.file.name)

    return funcs, calls

# str2bool is used for boolean arguments parsing.
def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

# Write data to json file
def write_to_json(output_filename, data):
    with open(output_filename + '.json', 'w') as fp:
        json.dump(data, fp, indent=4, sort_keys=True)

# Read the list of syscalls (json file)
def read_syscalls_list(filename):
    with open(filename) as f:
        return json.load(f)

def get_all_folders_and_subfolders(folder_path):
    folder_list = []
    for root, dirs, files in os.walk(folder_path):
        for dir in dirs:
            folder_list.append(os.path.join(root, dir))
    return folder_list

# Check which syscall is a function
def compare_syscalls(syscalls):

    called_syscalls = defaultdict(list)
    define_syscalls = defaultdict(list)

    for key, value in global_calls.items():
        
        if key in syscalls or key in alias_syscalls_list:
            print_verbose(key,verbose)
            called_syscalls[key] = value

    for key, value in global_funcs.items():

        # Manual sanity check (glibc parsing limitation)
        if "main" == key:
            for x in ["access", "openat", "arch_prctl", "mprotect", "exit_group"]:
                define_syscalls[x] = value
        elif "pthread_create" == key:
            for x in ["rt_sigaction", "rt_sigprocmask", "clone", "set_tid_address", "set_robust_list", "prlimit64"]:
                define_syscalls[x] = value

        if key in syscalls or key in alias_syscalls_list:
            print_verbose(key,verbose)
            define_syscalls[key] = value

    return (called_syscalls, define_syscalls)

def process_source_code(folder, v):
    global verbose 
    verbose = v
    includePaths = get_include_paths(folder)
    check_input_path(folder, includePaths)

    output_dict = {
            'functions':'',
            'calls':'',
            'called_syscalls':'',
            'define_syscalls':'',
            'all_system_calls':''
        }
    output_dict['functions'] = [{'name':key, 'value':value} for key,value in global_funcs.items()]
    output_dict['calls'] = [{'name':key, 'value':value} for key,value in global_calls.items()]

    # Compare syscalls list with function declarations/calls
    (called_syscalls, define_syscalls) = compare_syscalls(syscall_list)
    output_dict['called_syscalls'] = called_syscalls
    output_dict['define_syscalls'] = define_syscalls
    output_dict['all_system_calls'] = called_syscalls | define_syscalls
    return output_dict

def main():
    global verbose

    parser = argparse.ArgumentParser()
    parser.add_argument('--folder','-f', help='Path to the folder (source files) of the application to analyse', required=True)
    parser.add_argument('--output', '-o', help='Path to the output resulting json file')
    parser.add_argument('--verbose', '-v', type=str2bool, 
                        nargs='?', const=True, default=False,
                        help='Verbose mode')
    parser.add_argument('--display', '-d', type=str2bool, 
                        nargs='?', const=True, default=False,
                        help='Display all syscalls')
    args = parser.parse_args()
    
    verbose = args.verbose
    output_dict = process_source_code(args.folder, args.verbose)
    if args.output is None:
        output_file = sys.stdout
    else:
        output_file = open(args.output, "w")
        
    if args.display:
        for s in output_dict['all_system_calls']:
            print(s)

    if verbose:
        json.dump(output_dict, output_file, sort_keys=True, indent=4)

if __name__== "__main__":
    if platform.system() == "Darwin":
        clang.cindex.Config.set_library_file(MAC_CLANG)
    else:
        filename="/usr/lib/x86_64-linux-gnu/libclang.so"
        if not os.path.isfile(filename):
            print_err("Cannot find {}. Please install clang shared library. See README.md for more information.".format(filename))

    main()