# Phase 3E Preconstruction Limitations

Status: non-normative implementation boundary, 2026-07-20.

This note narrows the claim made by `PHASE3E_PRECONSTRUCTION.md`.  It is the
authoritative interpretation of the current Phase 3E code until the decision
ledger freezes the Phase 3E question packet and the missing verification
contracts are implemented.

## Highest valid claim

The current implementation exercises strict work-accounting records, a
diagnostic legacy projection, shared-axis comparison candidates, deterministic
route traces, transaction/cap guard candidates, and terminal-shape replay.

Its highest valid output is:

`TERMINAL_SHAPE_CLASSIFICATION_CANDIDATE`

It must not be interpreted as a plan certificate, an infeasibility certificate,
an official dynamic-routing decision, or an empirical workload-economics result.
Any older private helper type or status containing `CERTIFICATE_CANDIDATE` or
`PHASE3E_PRECONSTRUCTION_MECHANICS_PASS` is an internal construction artifact and
is non-authoritative.  The public envelope API exposes structural replay, not its
private certificate-named construction helper.

Every terminal-shape artifact freezes the following statuses:

- `SEMANTIC_EVIDENCE_GATE_NOT_RUN`;
- `COMBINED_CAP_PROFILE_NOT_FROZEN`;
- `CARDINALITY_FRONTIER_BINDING_NOT_FROZEN`;
- `WORKLOAD_ECONOMICS_GATE_NOT_RUN`;
- `COUNTER_COMPLETENESS_GATE_NOT_RUN`;
- `official_scalar_cost = null`;
- `official_n_break_even = null`;
- `official = false`.

## Remaining blockers

1. Evidence sidecars are caller-supplied consistency claims.  Role-specific
   domain verifiers must read the referenced artifact payloads, execute the
   registered checks, and account for their verification work.
2. A pre-route, acyclic derivation/input commitment must bind the semantic
   verifier profiles, cardinality inputs, comparison formulas, bounds, and cap
   identities before any route selection.
3. One combined cap profile must structurally define route-specific local,
   fallback, rebuild, and campaign caps.  Literal cap IDs in decision bindings
   are not sufficient.
4. Cardinality evidence and route bounds must be typed to the current context,
   transaction index, frontier, causal evidence, and cap identity.  This is
   required to prevent reuse of stale bounds across local-recovery transactions.
5. Phase 3C/3D host solver replay must become evaluation-only or be charged as
   native planning work.  The domain runner must estimate and freeze the route
   before local ground materialization.
6. The decision ledger must resolve Q1--Q11 and the follow-up question packet,
   including reducer semantics, scalar/no-scalar policy, occurrence ordering,
   reference-machine protocol, retry policy, and counter-completeness controls.
7. Persistent verification must replay a source manifest and every referenced
   source artifact; parsing a terminal-shape JSON currently verifies only that
   record's field set and self-hash.  Phase 3E also inherits the project's legacy
   `object_id` format, which truncates SHA-256 to 16 hexadecimal characters.
   Official auditable artifacts require a ledger-ratified full-length (or at
   least 128-bit) content ID and a migration/versioning rule.

Until all seven items are closed, terminal labels that look plan-like or
infeasibility-like describe only replay shape.  Protocol failure, rebuild
required, and fallback-cap exhaustion remain noncertificates; fallback-cap
exhaustion can never be promoted to `INFEASIBLE_QUERY`.
