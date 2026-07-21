# Research Contract

## Definitions

- **V0:** the exact, symbolic, finite-horizon project boundary.
- **RAPM:** reusable abstract planning model; a nominal abstract world model plus an independently derived exact sound envelope, state/action maps, and frozen concretizer.
- **Query:** `q=(rho0,H,w,g,delta,Rmax(q))` over one built RAPM; the domain may register canonical initial laws, but the selected `rho0` belongs to the query.
- **Build coverage:** the explicitly identified ground-state set on which a RAPM is
  complete. Phase 0.5 uses the transition closure of a canonical query-support
  declaration and forbids reuse outside that set.
- **Per-query result:** contingent policy graph, value/risk certificates, and charged fallback locations.
- **Certified:** supported by complete backward induction with `exact_sound` evidence, not by nominal prediction or empirical accuracy.
- **Phase 3A construction slice:** the V0-027 two-domain, train-only exact-model/oracle
  positive control. It is a single registered construction/evaluation slice, not the
  frozen Phase 3 aggregate Gate.
- **WorkloadSpec:** a preregistered ordered family of genuine planning queries sharing
  a coverage-bounded world-model build, with route and accounting rules.
- **BuildEpoch:** immutable external build provenance spanning structure, kernel,
  coverage, feature/action registries, builder, schemas, source revision, and the
  resulting coverage/model IDs; it is not embedded in the portable RAPM.
- **Phase 3B portable campaign:** the V0-028 two-domain, no-Q/value-signature exact
  behavioural build followed by fresh-process planning on the serialized RAPMs.
- **Phase 3C local-recovery slice:** the V0-029 certificate-triggered, isolated,
  query-owned overlay positive control over an immutable reusable RAPM; it is not the
  aggregate Phase 3 or economics Gate.
- **Phase 3D general local-recovery Gate:** the V0-030 finite, cap-aware positive
  control for slack-aware causal localization, sparse worker authority, and joint
  deterministic value/risk composition; it is not the aggregate Phase 3 or economics
  Gate.
- **Phase 3E accounted dynamic-routing profile:** the contract-`1.0.0` consumer of
  frozen RAPM, failed-certificate, causal, and route-cardinality evidence. It freezes
  a route decision before route-specific execution, preserves native work provenance,
  and remains nonofficial until every V0-032 counter, verifier, failure-path, and
  access-order acceptance test passes.

## Normative decisions

V0 covers finite reachable state spaces, finite state-dependent primitive action sets, exact enumerable transition kernels, bounded additive registered rewards, one-time failure cost, full observability, and `H<=Hmax`. The primary research object is a coverage-bounded auditable RAPM compiled once for repeated multi-step contingent planning; the quotient tree, predicates, and CEGAR construct or repair it, while a policy graph remains a query result. Ground distinctions are recovered only after the independent certificate for the current plan fails.

A RAPM may be queried with a different horizon, registered reward coefficients, and
`delta in {0,0.05,0.10}` while its structural and coverage identities remain valid;
goal variation is permitted only when the portable model/schema explicitly implements
the registered stopping/reward semantics. Phase 3B schema v1 implements only
`goal_id=default`. Primary reports use `0.05`. Although `rho0` is query-owned,
the implemented Phase 0.5 cache is coverage-descriptor-exact: the build starts from the
query's canonical positive-mass support declaration, closes it under every legal action
and positive-probability successor, and includes the mode, declaration hash, covered
state count, and no-outside-reuse flag in `build_id`. A different `rho0` leaves
`structural_id` unchanged but produces a new query ID and descriptor-specific build ID;
the current cache does not infer equivalence between different declarations. Rebuild is
also mandatory after changing dynamics/rewrite rules, object/container/blocker
semantics, observation or action definitions, any unregistered reward/constraint
feature, `kappa`, predicate grammar/version, abstraction budgets, a structural
environment parameter, or the declared build coverage.

Canonical `Rmax` is `H` for G2048 and `2N/3` for LMB. Any change to reward-basis weights, merge/match reward, terminal bonus, or goal reward requires a separately declared and validated deterministic `Rmax(q)`; canonical bounds cannot be inherited by name alone.

In production, an exact J0 infeasibility proof for the identical structural/build/kernel
identity and byte-equivalent query returns `INFEASIBLE_QUERY` before refinement. The
canonical G2048 Phase 0.5 harness intentionally overrides only this scheduling rule to
exercise one mandatory split and charged fallback; it does not override the structure,
query, or infeasibility result.

The V0 primary claim is limited to one auditable construction/refinement algorithm operating on both symbolic domains with exact envelopes, counterexample-guided predicate splits, and charged constrained fallback. Shared grammar is secondary; shared coordinates are exploratory.

The safe-chain positive-control claim is narrower and logically separate. Given the
preregistered `D4` automorphism group, the system may claim an exact state-action
symmetry quotient only after constructing the complete reachable state-time graph,
full equal-stage orbit partition, stabilizer-orbit semantic actions, deduplicated
distinct-inverse-action uniform concretizer, representative-independent point model,
zero-width envelope, and J0-equal lifted constrained policy. This is a known-group exact
homomorphism baseline; it is not evidence that the system discovered symmetry,
strategic predicates, useful CEGAR refinements, shared cross-domain coordinates, or a
learned meta-controller.

The versioned `D4` group/action-transform profile belongs to structural build
configuration. The complete reachable state-time graph `R(q)`, its materialized orbit
quotient, lifted policy, and equality proof are query-scoped results. This is not
permission to put `rho0/H` in the structural key or to claim that one query's reachable
coverage makes the RAPM reusable for an uncovered distribution or horizon.

This profile performs no CEGAR split or fallback. A failed exact-quotient invariant
returns `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`. The original infeasible canonical
fixture remains the Phase 0.5 split/fallback test.

The feasible-aliasing positive control is now the independent profile
`g2048_select_safe_chain_aliased_partition_v0`. It retains the ground structural key,
kernel, query, J0 truth, and 192-state coverage of the safe-chain fixture but changes
the build-owned partition, action adapter, and grammar, so all corresponding hashes are
distinct. It starts from the ten-cell failure-plus-active-histogram encoder, whose
incremental rate is zero but whose leaves and construction costs are charged; it uses
full-V0 budgets. Its order-dependent `canonical:first/last` singleton concretizers are
deliberately not `D4`-equivariant. An exact counterexample extractor and the standard
joint ranking must choose the registered four-bit adjacency predicate twice, producing
`10 -> 11 -> 12` leaves and immediate `CERTIFIED` after the second split, with no
fallback.

