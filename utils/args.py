import argparse
import pathlib
import src.common as common
ONLY_DOCKER_OPT = "--only-build-docker"

def parse_args():
    """Process the arguments passed in
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd')
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
            help="enable debug output")
    parser.add_argument("-q", "--quiet", action="store_true", dest="quiet",
            help="disable any non-error output")
    parser.add_argument("--allow-dirty-db", action="store_true", dest="dirtydb",
            default=False, help="allow dirty DB with uncommited changes")

    run_parser = subparsers.add_parser("generate",
            help="run system call usage analysis for an application")

    run_parse_req_args = run_parser.add_argument_group('required arguments')
    run_parse_req_args.add_argument("-db", "--database", dest="dbpath",
            type=pathlib.Path, required=True, help="path to the database")
    run_parse_req_args.add_argument("-a", "--application-name", type=str, required=True,
            help="name of the application to be analyzed (e.g., nginx)", dest="application")
    run_parse_req_args.add_argument("-w", "--workload-name", type=str, required=True,
            help="name of the workload (e.g., wrk)", dest="workload")
    run_parse_req_args.add_argument("-d", "--dockerfile", type=pathlib.Path, required=True,
            help="path to the dockerfile that performs the analysis")

    run_parse_classifier_args = run_parser.add_argument_group('classifier arguments (exactly one required)')
    run_parse_classifier_args.add_argument("-b", action="store_true", dest="isbenchmark",
            help="consider this workload as a benchmark")
    run_parse_classifier_args.add_argument("-s", action="store_true", dest="issuite",
            help="consider this workload as a testsuite")

    run_parse_other_args = run_parser.add_argument_group('optional arguments')
    run_parse_other_args.add_argument(ONLY_DOCKER_OPT, action="store_true", dest="onlydocker",
            help="only build the Docker container, do not run the analysis")

    search_parser = subparsers.add_parser("search",
            help="retrieve and analyze data from the database")

    required_args = search_parser.add_argument_group('required arguments')
    required_args.add_argument("-db", "--database", dest="dbpath",
            type=pathlib.Path, required=True, help="path to the database")
    required_args.add_argument("-a", "--applications", dest="applist", type=str,
            help="comma-separated list of apps to consider, e.g., 'redis,nginx', '*' for all")
    required_args.add_argument("-w", "--workloads", dest="wllist", type=str,
            help="comma-separated list of workloads to consider, e.g., 'bench,suite', '*' for all")

    action_args = search_parser.add_argument_group('action arguments')
    action_args.add_argument("--show-usage", dest="showusage", action="store_true",
            help="output a list of required/stubbed/faked system calls for this set")
    action_args.add_argument("--guide-support", dest="supportfile", type=pathlib.Path,
            help="given the path to a newline separated file of supported system calls, " +
            "output the remaining system calls to implement to support this set")
    action_args.add_argument("--cumulative-plot", action="store_true", dest="cumulativeplot",
            help="output a cumulative support plot for this set")
    action_args.add_argument("--heatmap-plot", action="store_true",
            help="output a heatmap support plot for this set", dest="heatmapplot")
    action_args.add_argument("--paper-histogram-plot", action="store_true",
            help="output the histogram of the paper, ignores passed set", dest="paperhistogramplot")
    action_args.add_argument("--export-sqlite", action="store_true",
            help="export the DB as SQLite database")

    opt_args = search_parser.add_argument_group('optional arguments')
    opt_args.add_argument("--static-source", action="store_true",
            help="also include static source analysis data", dest="ssource")
    opt_args.add_argument("--output-sys-names", action="store_true", dest="outputnames",
            help="output system call names instead of numbers")

    args = parser.parse_args()

    common.ENABLE_VERBOSE = (args.verbose is True)
    common.ENABLE_QUIET = (args.quiet is True)
    ENABLE_DIRTY_DB = (args.dirtydb is True)

    if (args.cmd is None):
        parser.print_help()
        exit(1)

    return args

