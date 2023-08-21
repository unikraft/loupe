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

"""Displays the results in HTML format (only if covering is used)."""

import os
from io import StringIO
from syscalls_list import *

HTML_HEADER = '<html lang="en"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"></head><body>'

def saveResultsHtml(output, covFolder):
    htmlPath = os.path.join(output, "all_log")
    isExist = os.path.exists(htmlPath)
    if not isExist:
        os.makedirs(htmlPath)
        
    for name, htmlFile in covFolder.mapHtmlFile.items():
        if len(htmlFile.linesNotCov) > 0:
            with open(os.path.join(htmlPath, htmlFile.name), "w") as f:
                f.write(HTML_HEADER + "<div><h3>" + name + "</h3><table><tbody>")
                for line in htmlFile.linesNotCov:
                    for fct in line.fctList:
                        f.write("<tr><td>" + fct + "</td><td>(" + line.innerText +")</td></tr>")
                f.write("</tbody></table></div></body></html>")

def saveAggregateHtml(outAggregated, covFolder):
    with open(outAggregated, "w") as f:
        for name, htmlFile in covFolder.mapHtmlFile.items():
            if len(htmlFile.linesNotCov) > 0:
                f.write(HTML_HEADER + "<div><h3>" + name + "</h3><table><tbody>")
                for line in htmlFile.linesNotCov:
                    for fct in line.fctList:
                        f.write("<tr><td>" + fct + "</td><td>(" + line.innerText +")</td></tr>")
                f.write("</tbody></table></div></body></html>")

def process_value(maxDisplay, values):
    str_files = ''
    for i, v in enumerate(values):
        str_files += '<a href="../' + '/'.join(v.split("/")[1:]) + '">' + v.split("/")[-1] + '</a> '
        if i == maxDisplay:
            str_files += " +" + str(len(values) - i)+ " other files."
            return str_files
    return str_files

def checkIncludeFile(gObj, key, appName):
    info = " (<i>st|mc|unk)</i>"
    if key in gObj.functions:
        info = " (<strong>"
        for k in gObj.functions[key]["files"]:
            include = k.split("/")[-2].replace("_expand", "")
            if "glibc" in include:
                include = "<span style=\"color:red\">" + include + "</span>"
            info += include
            break
        info += ")</strong>"
    return info

def saveAggregateHtmlUnique(gObj, maxDisplay, outAggregatedUnique, covFolder, resultsFolder):
    
    strBuilder = StringIO()
    i = 0
    total = len(covFolder.allSyscalls)
    strBuilder.write(HTML_HEADER + "<div><h3>Covered syscalls</h3><table><tbody>\n")
    for s in covFolder.allSyscalls:
        if s in covFolder.covSyscalls and s not in covFolder.manualSetSyscalls:
            i += 1
            linkPdf = "<td><a href=\"#\">"+ s +"</a></td>"
            if os.path.isfile(os.path.join(covFolder.resultsFolder,os.path.join("dot_files", s + ".dot"))):
                linkPdf = "<td><a href=" + os.path.join("pdf_files", s + ".pdf") + ">" + s + "</a></td>"
            strBuilder.write("\t<tr>" + linkPdf + "</tr>\n")
    strBuilder.write("</tbody></table></div>\n")

    j = 0
    strBuilder.write("<div><h3>Not covered syscalls</h3><table><tbody>\n")
    for s in covFolder.allSyscalls:
        if s in covFolder.manualSetSyscalls:
            strBuilder.write("\t<tr><td><a href=" + os.path.join("pdf_files", s + ".pdf") + ">" + s + "</a></td></tr>\n")
            j += 1
        elif s in covFolder.notCovSyscalls and s not in covFolder.covSyscalls:
            strBuilder.write("\t<tr><td><a href=" + os.path.join("pdf_files", s + ".pdf") + ">" + s + "</a></td></tr>\n")
            j += 1
    strBuilder.write("</tbody></table></div>\n")
    
    #for s in covFolder.allSyscalls:
    #    if s not in covFolder.covSyscalls and s not in covFolder.notCovSyscalls:
    #        print(s)

    total = i+j
    strBuilder.write("\n<div><hr><p>Syscalls coverage: {:.2f}".format((i/total) * 100)+ "%</p><hr></div>")
    print("Syscalls coverage: {}/{} = {:.2f}".format(i, total, (i/total) * 100))
    
    with open(os.path.join(resultsFolder, "small.html"), "w") as file:
        file.write("<hr><div><h3>Static syscalls only (not compiled in the final binary)</h3><table><tbody>")
        for s in covFolder.allSyscalls:
            if s not in covFolder.notCovSyscalls and s not in covFolder.covSyscalls:
                file.write("<tr><td><a href=" + os.path.join("pdf_files", s + ".pdf") + ">" + s + "</a></td></tr>")
        file.write("</tbody></table></div>")
    
    strBuilder.write("\n<br><div><h3>functions not covered</h3><div><p><i>st</i>: static - <i>mc</i>: macro - <i>unk</i>: unknown</p></div><table><tbody>")
    i = 0
    for key, values in covFolder.notCovFct.items():
        if key not in covFolder.covFct and key not in covFolder.allSyscalls:
            linkPdf = "<td></td>"
            pdfPath = os.path.join(covFolder.resultsFolder, "pdf_files", key + ".pdf")
            if os.path.isfile(pdfPath):
                linkPdf = "<td><a href=../" + pdfPath + ">" + key + "</a></td>"
            info = checkIncludeFile(gObj, key, covFolder.appName)
            strBuilder.write("<tr><td>" + str(i) + "</td><td>" + key + info + "</td>" + linkPdf + "<td>" + process_value(maxDisplay, values) + "</td></tr>")
            i += 1

    strBuilder.write("\n</tbody></table></div><br><hr><div><h3>functions covered</h3><table><tbody>")
    i = 0
    for key, values in covFolder.covFct.items():
        linkPdf = "<td></td>"
        pdfPath = os.path.join(covFolder.resultsFolder, "pdf_files", key + ".pdf")
        if os.path.isfile(pdfPath):
            linkPdf = "<td><a href=../" + pdfPath + ">" + key + "</a></td>"

        info = checkIncludeFile(gObj, key, covFolder.appName)
        strBuilder.write("<tr><td>" + str(i) + "</td><td>" + key + info + "</td>" + linkPdf + "<td>" + process_value(maxDisplay, values) + "</td></tr>")
        i += 1

    strBuilder.write("</tbody></table></div></body></html>")
    
    with open(outAggregatedUnique, "w") as f:
        f.write(strBuilder.getvalue())