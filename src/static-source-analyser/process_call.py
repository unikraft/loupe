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

"""Processes the call graph to detect system calls (covered or not if asked)."""

import fileinput
from io import StringIO
import os
import re
import subprocess
from syscalls_list import *
from utility import *

# Add callee to database
def build_callee_info(function_db):
    for call, value in function_db.items():
        for callee in value["calls"]:
            if callee in function_db and \
               call not in function_db[callee]["callee_calls"]:
                function_db[callee]["callee_calls"][call] = 1

        for callee in value["refs"]:
            if callee in function_db and \
               call not in function_db[callee]["callee_refs"]:
                function_db[callee]["callee_refs"][call] = 1

def dump_path_ascii(str_graph, covFolder, path, reverse, **kwargs):
    externs = kwargs.get("externs", False)
    truncated = kwargs.get("truncated", False)
    std_buf = kwargs.get("stdio_buffer", None)
    isSyscall = False

    if len(path) == 0:
        return

    ascii_path = ""
    style = "\n"
    for function in reversed(path) if reverse else path:

        # Update the name if we have an aliases syscall
        if function.startswith("*"):
            if function.lstrip("*") in alias_syscalls_list:
                function = alias_syscalls_list[function.lstrip("*")]

        if function in covFolder.covFct and function not in syscall_list:
            style +=  '"' + function + '"' + " [color=green, style=filled];"
        elif function not in covFolder.covFct and function not in covFolder.notCovFct and function not in syscall_list:
            style +=  '"' + function + '"' + " [color=orange, style=filled];"
        elif function not in covFolder.covFct and function not in syscall_list:
            style +=  '"' + function + '"' + " [color=red, style=filled];"

        if ascii_path != "":
            ascii_path += " -> "
        ascii_path += '"' + function + '"'#  + style

    '''
    if truncated or externs or isSyscall:
        ascii_path += ';\n"{}"{}{}'. \
                      format(function if not reverse else path[-1],
                             " [style=dashed]" if externs else "",
                             " [style=dashed]" if truncated else "")
    '''

    print_buf(str_graph, std_buf, ascii_path + ";" + style)

# Dump path as ASCII to stdout
def dump_path(str_graph, covFolder, path, functions, function_name, **kwargs):

    max_depth = kwargs.get("max_depth", 0)
    reverse_path = kwargs.get("reverse_path", False)
    exclude = kwargs.get("exclude", None)
    call_index = kwargs.get("call_index", "calls")
    no_externs = kwargs.get("no_externs", False)
    std_buf = kwargs.get("stdio_buffer", None)

    # Pass on __seen_in_path as a way to determine if a node in the graph
    # was already processed
    if "__seen_in_path" in kwargs:
        seen_in_path = kwargs["__seen_in_path"]
    else:
        seen_in_path = dict()
        kwargs["__seen_in_path"] = seen_in_path

    # If reached the max depth or need to stop due to exclusion, recursion
    # display the path up till the previous entry.
    if (exclude is not None and re.match(exclude, function_name) is not None) \
       or (max_depth > 0 and len(path) >= max_depth):
        dump_path_ascii(str_graph, covFolder, path, reverse_path, stdio_buffer=std_buf,
                        truncated=True)
        return

    # If already seen, we need to terminate the path here...
    if function_name in seen_in_path:
        if (max_depth <= 0 or (len(path) + 1) <= max_depth):
            dump_path_ascii(str_graph, covFolder, path + [function_name], reverse_path,
                            stdio_buffer=std_buf)
        return

    seen_in_path[function_name] = True

    # Now walk the path for each child
    children = 0
    for caller in functions[function_name][call_index]:
        # The child is a known function, handle this trough recursion
        if caller in functions:
            children += 1
            if function_name != caller:
                dump_path(str_graph, covFolder, path + [function_name],
                          functions, caller, **kwargs)
            else:
                # This is a recurrence for this function, add it once
                dump_path_ascii(str_graph, covFolder, path + [function_name, caller], reverse_path,
                                stdio_buffer=std_buf)

        # This is a external child, so we can not handle this recursive.
        # However as there are no more children, we can handle it here
        # (if it can be included).
        elif (exclude is None or re.match(exclude, caller) is None) and \
             (max_depth <= 0 or (len(path) + 2) <= max_depth) and \
                not no_externs:
            children += 1
            dump_path_ascii(str_graph, covFolder, path + [function_name, caller], reverse_path,
                            externs=True, stdio_buffer=std_buf)
        else:
            print_buf(str_graph, std_buf, '"{}" [color=blue];'.
                      format(function_name))

    # If there where no children, the path ends here, so dump it.
    if children == 0:
        dump_path_ascii(str_graph, covFolder, path + [function_name], reverse_path,
                        stdio_buffer=std_buf)

