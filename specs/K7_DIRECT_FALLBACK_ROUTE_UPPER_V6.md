# K7 direct-fallback V6 finite admission candidate

Status: construction blocker, Contract `2.0.46`. This artifact does not
authorize route execution or formal `actual <= upper` verification.

## Authority chain

The canonical H1 source is accepted only by replaying the durable exact
infeasibility proof against a separately issued current source/kernel/query
identity and reissuing the complete pre-execution candidate. Exact Python
type, a self-consistent document or a recomputed content ID alone is
insufficient. The selected route must be `FALLBACK`, and the registered seven
owner cardinalities are fixed at:

```text
control.cap_checks           56
control.cap_rejections        0
fallback.states_expanded      8
fallback.actions_evaluated   16
fallback.ground_steps        16
fallback.outcome_rows        96
fallback.bellman_backups     16
```

The route-order barrier consumes a typed `AccessEventLogV1` and independently
replays the official estimate-before-execute protocol. Kernel, materializer,
worker or fallback execution before the immutable decision boundary is
rejected.

## Exact candidate partition

The V6 operational upper contains exactly 182 leaf rows:

```text
166 stage-forbidden zeros
  7 exact typed H1 owner cardinalities
  9 finite shared-resource admission-cap candidates
---
182 operational leaf terms
```

Projection must contain the eight official shared-resource axes, in official
order, exactly once. Missing, duplicate, reordered, foreign or negative axes
fail closed.

## Deliberate blocker

The current in-process direct-fallback runner does not enforce all nine shared
resource caps at their operation owners. The nine rows are therefore marked
`UNENFORCED_SHARED_ADMISSION_CAP`, and the envelope kind is exactly:

```text
FINITE_ADMISSION_CAP_CANDIDATE
```

Consequently:

```text
formal_actual_compliance_eligible = false
authorizes_route_selection = false
execution_permitted = false
official_execution_allowed = false
```

No V1 upper is relabelled, no caller-supplied actual hint is accepted, and no
CounterRecord, WorkVector, ComparisonVector, terminal or Gate result is
issued. A successor must bind one preregistered cap profile to every real
shared-resource owner before any of these flags may change.

The global locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
