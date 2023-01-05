#!/bin/bash

nl=$(cat result.log | grep -P "All tests successful." | wc -l)
if [ "$nl" -eq "1" ]; then
	rm result.log
	exit 0
fi

exit 1
