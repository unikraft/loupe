/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Copyright (c) 2020-2021, Hugo Lefeuvre <hugo.lefeuvre@manchester.ac.uk>
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from
 *    this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <ctype.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <linux/limits.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/user.h>

#define X32_SYSCALL_BIT	0x40000000
#define ARRAY_SIZE(arr)	(sizeof(arr) / sizeof((arr)[0]))

/* DO_ERRNO and DO_CRASH incompatible */
#define DO_ERRNO	0x1
#define DO_CRASH	0x2
#define DO_PTRACE	0x4
#define DO_PARTIALSTUB	0x8
#define DO_CHECKPATH	0x10
#define DO_PATHSTUB	0x20
#define SETF(N, F)	(N) = ((N) | (F))
#define ISSET(N, F)	(((N) & (F)) != 0)

static int QUIET = 0;
static int DEBUG = 0;

/* only valid when DO_CHECKPATH set */
static char EXECUTABLE_PATH[PATH_MAX + 1] = {0};

#define debug(...) \
  do { if (DEBUG)  { fprintf(stderr, "[D] " __VA_ARGS__); }} while (0);

#define warning(...) \
  do { if (!QUIET) { fprintf(stderr, "[W] " __VA_ARGS__); }} while (0);

#define error(...) \
  do { fprintf(stderr, "[E] " __VA_ARGS__); } while (0);

static int
install_filter(int num, int *syscalls, int flags, int f_errno)
{
    unsigned int upper_nr_limit = 0xffffffff;

    /* Assume that AUDIT_ARCH_X86_64 means the normal x86-64 ABI
       (in the x32 ABI, all system calls have bit 30 set in the
       'nr' field, meaning the numbers are >= X32_SYSCALL_BIT). */
    upper_nr_limit = X32_SYSCALL_BIT - 1;

    struct sock_filter *filter = malloc(sizeof(struct sock_filter) * (6 + 2 * num));
    struct sock_filter filter_base[] = {
        /* [0] Load architecture from 'seccomp_data' buffer into
               accumulator. */
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                 (offsetof(struct seccomp_data, arch))),

        /* [1] Jump to the end if architecture does not match X86_64. */
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 0, 3 + 2 * num),

        /* [2] Load system call number from 'seccomp_data' buffer into
               accumulator. */
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                 (offsetof(struct seccomp_data, nr))),

        /* [3] Check ABI - only needed for x86-64 in deny-list use
               cases.  Use BPF_JGT instead of checking against the bit
               mask to avoid having to reload the syscall number. */
        BPF_JUMP(BPF_JMP | BPF_JGT | BPF_K, upper_nr_limit, 1 + 2 * num, 0),
    };
    memcpy(filter, filter_base, sizeof(filter_base));
    struct sock_filter *pos = (struct sock_filter *)
	    (((uintptr_t) filter) + sizeof(filter_base));

    for (int i = 0; i < num; i++) {
        if (ISSET(flags, DO_PTRACE)) {
            debug("Registering ptrace rule for syscall %d.\n", syscalls[i]);
            struct sock_filter filter_sys_i[] = {
                /* [4 + i] Jump forward 1 instruction if system call number
                       does not match 'syscall_nr'. */
                BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, syscalls[i], 0, 1),

                /* [5 + i] Matching architecture and system call: handle via
		 * ptrace. */
                BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_TRACE),
            };
            memcpy(pos, filter_sys_i, sizeof(filter_sys_i));
            pos = (struct sock_filter *) (((uintptr_t) pos) + sizeof(filter_sys_i));
	} else if (ISSET(flags, DO_ERRNO)) {
            debug("Registering errno %d rule for syscall %d.\n", f_errno, syscalls[i]);
            struct sock_filter filter_sys_i[] = {
                /* [4 + i] Jump forward 1 instruction if system call number
                       does not match 'syscall_nr'. */
                BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, syscalls[i], 0, 1),

                /* [5 + i] Matching architecture and system call: don't execute
                   the system call, and return 'f_errno' in 'errno'. */
                BPF_STMT(BPF_RET | BPF_K,
                         SECCOMP_RET_ERRNO | (f_errno & SECCOMP_RET_DATA)),
            };
            memcpy(pos, filter_sys_i, sizeof(filter_sys_i));
            pos = (struct sock_filter *) (((uintptr_t) pos) + sizeof(filter_sys_i));
        } else if (ISSET(flags, DO_CRASH)) {
            debug("Registering crash rule for syscall %d.\n", syscalls[i]);
            struct sock_filter filter_sys_i[] = {
                /* [4 + i] Jump forward 1 instruction if system call number
                       does not match 'syscall_nr'. */
                BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, syscalls[i], 0, 1),

                /* [5 + i] Matching architecture and system call: don't execute
                   the system call, and crash. */
                BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
            };
            memcpy(pos, filter_sys_i, sizeof(filter_sys_i));
            pos = (struct sock_filter *) (((uintptr_t) pos) + sizeof(filter_sys_i));
        } else {
		printf("Error: install_filter(): "
                       "invalid flags (0x%x), this is a bug!\n", flags);
                return 1;
        }
    }

    struct sock_filter filter_end[] = {
        /* [4 + 2 * num] Destination of system call number mismatch: allow other
               system calls. */
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),

        /* [5 + 2 * num] Destination of architecture mismatch: kill process. */
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
    };
    memcpy(pos, filter_end, sizeof(filter_end));

    struct sock_fprog prog = {
        .len = 6 + 2 * num,
        .filter = filter,
    };

    if (syscall(SYS_seccomp, SECCOMP_SET_MODE_FILTER, 0, &prog)) {
        perror("seccomp");
        return 1;
    }

    return 0;
}

