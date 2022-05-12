#!/bin/bash

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

