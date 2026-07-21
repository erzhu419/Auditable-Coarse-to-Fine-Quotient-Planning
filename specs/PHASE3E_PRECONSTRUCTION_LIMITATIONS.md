# Phase 3E Preconstruction Limitations

Status: non-normative implementation boundary, 2026-07-21.

This note narrows the claim made by `PHASE3E_PRECONSTRUCTION.md`. Ledger V0-032
freezes contract `1.0.0` and profile `phase3e_accounted_dynamic_routing_v0`;
V0-033 additively freezes the four scoped P0 accounting, continuation, executor and
occurrence-closure rules.
The working tree now contains executable, authority-gated Phase 3E vertical
slices; it still does not contain an official Phase 3E campaign or Gate result.

The scientific center remains the reusable abstract planning model (RAPM):
multi-step contingent planning should occur primarily in one frozen abstract
world model. Ground distinctions may be restored only when the independent
value/risk audit cannot certify the selected abstract plan. Phase 3E makes that
exception auditable and chooses between local recovery and full fallback; it is
not a replacement objective and is not evidence of general strategic-abstraction
discovery.

## Implemented contract surface

The following contract-1.0 surfaces are implemented with strict schemas,
content identities, replay checks, and adversarial tests:

1. `phase3e_ids`, `accounting_v1`, and `actual_accounting_v1` implement
   domain-separated SHA-256 identities, the complete V1 counter catalogue,
   explicit native zeroes, reconciliation, the eight shared resource axes,
   exact actual projection, and componentwise selected-upper compliance.
   Common-prefix, selected-route, verification-suffix, failed-local, fallback,
   and occurrence work retain separate provenance. `phase3e_two_stage_accounting_v1`
   additionally seals the exact core, freezes the complete semantic/nonsemantic
   obligation list, derives one operational suffix and reducer-correct aggregate, and
   binds every source record/attestation in a manifest and receipt. Omission, padding,
   duplication, substitution, stale context, pre-plan verification and wrong-lane work
   fail exact replay.
2. `routing_v1` and `route_upper_formula_v1` implement typed contexts,
   frontiers, causal/cardinality/cap evidence, transactions, marginal uppers,
   strict componentwise route selection, trusted transaction-budget replay,
   terminal classes/codes, and formula-plus-hard-cap upper derivation. Equality,
   incomparability, stale/missing authority, or a non-`FOUND` causal result still
   selects fallback.
3. `semantic_verification_v1` now has authoritative handlers for work vectors,
   actual projections, protocol violations, route/attempt terminal classification,
   evaluation-lane `SemanticRole.OCCURRENCE_TERMINAL` over
   `Phase3EOccurrenceTerminalArtifactV1`, route uppers, route decisions, and ground
   fallback. The occurrence role covers `PROTOCOL_FAILURE` and
   `FALLBACK_CAP_EXHAUSTED`; route-attempt terminal authority cannot replace it. It additionally has
   **registered-safe-chain-only** handlers for causal search, local and fallback
   cardinalities, isolated local results, and sound local post-audits. Raw
   hashes, structurally plausible artifacts, or result strings do not acquire
   authority. `EXACT_CACHED_INFEASIBILITY` and `ABSTRACT_AUDIT` remain
   `NOT_IMPLEMENTED`.
4. `access_protocol_v1` and the one-decision `run_phase3e` consumer enforce
   estimate-before-execute. Every allowed frozen read carries the exact artifact ID:
   reusable RAPM, BuildEpoch, failed certificate, selected plan, action catalogue,
   current frontier/proof or content-addressed typed `NOT_APPLICABLE`, cardinality,
   cap, formula and comparison profile. The failed-certificate ID binding is not an
   independent abstract-audit proof;
   the route decision freezes before any transition enumeration,
   materialization, compiler, worker, stitch, post-audit, or fallback solver.
   Only the selected route may execute. The runner then joins native execution
   work with separately charged semantic-verification work, reprojects the
   aggregate, and checks all eight axes against the authoritative selected
   upper. Authorization accepts only the exact charged semantic dependency closure:
   decision -> causal plus both route uppers -> exactly one cardinality verification
   for each upper, with no missing, duplicate, or extraneous result.
