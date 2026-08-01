# K7 atomic clone3/pidfd runtime

Contract `1.99.0` supplies the low-level Linux execution primitive missing
after V0-106. It consumes exactly one real V0-104 cgroup lease and one opaque,
process-local sealed bootstrap authority. On admitted x86-64 hosts it performs
one native
`clone3(CLONE_INTO_CGROUP | CLONE_PIDFD | CLONE_CLEAR_SIGHAND)` and supervises
only the returned pidfd. There is no `fork`, `Popen`, helper-process or
fake-cgroup fallback.

Admission is explicitly unprivileged: all real/effective/saved/filesystem UIDs
and GIDs plus supplementary groups must be nonzero, and `CapInh`, `CapPrm`,
`CapEff` and `CapAmb` must all be zero. `CapBnd` is recorded but is not itself a
grant; `no_new_privs` prevents gaining a bounded capability through exec.

## Atomic child boundary

The checked-in x86-64 assembly trampoline is embedded by exact byte digest. A
`PYFUNCTYPE` call retains the GIL across the final `/proc/self/task` check and
`clone3`, so no Python runs on the child side and another Python thread cannot
enter the final check-to-clone interval. All launch authorities and descriptor
identities are rechecked inside that signal-blocked critical section. The child
executes only fixed raw syscalls before `execveat`:

1. install `PR_SET_PDEATHSIG(SIGKILL)` and close its parent-death race;
2. install `no_new_privs` and an empty Landlock write-denial ruleset;
3. install the registered seccomp filter denying the x32 ABI, process/thread
   creation, socket/IPC/key brokers, namespace/mount operations,
   metadata mutation and parent process/resource-control primitives;
4. clear the inherited signal mask, bind standard streams to `/dev/null`, and
   execute the sealed memfd by descriptor.

The executable and all optional inputs must be nonempty bounded memfds carrying
the complete immutable seal set. The bootstrap copies their verified bytes into
runtime-private, fixed-mode, fully sealed inodes, stores its authority state only
in a process/PID/object-identity registry, is single-use and unpickleable, and
exposes no caller-mutable slots.

## Parent supervision and cleanup

Before launch the parent writes and exactly reads back `memory.max`, disables
swap with `memory.swap.max=0`, and verifies writable `cgroup.kill`. The lease
already fixes `pids.max=1`, `cgroup.max.depth=0` and
`cgroup.max.descendants=0`. Output has an explicit cap and the deadline range is
bounded by twelve hours; neither bound is an assistant-side timeout.

Deadline and output-cap enforcement signal through `pidfd_send_signal` and use
bounded `waitid(P_PIDFD, ..., WNOHANG)` polling. Results distinguish an observed
SIGKILL from a child that raced to another terminal status, and separately
record total socket bytes observed and the retained prefix. Successful return
requires EOF, reap, empty leaf, zero live/dying descendant cgroups, unchanged
process/descendant and memory/swap caps, final `memory.peak`, lease removal and
bootstrap close.
Every exception path attempts child kill/reap, `cgroup.kill`, empty/descendant
proof and authority cleanup before it can propagate a cleanup failure.

## Evidence and remaining locks

The native child emits fixed setup-stage/errno records on a dedicated CLOEXEC
pipe and a `READY_FOR_EXEC` record immediately before `execveat`; this separates
sandbox/exec setup failure from a program that legitimately exits 126 or 127.
The embedded bytes were rebuilt from the checked-in assembly and matched at
624 bytes with SHA-256
`b51d9aa3e58bfdf04d8e02babf5e17b3e320ba7a126f01fdfd07ed6642ec8489`.
The opt-in real delegated-systemd test executes a sealed `/bin/true`, a sealed
Python denial probe and an invalid executable. The denial probe observes
`EPERM` for `fork`, `chmod`, socket creation, parent `prlimit64` and
`fcntl(F_SETOWN)` on the inherited channel, plus `EACCES` for ordinary-file and
`cgroup.procs` writes. The invalid image returns typed `EXECVEAT/ENOEXEC` setup
evidence rather than masquerading as a program exit 127.

This module deliberately returns only parent-observed low-level facts. Its raw
counters are not the formal accounting record and it issues no
`CounterRecord`, `WorkVector`, `ComparisonVector`, projection proof, attempt
terminal, certificate, scientific result or official-execution authority. It
does not yet bind the V0-106 business entry to the sealed bootstrap, emit the
parent accounting suffix, prove the complete loaded module graph, atomically
publish the two protocol frames or close the nine shared-resource semantics.
Those remain the next construction boundary.
