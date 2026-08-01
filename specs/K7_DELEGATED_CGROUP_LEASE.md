# K7 delegated cgroup-v2 attempt lease

Status: contract `1.96.0` real leaf-construction boundary; child launch and
formal accounting remain locked.

## Authority and order

The lease consumes an issuer-recorded process-local nonce token before any
cgroup access. The token binds the exact V0-103 request, V0-102 admission
result, delegated-parent FD number, descriptor stat identity and
`/proc/self/fd` target digest. It is single-use, cannot be pickled and cannot
cross a process boundary. This is an execution-construction guard, not a
durable replay ledger.

No pathname can authorize acquisition. All creation, open, read, write and
removal operations are relative to the caller-preopened parent directory FD
and use no-follow where the platform provides it.

## Successful lease invariants

The parent descriptor and leaf must be on cgroup v2. The delegated parent must
expose and enable `memory` and `pids`. A newly and exclusively created leaf must
have all registered controls and satisfy:

```text
cgroup.type              = domain
cgroup.procs             = empty
cgroup.threads           = empty
cgroup.events.populated  = 0
pids.current             = 0
memory.peak              = 0
pids.max                 = 1
cgroup.max.depth         = 0
cgroup.max.descendants   = 0
```

The last three values are written and read back before the lease is issued.
The lease is process-local and unpickleable. Close reopens the leaf name under
the owned parent FD, checks the exact leaf inode and empty state, removes only
that leaf and closes all owned descriptors. A setup failure after creation
must remove the leaf; inability to prove cleanup raises a typed invariant
instead of returning a normal blocker.

## Verification performed

Focused tests cover domain registration, profile identity, missing and ordinary
filesystem blockers, exact descriptor/target transplant rejection, single-use
nonce ordering, forged-token exclusion, controller/event/readback parsers,
domain and zero-peak requirements, post-create cleanup, unpickleability and all
locked formal claims.

The true positive syscall path was also run inside a temporary systemd user
scope with `Delegate=yes`. The supervisor process moved into a sibling subgroup,
enabled `memory` and `pids` at the delegated root, and passed that root as the
preopened FD. Acquisition read back all five frozen control values and close
removed the attempt leaf. The scope was transient and systemd reclaimed it on
exit.

## Still locked

This contract does not launch or place a child. In particular it supplies no
`clone3(CLONE_INTO_CGROUP | CLONE_PIDFD)`, pidfd deadline/signal/reap lifecycle,
post-reap descendant proof, final cgroup peak, child business bundle,
parent-owned accounting suffix, wrapper-complete atomic output or independent
source-semantic verifier. It issues no CounterRecord, WorkVector,
ComparisonVector, projection proof, attempt terminal, certificate or official
result. The nine shared-resource paths and both accounting/economics Gates
remain open.
