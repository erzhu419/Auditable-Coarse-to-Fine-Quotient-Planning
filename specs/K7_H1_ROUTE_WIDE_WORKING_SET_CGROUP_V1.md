# K7 H1 Route-Wide Working-Set Cgroup Admission V1

Status: bounded construction contract
Proposed contract: `2.0.59-E-C-E5A`
Profile key: `construction_k7_h1_route_wide_working_set_cgroup_v1`

## Scope

E5A creates the fresh delegated cgroup-v2 hierarchy needed to measure and cap
one future H1 route as a single working set.  It issues one content-addressed
prelaunch enforced allowed-cap envelope and retains the hierarchy as a
one-shot, PID-bound lease.

E5A is deliberately only `PRELAUNCH_ONLY`.  It does not move any process,
launch E3, run E4, observe a route-wide actual peak, issue an FQ11
`CounterRecord`, construct a `WorkVector` or `ComparisonVector`, or authorize
official execution.  Integrated placement, execution, peak readout and
cleanup-to-accounting are E5B obligations.

## Exact topology

The caller supplies an FD for one empty, child-free delegated cgroup-v2
parent.  `memory` and `pids` must be available and already enabled in that
parent's `cgroup.subtree_control`.  Ordinary directories, populated parents,
parents with old children, insufficient ancestor depth/descendant/PID limits,
and missing delegation fail before a positive admission can be issued.

E5A creates a cryptographically fresh outer cgroup `A` and exactly three
children:

| cgroup | `memory.max` | `memory.swap.max` | `pids.max` | max depth | max descendants |
|---|---:|---:|---:|---:|---:|
| outer `A` | `U` | 0 | 3 | 1 | 3 |
| `CONTROL` | inherited | inherited | 2 | 0 | 0 |
| `WORKER` | inherited | inherited | 1 | 0 | 0 |
| `BUSINESS` | inherited | inherited | 1 | 0 | 0 |

The outer subtree controller set is exactly `{memory, pids}`.  All four
cgroups must have empty `cgroup.procs` and `populated 0` at admission.  A
process-empty cgroup can still carry controller metadata or delayed kernel
charges, so E5A content-binds an exact `memory.current` observation for outer
`A`, `CONTROL`, `WORKER`, and `BUSINESS` rather than falsely requiring zero.
The delegated parent is a provisioning prerequisite outside the route-wide
measurement object: its `memory.current` is checked for canonical readability
but its numeric value is explicitly not a route operand and is not stored as
one.  All directory identities are distinct and are pinned by close-on-exec
directory FDs.  The delegated parent must contain only the newly created outer
name throughout prelaunch verification.

An existing E3 two-leaf fixture cannot be transplanted into E5A.  A parent
that already contains any leaf is not a fresh baseline, and E5A never accepts
caller-supplied `WORKER` or `BUSINESS` leaf FDs.

## Concurrency plan

The frozen non-overlap plan covers:

1. the route supervisor and in-process E4 writer as one process in `CONTROL`;
2. the self-cleaning pidfd capability-probe child in `CONTROL`, followed by,
   and never overlapping, the E3 broker in `CONTROL`;
3. E3 `WORKER` and `BUSINESS` in their named sibling leaves, with the E3
   single-role-at-a-time schedule preserved.

The maximum planned simultaneous process count is therefore three.  The
outer `pids.max=3` is not inferred from post-run observation.  E5A does not
itself establish that E5B followed the schedule.

## Allowed-cap derivation

Inputs `registered_hard_cap_bytes` and
`requested_outer_memory_max_bytes` must be exact finite positive integers.
Before any route launch E5A computes

\[
U=\min(\text{registered hard cap},
       \text{requested outer memory.max})
\]

and writes `U` to the fresh outer `memory.max`.  Exact readback must equal
`U`; rounded, infinite, missing or later changed values invalidate admission.
The content-addressed envelope then replays

\[
U=\min(\text{registered hard cap},\text{enforced outer memory.max}).
\]

Its exact `upper_kind` is `PRELAUNCH_ENFORCED_ALLOWED_CAP`, its comparison
axis is `peak_working_bytes`, and it is bound to the caller's exact
`logical_occurrence_id`, `route_attempt_id`, `decision_point_id`, and
`BuildEpoch_id`, plus the current E3 and E4 profile IDs, the E5A profile, the
topology plan and the fresh hierarchy identity.

A post-run peak never defines or tightens this envelope.  E3's maximum over
its two child leaves is not relabelled as a route-wide peak.

## `memory.peak` baseline and OFD retention

Only after the entire new hierarchy is proven process-empty may E5A reset the
outer `memory.peak`, exactly once.  Linux resets the peak to the current
charge, which may be nonzero for controller metadata; E5A records that exact
baseline and the exact outer `memory.current` read immediately after reset,
then reads the three leaves in frozen `CONTROL`, `WORKER`, `BUSINESS` order.
The hierarchy content ID binds every value and observation ordinal.  The
baseline must be no smaller than the recorded outer current and no larger
than `U`; every recorded current must be no larger than `U`.

