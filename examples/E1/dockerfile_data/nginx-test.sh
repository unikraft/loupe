#!/bin/bash

# nginx command: ./objs/nginx -p $(pwd) -g 'daemon off;'

# We first start a 3s benchmark on port 80 with wrk.
bench=$(wrk http://localhost:80/index.html -d3s)

# Then we parse the output for a chain of characters that typically indicates
# success (here the throughput, which is absent if the benchmark fails).
nl=$(echo ${bench} | grep -P "Transfer/sec:\s*\d+(?:\.\d+)MB" | wc -l)
if [ "$nl" -eq "1" ]; then
    # We return 0 if it is present, and 1 otherwise (failure).
    exit 0
fi

exit 1
