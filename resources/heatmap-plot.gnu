#!/usr/bin/gnuplot

# SPDX-License-Identifier: BSD-3-Clause
#
# Authors: Hugo Lefeuvre <hugo.lefeuvre@manchester.ac.uk>
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

set terminal svg enhanced font "arial,14" size 700, 250

unset key

set view map scale 1
set style data lines

unset xtics
unset ytics
unset ztics
set rtics axis in scale 0,0 nomirror norotate  autojustify

set xrange  [ -23.500000 : 0.50000 ] noreverse nowriteback
set yrange  [ -0.500000 : 13.50000 ] noreverse nowriteback
set cbrange [ 0 : 100 ]

set cblabel "Apps requiring the system call [%]"

set palette defined (\
0 "#fbfdbf", \
1 "#fec287", \
2 "#fb8761", \
3 "#e55964", \
4 "#b5367a", \
5 "#812581", \
6 "#4f127b", \
8 "#1c1044" \
)

set output '/mnt/heapmap-static-binary.svg'
plot '/mnt/data-staticbinary.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"

set output '/mnt/heapmap-static-source.svg'
plot '/mnt/data-staticsource.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"

set output '/mnt/heapmap-dynamic-used.svg'
plot '/mnt/data-dynused.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"

set output '/mnt/heapmap-dynamic-stubfake.svg'
plot '/mnt/data-dynstubfake.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"