/* fetch system call arguments in the registers */
static long ptrace_get_syscall_args(int argn, struct user_regs_struct regs)
{
    long ret;

    switch (argn)
    {
        case 0:
            ret = (long) regs.rdi;
	    break;
        case 1:
            ret = (long) regs.rsi;
	    break;
        case 2:
            ret = (long) regs.rdx;
	    break;
        case 3:
            ret = (long) regs.r10;
	    break;
        case 4:
            ret = (long) regs.r8;
	    break;
        case 5:
            ret = (long) regs.r9;
	    break;
        default:
            /* Uh, no, that one's wrong. */
            error ("BUG: Invalid position '%d' passed to -p.\n", argn);
            exit(EXIT_FAILURE);
    }

    return ret;
}

/* return -1 if the binary path differ */
int ptracer_check_path(pid_t pid) {
    char symlink_path[PATH_MAX + 1];
    char binary_path[PATH_MAX + 1];

    sprintf(symlink_path, "/proc/%d/exe", pid);

    /* readlink doesn't append null character */
    memset(binary_path, PATH_MAX + 1, 0);

    int nbytes = readlink(symlink_path, binary_path, PATH_MAX);
    if (nbytes == -1) {
        perror("readlink");
        return -1;
    }

    int ret = strcmp(binary_path, EXECUTABLE_PATH);
    if (ret != 0) {
        debug("Found different binary: %s\n", binary_path);
    }

    return ret;
}