That result supports only recovery from a deliberately installed action/partition
alias using a preregistered current-state geometry atom. Because every active histogram
cell is already one `D4` orbit, it is not discovery of an unknown state quotient or
symmetry. Because the final failure `317/16000` differs from J0 `99/5000`, it is a sound
constrained certificate, not exact policy/risk preservation. It does not support
automatic predicate invention, shared grammar/coordinates, or learning.

The Phase 3A profile is `phase3a_true_state_alias_oracle_control_v0`. It builds suite
coverage and one RAPM per domain from training inputs only, freezes their identities,
and only then evaluates registered held-out queries whose positive support is already
covered. G2048 uses two training queries—the canonical safe-chain `H=2` row and a
strict cross-`D4` `H=1` bridge—and selects a two-atom train-oracle signature partition
with eight cells on their 192-state closure; LMB uses query-independent exact behavioural
refinement with five cells on a 25-state closure. Both must contain a policy-reachable
active cell for which one lifted training policy graph actually reaches members from
multiple complete known-automorphism orbits. Cell membership alone, or separate
queries reaching separate orbit members, is insufficient. Thus this slice tests real
state aliasing beyond a supplied symmetry partition, not merely the action-frame aliasing
of V0-026.

The construction authority remains exact ground knowledge: G2048 uses an unrestricted
J0 table under the training reward/risk profile, and LMB uses the complete exact kernel
and a fixed behavioural-signature refinement. Consequently the result is an oracle
upper-bound/positive control. It may support cross-automorphism state aggregation and
held-out reuse within frozen coverage, but it may not be described as human-readable
predicate invention, oracle-free discovery of an unknown quotient, the full Phase 3
Gate, shared cross-domain coordinates, learned abstraction, CEGAR recovery, or
multiresolution strategic planning.

Passing this slice requires G2048 total `192 -> 8` and active `68 -> 7`, LMB total
`25 -> 5` and active `18 -> 3`, at least `5x` compression computed from **active**
states/cells in each domain, strict ground-to-abstract state-action compression, exact-
sound certification of every train and held-out row, zero J0-to-lifted reward and
failure gaps, and at least one policy-reachable cross-automorphism active cell per
domain, with at least two physical orbits jointly reached in that cell by the same
lifted training policy graph. The terminal pair is `PHASE3A_SLICE_PASS` plus
`PHASE3_AGGREGATE_NOT_RUN`; a construction or replay violation is
`PHASE3A_INVARIANT_VIOLATION`.

Reuse is claimed only **across the registered two-domain held-out suite**. G2048 covers
changes in initial support/distribution and horizon; LMB covers changes in reward basis,
horizon, and risk. Neither domain is claimed to cover all four axes, and the result
does not quantify over arbitrary in-coverage queries.

The Phase 3B profile is `phase3b_portable_rapm_campaign_v0`. Its exact behavioural
synthesizer uses every covered state's complete one-step reward-feature vector,
entered-failure/terminal kind, and successor-block distribution and refines to a fixed
point. It may use the complete exact one-step kernel, but construction dependencies
must contain no `Q*`, value/frontier, selected action/policy, query reward weights,
`delta`, `H`, or evaluation result. Equal action behaviours become semantic actions
with frozen distinct-action concretizers. This is query-neutral exact world-model
synthesis, not automatic predicate invention or learned dynamics. This dependency
claim is supported by the builder API/data flow and static import/source audits; it is
not a claim that the complete Phase 3B orchestration process forms a closed import DAG.

Portable RAPM schema v1 embeds the complete coverage and its `coverage_id`, a state
catalog with `planning_kind in {active,terminal,failure,success}`, the partition,
nominal model, exact envelope, semantic/ground action catalogs, frozen concretizer,
reward features, `normalizer_rules`, and `goal_ids`. The nonempty canonical
`normalizer_rules` registry is sorted by unique `proof_id`; each entry has exactly
`kind=nonnegative_feature_caps_v1`, a complete `reward_basis`, and `feature_caps`.
`reward_basis` contains every registered feature exactly once, sorted by name, with a
nonnegative rational raw weight including explicit zero weights. Cap entries are sorted
uniquely by registered feature name; every cap record has at least one non-null
nonnegative value, every positive-basis-weight feature has a cap record, and zero-weight
features need not have one. It
does not embed `BuildEpoch`; its `model_id` is a
content ID of only this extensional payload. The externally stored epoch binds that
model and coverage to construction provenance.

The serialized result is the planner authority. Every query occurrence runs in a fresh
Linux bubblewrap mount/network namespace containing staged copies of only
`portable.py`, `portable_planner.py`, and `portable_runtime.py`, the current read-only
RAPM/query files, system Python libraries, and an initially empty writable output
directory. The project checkout and other requests are not mounted, Python starts with
`-S`, and a content-addressed runtime attestation records the isolation and loaded
module origins. The portable query is the cell-level projection bound to the ground
request: exact cell `rho0`, `H`, raw and normalized reward weights,
normalizer/proof ID, `delta`, and goal. Schema v1 supports exactly the `default`
structural stopping goal and rejects every other goal. It also rejects an unknown
reward feature, negative raw weights, a nonpositive normalizer, an unregistered proof,
or raw weights not exactly equal to the selected proof's complete `reward_basis`.
Proof IDs therefore cannot be reused across reward bases. It
computes

```text
B_p(q) = sum_k w_k * min({H * per_step_cap_k if present,
                           total_cap_k if present}),
```

requires `normalizer >= B_p(q)`, and requires each normalized weight to equal the raw
weight divided by that normalizer. These rules do not authorize arbitrary rewards or
goals. Phase 3B binds G2048's proof to `(merge=1)` and the three LMB proofs to
`(match,terminal_clear)=(1,1),(1,0),(0,1)` respectively; LMB proof IDs cannot be
cross-used. The process may not load the
ground kernel, builder memory, J0 table, or evaluation record. It produces and
serializes the complete abstract policy graph from the portable model. After all
proposals freeze, the independent exact auditor, J0, and ground lift may load the
authoritative ground model as evaluation/fallback truth; none can feed back into
construction or the fresh planner.

