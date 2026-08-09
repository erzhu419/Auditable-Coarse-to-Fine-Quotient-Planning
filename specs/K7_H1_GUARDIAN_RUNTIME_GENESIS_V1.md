# K7 H1 Guardian Runtime Genesis V1

Status: additive bounded B2-B construction contract; no clone or birth.

Proposed contract: `2.0.59-E-C-E5B-B2-B`.

Profile key: `construction_k7_h1_guardian_runtime_genesis_v1`.

## Exact claim

B2-B consumes one exact issuer-live B2-A object in state
`PREPARED_SUCCESSOR`, builds a bounded source-closed guardian session, pins a
writable outer `cgroup.kill` capability without writing it, persists exactly
one `SUPERVISOR` birth intent, and persists exactly one unconsumed permit bound
to a new, distinct `CONTROL` `O_PATH | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW`
grant.  The exact B2-A object and the guardian session then move one way to
`RUNNING`.

B2-B contains no clone consumer and never calls `clone`, `clone3`, `fork`,
`vfork`, or a process launcher.  The permit says
`ISSUED_UNCONSUMED`, but `launch_authority_in_this_slice` is false.  A later
B2-C must consume a separately reviewed exact live object; durable bytes alone
do not confer authority.

The following bounded facts are true:

```text
bounded_guardian_source_closure_present = true
guardian_session_present = true
outer_cgroup_kill_pin_present = true
runtime_running_state_present = true
unconsumed_supervisor_birth_permit_present = true
distinct_control_opath_grant_present = true
```

## Deliberately limited source closure

The session opens, retains, reads in full and hash/replay-binds the exact files it
uses from B2-B, B2-A, E5A, V15, `phase3e_ids`, and the audit-only x86-64
trampoline source.  These are retained-FD hash/replay bindings, not kernel
content seals.  It retains and live-replays namespace and executable FD/OFD,
link and kernel identity; binds the exact single guardian PID/thread/start
tick, uid/euid/gid/egid, supplementary groups and kernel boot ID; and replays
import-time callable, `__code__`, global, class and layout identity.
Post-import monkeypatching of any consumed
B2-A/E5A/V15/ID helper fails closed.

The closure freezes Linux x86-64 LP64, syscall number 435, an 88-byte
`clone_args` layout, `SIGCHLD`, and these future intended flags:

```text
CLONE_PIDFD
| CLONE_PARENT_SETTID
| CLONE_CLEAR_SIGHAND
| CLONE_INTO_CGROUP
```

The `.S` file is comments-only audit source.  It is not assembled, mapped or
executed.

This is not a production full-source closure.  A fresh import of B2-B can
self-mint its own B2-B source expectation; neither the preregistration nor the
self source is anchored by an independent pre-existing authority.  Therefore:

```text
production_full_execution_source_closure_present = false
fresh_import_self_minting_externally_anchored = false
external_preregistration_anchor_present = false
assembled_or_executable_trampoline_present = false
```

The guardian path does not consume argv or environment inputs.  Its frozen
argv/environment input allowlist is empty.  Preregistration and durable
closure therefore observe and persist no argv/environment keys, values,
counts, equality digests, or aggregate digests.

## Writable kill pin and distinct grant

The outer `cgroup.kill` descriptor is opened before `RUNNING` as
`O_WRONLY | O_CLOEXEC | O_NOFOLLOW`.  It is a pre-frozen capability for a
future B2-C failure path, not evidence that B2-B can or did execute cleanup.
B2-B never writes this descriptor, including normal no-birth cleanup and all
fault paths.

The `SUPERVISOR` grant is a separate `openat(CONTROL, ".", O_PATH...)` open
file description.  B2-B checks same cgroup inode identity, different numeric
FD, `CLOEXEC`, and `kcmp(KCMP_FILE)==different`.  The grant FD is private; no
raw FD or `fileno` public API exists.

The handoff is pristine: all five B2-A candidate states must be `AVAILABLE`
and B2-A's frozen live-candidate registry must contain no object for this
runtime.  A previously issued B2-A candidate rejects B2-B before reservation;
it can never coexist with the private B2-B grant.

## Journal order

The private mode-0700 empty directory receives retained mode-0400 records in
this order:

1. bounded execution-source closure;
2. guardian-session genesis;
3. durable `SUPERVISOR` birth intent;
4. `SUPERVISOR` permit in `ISSUED_UNCONSUMED` state.

Every record is `O_EXCL`, `CLOEXEC`, file- and directory-fsynced, retained by
FD, content-addressed under its V15 domain, and replayed through the retained
FD and named inode.  This is process-level persistence, not a power-loss or
restart-recovery claim.

Immediately before the one `O_EXCL` open, B2-B registers one exact pending
transaction containing the canonical bytes, record ID, ordinal, filename, FD
slot and destination session field.  An interruption after open, a partial or
full write, file fsync, directory fsync, or final stat therefore retains both
the exact intended record and its canonical/lifetime-witness OFD.  Retry
truncates and rewrites that same retained inode, repeats both fsyncs, verifies
the named/retained identity, and finishes the in-memory publication
idempotently.  It never unlinks or adopts an unproved same-name file.  A
pending intent or permit is completed before the precommit-abort payload is
built, so the abort cites every real durable predecessor ID.