/* NOTE: buffer *must* be able to contain PATH_MAX bytes */
int ptrace_get_string_from_tracee(unsigned long long addr, pid_t child, void *buffer)
{
    long *buffer_int = (long*) buffer;
    unsigned long tmp;
    size_t byte = 0;
    size_t data;

    memset(buffer, 0, PATH_MAX);

    while (byte < PATH_MAX) {
        /* from the ptrace manpage:
         *   Since the value returned by a successful PTRACE_PEEK*
         *   request may be -1, the caller must clear errno before
         *   the call, and then check it afterward to determine
         *   whether or not an error occurred.
         */
        errno = 0;

        tmp = ptrace(PTRACE_PEEKDATA, child, addr + byte);
        if (errno == EFAULT || errno == EIO) {
            /* from the ptrace manpage:
             *   There was an attempt to read from or write to an invalid
             *   area in the tracer's or the tracee's memory, probably
             *   because the area wasn't mapped or accessible.
             *   Unfortunately, under Linux, different variations of this
             *   fault will return EIO or EFAULT more or less arbitrarily.
             * since we are always reading PATH_MAX, this is normal as long
             * as this doesn't happen for the first byte.
             */
             if (byte != 0) {
                 break;
             } else {
                 error("tracee passed an invalid path pointer (%p) to the "
                       "kernel - bug somewhere\n", (void *) addr);
                 exit(1);
             }
        } else if (errno) {
            perror("ptrace(PTRACE_PEEKDATA, _)");
            return -1;
        }

        buffer_int[byte / sizeof(long)] = tmp;

        byte += sizeof(long);
    }

    return 0;
}

int ptracer_loop(long sys, int argn, long argv, char *path, int flags, int f_errno)
{
    struct user_regs_struct regs;
    long syscall;
    int status = 0;
    siginfo_t siginfo;
    unsigned long pid, child_pid;
    int number_of_children = 1; /* keep track of the family */

    if (!ISSET(flags, DO_PTRACE) /* ptrace must be enabled */ ||
       /* either partial/path stubbing or check patch must be enabled */
       (!ISSET(flags, DO_PARTIALSTUB) && !ISSET(flags, DO_CHECKPATH)
        && !ISSET(flags, DO_PATHSTUB)) ||
       /* either crash or errno must be enabled */
       (!ISSET(flags, DO_CRASH) && !ISSET(flags, DO_ERRNO)) ||
       /* but not both of them */
       ( ISSET(flags, DO_CRASH) &&  ISSET(flags, DO_ERRNO))) {
        error ("BUG: ptracer_loop called with "
               "invalid flags (0x%x)\n", flags);
        return -1;
    }

    while (1) {
        while (1) {
            /* -1: make sure to listen to all (grand*-) children */
            /* __WALL: make sure to listen to all threads */
            pid = waitpid(-1, &status, __WALL);

	    if (pid == -1) {
                perror("waitpid");
                return -1;
            }

	    /* exit if our child died (sad, but happens) */
            if (WIFEXITED(status)) {
                number_of_children -= 1;
                debug("%lu: died, %d children remaining.\n", pid, number_of_children);
            }

            if (number_of_children == 0) {
                debug("actually, we're alone now. Exiting.\n");
                return 0;
            }

            if (status >> 8 == (SIGTRAP | (PTRACE_EVENT_SECCOMP << 8)))
                break;

            if (status >> 8 == (SIGTRAP | (PTRACE_EVENT_FORK << 8))  ||
                status >> 8 == (SIGTRAP | (PTRACE_EVENT_VFORK << 8)) ||
                status >> 8 == (SIGTRAP | (PTRACE_EVENT_CLONE << 8))) {
                number_of_children += 1;
                ptrace(PTRACE_GETEVENTMSG, pid, 0, &child_pid);
                debug("%lu: new child detected (%d). Tracing it as well.\n",
                      pid, child_pid);
		/* no need to reset child ptrace flags via PTRACE_SETOPTIONS
		 * as these are inherited automatically */
                ptrace(PTRACE_CONT, pid, 0, 0);
                continue;
            }

            /* got another signal, pass through */
            ptrace(PTRACE_GETSIGINFO, pid, 0, &siginfo);
            /* this log entry is not always useful */
            /* debug("%d: Got signal %d, transmitting.\n", pid, siginfo.si_signo); */
            ptrace(PTRACE_CONT, pid, 0, siginfo.si_signo);
        }

        ptrace(PTRACE_GETREGS, pid, 0, &regs);
        syscall = regs.orig_rax;

        debug("%lu: got a seccomp event for syscall %ld.\n", pid, syscall);
	if (ISSET(flags, DO_PARTIALSTUB) || ISSET(flags, DO_PATHSTUB)) {
            /* check system call number */
            if (syscall != sys) {
                debug("\tnot the syscall (listening for %ld).\n", sys);
                ptrace(PTRACE_CONT, pid, 0, 0);
                continue;
            }

            /* check system call argument */
            if (ISSET(flags, DO_PARTIALSTUB) && ptrace_get_syscall_args(argn, regs) != argv) {
                debug("\tnot the right argument (0x%lx vs 0x%lx).\n",
                       ptrace_get_syscall_args(argn, regs), argv);
                ptrace(PTRACE_CONT, pid, 0, 0);
                continue;
            } else if (ISSET(flags, DO_PATHSTUB)) {
                char path_buffer[PATH_MAX];

                /* here we need to dereference the argument first */
                ptrace_get_string_from_tracee(ptrace_get_syscall_args(argn, regs),
                                              pid, &path_buffer);

                if (strcmp(path_buffer, path) != 0) {
                    debug("\tnot the right argument ('%s' v.s. '%s').\n",
                           path_buffer, path);
                    ptrace(PTRACE_CONT, pid, 0, 0);
                    continue;
                }
            }
        }

        if (ISSET(flags, DO_CHECKPATH) && ptracer_check_path(pid) != 0) {
	    /* path is different, this is not a binary we want to mess with */
            debug("%lu: disabling seccomp for the child (different binary)\n", pid)
            ptrace(PTRACE_SETOPTIONS, pid, 0, PTRACE_O_SUSPEND_SECCOMP);
            ptrace(PTRACE_CONT, pid, 0, 0);
            continue;
        }

	/* right syscall *and* arguments, kill or return errno */
        debug("\thandling this system call.\n")
        if (ISSET(flags, DO_CRASH)) {
                debug("\tcrash mode, killing the child %lu.\n", pid);
		/* this will kill the child because of PTRACE_O_EXITKILL */
                return 0;
        } else /* ISSET(flags, DO_ERRNO) */ {
		/* change the system call number to an invalid one,
		 * then capture the result and change it to requested errno */
                regs.orig_rax = -1;
                ptrace(PTRACE_SETREGS, pid, 0, &regs);
                ptrace(PTRACE_SYSCALL, pid, 0, 0); /* run, stop on syscall exit */
                waitpid(pid, NULL, __WALL);
                regs.rax = f_errno;
                ptrace(PTRACE_SETREGS, pid, 0, &regs); /* set errno, finish */
                ptrace(PTRACE_CONT, pid, 0, 0);
	}
    }

    return 0;
}