5. The registered safe-chain LOCAL integration is real rather than a mocked
   selector test. The frozen Phase 3D preparation supplies causal and
   cardinality authority without a ground transition. Because the local upper
   strictly componentwise dominates the isolated-fallback upper, the runner
   freezes `LOCAL`, materializes exactly `16` transitions/`64` positive outcome
   rows, compiles the sparse capability, launches the bubblewrap worker with no
   host solver replay, stitches its result, and soundly post-audits exactly
   `8` transitions/`32` rows. The result carries distinct
   `LOCAL_SOLVER_RESULT=CANDIDATE_FOUND` and `POST_AUDIT=CERTIFIED` authorities,
   with actual work below the selected upper. The local-result authority binds the
   exact capability and worker-result IDs; a candidate additionally requires the exact
   stitched-plan and post-audit IDs. A negative `SEARCH_CAP_EXHAUSTED` or
   `NO_FEASIBLE_ASSIGNMENT` worker result closes the legal
   materialize->compile->worker prefix, forbids stitch/post-audit artifacts, and can
   continue only at a fresh fallback decision. The worker enforces and attests a
   256 MiB working-set limit; Phase 3E conservatively charges that cap as peak
   working capacity instead of placing nondeterministic peak RSS in the
   replay-exact Phase 3D semantic attestation. This is a scoped safe-chain
   positive control, not a general local-planning result.
6. The ground fallback has a finite route-specific cap and resource profile,
   exact safe-chain preselection cardinality authority, complete deterministic
   finite-horizon search semantics, and typed feasible/infeasible/cap-exhausted
   outcomes. `AuthorizedIsolatedGroundFallbackExecutorV1` runs the selected
   safe-chain fallback in bubblewrap, where the worker revalidates the frozen
   manifest, query, BuildEpoch, action catalogue and RAPM and binds its request
   to the exact decision and upper. The host does not replay the solver. Its
   finite capacity profile records one process launch, source/bundle/request/
   output caps, and a 256 MiB working-set cap; the adapter records actual
   process and I/O values, validates child peak RSS against the cap, and
   conservatively charges the 256 MiB cap as peak working capacity before launch. It
   returns the `GROUND_FALLBACK` result to
   the runner's semantic suffix. The current isolated positive run executes
   `48` transitions, observes `192` positive rows, performs `5696` Bellman
   backups, records exact run-dependent read/staged/output/mounted values below their
   frozen finite caps, validates the child's reported RSS, and returns
   `FEASIBLE_CERTIFIED`. Resource
   byte counts are evidence from each run rather than golden constants because
   the staged source payload changes with the build. This remains a
   safe-chain/Frozen-Phase-3C
   opaque-supervisor trust root, not a portable public fallback bundle or an
   official all-outcome campaign. A legacy callable lacking the required isolation
   evidence fails closed under this profile.
7. `phase3e_transactions_v1`, `phase3e_failure_continuation_v1`, and
   `phase3e_occurrence_runner_v1` implement the generic authority-gated control
   flow for at most two continuous local transactions. After a failed transaction-1
   post-audit, the fresh marginal decision may select local transaction 2 or execute
   direct fallback immediately; the latter path creates no fictitious transaction 2.
   A second local transaction requires a genuinely
   deeper frontier, a newly stitched selected-plan identity, a new common
   prefix, cardinalities, uppers, decision point, and semantic authorities.
   Old uppers cannot be reused. Prior execution-work authority is runner owned: the
   continuation packages deliberately omit prior `WORK_VECTOR` results, and the
   occurrence controller transports the exact selected-work result from completed-run
   history as evidence rather than recharging its original invocation. Transaction-2
   or fresh fallback pays one new registered continuation-authority protocol check in
   its own common prefix. A planner cannot omit that check or substitute a cheaper
   same-shaped vector. The current tests establish these structural and
   fail-closed controls; they do **not** execute a registered live safe-chain
   benchmark example whose first sound post-audit fails and whose deeper fresh decision
   then completes.
8. Terminal and occurrence evidence are no longer loose status labels.
   Terminal replay binds the exact runner aggregate, actual projection, selected
   upper and decision, route-semantic result, freeze attestation, and access log.
   Low-level occurrence aggregate replay recognizes four typed raw forms: historical `RecordedWorkV1`,
   complete two-stage `RunnerCommonAccountingEvidenceV1`, rejection-only
   `RunnerPartialCommonAccountingEvidenceV1`, and complete
   `RunnerMarginalWorkEvidenceV1`. Normatively, the authority-bearing occurrence
   terminal/run may accept the partial-common form only as the final unpaired common
   component of a rejected authority package; the lower-level type alone is not
   terminal authority, and it cannot stand in for a successful receipt. Runtime and
   serialized aggregate validation, occurrence-result admission, standalone terminal
   replay, and failed-route terminal admission independently reject earlier, paired,
   non-final, wrong-stage, or subsequently extended partial-common evidence—even if an
   attacker recomputes the outer content ID. Aggregation otherwise preserves every
   local/fallback component, rejects cheaper work-vector splicing, and keeps
   noncertificates in the denominator. Aggregate
   WorkVector/projection, route/attempt terminal classification, and occurrence-
   terminal replay are invocation-typed standalone evaluation work over an already
   sealed operational aggregate; their counter records cannot recursively enter the
   object they verify.
