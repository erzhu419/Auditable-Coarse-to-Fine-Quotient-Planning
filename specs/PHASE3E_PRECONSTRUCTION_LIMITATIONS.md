# Phase 3E Preconstruction Limitations

Status: non-normative implementation boundary, 2026-07-21.

## Relationship to the V0-039 direct-construction slice

V0-039 advances the construction side of the same ultimate target without changing
the current Phase 3E execution boundary:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

Profile `lmb_direct_exact_homomorphism_v1` removes V0-038's construction-time
behavioural-target/signature dependency for one exact finite LMB coverage. Its
production constructor accepts only the exact `LMBKernel` and frozen
`SuiteBuildCoverage`, internally freezes the complete eleven-state/one-action grammar,
and directly checks all 4096 state/action-subset candidates against the ground kernel.
Acceptance requires equal semantic-label sets, exact equality of aliased ground-action
dynamics before mixture, and exact same-label dynamics across state-cell members. The
canonical result selects state feature `action_count`, action feature
`completes_match`, thresholds `(3/2,5/2)`, compresses total/active `25/18 -> 5/3`, and
emits four abstract entries with a singleton envelope.

Restricted exact, no-exact and cap-exhausted runs belong to a separate non-production
control API and role-locked control verifier. The production verifier rejects
restricted-control provenance, incomplete registries and duck-typed result objects;
control evidence cannot mint a production model or certificate. Poison-import,
canonical transport, exact runtime-type, implementation-digest and independent-rebuild
tests protect the direct result. The old behavioural oracle is loaded only afterwards
for evaluation-only agreement, never as construction or certificate authority.

This is target-free direct construction inside fixed human-readable grammars, not
feature invention or oracle-free discovery from partial/learned dynamics. It still
requires the complete exact ground kernel, exact finite coverage and preregistered
feature semantics; it does not establish unknown-domain/scalable discovery,
held-out/cross-domain generalization or any aggregate Gate. It also does not close the
Phase 3E accounting, semantic-transport, dependent-transaction, rebuild, campaign or
independent-verification blockers below. Therefore the authoritative Phase 3E boundary
remains V0-037 and all locks remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## Relationship to the V0-038 feature-realization slice

V0-038 advances the construction side of the same ultimate target without changing
the current Phase 3E execution boundary:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

Profile `lmb_feature_realized_reusable_rapm_v1` now automatically selects feature
coordinates and exact rational midpoint predicates from one preregistered
human-readable LMB current-state grammar. Its canonical production constructor receives
only the exact `LMBKernel` and frozen `SuiteBuildCoverage` and internally fixes the
complete eleven-feature registry and bound spec; it receives no caller registry/spec,
query, J0, Q/value/frontier/policy or held-out evidence. Restricted grammars are
confined to a separate non-production negative-control API and verifier. Production
exhausts all 2048 subsets
of the eleven-feature grammar, exactly realizes the query-neutral behavioural quotient
with `action_count <= 3/2` and `action_count <= 5/2`, compresses total `25 -> 5` and
active `18 -> 3`, and serializes one portable model used unchanged by two fresh
in-coverage query-planning processes. A missing realization instead produces typed
`NO_EXACT_FEATURE_REALIZATION` with a bidirectional typed mismatch witness and no
positive model or certificate. The distinct 36-state seed-0 canonical-initial control
has an 11-cell target and a 7-cell `action_count` candidate and exhibits both
`TARGET_SEPARATED_FEATURE_ALIASED` and `TARGET_MERGED_FEATURE_SEPARATED`; it is not the
25-state golden.

This is a real but narrow automatic-synthesis result: selection occurs inside a fixed
human grammar and against a complete exact ground-model behavioural oracle on training
coverage. That target/signature dependence remains, so this is not oracle-free unknown-
quotient discovery. It is also not feature invention, partial/learned dynamics,
unknown-domain/scalable discovery, held-out or cross-domain generalization. It does not
close any of the Phase 3E accounting, semantic-transport, dependent-transaction,
rebuild, campaign or independent-verification blockers listed below. Therefore the
authoritative Phase 3E boundary remains V0-037 and all locks remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## Current V0-037 Phase 3E boundary (supersedes the older Phase 3E status lists below)

The ultimate target is unchanged:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

V0-037 closes three scoped plumbing boundaries and diagnoses one fixture boundary. It
does not establish synthesis or generality.

