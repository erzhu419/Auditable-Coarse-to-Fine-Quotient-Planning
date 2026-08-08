# K7 H1 Owner Cleanup Continuation Sidecar V1

Status: additive construction contract 2.0.59-E-C-C. This document does not
modify or relabel the frozen Owner V3 journal, Owner V4 pending-payload WAL, V2
cleanup transition, cleanup analysis, or cleanup pass.

## Closed boundary

One content-addressed sidecar allocation binds all of the following:

- one exact V3 runtime and V4 WAL binding;
- the exact V3 sequence/head cutoff named by a committed V2
  `NORMAL -> CLEANUP_ONLY` transition;
- one admitted, unsettled deferred-origin reservation;
- the V2 pre-admitted envelope, selected cleanup pass, and one exact planned
  cleanup action;
- the retained phase/gate snapshot and its verified Owner join.

The storage base is not caller-selectable. It must resolve to the exact
realpath/device/inode frozen by the attempt phase spec; the one sidecar root is
derived beneath that base. Consequently the same runtime/reservation cannot be
allocated in a second filesystem root to evade its reservation-scoped seal.

The reservation is either `memory:bind-working-hierarchy` on
`memory.working_bytes_peak` or `output:reserve-route-wide` on
`io.output_bytes`. The action must be the matching conservative action already
present in the selected pass.

## Only legal operation

The sole sidecar operation is:

`CONSERVATIVE_RELEASE_WITHOUT_NATIVE_START`

It records:

- `native_observed_value = {kind: NOT_APPLICABLE, reason:
  NATIVE_EFFECT_NOT_STARTED}`;
- `charged_value = reservation_upper`;
- reducer-correct combined charged state;
- combined outstanding reduced by the reservation upper exactly once;
- `native_effect_started = false`;
- `memory_read_performed = false`;
- `output_finalize_performed = false`.

Calling the operation again is idempotent: it returns the same immutable
release and does not append a second cursor record or apply a second spend.
Allocating the same V3 reservation with crossed transition/action semantics is
rejected by the reservation-scoped root allocation seal.

## Durability and replay

The sidecar owns a private directory, immutable allocation, stable lock and
append-only cursor inodes. The allocation and release each have a root hardlink
seal. Recovery reconciles these monotonic states:

1. no release and genesis cursor;
2. release fsynced but root seal absent;
3. release and root seal durable but cursor still at genesis;
4. release cursor committed.

A surviving root release seal can restore the in-directory link. A surviving
release can restore the root seal. A torn cursor suffix is truncated only to an
already verified complete prefix and only when the suffix is a strict byte
prefix of the unique deterministic next cursor record. Missing, replaced,
crossed, reordered, or multiply appended durable state fails closed.

The combined verifier holds `PHASE -> GATE -> OWNER -> SIDECAR`, revalidates the
exact V2 identities and Owner cutoff, and first performs a read-only stable-V4
preflight. A pending cursor, adjacent cursor state, temp link, or WAL payload is
rejected without repair and without mutation; recovery remains owned by the
historical Owner runtime. The verifier then applies the one sidecar release to
the unchanged V3 state. No V3 record or V4 payload is appended.

## Explicit non-claims

This sidecar provides no native cleanup capability, memory read, output
finalization/readback, output-owner close, arbitrary cleanup executor, current
access authority, formal CounterRecord, WorkVector, ComparisonVector, V7 route
authority, attempt closure, terminal classification, production execution
authority, or official execution permission. All corresponding flags remain
false.