9. Selected-route exceptions with one uniquely replayable native-work ownership chain now raise typed
   `Phase3ERouteExecutionFailedV1` noncertificate evidence. It retains the
   exact failed execution and verification `RecordedWorkV1` objects, their
   replayable marginal aggregate, context/decision/upper/freeze/access
   identities, exception classification, and access/native reconciliation
   result rather than dropping all pre-failure work. Python-level local-adapter
   failures attach and fail-close their internally owned recorder. Local
   materialization/compiler/launch/solver/post-audit and fallback staging/launch/
   worker-native/output counters are recorded as soon as observed, including the
   supervisor-side prefix of a child-launch failure. This remains deliberately
   conservative: internal work performed by an abnormally terminated child is
   unknowable without durable child-side streaming/checkpointing. Missing work may not
   be inferred or padded. The occurrence runner catches the route exception, appends
   its exact failed common/partial-marginal pair to every prior successful decision
   pair, replays one `Phase3EOccurrenceWorkAggregateV1`, and mints a typed
   `ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE` authority only after full
   evidence replay. Plan/infeasibility counts remain zero, noncertificate count is one,
   and closure/certification/economics denominators are all retained.
10. Phase 3B/3C/3D expose operational no-full-replay modes. Full planner replay,
   unrestricted ground upper, exact lift, and J0 remain in the standalone
   evaluation lane rather than being charged once while executed twice.
11. `phase3e_sealed_executor_v1` provides an additive sealed execution profile. A
    prepared decision binds an inert `ExecutorRecipeV1` and the exact
    `RuntimeTreeManifestV1` ID. Snapshotting occurs only at build/rebuild time. After
    the typed route freeze, the selected single-use factory resolves and byte-verifies
    the preregistered CAS tree, creates a private read-only lease, and only then grants
    a trusted constructor authority to create the concrete executor. Preconstructed
    callables, live-checkout fallback, foreign recipes, symlinks, extra files, changed
    bytes, pre-freeze construction and reuse fail closed.
12. `RuntimeFactoryCardinalityV1` freezes exact file count, total bytes, canonical
    manifest-document bytes, and the registered factory counter-upper formula before
    route execution. Each sealed local/fallback candidate binds its route-specific ID
    in its own cardinality source chain, both compared uppers reserve the corresponding
    factory work, and the selected factory rechecks the chosen chain. The success
    receipt binds exact factory work and
    `postconstruction_access_event_log_id`; the runner requires that ID to equal the
    final returned access log, closing the earlier-log substitution seam. The sealed
    safe-chain fallback freezes one route-wide `control.cap_checks=5815`: factory
    reserve `3`, worker share `5812`, with no post-hoc addition. A total cap `5812`
    would leave only `5809` worker checks and must close through cap rejection.
    Unsealed `reserve=0` payloads retain their historical schema/domain/content IDs.
13. A sealed route failure is decomposed rather than represented only by a merged
    partial. `SealedExecutorFailureMergeProofV1` binds factory partial
    WorkVector/comparison/projection identities, either a complete delegate triple or
    three typed nulls, and the merged partial triple. The companion failure evidence
    binds runtime/recipe/cap/constructor/freeze identities, a registered stage and the
    final post-failure access log. Replay rejects missing sources, mixed nulls,
    reducer/subject changes and stage/log substitution. This is currently exact in-
    process failed-route/occurrence replay, not a separate FQ7 semantic attestation or
    manifest-level independent-verifier authority.
14. A continuation package rejected after some operational verifier work is retained
    as `PARTIAL_ACCOUNTED_COMMON`. Its occurrence evidence reducer-replays the common
    core plus exactly the observed, context-matched operational semantic results and
    nonsemantic records. This is failure accounting only: it supplies neither a full
    two-stage receipt nor continuation/certificate authority and cannot infer missing
    work.
15. Registered nonsemantic checks consume typed witness objects and recompute their
    check-kind-specific claims; arbitrary evidence IDs cannot mint `VALID`. Semantic
    and nonsemantic plan records are disjoint from every sealed-core CounterRecord, so
    core/suffix double charging is rejected.
