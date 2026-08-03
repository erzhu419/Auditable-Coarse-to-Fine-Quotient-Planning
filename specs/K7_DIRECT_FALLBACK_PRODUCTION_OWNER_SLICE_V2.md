# K7 direct-fallback production-owner slice V2

Status: construction evidence only. This slice integrates real fallback
business primitives, but it does not close the 202-row accounting chain or
issue an FQ9 terminal.

## Exact implementation boundary

`phase3e_fallback_owned_v2.py` contains an independent copy of the V1
deterministic finite-horizon exact search. It does not call or wrap
`run_ground_fallback_search_v1`. Its `_OwnedFallbackLedgerV2` owns seven
literal unit-emission sites at the actual primitive boundaries:

```text
control.cap_checks
control.cap_rejections
fallback.states_expanded
fallback.actions_evaluated
fallback.ground_steps
fallback.outcome_rows
fallback.bellman_backups
```

The transition reservation and its `ground_steps` event occur before the
kernel call. Positive outcome-row events are retained before an oversized-row
protocol failure. A cap denial retains all preceding work and emits one
rejection event; it never becomes an infeasibility certificate.

The route session binds exactly one ledger instance to the active frame of the
frozen authorized owned-search executor. Every owner site must receive the
acknowledgement of the event it just appended before changing its native
counter. Direct calls to the real ledger outside that search frame fail before
mutation. Search completion independently reconciles all seven ledger values
and the complete event chain, so a temporarily disabled and then restored
gateway cannot hide work from a completed transcript.

## V3 source and runtime binding

The V3 boundary manifest freezes the complete owned-solver source bytes,
seven method ASTs, seven literal-call ASTs, call locations, V6 leaf metadata,
and the exact V2 construction-manifest parent. At owner-module import it also
freezes the original ledger class, seven exact function/code/global identities,
and the gateway object/global/code identity independently. Source replay joins
every archived method AST to those identities;
an unchanged disk archive cannot authorize a replaced runtime class or method.
Missing, extra, nonliteral, relocated, mutated, relabelled, runtime-replaced or
validator-substituted calls block replay. In-place replacement of the gateway,
any owner method, or either binding validator's `__code__` is also rejected;
the live-binding ID is derived from the already-verified import-time code
objects rather than mutable current attributes.

The V2 manifest and its Contract-2.0.36 parent are replayed rather than
silently rebased. Their historical manifest/site IDs and document digests
remain exact acceptance requirements. A dedicated fresh-Python-process test
also requires the clean V3 archive to replay as `VERIFIED`, preventing a
long-lived interpreter with stale module constants from being mistaken for a
source migration.

The active V3 route-segment runtime requires the exact replayed manifest,
frozen gateway, immediate source-owner globals/code, one thread, one active
scope, one issuer-created ledger, the frozen search invocation, and exact
session ancestry for all transcript nodes. It is inactive by default. The
session and runner recheck the import-time class, all seven methods and gateway
before ground execution, at every delivered event, and again before
completion; the owner sites additionally reject a missing event
acknowledgement before counter mutation.
Same-name/same-literal classes built with `exec` are rejected. This is a
Python construction control, not a native-code or process-isolation claim.

## Authorized canonical H1 runner

The canonical runner first freezes and replays:

```text
durable/current identity
-> exact preregistered cardinality
-> fallback cap and upper
-> marginal FALLBACK decision
```

Only then does it activate the owned route segment and access the ground
kernel. The registered H1 exact-infeasible fixture yields:

```text
fallback.states_expanded      8
fallback.actions_evaluated   16
fallback.ground_steps        16
fallback.outcome_rows        96
fallback.bellman_backups     16
control.cap_checks           56
control.cap_rejections        0
positive operation events   208
outcome                       INFEASIBLE_CERTIFIED
```

The zero rejection value is verified in the exact solver transport. The
positive-event transcript contains no fabricated zero event.

The standalone evaluation-only parity verifier reruns both the owned search
and historical V1 search and compares the exact frontier, outcome, selected
policy state, composed-candidate count, and all native counter values. Its
work is not operational route work.

## Deliberately unresolved

This slice emits no V6 CounterRecord, WorkVector, ComparisonVector, typed
semantic attestation, campaign closure, or terminal artifact. The later join
must still bind nine shared-resource receipts, eight derived reconciliation
values, and 178 explicit stage-forbidden native zeros before materializing the
202-row DIRECT_FALLBACK chain.

The locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
