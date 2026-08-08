# K7 H1 Attempt-Wide Rejection Gate V1

Status: construction-only component of current contract `2.0.59-B`.

Profile: `construction_k7_h1_attempt_rejection_gate_v1`.

This component gives the shared-resource owner, business engine and fallback
engine one durable cap-rejection slot per `route_attempt_id`. It does not issue
a route decision, terminal classification, CounterRecord, WorkVector or
ComparisonVector.

## Identity and allocation

The gate spec contains only attempt-scope identity:

- `logical_occurrence_id`;
- `route_attempt_id`;
- caller-pinned lifecycle provenance;
- the canonical real path and `(st_dev, st_ino)` of a private local gate root.

Decision-point, transaction and shared-owner profile-core IDs are deliberately
excluded from the gate identity. They belong to the rejection request. This
allows transaction 2 to reuse the attempt gate but prevents it from obtaining a
second rejection slot.

Freezing a spec durably allocates one root record named by
`route_attempt_id`. Initializing the gate adds a second allocation record that
pins the gate-directory, coordination-lock and high-water-cursor
`(st_dev, st_ino)` pairs, plus the cursor's random genesis token and genesis
record ID. The same request is replayable; a changed provenance, gate,
directory, lock inode, cursor inode or cursor genesis fails closed. An existing
gate directory may not recreate a deleted parent allocation commit; even
deleting both parent allocation records and freezing the same spec again cannot
reinitialize that directory. A first initialization interrupted before its
parent allocation commit therefore closes fail-safe and requires a new attempt
identity. The root is local construction provenance only. A later
production activation must freeze one unique broker root; this component does
not prevent the same logical attempt from being independently created on two
unrelated filesystems.

## Commit protocol

Each rejection binds a distinct `rejection_request_id` and the current:

- decision point;
- transaction;
- shared-owner profile core;
- source kind and site;
- one of the nine shared-resource paths;
- limit kind, reservation upper, candidate, hard cap and reason.

The broker first writes and fsyncs canonical bytes as `intent.json`, then
atomically hard-links the same inode as `commit.json` and fsyncs the directory.
Recovery may only finish the exact durable intent. A different request,
including a byte-identical request with a different `rejection_request_id`, is
a protocol failure. An ACK is accepted only after replay proves the complete
same-inode intent/commit pair; it binds the owner receipt, event and snapshot.

Initialization also creates one inode-pinned append-only high-water cursor. Its
hash-chained states are exactly:

```text
OPEN
-> INTENT_DURABLE
-> COMMITTED_UNACKNOWLEDGED
-> ACKNOWLEDGED
```

The cursor advances only after the corresponding record has been fsynced. If a
crash leaves a durable record ahead of the cursor, exclusive replay validates
the record and advances the cursor. If any intent, commit or ACK is missing
below the cursor high-water mark, replay fails closed instead of returning
`OPEN`. A torn, malformed, nonmonotone or replaced cursor also fails closed.
The parent allocation binds its inode and genesis, so deleting or replacing the
cursor cannot create a new gate lifetime.

Cursor record hashes use a fixed construction-local domain and are not formal
Phase 3E CounterRecord identities. Because broker kernel credentials are still
unverified, this construction does not claim protection against a process that
already has arbitrary write access and deliberately truncates the same cursor
inode back to an earlier valid prefix. Production activation must remove that
write authority or add an independently trusted monotonic anchor.

Every commit is canonicalized and checked against the one-MiB durable-record
cap before publishing an intent or advancing the cursor. Oversized caller text
therefore rejects without creating `intent.json`, `commit.json`, `ack.json` or
changing the high-water cursor.

## Cross-process ordering

All cooperating side effects must run inside
`hold_h1_attempt_gate_open_for_side_effect_v1`. The context holds a shared
`flock` from the OPEN check until the side effect returns. Rejection commit,
recovery, ACK and atomic snapshot replay use the exclusive lock. Thus a side
effect and a rejection receive one kernel-serialized order. The deprecated
point-in-time `require_*_open` API always rejects because it cannot close the
check/use race.

