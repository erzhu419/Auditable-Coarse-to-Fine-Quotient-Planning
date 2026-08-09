# K7 H1 E5A Prepared Lease Successor V1

Status: bounded executable companion prerequisite; not actual-observed E3 V2
slice 1.

Proposed contract: `2.0.59-E-C-E5B-B2-A`.

Profile key: `construction_k7_h1_e5a_runtime_lease_successor_v1`.

Readiness: `RUNTIME_LEASE_SUCCESSOR_ONLY`, with live state
`PREPARED_SUCCESSOR`.

## Exact claim

B2-A consumes one exact issuer-live E5A
`H1RouteWideWorkingSetCgroupLeaseV1` and moves its canonical FD ownership into
one exact, PID/thread-bound companion object.  The old lease becomes
`RUNTIME_TRANSFERRED`, leaves E5A's live registry, loses every canonical and
retry-witness FD slot, and can never become `ACTIVE` again.

The companion can reverify the still-empty E5A hierarchy and issue, at most
once per registered slot, one nonlaunchable `O_PATH | O_DIRECTORY |
O_CLOEXEC | O_NOFOLLOW` leaf candidate opened through the exact retained leaf.
Each candidate is slot/leaf/runtime/PID/thread-bound, registered in the same
E5A FD ownership registry, raw-closed and poisoned in a fork child, exposes no
public raw-FD/`fileno` interface, and must be closed in this fixture.  It is not
a birth permit and cannot authorize
`clone3`, `CLONE_INTO_CGROUP`, placement, release, or role execution.

This slice deliberately does **not** implement:

- an execution-source closure;
- a guardian session or pinned outer `cgroup.kill` control;
- `RUNNING`, `PEAK_READ`, or the normal V2 runtime state chain;
- a shared PID cell, PIDFD escrow, process birth, cgroup membership, death or
  creator-reap observation;
- route-wide actual-peak authority; or
- production receipts or formal Phase 3E accounting.

Consequently:

```text
prepared_e5a_successor_present = true
nonlaunchable_one_shot_leaf_candidates_present = true
e5a_runtime_lease_successor_present = false
launch_authorizing_leaf_grants_present = false
actual_process_birth_present = false
route_wide_actual_peak_authority_present = false
```

## Companion trust boundary

E5A V1 remains byte-for-byte frozen.  B2-A is an explicit companion adapter,
not an unrelated caller that treats private fields or serialized mappings as
authority.  Before transfer and again inside the ownership critical section,
the adapter verifies:

1. the E5A module's reviewed source SHA-256 is exactly
   `768b3cae4d7ed5edadb6596e3463e54022e54cacb3522a91381c751aaefe7d56`;
2. every consumed E5A callable is the exact import-time function object and
   still closes over the exact E5A module globals;
3. the FD lock, live/quarantine/ownership registries, record/lease types,
   profile/topology objects, kernel wrappers and signal wrapper are the exact
   import-time global objects;
4. the lease slots, canonical/retry-witness slots, role order and ownership
   record fields are the reviewed layouts; and
5. the E5A claim flags still say prelaunch-only, no process placement, no
   actual peak and no official execution.

The companion module itself is part of the trusted bridge and must be included
in the future execution-source closure before any actual birth.  The present
threat boundary rejects forgery through public APIs: caller mappings,
look-alike objects, copied objects, foreign PID/thread use and registry-absent
private-field clones do not acquire authority.  Like the staged V2 contract,
it does not claim resistance to arbitrary hostile Python private-state
mutation, a compromised interpreter, root, kernel/eBPF injection or a
compromised future guardian.

## Lock and fork order

Every adapter-owned transition uses this order:

```text
adapter registry lock
-> exact source E5A lease lock
-> exact successor object lock, when present
-> E5A FD ownership lock
```

This is compatible with frozen E5A cleanup's lease-lock-before-ownership-lock
order and prevents an adapter/E5A cleanup ABBA cycle.  The adapter releases
all of its locks before invoking the public V1 cleanup entry point.

E5A's at-fork callback remains the single raw-close owner for every canonical,
witness and candidate descriptor.  The companion registers an outer at-fork
barrier.  In the child, E5A first raw-closes its exact ownership snapshot; the
companion then poisons all successor/candidate slots and clears its registries.
The parent retains the exact live objects.

All created candidate FDs are published through E5A's reviewed
open-to-provisional-registry-to-identity-upgrade path, including its signal
mask and fork refusal window.  Candidate cleanup uses E5A's same-OFD witness
close semantics.  A non-EBADF ambiguous close remains in `CLOSE_PENDING`
quarantine and cannot reopen that slot.

## Atomic one-way transfer

Before the commit point, the adapter requires:

- exact E5A lease runtime type;
- same owner PID and exact E5A live-registry object identity;
- state exactly `ACTIVE`, never `CLEANUP_PENDING`;
- exact live topology, empty outer/leaves, cap controls, hierarchy document,
  allowed-cap envelope and retained `memory.peak` OFD pair;
- all seven canonical FD slots registered to the exact lease with exact live
  identities; and
- no retry-witness slot.

The adapter preallocates the successor and replacement ownership records.
Registration of the successor is the commit point.  From that point it
finishes forward under the same lock and E5A safe-signal shield:

```text
old E5A ACTIVE
-> old E5A RUNTIME_TRANSFERRED, all slots -1, absent from live registry
-> companion PREPARED_SUCCESSOR, exact canonical FD ownership
```

The post-commit path never restores `ACTIVE`.  If final successor
reverification fails, the adapter immediately follows the cleanup-only
handback described below; an unreachable live successor is forbidden.
Pending Python signal handlers run only after the old lease is fully
`RUNTIME_TRANSFERRED`; a handler therefore cannot reenter V1 cleanup while
the seven ownership records are split between owners.

