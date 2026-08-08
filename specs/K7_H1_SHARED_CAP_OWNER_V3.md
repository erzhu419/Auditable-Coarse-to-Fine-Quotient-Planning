# K7 H1 Shared-Cap Owner V3

Status: construction-only focused component of current contract `2.0.59-B`.

This slice replaces process-local callback accounting with a durable,
content-addressed reducer/settlement journal for the nine H1 shared-resource
paths. It proves exact arithmetic over construction-asserted inputs, not yet
the truth of native observations. It does **not** activate production execution
and it does **not** issue formal
`CounterRecord`, `WorkVector`, or `ComparisonVector` artifacts.

## Frozen boundary

The exact path order is:

1. `common.hash_invocations` (`SUM`)
2. `common.integrity_checks` (`SUM`)
3. `common.protocol_checks` (`SUM`)
4. `io.mounted_bytes_peak` (`MAX`)
5. `io.output_bytes` (`SUM`)
6. `io.read_bytes` (`SUM`)
7. `io.staged_bytes` (`SUM`)
8. `memory.working_bytes_peak` (`MAX`)
9. `process.launches` (`SUM`)

Every hard-cap profile covers these nine paths exactly.  A missing, additional,
reordered, or reducer-mismatched path is invalid.

The profile is one decision-point/transaction segment. The rejection gate is
route-attempt-wide, but a future occurrence aggregate must retain and sum the
separate owner vectors for failed local, later transaction, fallback, rebuild,
and retry segments. Creating a new profile must never erase earlier work.

## Acyclic identity graph

The identity construction is deliberately one-way:

```text
ProfileCoreV3
  -> H1AttemptRejectionGateSpecV1
  -> RuntimeBindingV3(ProfileCore ID, gate ID, source-manifest ID)
```

`ProfileCoreV3` never contains a gate ID.  The gate commit field
`shared_owner_profile_core_id` denotes the core ID, not the runtime ID.  The
runtime binding may contain both IDs because it is downstream of both.  No
object contains its own final content ID in the hashed payload and no
profile/gate/runtime cycle is allowed.

The source manifest and core bind the same caller-pinned lifecycle provenance,
program snapshot, program, and branch-analysis IDs.  These are local
construction provenance, not a production source authority.

## Durable journal

The owner directory is private and contains three immutable static documents:

- `profile-core.json`;
- `source-manifest.json`;
- `runtime-binding.json`.

All dynamic records are canonical JSON files named by monotonically increasing
sequence and content ID.  Each record binds the previous journal head.  A new
record is written to a private temporary regular file, file-synced, published
without replacement, and followed by a directory sync.  Reopening and replaying
the directory is the only spend authority; Python object identity, callback
return values, and mutable in-memory counters are never authorities.

The private owner root also contains an inode-pinned high-water cursor token.
Its hard-link state names bind the committed sequence/head, or the one exact
pending next sequence/head. Each append advances `committed -> pending`,
publishes the exact journal record, then advances `pending -> committed`.
Replay reconciles only those adjacent states. Deleting a journal tail or all
numbered records, deleting/replacing the cursor, or deleting the parent
allocation therefore fails closed instead of replaying a shorter valid prefix.
A strict orphan `.tmp-PID-hex` link is removed only while holding the owner
lock; malformed or non-regular temporary names are rejected.

The first initialization is intentionally fail-closed rather than resumable.
A crash after allocating a runtime directory but before its complete cursor,
allocation and static-record set consumes that runtime identity; the same
identity cannot be reinitialized. Recovery requires a newly registered
transaction/runtime identity, and later production accounting must retain the
failed initialization work.

The journal schemas are:

1. reservation/admission, including the distinct
   `REJECTION_ADMISSION_DURABLE` outcome;
2. native cell;
3. native evidence;
4. settlement;
5. receipt;
6. event;
7. snapshot.

A reservation must be durable before the corresponding side-effect guard can be
entered. Entering the guard durably appends the reservation's unique
`SIDE_EFFECT_STARTED` native cell before yielding to caller code. A
`KNOWN_NOT_STARTED_ZERO` settlement instead appends a mutually exclusive
`KNOWN_NOT_STARTED` cell; it is rejected after a start cell exists. Re-entering
a started cell is rejected, so an ambiguous crash is settled conservatively
rather than re-executed. A settlement, receipt, event, and snapshot form one semantic unit. A
crash after any durable member is recovered by replay and may only complete the
same requested unit.  While a settlement, receipt, or event is the incomplete journal head,
every unrelated reservation, settlement, or rejection append fails closed;
this prevents a later record from making adjacency-preserving recovery
impossible.  Retrying the same request is idempotent; reusing an
operation ID with different path, upper, site, basis, native value, or evidence
source is a protocol failure.

Canonical bytes are checked against the eight-MiB owner-record limit before a
pending cursor state or journal file is created. An oversize caller field
therefore cannot advance the high-water cursor and make the journal
unreadable. Opening an existing owner holds its owner lock across cursor,
allocation and static-record replay. It opens and verifies the gate first, so
the global gate-to-owner lock order is preserved.

