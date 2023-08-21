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

"""
Main file of the program.

Parses the source code of an app (via Clang and RTL representation) to detect system calls.
"""

import os
import re
import clang
import platform
import argparse
from bs4 import BeautifulSoup
from check_syscall import readCsvManual, COVERAGE_SUITE, COVERAGE_BENCHMARK
from classes import *
from output_html import *
from process_call import buildCallee, createGraph, buildCaller
from utility import *
from pathlib import Path
from parser_clang import process_source_code, MAC_CLANG

verbose = False

AGGREGATE_FILE  = "log_aggregated"

LINECOV         = "lineCov"
LINENOCOV       = "lineNoCov"
#
# Quick and Dirty parsing (since we have only line as html):
#
def search_function(line, cv):
    c_keyworks = ["if", "while", "switch", "for"]
    regex = r"(\w+)\s*\("
    matches = re.findall(regex, line)

    if len(matches) == 0:
        # No functions, no keywords
        return None
    elif len(matches) == 1:
        # Maybe either a function or a keywork
        if matches[0].replace(" ", "") in c_keyworks:
            # It is only a keyword so return
            print_verbose("[" + cv +"] Ignore: [" + matches[0].replace(" ", "") + "]\n-------", verbose)
            return None
        
        print_verbose("[" + cv +"] Take:   [" + matches[0].replace(" ", "") + "]\n-------", verbose)

        htmlLine = HtmlLine(line)
        htmlLine.fctList.append(matches[0].replace(" ", ""))
        return htmlLine
    elif len(matches) > 1:
        # Contains several possibilities (functions, keywords, ...)
        htmlLine = HtmlLine(line)
        for m in matches:
            m = m.replace(" ", "")
            if m in c_keyworks:
                print_verbose("[" + cv +"] Ignore: [" + m + "]", verbose)
            else:
                print_verbose("[" + cv +"] Take:   [" + m + "]\n-------", verbose)
                htmlLine.fctList.append(m)
        return htmlLine

def getHtmlLines(filename, covFolder):
    htmlFile = HtmlFile(filename)
    with open(htmlFile.filename, "r", encoding='utf-8') as f:
        text= f.read()
        htmlContent = BeautifulSoup(text, 'html.parser')

        for span in htmlContent.find_all("span", {"class": LINECOV}):
            htmlLine = search_function(span.get_text(), LINECOV)
            
            if htmlLine:
                htmlFile.linesCov.append(htmlLine)
                for fct in htmlLine.fctList:
                    if fct in syscall_list:
                        covFolder.allSyscalls.add(fct)
                        covFolder.covSyscalls.add(fct)
                    try:
                        covFolder.covFct[fct].add(filename + "#" + str(span.parent['name']))
                    except:
                        covFolder.covFct[fct].add(filename)             

        for span in htmlContent.find_all("span", {"class": LINENOCOV}):
            htmlLine = search_function(span.get_text(), LINENOCOV)
            if htmlLine:
                htmlFile.linesNotCov.append(htmlLine)
                for fct in htmlLine.fctList:
                    if fct in syscall_list:
                        # This contains temporary not covered syscalls since these ones may be covered later (filter done after)
                        covFolder.allSyscalls.add(fct)
                        covFolder.notCovSyscalls.add(fct)
                    try:
                        covFolder.notCovFct[fct].add(filename + "#" + str(span.parent['name']))
                    except:
                        covFolder.notCovFct[fct].add(filename)
    
    covFolder.mapHtmlFile[filename] = htmlFile

def iterateHtmlFolder(covFolder):

    pathlist = Path(covFolder.htmlFolder).glob('**/*.gcov.html')
    for path in pathlist:
        str_path = str(path)
        print_verbose("Gathering info of: " + str(str_path), verbose)
        if not os.path.isfile(str_path) or not os.access(str_path, os.R_OK):
            print_err("Can not open html file, \"{}\"!".format(str_path))
            sys.exit(-1)
        getHtmlLines(str_path, covFolder)

def iterateExtandFolder(gObj):

    pathlist = Path(gObj.expandFolder).glob('**/*.expand')
    for path in pathlist:
        
        str_path = str(path)
        print_verbose("Gathering info of: " + str(str_path), verbose)
        if not os.path.isfile(str_path) or not os.access(str_path, os.R_OK):
            print_err("Cannot open rtl file, \"{}\"!".format(str_path))
            sys.exit(-1)
        gObj.pathList.append(str_path)

def generateResults(gObj, covFolder, args, resultsFolder):
    isExist = os.path.exists(resultsFolder)
    if not isExist:
        os.makedirs(resultsFolder)

    if args.savehtml:
        print("[INFO] Generating result files (as .html) into: " + resultsFolder)
        saveResultsHtml(resultsFolder, covFolder)
    if args.aggregate:
        outAggregated = os.path.join(resultsFolder, AGGREGATE_FILE + ".html")
        print("[INFO] Generating aggregated html file: " + outAggregated)
        saveAggregateHtml(outAggregated, covFolder)
    if args.unique:
        outAggregated = os.path.join(resultsFolder, AGGREGATE_FILE + "_functions.html")
        print("[INFO] Generating unique aggregated html file: " + outAggregated)
        saveAggregateHtmlUnique(gObj, args.maxdisplay, outAggregated, covFolder, resultsFolder)