The writable descriptor and a retained duplicate must continue to share the
same open file description.  E5A pins that OFD through successful hierarchy
removal.  Later process-empty replay does **not** claim that a fresh current
read equals its admission snapshot: metadata accounting may change.  Instead,
replay verifies that the admission values remain content-bound, all cgroups
remain process-empty, every live current is finite and at most `U`, and the
live retained peak is at least both the frozen baseline and live outer current
while remaining at most `U`.  A decrease below the baseline indicates an
unauthorized second reset and fails closed.

No second reset is allowed.  E5B must use this retained OFD for final route
peak readout; opening a different child or outer control and relabelling it is
not equivalent.

## Lease, fork and cleanup

The lease is issuer-owned and bound to its creating PID.  All retained
descriptors are `CLOEXEC`.  One ownership registry covers canonical FDs while
the hierarchy is still under construction, after transfer to a live lease,
and while a failed cleanup is quarantined.  Open/register, close/drop, owner
slot updates and live/quarantine state transitions occur under the same
module-global reentrant lock.  Thus neither the pre-lease construction window
nor the final close-to-registry-drop window is invisible to fork handling.

The single module-global at-fork protocol acquires that lock in `before`,
releases it in `after_in_parent`, and in `after_in_child` raw-closes exactly
the frozen registered FD numbers, poisons all copied construction/lease slots,
clears all copied registries and installs a new lock.  The child callback does
not call `fstat`, inspect `fdinfo`, open `/proc`, or invoke a per-lease bound
method that can retain a closed lease.  A future E5B launcher must pass
purpose-built duplicates explicitly.

The lock alone is insufficient for a syscall issued by the same thread:
`RLock` is reentrant, so a fork attempted after the kernel returned a new FD
but before that FD was published could otherwise bypass the snapshot.  A
canonical path therefore cannot accept an arbitrary Python opener.  It uses
only captured concrete `open` and `F_DUPFD_CLOEXEC` helpers.  Immediately
after either syscall returns, the helper publishes the FD and owner slot as a
provisional registry record; only then may it perform the fallible exact
device/inode/mode/mount identity upgrade.

The syscall-through-provisional-publication interval runs under an
exception-safe thread-local `fork_forbidden` guard.  A process audit hook
rejects `os.fork`/`os.forkpty` before the syscall while that guard is active;
the at-fork `before` hook checks the same guard before acquiring the ownership
lock as defense in depth.  If fork rejection or another exception escapes
during identity upgrade, the descriptor is already registered.  A successful
rollback close retires it; if close reports failure and the FD remains live,
the provisional record and exact slot remain in construction quarantine for
retry or child raw-close.  The guard is removed on both success and exception.
Fork from another thread waits for normal registry publication through the
ownership lock.

The current thread additionally uses captured `pthread_sigmask` to block every
registered safe asynchronous signal from immediately before the concrete
open/dup syscall through provisional registry-and-slot publication.  The mask
excludes the unblockable `SIGKILL` and `SIGSTOP` signals and, when present,
the unsafe synchronous `SIGBUS`, `SIGFPE`, `SIGILL`, `SIGSEGV`, `SIGSYS`, and
`SIGTRAP` signals.  E5A never changes the disposition or masking of those
synchronous-fault signals.  The exact prior mask is then restored while
`fork_forbidden` remains active.  Restoring may synchronously dispatch a
pending handler and that handler may raise; this restoration is inside the
publication failure scope.  Because the FD is already provisional, failure
closes it or retains it as construction quarantine.  A second exact mask
replay after a handler exception proves restoration before the exception is
propagated.  Syscall failure also restores the original mask.

An identity-less provisional FD is never closed using its numeric mapping
alone.  Before the canonical close attempt, E5A uses the captured
`F_DUPFD_CLOEXEC` path under the same lock, signal mask, and fork guard to
publish one same-OFD retry witness in the canonical slot's pre-registered
`retry-witness:*` slot.  That witness is allowed to retain `identity = null`:
its authority is OFD continuity, not inode metadata.  After any non-`EBADF`
canonical close error, Linux `kcmp(KCMP_FILE)` decides whether the canonical
number still names the witness OFD.  Only the same-OFD result may retain the
canonical mapping.  A different-OFD or `EBADF` result first retires the
canonical numeric mapping without closing it, so a replacement such as a
reopened `/dev/zero` remains live and unregistered; E5A then closes or retains
the actual original-OFD witness.

Final retry-witness close is deliberately bounded: it uses the captured Linux
`close` while the ownership lock excludes every registered E5A acquisition.
Success or definitive `EBADF` retires the witness; a non-`EBADF` result that
leaves it live retains that one witness in quarantine.  It never recursively
allocates `retry-witness:retry-witness:*`.  This is also the final-close rule
for exact-identity witnesses.  Under Linux, a real close error releases the FD
number before reporting later I/O errors; with no registered reopen under the
lock, the immediate liveness replay is definitive.  Hostile mutation of the
captured helper or an unregistered thread reopening the number inside that
final syscall boundary is private-runtime behavior and remains outside this
contract.