## Public construction API

The focused tests expect the following public surface in addition to the
already-defined profile/source/initialize/open/replay functions.

```python
reserve_h1_shared_cap_owner_v3(
    handle,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reservation_upper: int,
) -> H1SharedReservationV3

settle_h1_shared_cap_owner_v3(
    handle,
    reservation: H1SharedReservationV3,
    *,
    value_basis: H1SharedValueBasisV3,
    native_observed_value: int | None,
    evidence_source_id: str,
) -> H1SharedSettlementResultV3

hold_h1_shared_cap_owner_v3_side_effect(
    handle,
    reservation: H1SharedReservationV3,
) -> ContextManager[H1SharedSideEffectStartV3]
```

The guard validates that the reservation is durable, belongs to this runtime,
is unresolved, and has not been superseded by an attempt-wide rejection.  It
then holds the gate's cross-process OPEN lock for the whole native effect.  This
is a cooperative construction mechanism only; production kernel credentials
remain unproved.

The process-local reentrancy marker is keyed by attempt-gate ID as well as
runtime. A reserve, replay, synchronize, nested side-effect guard, or
cross-transaction settlement that would reacquire the same guarded gate fails
before I/O instead of self-deadlocking. Settlement for the runtime whose guard
is already active uses the retained gate ordering and may only settle its
durable reservation.

## Admission and reducers

For `SUM`, admission uses:

```text
candidate = charged + outstanding + reservation_upper
```

For `MAX`, admission uses:

```text
candidate = max(charged, reservation_upper)
```

V3 permits only one unresolved construction exposure per `MAX` path until a
later physical active-cell/refcount protocol is bound.  Settling `SUM` adds the
charged value.  Settling `MAX` takes the maximum of the prior charge and the
new charged value.  A value is never clipped to a reservation or hard cap.

## Construction assertions and charge bases

`native_observed_value` and `charged_value` are separate fields, but the former
is still supplied by the construction caller. The journal therefore uses
`construction_exact_value_assertion`; every evidence/receipt/replay keeps
`native_authority_verified=false` and
`evidence_source_authority_verified=false` until the production adapter binds
real source events and syscall evidence.

| Basis | Lifecycle/evidence state | Asserted value | Charged value | Nonconservative assertion |
|---|---|---:|---:|---|
| `CONSTRUCTION_ASSERTED_NATIVE_VALUE` | started, then caller assertion | nonnegative value | same value | yes |
| `CONSTRUCTION_ASSERTED_SOURCE_EVENT` | started, then unit-event assertion | exactly `1` | `1` | yes |
| `KNOWN_NOT_STARTED_ZERO` | durably not started | `0` | `0` | yes |
| `CONSERVATIVE_RESERVATION_UPPER` | ambiguous at cutoff | typed null | reservation upper | no |
| `OBSERVED_OVERRUN` | observed | value greater than reservation | same value | yes |

Unit-event assertions are allowed only for the three `common.*` paths and
`process.launches`; magnitude assertions are allowed only for byte/peak paths.
An asserted value above its reservation must use `OBSERVED_OVERRUN`. An overrun
is durably preserved without clipping and marks `upper_bound_violation=true`.
Durable overrun evidence immediately poisons replay, even before settlement;
its exact evidence-to-settlement continuation is the only allowed append. No new
reservation or side-effect start is allowed, while existing cleanup settlement
remains possible. A future dispatcher must promote this to an attempt-wide
typed protocol-failure closure; V3 does not claim that global terminal.
Conservative settlement is an upper charge and is never described as a native
observation.

## Attempt-wide cap rejection

If admission exceeds a hard cap, no owner reservation and no native side effect
may start.  The broker performs this exact order:

1. durably commit the one-shot attempt rejection in the shared gate;
2. append the exact owner `REJECTION_ADMISSION_DURABLE` record that binds the
   operation, reducer and accumulator prestate used by that commit;
3. append one owner `CAP_REJECTION` receipt;
4. append its matching event;
5. append the owner snapshot with `control_cap_rejections=1`;
6. durably acknowledge the gate with those three owner IDs;
7. raise `H1SharedCapOwnerV3Rejected`.

The same deterministic request may replay that result.  A different second
rejection is a protocol failure.  Once the rejection intent is durable, the
owner, business engine, fallback engine, and all later side-effect guards share
the same closed attempt-wide gate.  A rejection contributes no resource-path
charge; its registered control rejection count is exactly one.

The reservation request ID used by the gate must be content-derived from the
runtime, operation, site, path, reducer, reservation upper, candidate, hard cap,
and reason.  It must not depend on process-local state.

Gate-first ordering is mandatory across transaction owners. A crash after the
gate commit but before owner admission is
`LOCAL_COMMIT_AWAITING_ADMISSION`: all transactions see the attempt closed,
and only a retry with the exact operation/site/path/upper can append the
missing admission and finish the pair/ACK. Generic synchronization does not
invent that evidence. Static context, limit kind, reason, profile hard cap and
the still-frozen reducer candidate are checked before this prefix is labelled
recoverable. New local settlement is blocked until recovery; completion of an
already durable settlement-to-receipt frontier remains allowed because it
does not change the rejection prestate.

