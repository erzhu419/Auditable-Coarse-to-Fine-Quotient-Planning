# K7 OS-supervisor admission

Status: contract `1.94.0` prelaunch boundary; no execution authority.

## Purpose

Formal nine-path accounting requires a parent-owned process supervisor, pidfd
lifecycle, an exclusive delegated cgroup-v2 attempt leaf and a post-reap
`memory.peak` read. Contract `1.94.0` makes absence of those capabilities an
explicit prelaunch noncertificate closure. It does not emulate them with child
RSS, `/proc` polling, process-group signalling, or an unverified directory.

## Read-only probe

The probe performs bounded no-follow reads of `/proc/self/cgroup`,
`/proc/self/mountinfo`, `cgroup.controllers` and, when present,
`cgroup.subtree_control`. Each successful read embeds exact bytes, byte count,
SHA-256 digest, source role and source path. It also records availability of
`pidfd_open` and `waitid(P_PIDFD)`, the resolved current unified-cgroup path,
controllers, required leaf files and current-directory access.

This evidence diagnoses the host only. It is not OS event provenance and is
not a cgroup lease.

## Mandatory delegated descriptor

The future executor may accept only a caller-preopened delegated-parent
directory descriptor. A discovered path elsewhere in the namespace is not a
substitute. If no descriptor is supplied, the mandatory result is:

```text
NOT_AVAILABLE
DELEGATED_CGROUP_PARENT_FD_NOT_SUPPLIED
ATTEMPT_CLOSURE_NONCERTIFICATE.OS_SUPERVISOR_NOT_AVAILABLE
```

Contract `1.94.0` intentionally does not validate or mutate a supplied
descriptor. Such a descriptor yields at most `PREFLIGHT_ONLY` together with
`DELEGATED_PARENT_RUNTIME_LEASE_VALIDATION_NOT_IMPLEMENTED`. No child is
launched in either state.

## Current-host result

The current WSL2 context exposes pidfd primitives and a unified cgroup-v2
mount, but this process has no usable delegated parent: the namespace root is
root-owned and not writable by the project user, and it is not an exclusive
attempt leaf. The current host therefore fails closed before child launch.

## Required successor

The next runtime must create a fresh attempt leaf beneath the preopened
delegated parent, program and read back `pids.max=1`,
`cgroup.max.depth=0`, and `cgroup.max.descendants=0`, verify an initially empty
leaf, and create the child atomically with cgroup placement plus pidfd. After
business cutoff it must reap by pidfd, prove the leaf unpopulated and empty,
then read the final peak through the already bound cgroup file descriptor.

Until that lease and the parent-owned accounting suffix exist, all OS,
nine-path, formal-vector and official-execution locks remain false.