One frozen `WorkloadSpec` contains the ordered campaign query IDs, coverage roots/rule,
expected count, allowed routes, and one `BuildEpoch` per domain. The campaign has at
least eleven distinct ground queries, at least eight distinct portable query projections and
four per domain, and at least one `H>=2` query per domain. Every query must use the same
domain RAPM/build epoch and remain
inside its declared coverage. Phase 3B's success tuple is
`PHASE3B_PORTABLE_RAPM_PASS`, `PHASE3_AGGREGATE_NOT_RUN`,
`LOCAL_HYBRID_GATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

The general route order is `ABSTRACT_CERTIFIED`, then—only after certificate
failure—`LOCAL_GROUND_RECOVERY`, and finally charged `FULL_GROUND_FALLBACK`; uncovered
or semantically changed work is `REBUILD_REQUIRED`, and a matching ground proof may
return `INFEASIBLE_QUERY`. The local ground frontier contains the earliest
policy-reachable `(cell,h)` proof failures and only their exact model dependencies may
be reopened. Phase 3B exercises only the abstract-certified route, so it does not prove
local hybrid repair.

For the first `n` queries in workload order and a preregistered scalar cost functional
`c` on exact work-counter vectors, operational accounting is

```text
C_world(n) = c(W_build(epoch))
             + sum_i<=n c(W_load + W_abstract_plan + W_audit
                          + W_local_ground + W_full_fallback)_i
C_ground(n) = sum_i<=n c(W_same_query_ground(i))
N_break_even = min {n>=1 : C_world(n)<=C_ground(n)}, else NOT_REACHED.
```

Evaluation-only J0 comparison work is stored separately. Phase 3B records the actual
noninterchangeable implementation counters: build ground-state/action/outcome counts,
behavioural rounds and model bytes; per-occurrence model/query loads and bytes,
abstract candidate/frontier/decision counts, portable-envelope and live ground-audit
reachable pairs, local/fallback zeroes, evaluation-only J0 candidates, and
reconciliation totals. It freezes no scalar `c`; its scalar totals and
`N_break_even` are `null`, not `NOT_REACHED`. It does not run the workload-economics
Gate or claim break-even. V0-028 is additive:
none of these labels may rewrite V0-024--V0-027's identities, goldens, or claims.

### Contract 0.8.0: Phase 3C local-recovery slice

The scientific center remains reusable abstract-primary planning. Contract `0.8.0`
therefore tests whether a frozen world model can answer one query unchanged and repair
another only where its complete-plan certificate exposes a local distinction; it does
not make refinement itself the endpoint.

Execution profile `phase3c_certificate_triggered_local_recovery` binds one immutable,
query-neutral, stage-1 eleven-cell aliased safe-chain RAPM and BuildEpoch to exactly two
in-coverage occurrences. The canonical `H=1, delta=0` query must route
`ABSTRACT_CERTIFIED`. The canonical `H=2, delta=1/20` proposal must fail before any
ground slice is materialized and then route `LOCAL_GROUND_RECOVERY`.

Authorization is based on the atomic selected-action `DirectBad` proof DAG, not a root
whose recursive bound merely inherits downstream uncertainty. The `H=2` frontier is
the two `h=1` cells/12 states/32 state-action pairs/128 outcomes. Its strict ancestor
dependency is only the selected abstract action's concretizer support (8 pairs/32
outcomes), giving total `40<48` pairs and `160<192` outcomes versus the same-query
all-action graph and `40<144` covered pairs. The local runtime mounts only the 32-pair
frontier slice and a redacted certified abstract boundary. It returns the unique
cardinality-minimal query-owned overlay over the eight-state `((1,1),(2,2))` cell (16
available pairs/64 outcomes, 8 decisions). The base bytes/ID and BuildEpoch stay
identical, and root plus rare `((2,3),)` decisions remain abstract. A whole-ground solve
or whole-model replacement is respectively charged fallback or `REBUILD_REQUIRED`,
never relabelled local recovery.

Independent post-audit requires sound risk `397/20000 < 1/20`, exact hybrid risk
`317/16000`, reward `3/64`, and normalized regret upper zero. J0 risk `99/5000` is
opened evaluation-only after the hybrid policy and certificate freeze. Fallback and
rebuild are zero. The terminal tuple is
`PHASE3C_LOCAL_RECOVERY_PASS/LOCAL_HYBRID_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.
The artifact verifier independently rebuilds/replans/reextracts/replays/restitches/
reaudits before J0 and validates isolation, identities, ordering and exact counters
even after coordinated manifest regeneration.

The local-recovery result sets `grammar_used=false`; the base model still binds its
separately charged V0-026 first-revision construction provenance. The slice supports
only certificate-triggered strict local recovery and a mixed abstract/local contingent
plan over an immutable reusable model. It does not support predicate invention, unknown quotient discovery, workload
economics, full Phase 3/5, scale, learning, or cross-domain generality. SHA-256
manifests bind integrity, not public-key authenticity. V0-029 is additive and leaves
all Phase 3B queries, results, bundle semantics and status tuple unchanged.

### Contract 0.9.0: Phase 3D general local recovery

Execution profile `phase3d_general_local_recovery` resolves `V0-RISK-004..006` in a
registered finite scope. Its operational input is a fully verified frozen Phase 3C
bundle supplied through `--phase3c-bundle`. The runner binds the source RAPM,
`BuildEpoch`, run, manifest, locality, authorization, and local pre-certificate without
calling the Phase 3C world constructor, `SuiteBuildCoverage.from_queries`/transition
closure, partition/quotient/RAPM builders, or ground `U_all`; every such counter, plus
binding and pre-authorization kernel steps, is zero. The binding pass captures the
complete registered 144-action catalogue. All causal/ancestor legality and capability-
cost lookups before authorization use this frozen catalogue rather than new ground
calls.
The source pre-certificate freezes the action-unrestricted reward upper bound. The
trusted authority then constructs the exact selected-policy
reward-min/risk-max Bellman circuit, retains every tied active extremizer, and searches
ambiguity-discharge sets under an explicit cap. One transaction can authorize only the
current earliest `DirectBad` antichain; a deeper causal layer requires a complete
post-audit and a new occurrence-bound transaction. On safe-chain this selects only the
common eight-state cell and reduces authorization from Phase 3C's `40/160` records to
`24/96`, with a `16/64` worker slice. The former is authorized capability scope, not a
claim that all 24 pairs/96 outcomes were executed.