First, canonical H2 preparation now has an immutable native trace containing exactly
4 causal-candidate evaluations, 18 protocol checks, 3 integrity checks and 5 cap
checks. Its incremental WorkVector is kept separate from the original failed prefix;
the reducer-derived aggregate is retained as post-core evidence. Both remain
`RETAINED_POST_CORE_NOT_YET_OCCURRENCE_CHARGED`. Content-ID hash invocations, I/O and
accounting materialization/sealing are outside that trace, so the existing broad
preparation/global-hash blockers remain and neither preparation vector enters the
logical-occurrence cost.

Second, the successful registered LOCAL path now has a scoped typed terminal and
logical-occurrence closure. A fixed 54-role bundle independently replays the Phase-3C
source lease, canonical bytes, role/path topology, preparation work, upper arithmetic,
strict route selection, access/freeze sequence, reducer merges, selected-upper
compliance, terminal and occurrence references. Its highest status is exactly:

```text
VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY
semantic_certificate_status = NOT_MINTED_FROM_TRANSPORT
```

The bundle does not serialize enough local ground-proof or post-audit ground-replay
input to recreate live semantic authority. It therefore verifies the topology of a
terminal artifact; it does not independently issue the plan certificate.

Third, bounded rebuild/new-`BuildEpoch`/single-retry objects now exercise identity,
budget and reducer-correct occurrence aggregation. This is control-plane mechanics,
not a semantically authorized operational rebuild/retry or rebuilt-world-model result.

Finally, the canonical H2 local transaction 1 now ends in sound
`POST_AUDIT=CERTIFIED`. The frozen state machine permits transaction 2 only after a
failed post-audit, so a real transaction 2 is unreachable on this fixture. The next
benchmark must be a separately registered dependent-horizon fixture with a genuine
ground post-audit failure, distinct deeper frontier, fresh cardinality/upper authority
and new selected execution. The proof-derived synthetic two-transaction profile is
still only a state-machine/aggregation control.

Remaining official blockers are all-path hash/I/O/runtime accounting, durable exact-
infeasibility proof replay, serialized proof inputs for an independent semantic bundle
verifier, the new dependent-horizon transaction-2 fixture, operational rebuild
semantics, complete campaign/workload replay, and the later scalar revision. Automatic
RAPM synthesis, unknown strategic abstraction discovery and cross-domain
generalization remain research work rather than conclusions from these controls.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## Historical V0-036 boundary

The implementation has moved beyond V0-035, but the scientific objective has
not changed: synthesize one reusable abstract world model, perform multi-step
contingent planning primarily inside it, and restore ground distinctions only
at the first proof frontier where the selected plan cannot be certified.

The model-first H2 path now has an honest `ABSTRACT_FAILED_PREFIX` accounting
kind and a retained, opaque authority chain from the isolated model-only result
through `ABSTRACT_AUDIT=FAIL`, ground binding, no-replanning Phase-3D causal
translation, cardinality and route-upper replay, strict marginal route choice,
and exactly one selected post-freeze executor factory.  The unselected route is
a rejection trap.  This closes the former `FAIL -> estimate -> prepared route`
control-flow gap; it does **not** make the route official.  The preparation
object permanently exposes these unresolved accounting facts:

```text
GROUND_HANDOFF_OPERATIONAL_WORK_NOT_NATIVE_ACCOUNTED
MODEL_FAILURE_ROUTE_PREPARATION_OPERATIONAL_WORK_NOT_NATIVE_ACCOUNTED
ABSTRACT_AUDIT_REPLAY_NOT_EVENT_GRAIN_ACCOUNTED
CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED
```

Those flags cannot be removed or changed into
`official_execution_allowed=true`.  On this restricted development host the
end-to-end call reaches the selected local worker and then encounters the
host's nested bubblewrap/`NETLINK_ROUTE` namespace denial.  That environmental
failure is retained as failed-route work; it is not converted into a passing
runtime claim.

Two other boundaries are now executable but deliberately weaker than their
future official forms.  First, a strict seven-role independent bundle verifier
replays the H2 model-failure **prefix** from an independently loaded Phase-3C
source snapshot, including final TOCTOU recheck; selected-route receipts,
terminal and occurrence closure remain `NOT_RUN`.  Second, the planner-free
exact-cache preflight derives kernel/manifest identity from the verified source
and compares all eight frozen coordinates, but always returns
`authorizes_infeasibility=false`: no current artifact contains the durable,
kernel-bound search-completeness payload and independent verifier required by
V0-021.

