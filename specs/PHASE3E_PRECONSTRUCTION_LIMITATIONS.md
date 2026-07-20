# Phase 3E Preconstruction Limitations

Status: non-normative implementation boundary, 2026-07-20.

This note narrows the claim made by `PHASE3E_PRECONSTRUCTION.md`.  Ledger V0-032
freezes contract `1.0.0` and profile `phase3e_accounted_dynamic_routing_v0`; the
working tree now implements a substantial component foundation, but not an official
Phase 3E runner or Gate result.

The scientific direction remains the reusable abstract world model.  Multi-step
contingent planning should occur primarily in that model.  Local ground distinctions
may be restored only after the abstract model cannot certify the selected plan at the
registered value and constraint tolerances.  Work accounting and dynamic routing make
that recovery auditable; they are not the strategic abstraction objective or evidence
that it has been achieved generally.

## Implemented contract foundation

The following contract-1.0 component surfaces now have strict schemas, canonical
round trips, replay logic, and attack tests:

1. `phase3e_ids` provides full domain-separated SHA-256 identities over strict
   canonical JSON.  Historical 0.x `object_id` values remain untouched and cannot be
   substituted for V1 authority.
2. `accounting_v1` implements `acfqp_counter_registry_v1`, complete registered leaf
   metadata, explicit observed native zeroes, local/fallback/rebuild separation,
   reconciliation records, and the exact eight-axis shared comparison projection.
3. `actual_accounting_v1` independently recomputes actual comparisons from referenced
   work, keeps common-prefix work outside marginal uppers, checks every selected-upper
   axis, and preserves separate failed-local/fallback work in occurrence sums.
4. `routing_v1` implements typed contexts, frontier/causal/cardinality/cap/upper/
   decision/transaction identities, strict componentwise marginal selection, trusted
   transaction-budget replay, terminal class/code, and typed verification-attestation
   records.
5. `route_upper_formula_v1` derives marginal leaf and eight-axis upper candidates from complete
   explicit pre-execution cardinality claims for all 34 operational leaves, the official
   projection, 13 registered native local hard-cap minima, and six structural guards.
   It binds a replayable arithmetic derivation proof, sets
   `authorizes_route_selection=false`, and rejects common-prefix, rebuild, or
   opposite-route work in a marginal formula. It does not yet prove source-count truth
   or operational cap enforcement.
6. `semantic_verification_v1` registers every FQ7 role and authoritatively replays work
   vector, actual projection, and terminal classification; it also registers the
   implemented `PROTOCOL_ACCESS` extension. Nine original FQ7 roles—including route
   decision—fail closed as `NOT_IMPLEMENTED`; a typed attestation cannot bypass that
   boundary, and plan or infeasibility terminal labels cannot be authorized by hashes
   alone.
7. `access_protocol_v1` implements the fail-closed estimate-before-execute event log,
   route-decision freeze attestation, selected-route exclusivity, and protocol-failure
   artifacts for early or rebound access.
8. `workload_vectors_v1` implements declared logical-occurrence order, reducer-aware
   vector prefixes, finite permutation enumeration, and componentwise worst frontiers
   while keeping scalar cost and break-even null.
9. `campaign_v1` implements rebuild/retry and attempt/occurrence closure mechanics,
   logical-occurrence denominators, certificate/noncertificate counts, and the rule
   that fallback-cap exhaustion is never infeasibility.
10. Phase 3B/3C/3D expose operational no-full-replay modes.  Phase 3B additionally
   requires a result-independent Bellman upper proof.  After the historical namespace
   binder has produced a `FrozenPhase3CWorld` outside the decision point, the Phase 3D
   preparation split reads terminal status and actions only from its frozen catalogues
   and stops after the failed-plan/causal/cardinality context, without live
   `kernel.actions`, `kernel.is_terminal`, `kernel.step`, slice materialization,
   compilation, or worker execution.  Passing a bundle path directly to this Phase 3E
   preparation API fails closed; the historical 0.9 bind-and-execute entry point keeps
   its original semantics.

These components reject noncanonical and cross-domain IDs; missing, duplicate,
unknown, wrongly scoped, or implicitly zero counters; projection omissions and double
charges; forged actual vectors; stale upper/transaction/profile bindings; local route
selection without strict dominance; local reopening after negative causal evidence;
worker budget lies; early execution access; local artifacts on a fallback route;
deleted or reordered event logs; hidden noncertificate occurrences; and injected
legacy scalar or break-even claims.

## Highest valid claim

The highest valid current claim is a **component-level contract-1.0 replay
foundation**.  It shows that the new identity, accounting, routing, access-order,
workload-vector, and campaign-closure objects can fail closed under their registered
unit and attack fixtures.

It does not produce an official route decision, plan certificate, infeasibility
certificate, workload-economics result, or complete campaign replay.  The older
preconstruction terminal envelope remains only
`TERMINAL_SHAPE_CLASSIFICATION_CANDIDATE`; private names containing
`CERTIFICATE_CANDIDATE` or `PHASE3E_PRECONSTRUCTION_MECHANICS_PASS` remain
non-authoritative construction artifacts.

## Remaining blockers

1. **Production-native instrumentation.**  Every actual abstract, local, direct-
   fallback, rebuild, infeasible, cap/protocol/integrity-failure, process, I/O, and
   verification path must emit the complete registry records.  Current component
   fixtures do not prove counter completeness in the operational runners or workers.
2. **Real direct fallback.**  A Phase 3E consumer must estimate, select, execute, cap,
   verify, and fully charge an authoritative direct ground fallback.  Fallback numeric
   cap authority and complete feasible/infeasible/cap-exhausted result paths are not
   integrated.
3. **Dependent transaction closure.**  The campaign and budget schemas allow two
   continuous local transactions, but no end-to-end runner yet performs a failed
   post-audit, freezes a genuinely deeper frontier and new upper, then executes the
   second decision point without stale reuse.
4. **Semantic role authority.**  Typed attestations are binding records, not semantic
   proof by themselves. Exact cached infeasibility, abstract audit, causal search,
   cardinality evidence, route upper, route decision, local solver result, post-audit,
   and ground fallback remain registered but deliberately `NOT_IMPLEMENTED`; each needs an
   authoritative verifier that reads the source artifact, recomputes its outcome,
   charges verification work, and rejects cross-role or context substitution.
5. **Integrated consumer.**  There is no end-to-end `run_phase3e` connecting frozen
   RAPM planning/audit, causal/cardinality preparation, tight route-upper derivation,
   decision freeze, selected execution, actual accounting, terminal classification,
   rebuild/retry policy, and campaign aggregation.
6. **Independent bundle verifier.**  No clean command yet starts from a Phase 3E
   manifest and independently replays every source artifact, access sequence, native
   counter, formula/upper, decision, actual vector, budget, terminal, occurrence, and
   campaign identity.  Individual schema round trips cannot substitute for that
   authority.

Until all blockers and the full V0-032 acceptance matrix close, every Phase 3E
artifact must preserve:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

`null` cannot be replaced by zero, `ops + bytes/4096`, or another temporary scalar.
Protocol failure, integrity failure, rebuild required, attempt-budget exhaustion, and
fallback-cap exhaustion remain noncertificates.  In particular, fallback-cap
exhaustion can never be promoted to `INFEASIBLE_QUERY`.
