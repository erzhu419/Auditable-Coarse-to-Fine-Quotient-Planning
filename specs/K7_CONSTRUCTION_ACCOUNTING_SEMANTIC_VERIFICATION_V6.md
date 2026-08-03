# Contract 2.0.56: exact V6 accounting semantic replay

Status: implemented construction verifier; no recorder-process, terminal, or
official-execution authority.

## Scope

This contract adds an independent semantic replay for the construction
accounting V6 chain.  It consumes retained native `CounterRecordV1` documents
as its only numeric source of truth, binds the exact V6 registry, stage,
comparison, and actual-projection profile identities, and deterministically
reconstructs:

```text
202 required CounterRecords
-> canonical WorkVectorV1
-> 182 operational projection terms
-> eight-axis ComparisonVectorV1
```

The portable record and vector byte shapes remain the existing V1 schemas;
their meaning in this verifier is supplied exclusively by the V6 registry and
profiles.  The implementation does not call or relabel the V1 semantic
verifier, V1 registry materializer, or V1 projection authority.

## Exact stage semantics

The caller must provide an exact registered `expected_stage_kind`.  The
verifier checks the frozen route-kind/stage-kind mapping and applies that
stage's official `allowed_nonzero_paths` directly.  Path-prefix heuristics are
not accepted.

For `DIRECT_FALLBACK`, the frozen partition is:

```text
required:     24 allowed / 178 stage-forbidden zeros
operational:  16 allowed / 166 stage-forbidden zeros
```

Every one of the 178 forbidden required paths must be present as an explicit,
observed zero CounterRecord.  The result publishes the exact forbidden paths
and corresponding record IDs.  This rule also avoids the inverse error of
rejecting stage-authorized common work on `REBUILD`.

## Replay obligations

The verifier requires:

- exactly one record for every required V6 path;
- no optional, evaluation-lane, unknown, duplicate, or missing path;
- exact registry metadata, lane, owner, unit, scope, reducer, and
  `observed=true` on every record, including native zeros;
- exact route, solver, and process reconciliation equations;
- exact route/stage nonzero exclusivity;
- exactly one registered projection term for each of the 182 operational
  leaves, with coefficient one and the registered semantics, reducer, and
  target axis; and
- byte-for-byte and ID-for-ID equality between recomputed vectors and any
  supplied WorkVector or ComparisonVector claim.

Caller-supplied vectors are equality targets only.  They never supply native
values or projection results.

## Honest boundary

This contract verifies accounting semantics, not source provenance.  It does
not prove which process emitted a record, authenticate per-record stage
provenance, issue a typed semantic attestation, classify a terminal, close a
logical occurrence, or establish `actual <= selected upper` for a production
route.  Those joins remain downstream obligations.

Therefore:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## Verification evidence

The focused suite covers profile identity mismatches, record completeness and
metadata, optional/evaluation injection, unobserved zeros, reconciliation,
claimed-vector substitution, exact projection, route/stage mismatches, all
178 direct-fallback forbidden-path injections, and the legitimate REBUILD
common paths.  Independent review reproduced the original stage-rule defect
and then passed the corrected 19-test suite with no remaining P1/P2 finding.
