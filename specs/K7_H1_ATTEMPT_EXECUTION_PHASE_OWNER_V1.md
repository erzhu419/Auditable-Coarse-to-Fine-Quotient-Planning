# K7 H1 Attempt Execution Phase Owner V1

Status: construction-only component of contract `2.0.59-E-B`.

Profile key: `construction_k7_h1_attempt_execution_phase_owner_v1`.

## Closed scope

This profile adds an independent, attempt-wide phase authority. It does not
reuse the cap-rejection gate as a lifecycle phase bit. The only legal state
chain is:

```text
NORMAL -> CLEANUP_INTENT_DURABLE -> CLEANUP_ONLY
```

The transition is immutable and can occur at most once. Remaining in
`NORMAL` never overrides an independently durable attempt rejection. No state
or recovery path can return from either cleanup state to `NORMAL`.

The phase specification binds the logical occurrence, route attempt,
caller-pinned lifecycle provenance, exact rejection gate, anchored program,
handler registry, complete 154-row cleanup analysis and inode-pinned base.
It is deliberately attempt-wide rather than transaction-scoped. The
transition separately binds the failing transaction and decision point,
Owner-V3 runtime, Owner-V4 WAL binding, exact dispatch trace, dispatch profile,
observed-tail attestation, semantic closure, cleanup pass, primary event,
branch and the retained gate/Owner state.

## Durable layout and recovery

One private root contains an immutable allocation record for each route
attempt and one private attempt directory. The allocation binds root,
allocation-lock, attempt-directory, phase-lock and cursor device/inode pairs.
All schemas reject missing and unknown fields, mistyped integer identities,
changed modes, symlinks and content-ID mismatches.

The phase cursor contains canonical chained records. Genesis is atomically
published. A transition publishes and fsyncs its exact intent before any
non-genesis cursor frame, then creates a root-level hard-link seal, advances
to `CLEANUP_INTENT_DURABLE`, hard-links the commit and advances to
`CLEANUP_ONLY`. Intent, seal and commit therefore name the same inode and
bytes. If phase-local intent/commit and cursor are rolled back while the root
seal remains, replay restores the phase-local links and monotonically
reconstructs both cursor records.

Only a non-newline suffix that is a strict prefix of the uniquely expected
next canonical cursor frame is classified as a crash tear. Arbitrary suffixes,
complete corrupt frames, a torn genesis, cursor gaps, reordered records or a
second transition fail closed.

The root seal protects crash recovery and phase-local rollback while the
inode-bound private root remains intact. It is not an external monotonic
service: a privileged or same-UID adversary that coherently deletes or
re-signs the allocation, root seal and every phase artifact is outside this
construction claim.

The supported crash points are after intent fsync, intent-cursor fsync,
commit-link fsync and cleanup-cursor fsync. Subprocess exit tests establish
reopening convergence at all four boundaries.

## Lock and lease rules

The global order is:

```text
PHASE EX -> REJECTION GATE EX -> OWNER EX -> native resources
```

Phase initialization additionally serializes the root allocation and attempt
phase locks before touching temporary files, the specification, cursor or
allocation. Normal, transition-only and cleanup-phase leases are mutually
exclusive, PID- and thread-bound, nonserializable and backed by non-inheritable
descriptors. Phase leases cannot nest. If a process forks while retaining a
lease, normal child-side context unwinding closes only the child's copied
descriptors and clears only its copied logical context; it never issues
`LOCK_UN` against the shared open-file-description. Only the creating
PID/thread may unlock. A foreign thread finalizer retains the descriptors and
fails closed rather than closing another thread's process-wide FDs.

The normal-phase lease requires both phase `NORMAL` and gate `OPEN`. The
transition-only lease requires phase `NORMAL` but deliberately permits an
already closed gate; it authorizes only an attempted phase transition. The
cleanup-phase lease requires the exact committed transition ID. Publishing an
exact intent immediately poisons the originating normal/transition lease. The
implementation conservatively consumes that process-local lease immediately
before immutable publication begins, so a pre-link error requires a fresh
lease and a post-link cleanup error can never reopen the old one.

Replay observes phase and rejection-gate state while retaining both locks in
the registered order. Its output is an atomic diagnostic snapshot, not a
production execution capability.

## Evidence and claim boundary

The callback-failure positive control consumes an issuer-retained,
exact-current Owner-V4 tail attestation under the retained phase and gate
locks, replays the exact Owner tail, validates its gate join, and publishes one
durable transition. A stale tail, crossed trace, closure, registry, cleanup
pass, owner, attempt or gate is rejected before intent publication.

This contract supplies only the phase primitive. The phase leases retain the
gate lock, while historical dispatcher and Owner public entrypoints attempt to
reacquire that same gate. They therefore cannot yet be used as phase-aware
normal or cleanup execution APIs. In particular, the historical dispatcher
cannot both create a cap-rejection trace and activate Owner V4 after the gate
has closed; historical post-rejection exact-prefix attestation is also
unavailable. These limitations are recorded as false claims rather than
hidden behind the transition-only lease.

The following remain false or absent:

- phase-aware normal dispatch and admitted-no-event recovery;
- historical cap-rejection-to-transition integration;
- a pre-admitted cleanup/output/readback envelope;
- a cleanup control journal and cleanup executor;
- conditional absent-role skip and output/readback fixed point;
- production current-access and formal V7 route authority;
- formal `CounterRecord -> WorkVector -> ComparisonVector` issuance;
- terminal/campaign closure and complete-bundle verification;
- official execution, scalar break-even, economics, Counter Completeness and
  sample-efficiency Gates.

The next additive contract must introduce retained-lease-aware normal-site
control journaling before presenting either normal or cleanup work as
executable under this phase authority.