This is a Linux syscall, POSIX-signal and CPython audit contract.  It does not
claim protection against arbitrary private-runtime mutation, a hostile native
extension bypassing Python audit hooks, or a deliberately injected pure-Python
trace callback between indivisible helper bytecodes; those are outside E5A's
registered execution model.

Cleanup is identity-bound and retryable:

1. each pinned cgroup must be empty;
2. every live directory name must resolve to its pinned device/inode;
3. children are removed in reverse role order and verified absent;
4. immediately before outer removal, both retained `memory.peak` FDs are
   re-proven live, equal to the frozen control identity, and members of the
   same OFD;
5. the pinned outer identity is removed from the pinned delegated parent;
6. every retained descriptor is definitively closed;
7. only then is one content-addressed closure minted, cached, and the lease
   changed to `CLOSED` and removed from the ownership registry.

A populated group or transient removal error leaves the lease in
`CLEANUP_PENDING`; the same owner may retry.  A retry first replays absence for
every already removed role and never attempts to read controls through that
dead cgroup FD.  Cleanup does not trust changed cap values: a changed cap
invalidates admission but must not cause deletion of an unverified foreign
identity.

A non-`EBADF` close error is not treated as success merely because inode
metadata still matches.  Cleanup duplicates the exact canonical OFD before
the close attempt and, when the error leaves the original live, retains that
duplicate as a registered retry witness.  Linux `kcmp(KCMP_FILE)` proves OFD
continuity after cgroup removal, where dead kernfs controls can reject
`lseek`.  This distinguishes an actually live original from an unrelated
same-inode/new-OFD reuse of its old FD number.  A post-close exception is
definitive when the original OFD is gone; an unrelated reused number is never
closed.  If the original remains live, its exact slot and witness stay in the
quarantine registry, `_closure` remains absent, and a later cleanup call is a
close-only retry because the hierarchy is already removed.

## Content domains

V12 registers disjoint domains for:

- the E5A profile;
- the topology plan;
- the fresh hierarchy identity;
- the prelaunch allowed-cap envelope;
- the cleanup closure.

Every ID is `SHA256(domain-tag || 0x00 || canonical-json)`.  V10 E3 and V11 E4
objects remain in their original domains.

## Required attacks and positive fixture

Default tests cover caller-minted objects, malformed identities and caps,
ordinary directories, missing delegation, stale/changed/infinite caps,
content-ID tampering, construction/live fork poisoning, closed-lease FD reuse
and construction rollback.  They also force a same-thread fork after a real
`/dev/null` open and provisional publication but before identity upgrade: the
audit exception must escape without a child or live-unregistered FD.  A
separate attack makes identity upgrade and close both fail; the live FD must
remain with its same-OFD provisional retry witness in construction quarantine,
both records must be raw-closed in a fork child, remain valid in the parent,
and then support explicit parent cleanup.  Another attack makes close really
release the provisional `/dev/null` FD, reuses exactly that number for
`/dev/zero`, and then raises `EIO`: `kcmp` must retire the ambiguous canonical
mapping without closing or registering `/dev/zero`, while safely closing the
original-OFD witness.  No nested retry-witness slot is permitted.
For both concrete open and dup, one repeated real, publication-thread-directed
`SIGALRM` attack queues the signal inside a wrapped concrete syscall after the
kernel has returned the FD but before the wrapper returns.  The handler must
not run before provisional publication; it runs only during exact mask restore
and its attempted `fork` must be rejected, with no child and no
live-unregistered FD.  A separate repeated attack queues the same thread-
directed `SIGALRM` immediately after provisional publication to exercise the
same restore-exception cleanup path directly.  Both attacks must restore the
exact helper-entry mask on every iteration.

The only positive test uses a real delegated systemd cgroup-v2 fixture.  It
must prove exact topology/readbacks/emptiness, distinct identities, one shared
retained `memory.peak` OFD, cap derivation, old-two-leaf rejection,
cleanup-pending retry including a real partial hierarchy after first-child
removal, pre-rmdir peak-FD/OFD replay, post-close-raise classification, a
persistent-live close quarantine and close-only retry, fork in the final
close-to-registry-drop window, same-inode/new-OFD reuse safety, final removal
and idempotent closure.  Successful construction-to-lease transfer must prove
all retry-witness slots empty before moving any canonical record, and closure
must prove every canonical and witness slot empty before minting its artifact.
Monkeypatching an ordinary directory into a positive cgroup is forbidden.

## Locked claims

The following remain false or `NOT_RUN`:

- runtime process placement and E5B integrated launch;
- route-wide actual-peak authority;
- E3-child-peak relabelling and post-run-derived upper;
- current-access and formal V7 authority;
- FQ11 counter completeness;
- formal CounterRecords, WorkVector, ComparisonVector and projection proof;
- official execution, scalar cost and break-even;
- `COUNTER_COMPLETENESS_GATE` and `WORKLOAD_ECONOMICS_GATE`.

Passing E5A establishes only a bounded prelaunch cgroup admission package.  It
prepares E5B; it does not complete the nine shared-resource sources or the
project's scientific objective.