## Lock, signal, fork and FD ownership order

All bridge transitions use:

```text
B2-B lock
-> exact B2-A adapter lock
-> old E5A source-lease lock
-> exact B2-A runtime lock
-> E5A FD ownership lock
```

Every new FD and a distinct `F_DUPFD_CLOEXEC` same-OFD lifetime witness are
opened inside E5A's safe signal and fork-publication shield and published to
B2-B's exact ownership registry before signal restoration.
An FD-number collision with any registered owner fails closed and is never
silently transferred.

The public start wrapper retains an outer safe-signal mask from before any
session reservation through exact failed-session discovery and cleanup entry.
Precommit and normal cleanup retain the same shield across quarantine
state/registry transitions and every canonical close-to-retire pair.  Signals
are restored only after all project locks are released.  A deferred reentrant
handler therefore observes either an exact retryable state or the exact
`ABORTED_PRECOMMIT`/`CLOSED` terminal state, never split registries or an
unretired `EBADF` canonical descriptor.

At-fork callback registration makes the before-order B2-B, B2-A, E5A.  The
child after-order lets E5A raw-close its descriptors, B2-A poison its copied
runtime, and finally B2-B raw-close every source/namespace/journal/kill/grant
descriptor and poison the copied session.  The parent remains live.

Canonical close uses its retained lifetime same-OFD witness.  A
non-`EBADF` close ambiguity remains in close-only quarantine; a numeric reuse
that is not the witnessed OFD is never closed.  If canonical and witness no
longer name the same OFD, both remain registered in quarantine; B2-B guesses
neither.  The final witness has no nested witness and remains retryable.

## Exception and cleanup semantics

Before the commit, any exception after a durable intent or permit first
persists `ABORTED_BEFORE_RUNNING_COMMIT`.  It then closes or quarantines all
B2-B FDs and leaves the exact B2-A object `PREPARED_SUCCESSOR`.  If abort
persistence or a close remains
ambiguous, the raised typed error carries the exact quarantine handle for the
dedicated precommit retry; the runtime remains exclusively reserved and cannot
mint another session until retry closes the quarantine.  No unrelated earlier
session is selected by runtime identity.

The public start call also gives each invocation a private call token.  If an
exception lands after the starting-map entry is removed but before the caller
receives the session, cleanup falls back only to the exact reservation carrying
that token; it cannot select or close an older session.
If signal restoration raises after precommit cleanup has already reached exact
`ABORTED_PRECOMMIT`, the wrapper preserves the original construction error and
does not expose a terminal object as a retry handle.

After commit, any final verification error follows normal cleanup.  Audit
failure is retained as the primary error but cannot block revocation or
descriptor cleanup.

Normal cleanup is:

```text
persist REVOKED_BEFORE_CONSUMPTION
-> RUNNING session to CLEANUP_PENDING quarantine
-> close grant
-> close retained source, namespace and executable FDs
-> close journal record and directory FDs
-> close writable cgroup.kill pin without writing it
-> exact B2-A runtime RUNNING to CLEANUP_PENDING
-> move runtime to B2-A quarantine
-> release all B2-B/B2-A/E5A locks
-> call frozen B2-A cleanup
```

The B2-A runtime is never restored to `PREPARED_SUCCESSOR` or E5A `ACTIVE`
after the B2-B `RUNNING` commit.  A descriptor or B2-A cleanup failure remains
retryable in `CLEANUP_PENDING` and never writes `cgroup.kill`.

## Nonclaims

All of the following remain false/null/`NOT_RUN`:

- permit consumption or executable trampoline;
- clone/process birth or five-launch authority;
- shared PID cell or PIDFD escrow;
- cgroup membership, death or reap observation;
- peak read or route-wide actual peak;
- E3 V2 completion or production shared-resource receipts;
- FQ11 completeness, `CounterRecord`, `WorkVector`, `ComparisonVector`, or
  actual projection proof;
- current-access, formal V7, official execution, scalar or break-even claims.

## Acceptance tests

Default tests cover claim locks, domain-separated argv/environment redaction,
V2 clone ABI flags, audit-only trampoline bytes, caller-minted/copy rejection,
live-code monkeypatch refusal, and precommit rollback.  Delegated-cgroup tests
cover exact `PREPARED_SUCCESSOR -> RUNNING`, the four-record journal, writable
kill pin with zero writes, distinct CONTROL grant, commit finish-forward,
source/record mutation cleanup, same-OFD close quarantine/retry, fork-child
poisoning, and exact B2-A cleanup handoff.  Transaction tests inject faults
after open, partial write, full write, file fsync and directory fsync for both
precommit permit persistence and normal revoke persistence; they also verify
intent/permit IDs in abort records.  Signal tests cover cleanup-entry delivery,
precommit quarantine delivery, and delivery after kernel close but before
registry retirement with a reentrant close handler.
