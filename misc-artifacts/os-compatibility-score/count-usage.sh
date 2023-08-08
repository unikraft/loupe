#!/bin/bash

# SPDX-License-Identifier: BSD-3-Clause
#
# Authors: Pierre Olivier <pierre.olivier@manchester.ac.uk>
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

source ../common/common.sh

# Create a temporary directory and store its name in a variable ...
TMPDIR=$(mktemp -d)

# Bail out if the temp directory wasn't created successfully.
if [ ! -e $TMPDIR ]; then
    >&2 echo "Failed to create temp directory"
    exit 1
fi

cleanup_csvs $TMPDIR

# syscall_get_usage(bench/suite/all, tempdir, syscall number)
syscall_get_usage() {
  used_staticsource=0
  used_staticbinary=0
  used_dyn_conservative=0
  used_dyn_stubfake=0

  for f in $(ls ${2}/*.csv); do
    hasdat=$(has_data $1 $f)
    if [ "$hasdat" -eq "0" ]; then
      continue
    fi

    is_used=$(syscall_required_staticbinary $f $3)
    if [ ! "$is_used" -eq "0" ]; then
      used_staticbinary=$((used_staticbinary+1))
    fi

    is_used=$(syscall_required_staticsource $f $3)
    if [ ! "$is_used" -eq "0" ]; then
      used_staticsource=$((used_staticsource+1))
    fi

    is_used=$(syscall_required_dyn_conservative $1 $f $3)
    if [ ! "$is_used" -eq "0" ]; then
      used_dyn_conservative=$((used_dyn_conservative+1))
    fi

    works_stubfaked=$(syscall_optional_dyn_stubfake $1 $f $3)
    if [ "$works_stubfaked" -eq "0" ]; then
      if [ ! "$is_used" -eq "0" ]; then
        used_dyn_stubfake=$((used_dyn_stubfake+1))
      fi
    fi
  done

  echo "$3,$used_staticbinary,$used_staticsource,$used_dyn_conservative,$used_dyn_stubfake"
}


# load_data(<suite/bench/all>)
load_data() {
  i=1

  WORKDIR=${TMPDIR}/$1
  mkdir -p $WORKDIR

  echo "Syscall#,staticbinary,staticsource,dyn_conservative,dyn_stubfake"
  for sys in {0..335}; do
    syscall_get_usage $1 $TMPDIR $sys
  done

}

check_files $TMPDIR
for p in "all" "suite" "bench"; do
  echo "Counting syscall usage in apps for $p..."
  load_data $p > generated-data/$p.csv
done

echo "Done!"

