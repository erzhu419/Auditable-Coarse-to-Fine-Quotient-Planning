# K7 sealed-source route segment V4

Status: proposed Contract `2.0.53`, construction-only. Contract `2.0.52` is
an explicit prerequisite. This document does not bump the global contract and
does not unlock official execution or either accounting Gate.

## Purpose

V3 constructs an owner-bound fallback session by reopening the repository
source through its live archive loader and by joining that source to live
filename identities. V4 is an additive, path-free construction successor. It
accepts only:

1. the canonical bytes of the sealed
   `acfqp.phase3e_fallback_owned_v2` source-archive member; and
2. the canonical bytes of the already verified V3 seven-boundary manifest.

V4 never invokes the V3 archive loader, `Path(__file__)`, cwd/repository
discovery, a kernel, a planner, or a fallback search while constructing the
authority or session.

## Exact byte authority

The verifier checks the complete source byte count and SHA-256, parses the
source only from the supplied bytes, and reconstructs the legacy V3 source
archive ID. It parses the manifest with the Phase-3E canonical JSON parser,
checks its complete document digest and content ID, and binds its single
source member to that archive ID.

All seven boundary rows are replayed against the V6 registry and direct
fallback stage profile. For every row V4 checks the boundary content ID,
dispatch, path, reducer, owner, source symbol, source digest/extent, complete
method AST, literal unit-call AST, and exact call location. Missing, duplicate,
unknown, non-unit, moved, or mutated sites fail before a session is issued.

## Runtime dependency is a typed blocker

The current exact sealed owner imports
`emit_owned_route_operation_v3`, `bind_owned_fallback_search_v3`, and
`finish_owned_fallback_search_v3`. The frozen V3 bind/finish authorizer accepts
only the historical V3 invocation and V3 activation accepts only the exact V3
session whose constructor uses the live loader. V4 therefore does not install
a duck recorder in the V3 context and does not bypass those authorizers.

Every V4 authority carries:

```text
SUCCESSOR_OWNED_ENGINE_IMPORTING_V4_GATEWAYS_REQUIRED
```

Production V4 activation deterministically raises that typed blocker. A later
sealed-source owned-engine revision must import the V4 gateway and define its
own exact bind/finish authorization before end-to-end owner integration can be
claimed.

## Construction harness and transcript semantics

The construction harness is explicitly distinct from production owner
execution. Harness events are labelled
`CONSTRUCTION_VERIFIED_SOURCE_REPLAY`; they never claim
`source_owned_runtime_event=true`.

The immutable start/event/terminal/transcript chain preserves V3 semantics:

- each event is exactly one `SUM` primitive from the seven verified sites;
- event sequence and predecessor IDs form one uninterrupted chain;
- cap-check and cap-rejection events remain ordinary positive primitives;
- completion requires a full seven-path ledger map whose positive values
  exactly equal the transcript and whose event count equals their sum;
- abort retains every already recorded positive event;
- missing events are not inferred to be zero; and
- no CounterRecord, WorkVector, ComparisonVector, FQ9 terminal, or production
  certificate is issued.

## Locked claims

```text
construction_only = true
production_owner_source_integrated = false
production_closure_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

This slice closes only the path-free sealed-byte construction prerequisite.
It does not execute H1 ground search and does not complete the nine shared
resource sources or formal accounting materialization.