#
# Dump function details:
#
def dump_function_info(functions, function, details):
    finfo = functions[function]
    print("  {}() {}".format(function,
          finfo["files"] if details else ""))
    if details:
        for caller in sorted(finfo["calls"].keys()):
            print("    --> {}".format(caller))

        if len(finfo["calls"]) > 0 and len(finfo["callee_calls"]) > 0:
            print("    ===")

        for caller in sorted(finfo["callee_calls"].keys()):
            print("    <-- {}".format(caller))

        print("\n")

#
# Build full call graph
#
def full_call_graph(functions, **kwargs):
    exclude = kwargs.get("exclude", None)
    no_externs = kwargs.get("no_externs", False)
    std_buf = kwargs.get("stdio_buffer", None)

    print_buf(std_buf, "strict digraph callgraph {")
    # Simply walk all nodes and print the callers
    for func in sorted(functions.keys()):
        printed_functions = 0
        if exclude is None or \
           re.match(exclude, func) is None:

            for caller in sorted(functions[func]["calls"].keys()):
                if (not no_externs or caller in functions) and \
                   (exclude is None or
                   re.match(exclude, caller) is None):

                    print_buf(std_buf, '"{}" -> "{}";'.format(func, caller))

                    if caller not in functions:
                        print_buf(std_buf, '"{}" [style=dashed]'.
                                  format(caller))

                    printed_functions += 1

            if printed_functions == 0:
                print_buf(std_buf, '"{}"'.format(func))

    print_buf(std_buf, "}")

def filter_name(name):

    # Some syscalls are aliases by glibc
    if name.startswith("*"):
        name = name.lstrip("*")
        name = re.sub("^_+GI_+", '', name)

    if name.startswith("_"):
        name = re.sub('^_+','',name)

    if name in alias_syscalls_list:
        name = alias_syscalls_list[name]

    return name

'''
Example:
    asm volatile
    9   │     (
    10   │         "int $0x80" or "syscall"
    11   │         : "=a" (ret)
    12   │         : "0"(__NR_fork), "b"(fd), "c"(buf), "d"(size)
    13   │         : "memory"    // the kernel dereferences pointer args
    14   │     );
'''
def processInlineAsmSyscall(content, line):
    split_text = line.strip().split(":")
    if len(split_text) == 2:
        register = split_text[1].replace(")", "")
        for i, c in enumerate(content):
            if "reg:"+ register in c:
                split_text = content[i+1].strip().split(" ")
                if len(split_text) > 2:
                    try:
                        syscall_number = int(split_text[1])
                        return (list(syscall_list)[syscall_number])
                    except:
                        print_err("Unknown inline assembly syscall number for " + line)
                        return None
                break;
    return None
    
# Example: syscall(SYS_write,1,"Hello world\n", 12)
def processDirectSyscall(content, line):
    regex = re.compile(r"^.*\(symbol_ref:(?P<reg>[A-Z]{2}).*$")
    match = re.match(regex, line)
    if match:
        register = match.group("reg")
        i = 0
        for c in content:
            if "reg:"+ register in c and "call_insn" not in c:
                split_text = content[i-1].strip().split(" ")
                if len(split_text) > 2:
                    try:
                        syscall_number = int(split_text[1])
                        return (list(syscall_list)[syscall_number])
                    except:
                        print_err("Unknown inline assembly syscall number for " + line)
                        return None
                break

            i = i + 1

    return None

def createGraph(gObj, covFolder, args):

    # Regex to extract functions
    function = re.compile(
        r"^;; Function (?P<mangle>.*)\s+\((?P<function>\S+)(,.*)?\).*$")
    call = re.compile(
        r"^.*\(call.*\"(?P<target>.*)\".*$")
    symbol_ref = re.compile(r"^.*\(symbol_ref.*\"(?P<target>.*)\".*$")

    # Parse each line in each file given
    function_name = ""

    # Used to parse inline asm syscall
    asm=False

    content = list()
    for line in fileinput.input(gObj.pathList):
        # Find function entry point
        match = re.match(function, line)
        content.append(line)
        if match is not None:
            content = list()
            function_name = match.group("function")
            function_name = filter_name(function_name)

            if function_name in syscall_list:
                covFolder.allSyscalls.add(function_name)

            addTograph(gObj, function_name, fileinput.filename())

            gObj.functions[function_name]["files"].append(fileinput.filename())
        # Find direct function calls
        else:
            match = re.match(call, line)
            if match is not None:
                target = match.group("target")
                target = filter_name(target)

                # Direct syscall
                if  "syscall" in target.lower():
                    syscall = processDirectSyscall(list(reversed(content)), line)
                    if syscall is not None:
                        target = syscall

                if target in syscall_list:
                    covFolder.allSyscalls.add(target)
                    addTograph(gObj, target, fileinput.filename())

                    gObj.functions[target]["files"].append(fileinput.filename())

                if target not in gObj.functions[function_name]["calls"]:
                    gObj.functions[function_name]["calls"][target] = True
            else:
                match = re.match(symbol_ref, line)
                if match is not None:
                    target = match.group("target")
                    if target not in gObj.functions[function_name]["refs"]:
                        gObj.functions[function_name]["refs"][target] = True

        # Check assembly inline syscall
        if asm:
            syscall = processInlineAsmSyscall(content, line)
            if syscall is not None and syscall in syscall_list:
                gObj.systemCalls.add(syscall)
                addTograph(gObj, syscall, fileinput.filename())
                if syscall not in gObj.functions[function_name]["calls"]:
                    gObj.functions[function_name]["calls"][syscall] = True
            asm=False

        if "asm_operands" in line and ("int $0x80" in line or "syscall" in line or "SYSCALL" in line or "sysenter" in line or "SYSENTER" in line):
            asm=True

    # Build callee data
    build_callee_info(gObj.functions)

    # Create results folders
    if gObj.outDotFolder != None and gObj.outPdfFolder != None:
        createFolder(gObj.outDotFolder)
        createFolder(gObj.outPdfFolder)

