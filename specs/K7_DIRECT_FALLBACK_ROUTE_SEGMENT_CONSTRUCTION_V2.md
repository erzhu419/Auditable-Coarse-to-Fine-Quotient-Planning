# K7 direct-fallback route-segment construction V2

Status: Contract 2.0.44 construction control. This profile is not a production
fallback implementation and does not issue a CounterRecord, WorkVector,
ComparisonVector, terminal certificate, or Gate result.

## Frozen purpose

The historical five-stage root-cap runtime and its Contract-2.0.36 source
inventory remain byte-for-byte unchanged. Contract 2.0.44 adds a separate,
single-stage V6 chain for testing owner-bound route accounting without
relabeling any V1 artifact. The chain is:

```text
route-segment start
  -> DIRECT_FALLBACK stage start
  -> zero or more positive primitive events
  -> stage completion
  -> segment completion | segment abort
```

An absent event is unknown, never an inferred native zero. Abort retains every
positive event already issued.

## Exact construction manifest

The additive manifest contains exactly these seven SUM paths:

```text
control.cap_checks
control.cap_rejections
fallback.states_expanded
fallback.actions_evaluated
fallback.ground_steps
fallback.outcome_rows
fallback.bellman_backups
```

It freezes the complete source bytes, symbol AST, literal dispatch, unit amount
and call location of seven methods in
`DirectFallbackOwnedOperationSourceV2`. It also freezes the exact
Contract-2.0.36 parent manifest ID, fallback-site ID, parent manifest document
digest and parent site document digest. Missing, extra, nonliteral, relocated
or mutated source calls block replay.

These seven methods are deliberately a construction/test shim. Calling one
method is not evidence that a fallback business primitive occurred. Therefore
this manifest must never be relabeled as a production source manifest.

## Runtime authority boundary

The active runtime is inactive by default. In an active segment it requires:

- the exact independently replayed construction manifest;
- one V6 `DIRECT_FALLBACK` stage;
- literal unit events only;
- the frozen gateway and immediate source-owner module/globals/code;
- one owning thread and no nested active scope;
- session-code ancestry for every chain node and transcript.

Direct session emission, a readable issuer token, a readable gateway token,
duck-typed manifests, exact-class path relabeling, live owner deletion or
replacement, gateway replacement, and `sys._getframe` substitution all fail
closed. This is Python-API spoof resistance for a construction control, not a
native-code or production process-isolation claim.

## Explicitly unresolved

The profile keeps local construction domains and marks central domain
registration pending. It issues no runtime owner evidence for the real
fallback solver. The next production slice must bind a new manifest directly
to seven real `_OwnedFallbackLedger` primitive sites, reproduce the exact V1
mathematics, and obtain trusted runner provenance. Because this construction
manifest is frozen, the production manifest must use a new version; it may not
rewrite Contract 2.0.44.

The later all-path join must still add nine independently supervised shared
resource receipts, eight derived reconciliation values and 178 explicit
stage-forbidden zeros before producing the 202-row V6 accounting chain.

## Acceptance evidence

The focused suite covers 31 lifecycle, source-replay and spoof attacks. An
independent read-only replay reproduced the real-token node attacks and the
`sys._getframe` gateway attack and accepted the profile only within the
construction-only claim boundary.

The global locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
