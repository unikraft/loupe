import argparse
from typing import Tuple


def get_output_vars(args: argparse.Namespace, logger) -> Tuple[bool, bool]:
    """Detects whether the use wants benchmark and/or testing enabled

    :param logger: the logger being used
    :param args: the arguments passed in
    :return: a tuple indicating at index 0, whether a benchmark is wanted and at
    index 1 whether a testsuite is wanted
    """
    if (not (args.applist and args.wllist)) and args.paperhistogramplot is not True:
        logger.error(
            "Application list (-a/--applications) and workload list "
            + "(-w/--workloads) are required for this option."
        )
        logger.error("Call with --help for more information.")
        exit(1)

    if args.showusage or args.cumulativeplot or args.heatmapplot or args.supportfile:
        if "*" in args.wllist and len(args.wllist) > 1:
            logger.warning(
                "* in the workload list but other entries are specified: "
                + str(args.wllist)
            )
            logger.warning("Ignoring them.")
            return True, True
        elif "*" in args.wllist:
            return True, True
        elif "benchmark" in args.wllist or "bench" in args.wllist:
            return True, False
        elif "testsuite" in args.wllist or "suite" in args.wllist:
            return False, True
        else:
            logger.error(
                "Invalid workload passed (valid: '*', 'benchmark'/'bench', 'testsuite'/'suite')"
            )
            exit(1)
    return False, False