Before isolation, a trusted compiler eliminates the four-node/twenty-realization
source boundary into a `SparseRobustAffineCapability` with one frontier input, zero
exit ports, one reward-min form, and one risk-max form. Minimality means minimum form/
port representation over the fully enumerated finite admissible domain in the frozen
sparse min/max-affine class. The source boundary and equivalence/necessity evidence are
available in the trusted bundle for audit, but the isolated worker receives exactly
three mounted inputs: sparse capability, sparse slice, and occurrence-bound request.

The standard-library worker jointly enumerates deterministic assignments across every
authorized cell/member, composes cell values as `(min reward,max risk)`, and Pareto
prunes only complete root points. It exhausts every lower-cardinality subset before
accepting a cardinality-minimal result; caps and cap-exhausted statuses are explicit.
Safe-chain exhausts 257 assignments and the operational sound post-audit reproduces
reward lower `3/64`, failure upper `397/20000`, regret upper zero, and the immutable
RAPM/BuildEpoch. Its exact-hybrid fields are `null` with status
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`; the operational runner cannot perform
an exact lift. The standalone verifier reconstructs and exact-lifts only in its
evaluation lane, obtaining exact failure `317/16000` from eight patched and twelve
retained abstract decisions before it opens J0. A separate two-cell/two-member control
exhausts 25 assignments and reaches `(1,1/25)` at thresholds `(3/4,1/20)`, while
independent minimum-risk selection returns value zero.
Passing returns `PHASE3D_GENERAL_LOCAL_RECOVERY_PASS`,
`GENERAL_LOCAL_RECOVERY_GATE_PASS`, `PHASE3_AGGREGATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

Ground dynamics enter the operational path only after the abstract full-plan proof
fails and only through the authorized occurrence-bound slice. Frontier materialization
steps exactly 16 pairs and observes 64 positive-probability outcomes. The final sound
post-audit receives `PatchedAuditKernelView`, may step exactly the eight overlay pairs,
and keeps unpatched behavior in the abstract envelope. Thus operational ground work is
exactly `16+8=24` step calls, with zero extra accounting calls and zero calls outside
authorized or patched pairs. The output embeds byte-identical source RAPM/epoch
documents plus the Phase 3C run, manifest, locality, authorization, and local pre-
certificate with content/hash links. The independent verifier's authoritative rebuild,
exact lift, and J0 checks are evaluation-only and cannot be counted as operational work.

This supports exact finite-domain causal authorization, sparse authority compilation,
and joint value-risk local repair under declared caps. It does not support automatic
predicate/quotient discovery, one-shot dependent-horizon repair, an information-
theoretically minimum encoding, uncapped scalability, economics, learning, or cross-
domain empirical generality. Workload economics/dynamic routing is the next Gate;
learned proposal/model synthesis follows it.

### Contract 1.0.0: accounted dynamic routing

Ledger V0-032 freezes profile `phase3e_accounted_dynamic_routing_v0`. The scientific
center remains an automatically synthesized reusable abstract world model in which
multi-step contingent planning occurs primarily. Ground distinctions may be reopened
only after that model cannot certify the current plan at the registered value/risk
thresholds. Phase 3E accounts and routes that recovery; it does not replace the
world-model objective with a local-repair or accounting objective.

`WorkVectorV1` is the complete native ledger. Operational, evaluation, provenance,
and diagnostic lanes remain distinct, and local, fallback, rebuild, failed-attempt,
verification, process, I/O, and peak-capacity leaves retain their source. The shared
comparison profile projects every operational charged leaf exactly once onto eight
axes: kernel transition calls, registered nonkernel compute events, process launches,
read bytes, staged bytes, output bytes, peak mounted bytes, and peak working bytes.
Additive traffic and peak capacity are never summed together. Evaluation-only replay
never enters an operational route vector.

At one decision point only marginal `U_local_attempt` and `U_direct_fallback` are
compared. Local is selected only under strict componentwise dominance; equality,
incomparability, missing/stale/invalid evidence, a profile mismatch, or any causal
outcome other than `FOUND` selects fallback. Common-prefix work is charged once outside
both marginal uppers. A failed local attempt closes its transaction with its actual
work intact; any fallback begins a new decision point.

Every upper, cap, cardinality proof, frontier, causal result, decision, transaction,
work vector, projection, attestation, and terminal artifact is typed and content
addressed by full SHA-256 over `domain-tag || 0x00 || canonical-json`. Route uppers bind
all query/build/plan/threshold/occurrence/attempt/decision/transaction/frontier/cap/
cardinality/formula/profile identities. A changed identity makes the upper stale even
when its numeric vector is unchanged. Typed `NOT_APPLICABLE` records are not missing
fields and cannot replace a required local identity.

The registered profile permits at most two continuous local transaction indices and
uses the exact V0-032 causal, materialization, compiler, solver, rational, and
post-audit caps. A trusted replay derives the budget outcome from unique native
records; worker budget labels are untrusted. Tight route uppers are computed from
frozen pre-execution cardinalities and exact formulas capped by the registered hard
limits, never by substituting a broad hard cap.

The operational protocol is estimate-before-execute. Before the content-addressed
route decision freezes, no ground transition enumeration, local materialization,
compiler, local/fallback worker, stitch, or post-audit is permitted. A fallback-selected
path has native-zero local execution leaves and no local execution artifacts. A local
path may materialize, compile and launch only after the decision; it either closes
after a negative worker result or, for a candidate, continues through exact-bound
stitch and sound post-audit artifacts. Preselection reads bind the exact failed-
certificate and action-catalogue identities alongside every other frozen input. The
charged semantic authority is the exact decision/causal/two-upper/two-cardinality
dependency closure, not an arbitrary set of attestations. Phase 3B/3C/3D full solver/J0/lift reconstruction belongs to standalone
evaluation verifiers; the 1.0.0 operational path cannot replay it on the host.

Terminal authority is the typed `(terminal_scope, terminal_class, terminal_code)`
triple. Feasible plan, exact infeasibility, and noncertificate attempt closures are
disjoint. `FALLBACK_CAP_EXHAUSTED`, protocol/integrity failure, rebuild required, and
attempt-budget exhaustion never become infeasibility certificates. Every registered
logical occurrence stays in the closure, certificate-coverage, and future economics
denominators, including all failed local, fallback, rebuild, and retry work.