def addTograph(gObj, function_name, filename=""):
    if function_name in gObj.functions:
        print_warn("Function {} defined in multiple files \"{}\"!".format(function_name,', '.join(map(str,gObj.functions[function_name]["files"] +[filename]))))
    else:
        gObj.functions[function_name] = dict()
        gObj.functions[function_name]["files"] = list()
        gObj.functions[function_name]["calls"] = dict()
        gObj.functions[function_name]["refs"] = dict()
        gObj.functions[function_name]["callee_calls"] = dict()
        gObj.functions[function_name]["callee_refs"] = dict()
        
def getExcludeRegex(args):
    if args.exclude is not None:
        try:
            exclude_regex = re.compile(args.exclude)
            return exclude_regex
        except Exception as e:
            print_err("ERROR: Invalid --exclude regular expression: \"{}\" -> \"{}\"!".format(args.exclude, e))
            return None
    return None

def buildAll(gObj, args):
    full_call_graph(gObj.functions, exclude=getExcludeRegex(args), no_externs=args.no_externs)

def buildCaller(gObj, covFolder, caller_lst, args, isCovered=False):
    
    for caller in caller_lst:
        if caller not in gObj.functions:
            print_warn("Can't find caller \"{}\" in RTL data!".format(caller))
            return 1

    str_graph = StringIO()
    str_graph.write("strict digraph callgraph {" + "\n")
    for caller in caller_lst:
        str_graph.write('"{}" [color=blue, style=filled];'.format(caller) + "\n")
        dump_path(str_graph, covFolder, [], gObj.functions, caller, max_depth=args.max_depth, exclude=getExcludeRegex(args), no_externs=args.no_externs)
    str_graph.write("}" + "\n")

    value = str_graph.getvalue()

    if args.generateDot and not isCovered:
        dotFile = os.path.join(gObj.outDotFolder, caller_lst[0] + ".dot")
        with open(dotFile, 'w') as f:
            f.write(value)

        if args.generatePdf:
            os.system('dot ' + dotFile + ' -Grankdir=LR -Tpdf -o ' + os.path.join(gObj.outPdfFolder, caller_lst[0] +'.pdf'))

def process_neighbour(line, covFolder):
    line = line.replace("\"", "")
    split_line = line.split("->")
    syscall = split_line[-1].strip().replace(";", "")
    fct = split_line[-2].strip()

    if ";" in fct:
        fct = fct[fct.find(";")+1:]
    if fct in covFolder.covFct:
        covFolder.covSyscalls.add(syscall)
        covFolder.syscallsNeighboursCov[syscall].add(fct)
    else:
        covFolder.syscallsNeighboursNotCov[syscall].add(fct)

def buildCallee(gObj, covFolder, callee_lst, args):

    for callee in callee_lst:
        if callee not in gObj.functions:
            print_warn("Can't find callee \"{}\" in RTL data!".format(callee))
            return 1

    str_graph = StringIO()
    str_graph.write("strict digraph callgraph {" + "\n")
    for callee in callee_lst:
        str_graph.write('"{}" [color=blue, style=filled];'.format(callee))
        dump_path(str_graph, covFolder, [], gObj.functions, callee, max_depth=args.max_depth, reverse_path=True, exclude=getExcludeRegex(args), call_index="callee_calls")
    str_graph.write("}" + "\n")

    value = str_graph.getvalue()

    regex = r".*-> \""+  callee_lst[0] + "\";"
    match = re.findall(regex, value)
    if match is not None:
        for m in match:
            process_neighbour(m, covFolder)

    if gObj.outDotFolder != None:
        dotFile = os.path.join(gObj.outDotFolder, callee_lst[0] + ".dot")

        if args.generatePdf:
            with open(dotFile, 'w') as f:
                f.write(value)
            
            try:
                subprocess.call('dot ' + dotFile + ' -Grankdir=LR -Tpdf -o ' + os.path.join(gObj.outPdfFolder, callee_lst[0] +'.pdf'), timeout=10, shell=True)
            except subprocess.TimeoutExpired:
                print_warn("60sec timer expired for " + dotFile)