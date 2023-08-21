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

"""Contains classes used by the analyser."""

from collections import defaultdict

class GraphObject:
    def __init__(self, expandFolder):
        self.expandFolder = expandFolder
        self.pathList = list()
        self.functions = dict()
        self.aliases = set()
        self.outDotFolder = None
        self.outPdfFolder = None

class CovFolder:
    def __init__(self, appName, htmlFolder, resultsFolder, csvFile):
        self.appName = appName
        self.htmlFolder = htmlFolder
        self.resultsFolder = resultsFolder
        self.csvFile = csvFile
        self.mapHtmlFile = dict()
        self.covFct = defaultdict(set)
        self.notCovFct = defaultdict(set)
        self.allSyscalls = set()
        self.covSyscalls = set()
        self.manualSetSyscalls = set()
        self.notCovSyscalls = set()
        self.syscallsNeighboursCov = defaultdict(set)
        self.syscallsNeighboursNotCov = defaultdict(set)

class HtmlFile:
    def __init__(self, filename):
        self.filename = filename
        self.name = filename.split("/")[-1]
        self.linesCov = list()
        self.linesNotCov = list()

class HtmlLine:
    def __init__(self, innerText):
        self.innerText = innerText
        self.fctList = list()