Both handback and final companion-closure commits run with E5A's reviewed safe
signal set blocked.  All replacement records and both quarantine-registry
reservations are prepared before the handback commit.  Every commit boundary
is an idempotent finish-forward write: an injected exception replays the whole
target state without fault injection before signals are restored.  The final
closure similarly finishes `closure -> CLOSED -> registry removal` before
unmasking, so no `CLOSED` object can retain a stale runtime registry entry.

## Read-only prepared verification

`verify_h1_e5a_runtime_lease_successor_v1` is restricted to the exact owner
PID and exact `threading.Thread` object.  It verifies:

- exact issuer registry membership and `PREPARED_SUCCESSOR` state;
- the retired old E5A object and its empty FD slots;
- all seven canonical FD registry entries and live kernel identities;
- unchanged hierarchy names, identities, controller/cap values, empty
  population, admission snapshots, retained peak identity and same OFD;
- exact successor content ID under the reserved V15 successor domain; and
- all false/null/`NOT_RUN` claim locks.

This verification is only valid before births.  It is not a general live-route
verifier because E5A's frozen verifier correctly requires empty leaves.

## Nonlaunchable candidate lifecycle

The exact slot map is:

| Slot | Candidate leaf |
|---|---|
| `SUPERVISOR` | `CONTROL` |
| `PIDFD_PROBE` | `CONTROL` |
| `BROKER` | `CONTROL` |
| `WORKER` | `WORKER` |
| `BUSINESS` | `BUSINESS` |

For each slot the state is one-way:

```text
AVAILABLE -> ISSUE_PENDING -> ISSUED -> CONSUMED
                           -> ABORTED
                           -> CLOSE_PENDING -> CONSUMED
                ISSUED -> CLOSE_PENDING -> CONSUMED
```

Issuance first repeats prepared verification, then opens `.` through only the
registered leaf FD.  The candidate contains one live canonical leaf slot and
no parent, outer, `memory.max`, `memory.peak`, `cgroup.kill`, other leaf or
route artifact authority.  Its public `launch_authority` is always `false`.
Duplicate issuance, unknown/bool/crossed slot requests, copied candidates,
foreign PID/thread use, registry removal and use after close all fail closed.

The candidate owner and `ISSUE_PENDING` slot are registered before the open
syscall under the same safe-signal shield.  Registry reservation, slot
reservation, open, identity upgrade, flag/support validation and terminal
state commit are one exception-safe region.  Any exception either closes the candidate and
consumes the slot, or preserves the exact owner as `CLOSE_PENDING` for
candidate/runtime cleanup; it can never leave an unregistered owner while the
slot appears `AVAILABLE`.  A pending handler can observe the reserved
`ISSUE_PENDING` state, but it can never observe `AVAILABLE`; a same-slot
reentrant issue therefore fails closed before any second owner or FD exists.

The present fixture closes every candidate without calling clone.  A future
source-closed guardian/trampoline slice must consume a different exact
launch-authorizing object after source closure, guardian session, cgroup.kill
and complete permit semantics exist.  It cannot relabel this candidate.

The descriptor exists only in the companion's private ownership slots.  Tests
may inspect that trusted seam, but an ordinary public-API caller cannot obtain
the descriptor.  Arbitrary hostile private introspection remains outside the
explicit threat boundary above.

## Cleanup-only handback

Abandonment closes all candidates first.  The adapter then atomically moves
all seven exact ownership records back to the *same old E5A lease*, but only
with this state and registry:

```text
old E5A state = CLEANUP_PENDING
old E5A registry = _QUARANTINED_LEASES
old E5A live registry membership = absent
```

The companion becomes `CLEANUP_PENDING`; it never owns a usable canonical FD
again.  The adapter then calls the frozen public E5A V1 cleanup function.  V1
alone revalidates identities, removes the empty leaves/outer hierarchy, retains
the peak OFD pair until outer removal, and closes every canonical/witness FD
with reviewed same-OFD retry semantics.

If V1 removal or close fails, the old lease remains `CLEANUP_PENDING` in E5A's
quarantine and the companion remains `CLEANUP_PENDING`; retry calls V1 cleanup
again.  No adapter closure is issued.  Success requires the exact old E5A V1
closure, old state `CLOSED`, every slot `-1`, and no ownership record for the
old or companion owner.  Only then is a V15 construction cleanup closure
issued.  It explicitly records no birth and no peak read.

## Required tests

The executable acceptance suite covers:

1. source/callable/global/layout manifest validation and monkeypatch refusal;
2. mapping, look-alike, copy/pickle and registry-absent forgery rejection;
3. exact one-way ownership transfer and old public verify/cleanup rejection;
4. read-only hierarchy/cap/OFD verification;
5. all five exact slot/leaf candidate mappings and `O_PATH`/`CLOEXEC` support;
6. duplicate, unknown, bool, crossed-owner and post-close candidate attacks;
7. candidate close-only quarantine and retry;
8. successor/candidate cross-thread rejection;
9. fork-child raw-close and poison while the parent remains live;
10. cleanup-only handback, old lease never `ACTIVE`, V1 closure binding, and
    no residual FD/registry/cgroup identity;
11. V1 cleanup close failure remaining retryable through the companion; and
12. all runtime, birth, peak, accounting, current-access, V7, official and
    economics claim locks remaining false/null/`NOT_RUN`.

## Downstream Gate

B2-A closes only the ownership-transfer/candidate/abandon lifecycle.  The next
slice must add and source-close an actual guardian session, pin `cgroup.kill`,
and define a distinct launch-authorizing permit before even one SUPERVISOR
birth.  Only that later combination may transition into a genuine runtime
state; this file cannot be used as evidence that slice 1 or the total target is
complete.