The gate is attempt-wide but each owner is transaction-bound. A rejection
owned by another profile is reported explicitly as an external attempt
rejection. Its local pair is not falsely marked verified; the later attempt
aggregate must resolve the other owner's typed ACK references. A closed gate
still permits exact lookup of an already durable local reservation, allowing a
restarted process to finish known-zero or conservative cleanup without
admitting new work.

A pending cursor created before an admitted reservation record is published may
be completed after another transaction closes the gate only by operands that
recreate its exact content ID. A different request cannot close the gate or
replace the pending append through this owner's pending continuation. If the
pending record is the durable-before-effect
start cell, no effect is re-executed; only the exact conservative settlement
may complete that ambiguous prefix. Exact and known-zero settlement are
rejected.

## Replay, idempotence, and attacks

Independent joint replay takes the gate lock before the owner lock and rejects:

- noncanonical JSON;
- unexpected fields or schemas;
- content-ID or filename mismatch;
- sequence gaps, duplicates, or previous-head forks;
- changed static profile/source/runtime bytes;
- a foreign reservation, native cell, evidence, settlement, or owner pair;
- duplicate spending of one operation;
- different retry semantics under one operation ID;
- settlement/receipt/event/snapshot reordering, burial, duplication, or mismatch;
- an owner rejection not equal to the exact committed gate rejection;
- an ACK whose receipt/event/snapshot IDs differ from the exact owner pair;
- directory symlinks, non-private files, unknown files, and runtime transplants.

Concurrent processes operate under an inode-pinned advisory owner lock and the
attempt gate's inode-pinned coordination lock.  Two processes retrying one exact
operation must converge to one reservation, one settlement, and one charge.
Distinct operations remain distinct journal spends.

Gate-commit-before-owner-admission, owner-admission-before-pair, lifecycle
cell/evidence-before-settlement, settlement/receipt/event frontiers, and
owner-pair-before-ACK are explicit `recovery_required` prefixes, not replay
successes. `synchronize_*` first recovers an intent-only gate to the same
commit; it may append/replay the pair and ACK only after exact owner admission
evidence exists. Missing admission requires the exact reserve request. A
completed historical settlement returns its frozen pair even if a later
transaction owns the attempt-wide rejection.

## Claim boundary

Every core, source, runtime, journal record, snapshot, replay, and gate artifact
keeps these claims false:

```text
production_activation_chain_verified = false
real_syscall_adapter_bound = false
kernel_writer_credential_verified = false
formal_actual_compliance_eligible = false
formal_counter_eligible = false
formal_counter_records_issued = false
formal_work_vector_issued = false
formal_comparison_vector_issued = false
production_execution_authorized = false
official_execution_allowed = false
native_zero_eligible = false
```

The construction validates local POSIX mechanics, exact reducer arithmetic,
durable lifecycle ordering, high-water rollback detection and joint gate/owner
replay for cooperative writers. It does not yet prove a unique production root, broker OS
credential exclusivity, upstream snapshot semantic rebinding, resolved formal
resource operands, persistent route-decision/current-access authority, full
dispatcher cleanup, power-loss behavior on the target filesystem, operational
I/O accounting, or the final `CounterRecord -> WorkVector -> ComparisonVector`
chain.

Because production writer credentials are not yet isolated, this local cursor
does not claim resistance to a same-UID attacker that can deliberately recreate
an earlier valid cursor-link state and matching journal prefix, delete the
entire root, or restore a filesystem/VM snapshot. Production activation needs
broker-only filesystem authority or an independent monotonic anchor. Cursor,
recovery and cleanup work must itself be charged by the later formal recorder.

## Focused acceptance tests

The V3 slice is accepted only if tests cover:

1. ProfileCore -> gate -> runtime acyclicity and identity mismatch rejection;
2. durable reserve-before-side-effect ordering;
3. exact `SUM` and `MAX` reducer replay;
4. all five construction assertion/charge bases and their path restrictions;
5. crash and exact retry after every settlement-chain record;
6. idempotent retry and conflicting operation reuse rejection;
7. cross-process single spend;
8. canonical-byte, sequence/head, pair-burial, high-water rollback, cursor,
   allocation, unknown-file, and transplant attacks;
9. cap rejection owner receipt/event/snapshot followed by gate ACK, including
   gate-first/missing-admission recovery, external-transaction ownership,
   intent-only recovery and forged cross-journal rejection;
10. durable start versus known-zero, overrun poison, stale-gate initialization,
    orphan-temp cleanup, partial-initialization identity consumption, and
    historical-pair retry across another lifecycle frontier;
11. owner-open/cursor and gate/owner lock-order concurrency, same-gate
    reentrancy rejection, pre-write size limits, exact pending reservation/start
    convergence, producer/replay semantic equivalence and no-mutation failure
    paths;
12. all production, native-authority, formal-actual, native-zero, and official
    claims remaining false.
