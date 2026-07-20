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

## Acceptance tests

- Mutating `H`, registered reward/goal fields, or `delta` leaves the Phase 0.5 coverage
  descriptor unchanged; mutating `rho0` leaves `structural_id` unchanged but changes
  `query_id` and the descriptor-specific `build_id`.
- Mutating each structural field invalidates the RAPM build key.
- Two builds with identical structure/source but different coverage declaration hashes
  or covered-state counts have different build IDs.
- A query with any positive-mass initial state outside the recorded transition closure
  is rejected before planning; it cannot reuse a certificate or RAPM cache entry.
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

## Out of scope

Neural encoders, learned/statistical world models, MCTS, first-hit options, SMDP duration, POMDP/belief adapters, visual perception, infinite horizon, cross-domain meta-controllers, interpreting a supplied `D4` group as an automatically discovered abstraction, interpreting Phase 3A exact-model cross-orbit aggregation as oracle-free unknown-quotient discovery, or interpreting Phase 3B exact one-step synthesis as predicate invention, local hybrid planning, workload break-even, or a full Phase 3/5 pass.

## Known failure modes

State explosion, incomplete predicate grammar, no common semantic action, overly conservative envelopes, infeasible chance constraints, build cost that never amortizes, incorrect state/action group transforms, and a cache key that omits or misstates build coverage. For the exact `D4` baseline, a nonzero width is an invariant failure rather than acceptable conservatism. For the aliased profile, hard-coding its two cell IDs instead of extracting and ranking exact witnesses invalidates the CEGAR-discovery claim. For Phase 3A, using held-out fields during atom selection, accepting a cross-orbit cell reachable only outside the registered policies, or calling the eight-cell G2048 interval model an exact homomorphism invalidates the claim.

## Open risks

Later claims about shared grammar/coordinates and practical amortization remain empirical. They do not weaken Phase 0.5 soundness obligations. V0-027 closes the immediate cross-automorphism state-alias positive control. V0-028 establishes the no-Q/value-signature portable world-model path, and V0-029 executes one certificate-triggered strict local-repair slice; automatic predicate invention, broader recovery, workload economics, and the complete statistical Phase 3/Phase 5 Gates remain open empirical work.