Opening, reinitializing, and consuming an existing handle first safely open the
coordination-lock file and acquire the operation's shared or exclusive
`flock`. Only while retaining that lock may they read the high-water cursor or
dynamic intent/commit/ACK records, enumerate the validated layout, or
recompute the allocation identity that includes cursor state. Handle consumers
compare the directory and lock inodes against their pins before acquisition;
path-based open verifies the acquired inode against the parent allocation
before returning. Consequently a concurrent append cannot expose a valid
reader to a transient torn cursor tail.

Writer-shaped orphan temp files use the exact
`.tmp-<positive-pid>-<32-lowercase-hex>` grammar. Shared-lock validation may
recognize but never remove them. Cleanup occurs only while retaining the
exclusive gate lock; malformed names and non-private/non-regular matches fail
closed.

The three yielding lock contexts register a process-local `ContextVar` entry
keyed by exact gate ID and mode:

```text
ADMISSION_EXCLUSIVE
DEPENDENT_REPLAY_EXCLUSIVE
SIDE_EFFECT_SHARED
```

While one of those contexts is active, every ordinary public API targeting the
same gate rejects before path resolution, file opening or journal replay. This
includes open/reinitialize, direct commit, recovery, read, ACK, snapshot,
point-check, and all nested lock-context combinations. It prevents a single
thread or inherited execution context from waiting forever on a second open
file description for a lock it already retains. APIs for a different gate ID
remain usable. The sole same-gate exception is
`commit_h1_attempt_rejection_with_admission_lease_v1`: it consumes the active,
nonserializable admission lease and its already locked directory descriptor,
so it neither reacquires the lock nor opens a TOCTOU window.
The lease is bound to the creating thread and active context and serializes its
complete commit operation with a private mutex. Sharing one live lease across
threads or outside its context fails before journal mutation.

The lock is not native side-effect evidence. A later owner/dispatcher must
durably record reservation, start/existence, native evidence and settlement.

Dependent owner replay uses
`hold_h1_attempt_rejection_gate_for_replay_v1`. It takes the gate's exclusive
lock, completes cursor/commit recovery, and yields an issuer-created,
nonserializable typed snapshot containing the exact state and exact commit/ACK
objects (or Python `None`) while the lock remains held. The owner may then take
its own lock inside this context, establishing one gate-to-owner lock order for
joint replay.

## Frozen claim boundary

The implementation verifies local POSIX-style record mechanics, inode pinning,
idempotence, crash replay after published records, and cooperating-process lock
ordering. It explicitly keeps these false:

```text
production_activation_chain_verified = false
kernel_writer_credential_verified = false
filesystem_durability_model_verified = false
power_loss_recovery_empirically_verified = false
operational_io_accounting_connected = false
formal_counter_eligible = false
production_execution_authorized = false
official_execution_allowed = false
```

The standalone generic gate API still receives candidate, cap and reason as
caller parameters. In the Contract-2.0.59-B Owner-V3 path, however, the owner
derives the candidate from durable reducer state, reads the cap from its frozen
profile and fixes the reason before invoking this gate; the gate has no
known-not-started input. A later production activation must also establish
broker-only credentials, a unique root, real filesystem durability support and
native side-effect evidence.

## Required attacks

The registered tests cover:

- same and conflicting two-process rejection races;
- open, initialize and existing-handle validation blocked across a deliberately
  partial cursor append until the writer releases the exclusive lock;
- the complete three-context by ordinary-public-API same-thread reentry matrix,
  plus cross-gate access, the admission-lease commit exception and foreign-
  thread same/different lease calls;
- oversized commit rejection before any durable gate mutation;
- invalid ACK operands rejected before intent recovery or cursor mutation;
- transaction/profile changes sharing the same attempt slot;
- allocation under a different base;
- gate-directory, lock-inode and cursor-inode replacement;
- dynamic-tail/all-record deletion and cursor deletion;
- parent allocation deletion followed by attempted reinitialization;
- point-check rejection and lock-held side-effect ordering;
- crash after intent, commit and ACK publication;
- orphan commit/ACK rejection;
- transplanted identities, unknown records, strict orphan-temp cleanup and
  mutated objects;
- complete atomic snapshot/count invariants.

Real `SIGKILL`/power-loss matrices, fork-inherited-lock behavior, non-local
filesystem semantics and kernel credential isolation remain prerequisites for
production activation, not claims of this construction contract.