An adversarial authority audit also found that a module token inside a public
frozen dataclass was copyable.  V0-036 therefore treats runtime semantic and
continuation authority as an exact live object, not as a copied token or a
same-shaped dataclass.  Semantic results, prepared estimates, route
continuations, trusted local/fallback provenance, occurrence/campaign handles,
and cache/workload runtime handles must retain an internal mint, exact member
identity, and a replayed fingerprint; `replace`, shallow/deep copy, field
substitution and cross-role reuse are inert.  This correction is a trust-boundary
repair, not strategic-model evidence.

The remaining official blockers are consequently narrower and more precise:

1. event-granular native accounting for the complete model-failure preparation
   path, every content hash, I/O/mount/runtime event, and all abnormal exits;
2. sealed model-only runtime resource caps and an independently replayable event
   trace;
3. a real ground-derived failed post-audit whose new proof frontier drives
   production transaction 2, rather than the existing synthetic control;
4. model-failure terminal/occurrence closure, operational rebuild/new
   `BuildEpoch`/single retry, and every remaining terminal branch;
5. a durable exact-infeasibility proof payload with an independent complete-
   search verifier;
6. selected-route receipts plus a complete manifest-level bundle verifier;
7. the full registered workload and, only after a later scalar ledger revision,
   scalar break-even; and
8. the ultimate research work: automatic RAPM synthesis, unknown strategic
   abstraction discovery, cross-domain generalization and learned proposals
   that remain subordinate to exact audit.

Therefore all official and economics locks remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

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

V0-037 additionally demonstrates a scoped successful
`PLAN_CERTIFICATE/LOCAL_GROUND_RECOVERY` terminal/occurrence closure and a 54-role
independent accounting/topology transport. The latter's highest claim is exactly
`VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY`; it cannot independently mint the
semantic certificate.

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

1. **Durable infeasibility and transport semantic authority.** The registered
   model-only `ABSTRACT_AUDIT` chain replays, but planner-free cached infeasibility
   still needs a durable kernel-bound complete-search proof and independent verifier.
   The selected-route bundle also needs serialized local ground-proof and post-audit
   inputs before it can verify certificate semantics. No hash or fallback-cap outcome
   may substitute for those proofs.
2. **Complete remaining native/hash instrumentation.** Close planner invocation,
   continuation/fallback authority-package construction and rejection, and every
   abstract-only, rebuild, exact-infeasible, cap/protocol/integrity failure, terminal,
   serialization, I/O, verification and hash path. Add durable child-side records if
   internal work before abnormal termination is to be claimed. The runner still
   declares `unassigned_postfreeze_operational_leaves=(common.hash_invocations)` and
   `ALL_PATH_NATIVE_HASH_INSTRUMENTATION`; the current registered positive and typed-
   failure paths cannot prove counter completeness for all official paths.
3. **New dependent-horizon transaction evidence.** The repaired canonical H2
   transaction 1 ends `POST_AUDIT=CERTIFIED`, so transaction 2 is unreachable there.
   Register a different fixture whose genuine ground post-audit fails, derive the
   deeper frontier and all transaction-2 authorities from frozen sources, execute the
   fresh local-or-fallback decision, and then certify or close. The synthetic control
   alone is not this evidence.
4. **Operational rebuild/retry semantics and remaining campaign closure.** Bounded
   new-epoch/single-retry identity, budget and aggregation mechanics exist, and
   fallback cap exhaustion already
   closes at occurrence scope as an authority-verified denominator-preserving
   noncertificate. Still perform a semantically authorized RAPM rebuild/new
   `BuildEpoch`, the one permitted retry, exact infeasibility, protocol/integrity
   failure and attempt-budget exhaustion in complete campaign orchestration while
   charging all work.
5. **Integrated upstream/campaign consumer.** Connect manifest loading, model-only
   plan/audit, failed-prefix preparation, selected execution, retries and closure as
   one fully accounted production consumer rather than separately invoked scoped
   stages.
6. **Semantic and campaign bundle verification.** Extend the current fixed 54-role
   accounting/topology verifier with serialized ground proof inputs, independent post-
   audit replay, all route/retry branches and campaign closure. Runtime seals and
   topology-only replay are insufficient for this Gate.
7. **Workload economics.** Freeze a later scalar ledger revision, run the full
   registered logical-occurrence workload including worst order, and only then
   define or report `N_break_even`. Until then only vector prefix and componentwise
   worst-frontier mechanics may run; vector dominance is not a scalar crossing.
8. **Research generality.** The safe-chain controls do not demonstrate
   oracle-free predicate/quotient discovery, unknown strategic coordinates,
   cross-domain reuse, scale, or learning. Progress on accounting must not be
   relabelled as completion of the reusable-world-model objective.

Until these blockers and the V0-032/V0-033/V0-037 acceptance matrix close, every Phase 3E
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
