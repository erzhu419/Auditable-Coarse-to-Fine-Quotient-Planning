# K7 H1 Anchored Lifecycle Construction Dispatcher V1

Status: construction-only focused component of current contract `2.0.59-C`.

This slice connects the caller-pinned local-Git lifecycle snapshot from
Contract 2.0.59-A to the durable construction owner from Contract 2.0.59-B.
It freezes an ordered typed dispatcher and a byte-level replayable trace.
It does **not** bind production hooks, prove native observations, or authorize
official execution.

## Anchored program and handler registry

The registry is rebuilt from the verified Git blob, not from mutable worktree
JSON. It accepts exactly:

- 62 ordered lifecycle sites;
- 16 operation families;
- 143 declared failure edges;
- 144 declared first-failure branches; and
- all nine shared-resource paths.

The loaded candidate module is used only as an equality cross-check. Its old
Owner-V2 method strings remain migration annotations and are never resolved by
dynamic `getattr` dispatch. The exact handler partition is:

| Handler mode | Count | Construction action |
|---|---:|---|
| immediate unit settlement | 5 | reserve, hold, callback, settle one event |
| immediate magnitude settlement | 41 | reserve, hold, callback, settle magnitude |
| deferred-origin admission only | 2 | reserve only |
| deferred completion | 2 | reuse origin reservation, hold, callback, settle |
| no-charge lifecycle control | 12 | callback only |

There are 48 reservation sites and 46 immediate settlements. All 48
reservation uppers are frozen before the first callback and bind the anchored
program/registry, Owner-V3 runtime and the exact
occurrence/attempt/decision/transaction context. A caller can execute only the
next site in the frozen program; it cannot select a site, path, reducer,
operation identity, or new upper at dispatch time.

## Deferred-origin restriction

The following two origins are deliberately admission-only:

- `memory:bind-working-hierarchy`;
- `output:reserve-route-wide`.

At the origin, `SUCCESS` means only that Owner V3 durably admitted the frozen
reservation. There is no side-effect hold, callback, native cell, evidence, or
settlement. The corresponding completion reuses the origin reservation and
only then performs hold, construction callback and settlement. Its Owner
reservation operation identity remains the origin site's identity.

This restriction is required because the current Owner-V3 construction
frontier rejects unrelated appends behind a started-but-unsettled native cell.
It is not evidence that a real long-lived memory hierarchy or output stream has
been started. Native start and lifetime binding remain obligations of the
later live-hook activation contract.

## Construction dispatch semantics

For charged immediate/completion sites, the dispatcher enforces:

```text
durable reservation
  -> durable side-effect-start cell
  -> one construction callback
  -> exact or conservative settlement
```

Callback shape is checked before any Owner mutation. A missing or forbidden
callback therefore raises without an event and can be corrected before retry.
Callback exceptions and invalid returned magnitudes occur after admission and
therefore settle the frozen reservation upper conservatively before normal
dispatch closes. An aggregate cap rejection happens before callback invocation.
An observed value above its reservation is retained without clipping and
poisons later work.

Process-local recursive dispatch, Owner entrypoint drift, skipped/reordered
sites, crossed profile/runtime identities, any extra Owner record, and an
attempt-wide gate closure by another transaction fail closed. Pre-admission
validation and protocol errors need not emit an event or close a retryable
session. These checks are construction safety checks; callable-code
fingerprints are neither loaded-byte provenance nor source authority.

## Trace replay and Owner join

Every event binds its exact schema/content ID, dispatch context, site/order,
handler mode, operation identities, frozen operand, callback result class,
state transition, prior event, and Owner journal sequence/head interval. The
trace verifier replays the declared state machine and joins every charged event
to the durable Owner-V3 chain:

```text
reservation
  -> native cell
  -> evidence
  -> settlement
  -> receipt
  -> event
  -> snapshot
```

It verifies journal sequence/head continuity, path/reducer/site/value basis,
charged and outstanding values, deferred pairs, mount ambiguity, and exact
coverage of the Owner record set. The trace snapshot also binds the current
attempt-gate join, rejection commit/ACK and new-work state. Coherently re-signed
context/operand/role or future-field changes, out-of-band Owner appends, and an
external transaction closing the attempt gate are rejected. A 62-site
success trace may claim only `full_declared_success_reached`; it does not prove
that every production failure continuation exists.

Owner V3's journal is durable. The dispatcher events and trace are currently
in-memory content-addressed documents and are not crash-safe exactly-once
records. The callback values and frozen uppers are construction assertions,
not native evidence.

## Failure boundary

A callback failure, cap rejection, overrun, or other failure that produces a
dispatch event closes normal forward dispatch and records a provisional
first-failure prefix only. A pre-admission validation/protocol error may issue
no event and may leave the session retryable. Contract 2.0.59-C does not execute
the remaining cleanup continuation, close the attempt, classify a terminal, or
issue a certificate.

## Explicit non-authorities

This contract does not provide:

- production source or loaded-execution-byte/TOCTOU authority;
- production live-hook or kernel-credential binding;
- native extent, cardinality, cgroup or physical-instance evidence;
- complete post-first-failure cleanup continuations;
- branch-complete output-role/readback joins;
- a current-access atomic/post-freeze bridge;
- a joint output/read fixed point or formal numeric operands;
- a formal V7 route upper or route decision;
- formal `CounterRecord`, `WorkVector`, or `ComparisonVector` artifacts;
- terminal/campaign closure or a complete-bundle verifier; or
- workload-economics or sample-efficiency evidence.

The required lock state is therefore:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## Next construction boundary

The next stage must add the complete first-failure cleanup program and bind
output-role leaf selection to readback without changing this trace's claim.
Production activation and the current-access/output-read authority chain remain
separate later stages. Only after those boundaries close may the formal V7 and
accounting artifacts be constructed.