void
usage(char *name)
{
    fprintf(stderr,
            "Usage: %s -e <errno/'crash'> "
	    "-n <num_syscalls> <syscall numbers> <prog> [<args>]\n"
            "Optional parameters:\n"
            "    Enable partial stubbing/faking mode:\n"
            "         -p <parameter position> <parameter value>\n"
            "         -t <path pointer position> <path value after deref>\n"
            "         NOTE: both only works with one syscall, i.e., -n 1 *\n"
            "         NOTE: uses ptrace, enabling this makes your "
            "program *much* slower.\n"
            "    Enable path checking mode (only check for target binary):\n"
            "         -y <path to target binary>\n"
            "         -z\n"
            "         NOTE: uses ptrace, enabling this makes your "
            "program *much* slower.\n"
            "         NOTE: -z assumes prog as path\n"
            "    Enable debug output:\n"
            "         -d\n"
            "    Enable quiet output (disables warnings):\n"
            "         -q\n"
            "         NOTE: not compatible with -d\n"
            "Examples:\n"
            "  (1) crash when encountering mprotect\n"
            "         %s -e crash       -n 1 10    /usr/bin/file ./file.txt\n"
            "  (2) do not execute mprotect, but return success\n"
            "         %s -e 0           -n 1 10    /usr/bin/file ./file.txt\n"
            "  (3) stub mprotect\n"
            "         %s -e 38          -n 1 10    /usr/bin/file ./file.txt\n"
            "  (4) stub read, write, and open\n"
            "         %s -e 38          -n 3 0 1 2 /usr/bin/file ./file.txt\n"
            "  (5) stub mmap only when argument 3 (flags) matches 34\n"
            "      (= 0x22 = MAP_PRIVATE|MAP_ANONYMOUS)\n"
            "         %s -e 38 -p 3 34 -n 1 9      /usr/bin/file ./file.txt\n"
            "  (6) stub open() only when argument 0 (pathname) matches '/etc/shadow'\n"
            "         %s -e 38 -t 0 '/etc/shadow' -n 1 2 /usr/bin/file ./file.txt\n"
            "  (7) stub read, but only for binary /usr/bin/red if the program forks\n"
            "         %s -e 38  -y /usr/bin/red -n 1 0 /usr/bin/blue ./secret.txt\n"
            "  (8) stub read, but only for binary /usr/bin/blue if the program forks\n"
            "         %s -e 38  -z -n 1 0 /usr/bin/blue ./secret.txt\n",
            name, name, name, name, name, name, name, name, name);
}