def main():
    global verbose
    if platform.system() == "Darwin":
        clang.cindex.Config.set_library_file(MAC_CLANG)
    else:
        filename="/usr/lib/x86_64-linux-gnu/libclang.so"
        if not os.path.isfile(filename):
            print_err("Cannot find {}. Please install clang shared library. See README.md for more information.".format(filename))

    parser = argparse.ArgumentParser()
    parser.add_argument('--folder','-f', help='Path to the folder (source files) of the application to analyse', required=True)
    parser.add_argument('--coverage', help='[EXPERIMENTAL] Type of coverage (can be: None,' + COVERAGE_BENCHMARK + 'or' + COVERAGE_SUITE + ')', default=None)
    parser.add_argument('--aggregate', '-a', type=str2bool, nargs='?', const=True, help='Aggregate results into a single aggregated file ('+ AGGREGATE_FILE + ')' , default=True)
    parser.add_argument('--savehtml', '-s', type=str2bool, nargs='?', const=True, help='Save intermediate results as .html', default=False)
    parser.add_argument('--unique', type=str2bool, nargs='?', const=True, help='Count only functions once in an aggregated unique file', default=True)
    parser.add_argument('--maxdisplay', type=int, help='Max referenced files to show in the aggregate unique file (default: 10)', default=10)
    parser.add_argument('--verbose', '-v', type=str2bool, nargs='?', const=True, help='Verbose mode', default=False)
    parser.add_argument('--display', '-d', type=str2bool, nargs='?', const=True, help='Display system call', default=True)
    parser.add_argument('--csv', '-c', type=str2bool, nargs='?', const=True, help='Save system call as CSV', default=True)

    # Use to manage the call graph
    parser.add_argument('--generatePdf', type=str2bool, nargs='?', const=True, help='Generate PDF files', default=False)
    parser.add_argument('--generateDot', type=str2bool, nargs='?', const=True, help='Generate dot files', default=False)
    parser.add_argument("--exclude",    help="RegEx for functions to exclude", type=str, metavar="REGEX")
    parser.add_argument("--no-externs", help="Do not show external functions", action="store_true")
    parser.add_argument("--no-warnings", help="Do not show warnings on the console", action="store_true")
    parser.add_argument("--max-depth", metavar="DEPTH", help="Maximum tree depth traversal, default no depth", type=int, default=0)
    args = parser.parse_args()

    appName = os.path.basename(os.path.normpath(args.folder))
    expandFolder = os.path.join(args.folder,  "expand/")

    if not os.path.exists(expandFolder):
        print_warn("Expand folder not found. Analyse may be incomplete.")
        expandFolder = None

    verbose = args.verbose
    if args.coverage != None:
        if args.coverage != COVERAGE_SUITE or args.coverage != COVERAGE_BENCHMARK:
            print_err("The coverage args must either be " + COVERAGE_SUITE + " or " + COVERAGE_BENCHMARK)
        htmlFolder     = os.path.join(args.folder, args.coverage)
        resultsFolder  = os.path.join(args.folder, "results_" + args.coverage)
        covFolder = CovFolder(appName, htmlFolder, resultsFolder, os.path.join(args.folder, appName + ".csv"))
        print("[INFO] Analysing html folder: " + htmlFolder + " (this may take some times...)")
        iterateHtmlFolder(covFolder)
    else:
        covFolder = CovFolder(appName, None, None, None)

    # Use clang parser to analyse source code
    print("[INFO] Perfoming clang analysis... (this may take some times...)")
    output_dict = process_source_code(args.folder, args.verbose)
    
    # Build the graph
    if expandFolder != None:
        gObj = GraphObject(expandFolder)
        print("[INFO] Analysing expand folder: " + gObj.expandFolder + " (this may take some times...)")
        iterateExtandFolder(gObj)
        if len(gObj.pathList) == 0:
            print_err("Cannot find .expand files. Exit")
            sys.exit(1)

        if args.coverage != None:
            # Add pdf and dot folders to gCov
            gObj.outDotFolder = os.path.join(resultsFolder, "dot_files")
            gObj.outPdfFolder = os.path.join(resultsFolder, "pdf_files")
        
            # Manual inspection of data (sanitize)
            if os.path.exists(os.path.join(args.folder, appName + ".csv")):
                readCsvManual(covFolder)

        print("[INFO] Generating call graph: " + gObj.expandFolder + " (this may take some times...)")
        createGraph(gObj, covFolder, args)

        # Track syscalls as entrypoint to have a plot
        for s in covFolder.allSyscalls:
            buildCallee(gObj, covFolder, [s], args)

        # Add all syscalls to the system calls discovered by the clang analysis
        for s in covFolder.allSyscalls:
            if s not in output_dict['all_system_calls']:
                output_dict['all_system_calls'][s] = "expand_file"

        # Add all aliases system calls to the system calls discovered by the clang analysis
        for obj in gObj.aliases:
            if s not in output_dict['all_system_calls']:
                output_dict['all_system_calls'][s] = "expand_file"

    print("[INFO] Number of system calls discovered: " + str(len(output_dict['all_system_calls'])))
    if args.display:
        for s in output_dict['all_system_calls']:
            print(s)

    # Write syscalls in a CSV file with the following format (syscall number, covered {Y|N})        
    if args.csv:
        with open(os.path.join(args.folder, "syscalls_" + appName + ".csv"), "w") as f:
            for k,v in syscall_list.items():
                if k in output_dict['all_system_calls']:
                    f.write("{},Y\n".format(v))
                else:
                    f.write("{},N\n".format(v))
        print("[INFO] CSV file saved in: " + os.path.join(args.folder, "syscalls_" + appName + ".csv"))

    # Generate HTML output (for coverage only)
    if args.coverage != None and expandFolder != None:
        generateResults(gObj, covFolder, args, resultsFolder)
        if verbose:
            print_verbose("Printing aliases functions:", verbose)
            for obj in gObj.aliases:
                print(obj)

if __name__== "__main__":
    main()