16. `Phase3EOccurrenceRunResultV1` replays raw components, aggregate, ordered runs,
    transactions, final closure and terminal authority at construction. Runtime
    replacement cannot preserve a stale aggregate or authority after reorder, splice,
    rehash, or relabelling.

Bubblewrap integration tests require a host that permits its mount/network
namespaces. A restricted container may report the test as skipped after a
`NETLINK_ROUTE` namespace denial; the same test must pass in the supported Linux
execution environment before making the scoped runtime claim.

## Highest valid claim

The highest valid claim is an **accounted, authority-gated Phase 3E vertical
slice for the registered safe-chain workload**. It demonstrates a genuine
RAPM-failure-to-local route, a capped ground-fallback route, result-blind route
freezing, route-native accounting, scoped semantic replay, terminal-evidence
binding, exact two-stage verification charging, sealed post-freeze construction,
runner-owned continuation authority, and provenance-preserving occurrence failure
closure.

It is not an official execution profile, a completed counter-completeness Gate,
a workload-economics result, or a general campaign certificate. In particular,
`run_phase3e` consumes a caller-prepared failed-plan/authority package; it does
not yet autonomously run the full RAPM plan/audit/preparation pipeline from a
manifest.

## Remaining blockers

The four former scoped P0 blockers are closed by V0-033: exact non-cyclic two-stage
verification accounting, runner-owned continuation WorkVector authority, sealed
post-freeze executor/runtime CAS, and occurrence-level failed-route terminal replay.
Their registered vertical-slice paths are no longer absent, but that does not imply
all-path enforcement or that the wider Gate has run. The remaining blockers are:

1. **Abstract and cached-infeasibility authority.** Implement independent
   `ABSTRACT_AUDIT` replay and exact identical-query/build/kernel cached
   infeasibility matching. No hash or fallback-cap outcome may substitute for
   either authority.
2. **Complete remaining native/hash instrumentation.** Close planner invocation,
   continuation/fallback authority-package construction and rejection, and every
   abstract-only, rebuild, exact-infeasible, cap/protocol/integrity failure, terminal,
   serialization, I/O, verification and hash path. Add durable child-side records if
   internal work before abnormal termination is to be claimed. The runner still
   declares `unassigned_postfreeze_operational_leaves=(common.hash_invocations)` and
   `ALL_PATH_NATIVE_HASH_INSTRUMENTATION`; the current registered positive and typed-
   failure paths cannot prove counter completeness for all official paths.
3. **Live dependent transaction evidence.** Exercise a genuine failed sound
   post-audit, derive the deeper frontier and all transaction-2 authorities from
   frozen sources, execute the fresh local-or-fallback decision, and then certify or
   close. The generic orchestrator and attack controls alone are not this evidence.
4. **Rebuild/retry and remaining campaign closure.** Fallback cap exhaustion already
   closes at occurrence scope as an authority-verified denominator-preserving
   noncertificate. Still connect an operational rebuild recipe/new `BuildEpoch`, the
   one permitted retry, exact infeasibility, protocol/integrity failure and attempt-
   budget exhaustion to the complete campaign orchestration while charging all work.
5. **Upstream RAPM consumer.** Start from a manifest, plan and audit in the frozen RAPM,
   and construct the prepared authority package instead of receiving it from a caller.
6. **Manifest-level independent verifier.** Add a clean command that starts
   from a Phase 3E bundle/manifest and independently replays source identities,
   access order, counters, cardinalities, formulas, uppers, route decisions,
   budgets, terminals, occurrence totals, and campaign closure. Runtime seals and
   unit-level strict round trips are insufficient for this Gate.
7. **Workload economics.** Freeze a later scalar ledger revision, run the full
   registered logical-occurrence workload including worst order, and only then
   define or report `N_break_even`. Until then only vector prefix and componentwise
   worst-frontier mechanics may run; vector dominance is not a scalar crossing.
8. **Research generality.** The safe-chain controls do not demonstrate
   oracle-free predicate/quotient discovery, unknown strategic coordinates,
   cross-domain reuse, scale, or learning. Progress on accounting must not be
   relabelled as completion of the reusable-world-model objective.

Until these blockers and the V0-032/V0-033 acceptance matrix close, every Phase 3E
artifact preserves exactly:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

`null` cannot be replaced by zero, `ops + bytes/4096`, or another temporary
scalar. Protocol failure, integrity failure, rebuild required, attempt-budget
exhaustion, and fallback-cap exhaustion remain noncertificates. In particular,
fallback-cap exhaustion can never be promoted to `INFEASIBLE_QUERY`.