int
main(int argc, char **argv)
{
    char *evalue = NULL;
    char *nvalue = NULL;
    int c, sysnum, errno, *syscalls, status;
    int flags = 0; /* make sure to zero initialize */

    /* only valid with flags = DO_PARTIALSTUB or DO_PATHSTUB */
    int ptrace_pos = 0;

    /* only valid with flags = DO_PARTIALSTUB */
    int ptrace_val = 0;

    /* only valid with flags = DO_PATHSTUB */
    char *ptrace_str = 0x0;

    pid_t pid;

    if (argc < 5) {
        usage(argv[0]);
        exit(EXIT_FAILURE);
    }

    while ((c = getopt (argc, argv, "qzdy:p:e:n:t:")) != -1) {
        switch (c)
        {
            case 't':
		SETF(flags, DO_PTRACE);
		SETF(flags, DO_PATHSTUB);

                ptrace_pos = strtol(optarg, NULL, 0);
                if (ptrace_pos < 0 || ptrace_pos > 5) {
                    error ("Invalid position '%d' passed to -p.\n", ptrace_pos);
                    usage(argv[0]);
                    exit(EXIT_FAILURE);
                }

                if (optind < argc && *argv[optind] != '-') {
                    ptrace_str = argv[optind];
                    optind++;
                } else {
                    error ("-t option requires TWO arguments "
                           "<parameter position> <parameter value>\n");
                    usage(argv[0]);
                    exit(EXIT_FAILURE);
                }

                break;
            case 'p':
		SETF(flags, DO_PTRACE);
		SETF(flags, DO_PARTIALSTUB);

                ptrace_pos = strtol(optarg, NULL, 0);
                if (ptrace_pos < 0 || ptrace_pos > 5) {
                    error ("Invalid position '%d' passed to -p.\n", ptrace_pos);
                    usage(argv[0]);
                    exit(EXIT_FAILURE);
                }

                if (optind < argc && *argv[optind] != '-') {
                    ptrace_val = strtol(argv[optind], NULL, 0);
                    optind++;
                } else {
                    error ("-p option requires TWO arguments "
                           "<parameter position> <parameter value>\n");
                    usage(argv[0]);
                    exit(EXIT_FAILURE);
                }

                break;
            case 'e':
                evalue = optarg;
                if (optarg[0] == '-') {
                    error ("Invalid value passed to -e.\n");
                    exit(EXIT_FAILURE);
                }

                if (strcmp(evalue, "crash") == 0) {
		    SETF(flags, DO_CRASH);
	        } else {
                    errno = strtol(evalue, NULL, 0);
		    SETF(flags, DO_ERRNO);
		}
                break;
            case 'n':
                nvalue = optarg;
                sysnum = strtol(nvalue, NULL, 0);
                break;
            case 'd':
                DEBUG = 1;
		break;
            case 'y':
		SETF(flags, DO_PTRACE);
		SETF(flags, DO_CHECKPATH);

                strcpy(EXECUTABLE_PATH, optarg);
                if (optarg[0] == '-') {
                    error ("Invalid value passed to -y.\n");
                    exit(EXIT_FAILURE);
                }

		break;
            case 'z':
		SETF(flags, DO_PTRACE);
		SETF(flags, DO_CHECKPATH);
		break;
            case 'q':
                QUIET = 1;
		break;
            case '?':
		if (optopt == 'e' || optopt == 'n') {
                    error ("Option -%c requires an argument.\n", optopt);
                } else if (isprint (optopt)) {
                    error ("Unknown option `-%c'.\n", optopt);
		} else {
                    error ("Unknown option character `\\x%x'.\n", optopt);
		}
		/* intentional fall through */
            default:
                exit(EXIT_FAILURE);
      }
    }

    if (QUIET && DEBUG) {
        QUIET = 0;
        warning("quiet (-q) and debug (-d) incompatible, disabling quiet.\n");
    }

    if (argc < optind + sysnum + 1 /* a mandatory binary path */) {
        error("Error, not enough syscall numbers supplied "
              "(definitely not %d!).\n", sysnum);
        exit(EXIT_FAILURE);
    }

    syscalls = malloc(sysnum * sizeof(int));
    for (int i = 0; i < sysnum; i++) {
        syscalls[i] = strtol(argv[i + optind], NULL, 0);
    }

    if (ISSET(flags, DO_CHECKPATH)) {
        if (EXECUTABLE_PATH[0] == '\0')
            realpath(argv[sysnum + optind], EXECUTABLE_PATH);
        warning("Path checking mode enabled, "
            "I will only check for binary %s\n", EXECUTABLE_PATH);
    }

    /* if we're going to use ptrace, fork and setup tracing. */
    if (ISSET(flags, DO_PTRACE)) {
        if (ISSET(flags, DO_PATHSTUB)) {
            debug("Altering syscall behavior for arg %d set to '%s'.\n", ptrace_pos, ptrace_str);
        }
        debug("Running in ptrace mode, about to fork().\n");
        pid = fork();
	if (pid == -1) {
            perror("fork");
            exit(EXIT_FAILURE);
	} else if (pid != 0) {
	    /* parent = tracer */
            waitpid(pid, &status, 0); /* sync execv */
	    ptrace(PTRACE_SETOPTIONS, pid, 0,
                /* connection with seccomp */
                PTRACE_O_TRACESECCOMP |
                /* kill the child if we die */
                PTRACE_O_EXITKILL |
                /* follow clones */
                PTRACE_O_TRACECLONE |
                /* follow forks */
                PTRACE_O_TRACEFORK |
                /* follow vforks */
                PTRACE_O_TRACEVFORK |
                /* follow execs */
                PTRACE_O_TRACEEXEC
            );
	    ptrace(PTRACE_CONT, pid, 0, 0);

	    if (sysnum > 1) {
                error("Error, several system calls declared (%d), "
                      "but ptrace option only compatible with one at a time.", sysnum);
                exit(EXIT_FAILURE);
            }
            ptracer_loop(syscalls[0], ptrace_pos, ptrace_val, ptrace_str, flags, errno);
            exit(EXIT_SUCCESS);
	} else {
	    /* child = tracee */
            ptrace(PTRACE_TRACEME, 0, 0, 0);
            debug("Ptrace mode: child just started tracing.\n");
	}
    }

    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) {
        perror("prctl");
        exit(EXIT_FAILURE);
    }

    if (install_filter(sysnum, syscalls, flags, errno))
        exit(EXIT_FAILURE);

    debug("Alright, execv-ing now.\n");
    execv(argv[sysnum + optind], &argv[sysnum + optind]);
    perror("execv");
    exit(EXIT_FAILURE);
}
