# Partial-support total lift and lossless parallel execution

Status: nonauthorizing repair construction
Proposed contract: `1.39.0`
Profile: `v074_partial_support_total_lift_parallel_execution_v0`

## Purpose

V0-072 attempt 2 failed closed after four completed occurrences.  The
matched-direct runtime produced a route-native certificate at its `16384`
checkpoint, but the standalone exact evaluator required the selected policy
to contain actions for every exact positive-probability child state.  That
requirement disagreed with the already-frozen partial-support semantics:
an exact outcome outside the frozen row support is represented by the
typed `ABSORBING_POLICY_ABORT_FAILURE` handler.

This revision repairs that boundary without changing a historical attempt,
reusing its target evidence, or treating its durable prefix as a scientific
endpoint.  It also freezes two lossless execution optimizations needed before
another confirmatory campaign:

1. a pre-target, content-addressed source proposal archive; and
2. occurrence-level process parallelism with private child journals and a
   canonical ordinal merge.

Neither optimization may change a draw, checkpoint, exact `Fraction`,
confidence allocation, planner cap, selected plan, certificate, or endpoint.

### Current implementation boundary

The current `1.39.0` slice implements the exact partial-support lift and a
registered synthetic transport/scheduling control. The frozen-source envelope
accepts canonical source bytes and preserves offline work, but it does not yet
semantically compile the production V0-072 proposal schema. The registered
parallel workers are synthetic and are not the production V0-072 occurrence
worker. Production proposal consumption, campaign execution, and endpoint
verification remain a later integration step under fresh identities.

Likewise, this mechanics slice does not claim the fresh-science obligation
that the exact held-out value/risk lies inside the operational statistical
envelope. That containment check requires a newly preregistered campaign and
independent complete-bundle verifier; it remains `NOT_RUN`.

## Historical boundary

The two V0-072 anchored attempts are immutable failed-attempt provenance.
Attempt 2 is:

```text
attempt_id       = a925bb7104727ccce81b4da5361fab9610638f5e6a35e46177faa3dfced4174a
closure          = CAUGHT_FAILURE
terminal         = ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE
completed        = 4 / 15 occurrences
result published = false
endpoint read    = forbidden
```

The old authority chain has no remaining attempt slot.  It may not be
resumed, retried, or combined with a later execution.  Its K7 data are
retrospective regression evidence only.  A future sample-efficiency claim
requires a separate preregistration, manifest and anchor plus fresh target
identities/tapes and genuinely fresh held-out occurrences.

## Exact partial-policy lift

### Bound modeled support

Before exact evaluation, the operational terminal authority must freeze one
content-addressed chain comprising
`RegisteredModeledPolicySupportAuthorityV1` and its
`RegisteredVerifiedOccurrenceRuntimeAdapterV1`. Across that chain it binds:

- occurrence, context, query, route, final model container/epoch and
  selected-plan identities;
- every distinct inverse ground realization of the selected root semantic
  action and its exact uniform weight;
- for each selected root realization, the frozen non-`OTHER` active child
  states with positive upper mass in that realization's operational root row;
- through the verified runtime adapter, the selected child decision and fixed
  concretizer for every such modeled child state; and
- the unique context/query-bound
  `ABSORBING_POLICY_ABORT_FAILURE` handler.

The support authority directly binds the replayed final model, row supports
and escape handler; the surrounding adapter binds the selected root/child
decisions. The terminal chain must expose explicit, independently auditable
references for the query, final model container/epoch, selected plan, every
required child decision and every fixed concretizer. The verifier must replay
the complete reference path; an opaque claim of transitive binding is not
sufficient.

The selected modeled child-state union must be a subset of the selected
child-decision domain.  A known modeled child without a decision is a protocol
failure, not an abort.  A mechanically extracted policy may also contain
decisions for model states reachable under nonselected root actions; these
remain typed dormant decisions and are not used for the selected recurrence.
They must not cause an exact outcome absent from the current root row's
modeled support to bypass `OTHER`.

### Exact evaluation rule

The standalone evaluator reconstructs exact ground rows from its
evaluation-only authority.  For every selected root ground realization and
every exact positive-probability outcome:

```text
environment failure
  -> charge exact environment-failure probability

nonfailure child in ModeledPolicySupportV1
  -> require its bound child decision
  -> integrate the complete fixed concretizer

nonfailure child absent from ModeledPolicySupportV1
  -> map to ABSORBING_POLICY_ABORT_FAILURE
  -> failure value 1
  -> continuation reward 0
```

An absent exact child must never be silently dropped.  Each such branch
produces a content-addressed witness binding the root realization, exact
child state, conditional probability, root concretizer weight and marginal
abort probability.

The exact selected-policy result must report:

```text
total_failure_probability
environment_failure_probability
policy_abort_failure_probability
```

