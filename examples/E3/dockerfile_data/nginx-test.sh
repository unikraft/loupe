#!/bin/bash

# nginx command: ./objs/nginx -p $(pwd) -g 'daemon off;'

WRK_PATH=wrk
PORT=80

test_works() {
  # This is the same behavior as in E1.

  bench=$(${WRK_PATH} http://localhost:${PORT}/index.html -d3s)

  failure=$(echo ${bench} | grep -P "unable to connect to localhost" | wc -l)
  if [ "$failure" -eq "1" ]; then
      exit 200
  fi

  nl=$(echo ${bench} | grep -P "Transfer/sec:\s*\d+(?:\.\d+)MB" | wc -l)
  if [ "$nl" -eq "1" ]; then
      exit 0
  fi

  exit 1
}

benchmark() {
  # We output a performance number to stdout. If we do not output anything,
  # Loupe will assume that the benchmark failed.

  # Note that we use a different / much longer benchmark than for test_works()
  # because we are a bit more careful about the stability of the measurements.
  # We wouldn't want to use the same in test_works because it may not add any
  # value to the test (if it works for 3s, it's likely to work for 10s), and it
  # would multiply the runtime of the analysis by 3x)

  taskset -c 6 ${WRK_PATH} http://localhost:${PORT}/index.html -d10s | \
          grep -P "Requests/sec:\s*\d+(?:\.\d+)" | grep -Po "\d+(?:\.\d+)"
  exit $?
}

# The test script may be passed an argument. If the value of the argument is
# benchmark, then the script is asked to output a performance number to stdout.
# If the value is something else (or nothing), we default to the simple "it
# works/it doesn't" behavior we had in E1.

if [ "$2" == "benchmark" ]; then
  # evaluate performance

  benchmark
else
  # simply test if it works

  test_works
fi
