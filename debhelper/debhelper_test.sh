#!/bin/bash

dh_auto_test

if [ $? -eq 0 ]; then
	echo "All tests successful." > result.log
  else
	exit 1
fi