with exact equality:

```text
total = environment + policy_abort.
```

The deterministic full-ground optimum remains the regret comparator.  The
escape handler is controller failure semantics, not policy randomization,
an added legal ground action, hidden-law access, or permission to omit a
modeled decision.

### Soundness checks

The independent verifier must establish:

1. the modeled-support authority is derived from the independently replayed
   runtime result, not supplied by the evaluator caller;
2. every modeled selected child has exactly one legal semantic decision;
3. every exact unmodeled child is charged once as abort;
4. no exact branch is both recursed and aborted;
5. no exact branch is omitted;
6. root and child fixed-concretizer weights remain exact, uniform and over
   distinct ground actions;
7. exact selected reward, failure and normalized regret are checked against
   the independently replayed operational robust envelope; the mechanism and
   attack tests are implemented, while validation under a fresh scientific
   statistical premise remains `NOT_RUN`; and
8. risk and normalized regret are recomputed against the independent
   deterministic ground optimum.

## Frozen source proposal archive

Source reconstruction is independent of every target occurrence and must not
remain on the target execution critical path.

The future production `FrozenSourceProposalArchiveV1` is created before target
access and binds:

- complete upstream source campaign/archive/verification identities;
- the exact proposal feature, ranking and abstention documents consumed by
  the target selector;
- ordered source-only commitments;
- source context and target context disjointness obligations;
- the complete offline source WorkVector reference; and
- a semantic verifier/profile identity.

The target runner may load only this verified proposal archive.  It may not
load a source runtime object graph, caller-supplied gain, target-derived
field, or post-target cache entry.  Loading the archive charges its actual
read/staging work; the complete source construction work remains reported as
offline work and is never converted to zero.

Standalone evaluation may reconstruct and replay the full source graph in a
separate evaluation lane.  Such replay is not operational target-route work
and cannot retroactively alter the frozen proposal.

Any archive identity, source commitment, proposal, verifier, context
disjointness, or upstream-work mismatch locks target execution before its
first observation.

The checked-in V0-074 envelope currently proves only byte sealing, external
identity binding, offline-work retention, source/target ID disjointness and
strict replay. It accepts a generic canonical source document and does not
claim production proposal-schema verification.

## Occurrence-level process parallelism

Parallelism begins only after the complete occurrence plan and all scientific
identities are frozen.

Each occurrence executes in an isolated process with:

- exactly one registered occurrence ID and ordinal;
- a private append-only child journal;
- no shared mutable attempt writer;
- no ability to execute another occurrence;
- seeds derived only from frozen scientific identities, never worker number,
  PID, launch order or completion order; and
- a content-addressed result/work/closure envelope.

The parent verifies every child envelope, then merges strictly by registered
occurrence ordinal.  For a successful campaign:

```text
sequential canonical result bytes
==
parallel canonical result bytes
```

for every allowed worker count.  Checkpoints within one occurrence and
adaptive rounds within one occurrence retain their registered order.

If any child fails, the campaign emits no scientific endpoint.  All already
launched child work and journals remain charged and referenced; sibling work
must not be deleted or rewritten as zero.  Process death, duplicate/missing
ordinal, cross-occurrence result, noncanonical merge, stale archive, or
worker-dependent output closes as a protocol failure.

Parallel execution changes wall-clock scheduling only.  It does not authorize
floating-point replacement, integer approximation, reduced draws, relaxed
caps, early checkpoint skipping, target-tape reuse, or confidence changes.

The current worker registry contains synthetic hash/failure controls only.
No production V0-072 campaign worker is registered in this slice.

## Acceptance tests

The current mechanics slice must pass the applicable tests below. The
envelope-containment obligation in Soundness check 7 is not a current
mechanics pass claim; it remains deferred until a separately preregistered
production integration:

1. a missing exact child contributes exact abort probability and zero
   continuation reward;
2. modeled-child omission, duplicate branch accounting and unbound escape
   handlers fail closed;
3. fixed-concretizer multi-root mixtures charge the correctly weighted abort
   probability;
4. exact total failure equals environment failure plus abort failure;
5. the historical attempt-2 exception becomes a regression fixture, not a
   rewritten result;
6. source archive byte/key/role/context/work tampering fails before target
   access;
7. the source archive does not contain target observations or identities;
8. sequential and `2..N` worker execution produce byte-identical canonical
   synthetic occurrence results;
9. reordered, duplicated, missing, transplanted and failed child envelopes
   fail closed while retaining launched work; and
10. no historical V0-072 result or sample-efficiency endpoint is minted.

## Gate state

This construction alone does not rerun V0-072 or open a scientific Gate.
Until a genuinely fresh held-out campaign has its own preregistration,
manifest, anchor, target identities/tapes and completed independent replay:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
total_objective_claimed = false
```