Contract 1.0.0 freezes no scalar cost: `official_scalar_cost` and
`official_N_break_even` are null and the scalar Gate is `NOT_RUN`. Until the native
counter registry covers every operational and failure path, the no-full-replay
migration, typed attestations, exact projections, trusted cap replay, terminal closure,
access-order attacks, and independent verifier all pass, the only valid status is
`official_execution_allowed=false`, `COUNTER_COMPLETENESS_GATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

V0-033 closes the four former scoped P0 contract gaps with exact two-stage non-self-
referential accounting, runner-owned continuation `WORK_VECTOR` authority, a
content-addressed runtime tree and single-use post-freeze executor factory, and
whole-occurrence typed failure/aggregate-terminal replay. These are four scoped
interface closures, not completion of the Phase 3E Gate or of automatic reusable-world-
model synthesis. Their current strict evidence includes manifest-derived
`RuntimeFactoryCardinalityV1` in route uppers, a success receipt bound to the final
access log, `SealedExecutorFailureMergeProofV1` over exact factory/delegate/merged
partials, and rejection-only `PARTIAL_ACCOUNTED_COMMON` preservation of already
observed verifier work. The foregoing official status remains locked because exact
cached-infeasibility/abstract-audit authority, complete all-path native/hash
instrumentation (including planner/package control, all terminals, and the unassigned
`common.hash_invocations` leaf), registered live dependent transaction-2 evidence,
rebuild/retry, the upstream manifest-to-plan/audit consumer, and independent complete-
bundle verification are still absent.

## Pseudocode / schema

```text
declare_coverage(rho0):
  support = canonical positive-mass QuerySpec support
  covered_states = transition_closure(support, all legal actions/outcomes)
  descriptor = (mode=query_support_transition_closure, initial_support_sha256,
                covered_state_count, reuse_outside_coverage_forbidden=true)

build(structural_config, coverage_descriptor, grammar, budgets) -> RAPM
query(RAPM, QuerySpec) -> PolicyResult

PolicyResult:
  policy_graph
  value_certificate
  risk_certificate
  fallback_locations
  accounting
  status

ExactD4BaselineResult:
  complete_state_time_graph_id
  group_profile_id
  state_orbits, action_orbits, concretizer
  representative_independence_proof
  singleton_envelope_proof
  ground_vs_lifted_value_risk_proof
  status = CERTIFIED or EXACT_D4_QUOTIENT_INVARIANT_VIOLATION

AliasedCEGARPositiveControlResult:
  profile_key, ground_structural_id, build_id, query_id
  base_partition_id, semantic_adapter_id, grammar_id
  ordered_iteration_ids, accepted_split_ids
  exact_lifted_return_risk, sound_certificate
  status = one of the eight CEGAR statuses

Phase3AConstructionSliceResult:
  profile_key, suite_registry_id, train_split_id, heldout_split_id
  coverage_id_by_domain, rapm_id_by_domain
  construction_trace_by_domain, cross_automorphism_audit
  J0_Jkappa_J2_rows, heldout_reuse_audit
  status = PHASE3A_SLICE_PASS or PHASE3A_INVARIANT_VIOLATION
  full_phase3_gate_status = PHASE3_AGGREGATE_NOT_RUN

WorkloadSpec:
  workload_id, ordered_query_ids, coverage_roots, coverage_rule
  expected_query_count, allowed_routes, build_epoch_ids

BuildEpoch:
  external provenance over structural/kernel/coverage/registry/adapter/synthesizer/
  contract/schema/source IDs, plus portable_rapm_id

PortableRAPM:
  coverage, coverage_id, state_catalog(planning_kind), partition
  nominal, exact_envelope, semantic/ground_action_catalogs, concretizer
  reward_features, normalizer_rules, goal_ids=[default]

NormalizerRule:
  proof_id, kind=nonnegative_feature_caps_v1
  reward_basis sorted by name: complete (name, nonnegative raw weight) vector
  feature_caps sorted by name: (name, per_step_cap|null, total_cap|null)

PortableQueryV1:
  model_id, cell_rho0, H, raw_reward_weights, normalized_reward_weights
  normalizer, normalizer_proof_id, goal_id=default, delta

Phase3BPortableCampaignResult:
  profile_key, workload_id, build_epoch_id_by_domain, portable_rapm_id_by_domain
  construction_dependency_audit, fresh_process_query_results
  status = PHASE3B_PORTABLE_RAPM_PASS or PHASE3B_INVARIANT_VIOLATION
  full_phase3_gate_status = PHASE3_AGGREGATE_NOT_RUN
  local_hybrid_gate_status = LOCAL_HYBRID_GATE_NOT_RUN
  workload_economics_gate_status = WORKLOAD_ECONOMICS_GATE_NOT_RUN

Phase3CLocalRecoveryResult:
  profile_key, base_epoch_id, base_rapm_id, query_occurrence_ids
  pre_audits, direct_proof_inventory, frontier, authorized_slice
  isolated_repair_attestation, local_overlay, hybrid_policy, post_audit
  status = PHASE3C_LOCAL_RECOVERY_PASS or PHASE3C_INVARIANT_VIOLATION
  full_phase3_gate_status = PHASE3_AGGREGATE_NOT_RUN
  local_hybrid_gate_status = LOCAL_HYBRID_GATE_PASS
  workload_economics_gate_status = WORKLOAD_ECONOMICS_GATE_NOT_RUN

Phase3EAccountedDynamicRoutingV1:
  contract_version = 1.0.0
  profile_key = phase3e_accounted_dynamic_routing_v0
  counter_registry_id, comparison_profile_id, actual_projection_profile_id
  logical_occurrence_id, route_attempt_id, decision_point_id, transaction_id
  frontier_snapshot_id, causal_evidence_id, cardinality_evidence_ids
  route_upper_formula_ids, route_upper_derivation_proof_ids
  local_upper_id, fallback_upper_id, route_decision_id, access_event_log_id
  runtime_factory_cardinality_ids
  sealed_executor_construction_receipt_id, postconstruction_access_event_log_id
  sealed_executor_execution_merge_proof_id
  sealed_executor_failure_evidence_id, sealed_executor_failure_merge_proof_id
  sealed_failure_source_triples=(factory, delegate-or-typed-null, merged)
  partial_common_accounting_ids
  operational_work_vector_ids, evaluation_work_vector_ids
  typed_verification_attestation_ids, route_terminal_artifact_id
  occurrence_terminal_artifact_id, occurrence_terminal_semantic_result_id
  rebuild_policy_id, rebuild_event_ids, occurrence_closure_ids, campaign_summary_id
  workload_vector_spec_id, vector_prefix_ids, worst_frontier_ids
  official_execution_allowed = false
  official_scalar_cost = null
  official_N_break_even = null
  counter_completeness_gate_status = COUNTER_COMPLETENESS_GATE_NOT_RUN
  workload_economics_gate_status = WORKLOAD_ECONOMICS_GATE_NOT_RUN
```

Total cost follows the V0-028 route-resolved equation above. Cached execution is not a
new query; build, load, abstract plan, audit, local ground, full fallback, and
evaluation-only J0 costs remain separate.

## Invariants

1. A per-query policy is never stored as if it were part of reusable dynamics.
2. `structural_id` and `query_id` remain semantically disjoint; `build_id` composes the
   structural identity with an explicit coverage descriptor and source identity.
3. Every certified root has certified reachable descendants.
4. Fallback solves and charges the same query.
5. Lower-authority vision text cannot change this contract.
6. A known-infeasible production shortcut resolves an exact proof for the identical
   structural/build/kernel identity and query hash; it never reuses an infeasibility
   result across dynamics or query fields.
7. The exact `D4` baseline merges only states with the same remaining horizon and never
   aliases failure/terminal semantics with a nonterminal state.
8. Its fixed stochastic concretizer is uniform over distinct inverse ground actions;
   it does not relax the deterministic selector policy class.
9. A coverage-limited RAPM is closed under all legal actions/outcomes from its declared
   support and rejects every query whose support is outside the recorded closure.
10. The aliased profile never imports stabilizer-orbit actions, exact-`D4` status, or
    exact-homomorphism evidence; certification terminates refinement before any optional
    third tightening split.
11. Phase 3A suite coverage hashes the canonical union of training support states and
    closes only that union; held-out query fields are not constructor inputs.
12. Each Phase 3A held-out row references the same frozen coverage and RAPM identity as
    its domain's registered training construction, and an uncovered held-out support
    is rejected.
13. `PHASE3A_SLICE_PASS` can coexist only with
    `PHASE3_AGGREGATE_NOT_RUN`; it cannot be promoted to a Phase 3 Gate pass.
14. A Phase 3B build epoch is immutable and externally binds the coverage/model IDs;
    construction is independent of all query values, policies, horizons, reward
    weights, and risk thresholds. Epoch identity and extensional model identity are
    distinct content-addressed objects.
15. A Phase 3B fresh planner resolves every planning dependency from the portable RAPM
    and its cell-level portable-query-v1 projection; the later exact auditor is
    separately recomputed and cannot
    feed results back into construction/planning.
16. Local ground recovery is unreachable before a plan-certificate failure and is
    limited to the recorded earliest atomic `DirectBad` frontier and its dependencies.
17. A Phase 3B pass always carries all three `*_NOT_RUN` Gate statuses and preserves
    every earlier profile's historical result label.
18. Phase 3C computes a local frontier only from direct atomic proof residuals after a
    failed complete certificate; propagated ancestor uncertainty cannot widen it.
19. A Phase 3C overlay is query-owned and leaves base RAPM/BuildEpoch bytes and IDs
    invariant; its scope is a strict subset of coverage and its hybrid graph retains
    both local and abstract reachable decisions.
20. J0 cannot enter Phase 3C frontier, authorization, local selection, stitching, or
    post-audit; evaluation opens it only after those artifacts freeze.
21. Phase 3D causal search uses certificate slack and all tied active extremizers; a
    reachable DirectBad residual that cannot close a failed root obligation is not
    authorized by that transaction.
22. Phase 3D worker authority consists only of capability, request, and sparse slice;
    presence of the trusted source boundary in the bundle does not mount it in the
    isolated runtime.
23. Every Phase 3D exponential search has a declared cap and distinct exhausted
    status; an incomplete prefix cannot be returned as an exact result.
24. Local action choice is one global deterministic value-risk composition across all
    authorized members/cells, never independent minimum-risk selection.
25. Phase 3D leaves Phase 3C schemas, goldens, and claims unchanged.
26. Operational Phase 3D consumes and preserves a verified frozen Phase 3C bundle and
    its locality, authorization, and pre-certificate `U_all`; it performs zero model
    construction/closure and zero ground steps before local authorization. Its complete
    144-action binding catalogue supplies pre-authorization legality/cost queries.
    Verifier reconstruction and exact lift are evaluation-only.
27. Phase 3D operational post-audit can step only exact overlay pairs through
    `PatchedAuditKernelView`; unpatched decisions remain envelope-evaluated. Operational
    exact lift is forbidden and its exact-hybrid fields remain null.
28. Phase 3E freezes verified marginal route uppers and the route decision before any
    route-specific ground transition, compiler, worker, stitch, or post-audit access.
29. Every Phase 3E operational charged leaf is present, including native zero, and
    projects exactly once to one shared additive or peak axis; evaluation, provenance,
    diagnostic, and derived-only fields cannot enter operational comparison cost.
30. Local selection requires strict componentwise dominance and `local_allowed=true`;
    equality, incomparability, stale/missing evidence, cap exhaustion, no sound cover,
    or local-cap impossibility deterministically selects fallback.
31. Host full solver replay, unrestricted ground upper recomputation, exact lift, and
    J0 are forbidden in the 1.0.0 operational lane and remain separately charged
    evaluation work.
32. A complete hash chain establishes bytes and binding only. It cannot change a
    noncertificate closure or cap exhaustion into a plan/infeasibility certificate,
    and no registered logical occurrence may be removed from a Gate denominator.
33. A route-upper transport envelope is not generation evidence. Its complete
    eight-axis vector must replay from the exact registered cardinality set, one
    formula term per operational leaf, hard-cap minima/structural guards and the
    current context/decision/transaction/frontier identities.
34. A typed verification attestation is accepted only after the registered semantic
    verifier recomputes its result and charges an operational verification record.
    A role without an implemented authority fails closed even when its claimed outcome
    belongs to the legal vocabulary.
35. Contract 1.0 workload ordering is vector-valued. Until a later ledger revision
    freezes a scalar, every prefix/campaign artifact keeps scalar cost and
    `N_break_even` null and the scalar/economics Gates `NOT_RUN`.
36. Every preselection read, including the failed certificate and action catalogue,
    binds the exact prepared identity; inapplicable fallback frontier/proof fields use
    content-addressed typed nulls rather than dummy IDs or omission.
37. Route-decision authorization contains exactly the causal result, both route-upper
    results and one matching cardinality verification per upper. Missing, duplicate or
    extra semantic results invalidate authorization.
38. A local candidate binds exact capability, worker, stitch and post-audit artifacts.
    A negative local solver result closes after materialize/compile/worker, forbids
    stitch and post-audit artifacts, and may continue only at a fresh fallback decision.
39. A failed transaction-1 post-audit creates a fresh decision that may choose local
    transaction 2 or direct fallback without inventing transaction 2. Both route
    adapters preserve every observed work prefix incrementally when later execution
    fails.
40. Each sealed candidate route derives `RuntimeFactoryCardinalityV1` from its exact
    frozen manifest/cap and binds that ID in its route-specific cardinality source
    chain before comparison; after selection the factory rechecks the chosen chain.
    The registered sealed safe-chain fallback uses the preselection identity
    `C_route=5815=C_factory(3)+C_solver(5812)`: cardinality incorporates the reserve
    before the route-total cap is applied, never as a post-hoc `+3`. A total `5812`
    with reserve `3` yields worker share `5809` and a cap-rejection/noncertificate
    path. The positive upper proof leaf is `5815`; a reserve-zero legacy payload keeps
    its original schema, domain and content ID.
41. A successful sealed construction receipt binds the exact factory work and the
    final selected-route `AccessEventLogV1` returned by `Phase3ERunResultV1`; an earlier
    or foreign log cannot authorize the result.
42. A sealed failure retains exact factory, delegate-or-typed-null, and merged
    WorkVector/comparison/projection triples. A rejected continuation may retain
    observed verifier work as `PARTIAL_ACCOUNTED_COMMON`, but that evidence is neither
    a successful receipt nor continuation/certificate authority. The failure merge is
    not yet a separate FQ7 or independent-bundle semantic authority.
43. `Phase3EOccurrenceTerminalArtifactV1`, not a route-attempt terminal, is the
    evaluation-lane occurrence authority for `PROTOCOL_FAILURE` and
    `FALLBACK_CAP_EXHAUSTED`; both retain counts `0/0/1` and every denominator.
44. Nonsemantic `VALID` is derived only by registered check-kind replay over typed
    evidence; a caller cannot supply evidence IDs. Plan source records are disjoint
    from sealed-core records. Every occurrence runtime result independently replays
    its aggregate, ordered run/transaction correspondence, final closure and terminal
    authority, rejecting stale or rearranged histories.

## Acceptance tests

- Mutating `H`, registered reward/goal fields, or `delta` leaves the Phase 0.5 coverage
  descriptor unchanged; mutating `rho0` leaves `structural_id` unchanged but changes
  `query_id` and the descriptor-specific `build_id`.
- Mutating each structural field invalidates the RAPM build key.
- Two builds with identical structure/source but different coverage declaration hashes
  or covered-state counts have different build IDs.
- A query with any positive-mass initial state outside the recorded transition closure
  is rejected before planning; it cannot reuse a certificate or RAPM cache entry.
- Phase 3D independently reproduces the `24/96` authorized capability scope,
  `1/0/1+1`, 257-assignment, and 25-assignment goldens; deleting a retained sparse
  port/form or forging a cap counter fails replay. Operational work separately
  reconciles 16 materialization steps/64 positive outcomes and eight restricted
  post-audit steps to 24 total, with zero accounting/out-of-scope steps and no exact
  hybrid replay.
- Phase 3D source-boundary tests monkeypatch the Phase 3C constructor, transition
  closure, partition/quotient/RAPM builders, and operational unrestricted-upper solver
  to fail if called; valid runs still preserve source model/epoch/run/manifest/locality/
  authorization/pre-certificate bytes and provenance, while malformed or coherently
  re-signed source artifacts fail verification/replay. The binding-time 144-action
  catalogue, rather than fresh pre-authorization calls, must serve causal and ancestor
  legality/cost lookup.
- The standalone Phase 3D verifier's evaluation-only reconstruction/lift reproduces
  exact failure `317/16000` with eight patched and twelve abstract decisions before J0;
  those operations never enter operational work counters or post-certificate exact
  fields.
- A cached execution is excluded from planning-query counts.
- Both Phase 0.5 domains emit a reusable model and separate query result.
- Result labels reject nominal-only “certificates.”
- A production known-infeasible query performs zero refinement steps, while the named Phase 0.5 regression still performs its mandatory split.
- A proof with a mismatched structural ID, build ID, kernel hash, or query hash cannot
  activate the production infeasibility shortcut.
- For the safe-chain fixture, changing the spawn law changes the structural/build hash;
  changing only the `D4` initial distribution leaves `structural_id` unchanged but
  changes the query/run identity and its coverage-specific build ID.
- The safe-chain exact profile has complete state and action orbit coverage, zero-width
  reward/cost envelopes, singleton transition uncertainty, exact value/risk equality to
  J0, failure `99/5000`, zero action-restriction gap, and strict compression in both
  reachable state-time nodes and total legal state-action pairs.
- Injecting a non-equivariant transition, duplicate-action multiplicity bias, or
  representative-dependent aggregate produces
  `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`, never a split or ground fallback.
- The aliased profile reconstructs ten base cells from all 192 covered states, selects
  two exact-witness-driven `first_survivor_adjacent_nonmerged_count|<=|1/2` splits at
  four bits each, and ends at twelve leaves with reward `3/64`, exact lifted failure
  `317/16000`, sound `U_F=397/20000`, regret zero, eight pointwise certificates, and
  zero fallback calls.
- Its ground structural/query identities equal the exact baseline inputs, while the
  profile/build/adapter/grammar/partition/result identities differ; neither verifier
  accepts the other profile's result label or artifact topology.
- Reordering, changing, or deleting held-out queries leaves both Phase 3A construction
  signatures unchanged; passing held-out values into either builder fails leakage
  validation.
- The G2048 Phase 3A partition has 8 cells over 192 states and 7 active cells over 68
  active states; 14 abstract entries replace 18 complete `D4` state-action orbits and
  144 active ground state-action pairs. The 20-state training-support union and bridge
  witnesses `(0,2,2,2)`/`(0,2,4,2)` are reproduced; those non-`D4` states are jointly
  policy-reachable in one cell with action `AWAY`, and the bridge exact row is
  `(reward,failure,U_F)=(13/400,199/5000,1/25)`.
- The LMB partition has trace `3 -> 5 -> 5`, five cells over 25 states, four abstract
  entries versus 16 physical state-action orbits and 40 ground state-action pairs, and
  three active cells over 18 active states; within every active cell, the same lifted
  training policy graph reaches members from multiple of its ten active physical-
  automorphism orbits.
- Every registered Phase 3A train/held-out row reproduces the V0-027 rational goldens,
  has `J0=Jkappa=lifted` reward and failure, and normalized regret upper bound zero.
- Phase 3B builder API/data-flow and static source audits fail on an injected
  Q/value/frontier/policy/query/evaluation dependency in the behavioural builder or
  portable planner and pass when driven only by the complete one-step behavioural
  model. This is not generalized into a whole-run closed-import-DAG claim.
- Phase 3B reproduces G2048 trace `2 -> 9 -> 10 -> 10`, state/action compression
  `192 -> 10` and `144 -> 17`, and LMB trace `3 -> 5 -> 5`, `25 -> 5`, and `40 -> 4`.
- The portable RAPM round-trips canonically; fresh bubblewrap-isolated subprocesses plan eleven distinct
  ground queries whose projections contain at least eight distinct portable queries,
  at least four per domain and with multi-step coverage in both,
  before the independent exact audit/J0/lift phase begins, while retaining one
  model/build-epoch ID per domain.
- Each occurrence attests a read-only current model/query, initially empty writable
  output, unmounted project/other-request files, `-S`, isolated network namespace, and
  exactly the three staged application modules.
- Phase 3C independently reproduces the H1 abstract-certified row and the H2 failed
  pre-audit, two-cell/12-state direct frontier, `32+8=40<48<144` authorized pairs,
  `128+32=160<192` authorized outcomes, worker-only 32-pair frontier mount,
  eight-state/16-available-pair/64-outcome/eight-decision minimal overlay, retained
  abstract nodes, immutable
  base, exact/sound post-goldens, late J0 and zero fallback/rebuild.
- Re-hashing the entire Phase 3C bundle after changing a route, witness/frontier, slice,
  patch, abstract node, base/query/coverage, isolation attestation, evaluation order,
  post-certificate or counter still fails independent semantic replay.
- Portable query validation rejects an unregistered normalizer proof, negative raw
  weight, reward-basis mismatch, missing positive-weight feature cap, bound-violating
  normalizer, or normalized weight unequal to `raw/normalizer`.
- Portable model validation rejects duplicate/unsorted proof IDs or feature names,
  an incomplete/negative reward basis, unknown feature names, a non-v1 rule kind,
  negative caps, or a positive-basis-weight feature with both caps null.
- Every registered Phase 3B result is `ABSTRACT_CERTIFIED`, agrees with independent J0
  and ground lift, and records zero local/fallback cost without claiming their Gates.
- Mutating the kernel, coverage, feature/action registry, synthesizer, schema, or source
  revision changes `BuildEpoch`; it changes the portable model ID only if its payload
  changes. Changing a query cannot mutate the frozen epoch or model.
- Independent verification rebuilds both authoritative kernels, coverage closures,
  behavioural models, and their G2048/LMB authority normalizer registries; it reprojects
  all queries, recomputes portable-envelope and live
  exact ground audits, lifts through serialized `kappa`, runs J0, validates IDs,
  cross-links and counters, and can replay the isolated planner.
- Contract-1.0 component attacks cover canonical/domain IDs; exact native counter
  completeness and reconciliation; eight-axis actual projection; 34-leaf route-upper
  derivation with 13 native cap minima and six structural guards; strict-dominance
  selection; pre-freeze access; transaction/rebuild closure; logical-occurrence
  denominators; scalar-free prefix frontiers; and partial semantic authority. These
  tests must retain `official_execution_allowed=false` and both Phase 3E Gates
  `NOT_RUN` until the integrated production and independent bundle paths also pass.
- Sealed-route attacks mutate manifest cardinality/source binding, the success
  receipt's final access-log ID, every factory/delegate/merged failure-proof reference,
  the all-ID/all-typed-null delegate rule, failure stage, and post-failure log; each
  mutation must fail exact replay.
- Rejected-continuation attacks remove, duplicate, overlap, change lane/registry, or
  stale-bind an observed verifier record in `PARTIAL_ACCOUNTED_COMMON`; each must fail,
  and no such evidence may mint a successful charge receipt, continuation authority,
  plan certificate or infeasibility certificate. A protocol-failure occurrence
  noncertificate remains the only allowed terminal use.

## Out of scope

Neural encoders, learned/statistical world models, MCTS, first-hit options, SMDP duration, POMDP/belief adapters, visual perception, infinite horizon, cross-domain meta-controllers, interpreting a supplied `D4` group as an automatically discovered abstraction, interpreting Phase 3A exact-model cross-orbit aggregation as oracle-free unknown-quotient discovery, interpreting Phase 3B exact one-step synthesis as predicate invention or local hybrid planning, or interpreting Phase 3D as workload break-even or a full Phase 3/5 pass.

## Known failure modes

State explosion, incomplete predicate grammar, no common semantic action, overly conservative envelopes, infeasible chance constraints, build cost that never amortizes, incorrect state/action group transforms, and a cache key that omits or misstates build coverage. For the exact `D4` baseline, a nonzero width is an invariant failure rather than acceptable conservatism. For the aliased profile, hard-coding its two cell IDs instead of extracting and ranking exact witnesses invalidates the CEGAR-discovery claim. For Phase 3A, using held-out fields during atom selection, accepting a cross-orbit cell reachable only outside the registered policies, or calling the eight-cell G2048 interval model an exact homomorphism invalidates the claim.

## Open risks

Later claims about shared grammar/coordinates and practical amortization remain empirical. They do not weaken Phase 0.5 soundness obligations. V0-027 closes the immediate cross-automorphism state-alias positive control; V0-028 establishes the no-Q/value-signature portable world-model path; V0-029 executes the first strict local repair; and V0-030 closes joint finite local composition, slack-aware causality, and finite-domain sparse capability. Automatic predicate invention, dependent-horizon recovery, workload economics/dynamic routing, and the complete statistical Phase 3/Phase 5 Gates remain open empirical work.
