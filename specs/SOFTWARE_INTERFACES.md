# Software Interfaces

## Definitions

All public records are versioned, immutable value objects with canonical serialization. Probabilities, benchmark rewards, thresholds, and rate inputs use reduced rationals at the boundary.

Core interfaces are `DomainProtocol`, `Enumerator`, `GroundConstrainedOracle`, `Partition`, `RAPMBuilder`, `NominalPlanner`, `ExactAuditor`, `PredicateGrammar`, `RefinementEngine`, `FallbackSolver`, `ArtifactWriter`, and `RunAccounting`. The safe-chain positive control additionally uses a versioned `ExactGroupQuotientProfile` and `ExactGroupQuotientBuilder`; these are known-symmetry adapters, not learned refinement interfaces. The separately keyed aliased safe-chain positive control uses the ordinary RAPM and refinement interfaces plus a versioned `AliasedCEGARProfile`; it never calls the exact-group builder.

Phase 3A additionally exposes `SuiteBuildCoverage`, `GroundOracleTable`,
`OraclePartitionSelector`, `ExactBehavioralQuotientBuilder`, `SemanticKernelView`,
`PolicyLifter`, and `Phase3AConstructionRunner`. These are exact-model/oracle control
interfaces, not learned feature or predicate discovery APIs.

Phase 3B adds `WorkloadSpec`, `BuildEpoch`, `PortableRAPMWriter`,
`PortableRAPMLoader`, `ExactOneStepBehavioralSynthesizer`,
`FreshProcessAbstractPlanner`, `ConstructionDependencyAudit`, `QueryRoute`,
`LocalGroundFrontier`, and `WorkloadAccounting`. These make the reusable world model
and its planning boundary explicit; they do not expose a learned-model or local-hybrid
claim.

Phase 3C adds the direct-proof inventory, authorized-slice, isolated local-runtime,
query-owned overlay, hybrid-stitch, and post-audit interfaces defined below. They do not
turn the immutable RAPM into an online mutable model API.

Phase 3D adds `CausalProofCircuit`, `SlackAwareCausalFamily`,
`SparseCapabilityCompiler`, `SparseRobustAffineCapability`,
`GeneralLocalRecoveryRequest`, `GeneralLocalSolver`, and
`GeneralLocalRuntimeAttestation`, plus the restricted `PatchedAuditKernelView`. These
are exact finite-domain, cap-aware interfaces;
`FrozenPhase3CWorld` and `load_frozen_phase3c_world` form their operational source
boundary. The loader verifies and binds a frozen Phase 3C artifact bundle without
transition closure, kernel steps, or any partition/quotient/RAPM builder. These
interfaces do not authorize learned predicates, mutable models, or an uncapped solver.

## Normative decisions

`DomainProtocol` is the only domain-specific authority for physical state/action
canonicalization, validation of query-owned initial distributions, optional named
fixture defaults, legal primitive actions, exact outcomes, failure/success tests,
registered reward/goal features, semantic labels, frozen concretizer, and registered
strategic features. Planner code cannot inspect domain object internals.

Minimal records:

```text
Outcome(probability, next_state, reward_features, entered_failure)
QuerySpec(rho0, horizon, reward_weights, goal_id, delta,
          normalizer_value, normalizer_proof_id)
EnvelopeEntry(reward_set_or_bounds, failure_set_or_bounds,
              successor_distribution_set, provenance)
PolicyNode(cell_id, remaining_horizon, semantic_action, child_node_ids,
           selector_class="deterministic_markov")
Certificate(evidence, raw_regret_upper, normalizer_value,
            normalized_regret_upper, failure_upper, dependencies, status)
Counterexample(x, x_prime, cell_id, semantic_action,
               remaining_horizon, audit_channel, observed_gap)
Predicate(id, feature_name, operator, rational_threshold, rate_bits)
SplitEvaluation(predicate, child_signatures, audit_reduction,
                newly_certified_pairs, failure_width_reduction,
                incremental_rate, status)
Accounting(build, query, audit, refinement, fallback, totals)
ExactGroupQuotientProfile(group_id, ordered_elements, state_transform,
                          action_transform, canonical_order,
                          concretizer_rule="uniform_distinct_inverse_actions")
OrbitCell(cell_id, remaining_horizon, canonical_state_id, member_state_ids,
          stabilizer_element_ids)
ActionOrbit(action_orbit_id, canonical_action_ids,
            inverse_ground_action_ids_by_state)
BuildCoverageSpec(mode, initial_support_sha256, covered_state_count,
                  reuse_outside_coverage_forbidden)
AliasedCEGARProfile(profile_key, ground_structural_key, base_encoder_id,
                    semantic_adapter_id, grammar_id, budget_profile,
                    expected_iteration_contract)
RefinementIteration(index, input_partition_id, proposal_id, audit_id,
                    witness_ids, ranked_candidate_ids, accepted_split_id,
                    output_partition_id, counters_before, counters_after)
SuiteBuildCoverage(mode, declared_support_set_sha256,
                   declared_support_state_count, covered_state_count,
                   exact_state_cap, admissible_query_support_rule,
                   reuse_outside_coverage_forbidden)
GroundOracleTable(states, max_horizon, reward_weights, goal, delta,
                  state_records, first_action_frontiers)
OraclePartitionSelection(partition, quotient_models, selected_atoms,
                         candidate_trace, training_evaluations,
                         reachable_mixed_cells)
ExactBehavioralQuotient(partition, semantic_adapter, refinement_trace,
                        failure_targets, quotient_models)
Phase3AQueryEvaluation(split, query_id, J0, Jkappa, nominal_J2,
                       exact_audit, ground_lift)
WorkloadSpec(workload_id, ordered_query_ids, coverage_seed_ids,
             expected_query_count, allowed_routes, build_epoch_ids)
BuildEpoch(structural_id, kernel_hash, coverage_id, feature_registry_id,
           terminal_registry_id, semantic_adapter_id, synthesizer_id,
           contract_version, schema_version, source_revision, portable_rapm_id)
PortableRAPM(coverage, coverage_id, state_catalog_with_planning_kind, partition,
             nominal, exact_envelope, semantic_and_ground_action_catalogs,
             concretizer_registry, reward_features, normalizer_rules, goal_ids)
NormalizerRule(proof_id, kind="nonnegative_feature_caps_v1",
               complete_reward_basis_sorted_by_name,
               feature_caps_sorted_by_name)
FeatureCap(name, per_step_cap_or_null, total_cap_or_null)
PortableQueryV1(model_id, cell_rho0, horizon, raw_reward_weights,
                normalized_reward_weights, normalizer, normalizer_proof_id,
                goal_id="default", delta)
ConstructionDependencyAudit(builder_api_fields, builder_source_imports,
                            forbidden_dependency_hits)
FreshProcessQueryRequest(portable_rapm_path, portable_rapm_sha256,
                         portable_query_path, portable_query_sha256)
FreshProcessQueryResult(query_id, rapm_id, frontier, selected_policy_graph,
                        runtime_attestation, accounting)
LocalGroundFrontier(query_id, policy_graph_id, failed_node_ids,
                    ground_cell_member_ids, successor_dependency_ids)
WorkloadAccounting(build_ground_state_action_outcome_counts,
                   build_refinement_rounds_and_model_bytes,
                   per_occurrence_load_bytes, abstract_candidate_frontier_decision_counts,
                   portable_and_ground_audit_reachable_pairs,
                   local_ground, full_fallback, evaluation_only_j0_candidates,
                   reconciliation, scalar_break_even=null)
```

`rho0` is either one canonical state with unit mass or a finite exact distribution. It belongs to `QuerySpec`; a domain may register and return a canonical default distribution for fixture construction, but that default is not part of the structural key. The query validator accepts only registered rewards/goals whose semantics are implemented by the active schema, `H<=Hmax`, `delta in {0,1/20,1/10}`, and a deterministic proved `Rmax(q)` recorded as both `normalizer_value` and `normalizer_proof_id`. Portable schema v1 implements only `goal_id=default`. Canonical `H` and `2N/3` bounds are accepted only for their unchanged registered G2048 and LMB rewards.

Phase 0.5 freezes `BuildCoverageSpec.mode` to
`query_support_transition_closure`. `RAPMBuilder` receives the explicit ordered
positive-mass `QuerySpec.rho0` declaration, hashes that canonical declaration including
exact masses as `initial_support_sha256`, and closes its state support under all legal
actions and positive-probability outcomes until a fixed point or the exact state cap.
It records the resulting distinct state count and
`reuse_outside_coverage_forbidden=true`. The coverage descriptor is build metadata,
not structural environment semantics: `structural_id` excludes it, while `build_id`
includes it. A domain `initial_distribution()` method, where retained for compatibility,
is only a named query factory; generic build code may not invoke it implicitly.

The structural key contains every transition-semantic or build-validation field,
including board geometry, rank cap, `Hmax`, adjacency, merge/action rules, spawn
law/timing, and failure timing. It never contains `rho0`, `H`, `delta`, or reward
coefficients. Policy/result schemas represent
one deterministic selector at every state/cell and remaining horizon; they have no
mixture weights or convexified frontier entries.

The refinement engine owns the eight result statuses frozen in `MILESTONES_AND_GATES.md`. A predicate is rejected if it occurs on the root-to-cell path, creates an empty child, reproduces the same partition, has a previously evaluated child-partition signature, or canonicalizes to an existing threshold. All separating witness/predicate proposals are ranked jointly by decreasing `(audit-width reduction / incremental rate)`, then more newly certified pairs, larger failure-width reduction, smaller rate, lexicographic predicate ID, and canonical witness ID. This prevents a widest-but-grammar-inseparable pair from hiding a useful exact counterexample elsewhere while remaining deterministic.

`ExactGroupQuotientBuilder` is a separate no-refinement path. For the registered
safe-chain profile it consumes the complete reachable `(state,h)` graph, verifies every
`D4` state/action automorphism, constructs full equal-stage orbit cells, canonicalizes
by lexicographic state key with the registered group-element tie order, forms semantic
actions as stabilizer orbits, and forms `kappa` by exact uniform mass over deduplicated
distinct inverse action IDs. Any support, equivariance, representative-independence,
envelope-collapse, or value-preservation failure returns
`EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`. This is a baseline validation status, not a
ninth `RefinementEngine` status, and it cannot trigger CEGAR or fallback.

The `ExactGroupQuotientProfile` and transforms are structural/build-owned. The builder's
materialized reachable graph, orbit cells, plan, and certificate are query-owned;
passing `rho0` or `H` to this materialization does not add them to the structural key or
authorize reuse outside the build's declared coverage.

`AliasedCEGARProfile` freezes a different build path over the same safe-chain ground
structure and query. It requires a complete 192-state coverage inventory; a ten-cell
base partition consisting of one failure cell plus one cell per active
`(empty_count, nonzero-rank histogram)`; zero incremental rate for that fixed encoder;
and `RefinementBudget.full_v0()`. The adapter exposes only deterministic singleton
`canonical:first/last` realizations. Its grammar registry contains exactly the six
action-frame features in `BENCHMARK_GRAMMAR.md`, each with threshold `1/2`; therefore
the selected adjacency predicate costs four bits.

The runner cannot pass target cell IDs to `RefinementEngine` as a fixture schedule.
For each iteration, `ExactAuditor` emits every reachable counterexample, the grammar
emits every separating candidate, and the joint V0 order selects one candidate using
all frozen tie breakers. The golden order is histogram `(1,1,2)` and then `(1,2,2)`.
After the second replan/audit returns `CERTIFIED`, the runner stops before fallback or
the optional `(2,2,2)` tightening split.
Construction/replay violations use the profile-validation status
`ALIASED_CEGAR_INVARIANT_VIOLATION`, outside the refinement engine's eight results;
ordinary audit, budget, refinement, and fallback endings do not gain a ninth status.

`SuiteBuildCoverage.from_queries(kernel, training_queries)` accepts only the training
query tuple. It canonicalizes the union of positive-support states independently of
query order/masses, computes the complete all-action/all-positive-outcome closure, and
freezes the descriptor before any held-out evaluation. `validate_query_coverage` is the
only held-out interaction: it accepts a support subset or raises
`QueryOutsideBuildCoverageError`; it cannot extend coverage.

For G2048, `GroundOracleTable` is built from the 192-state training closure, the fixed
relative-survivor adapter, `h=1,2`, and the training reward/risk profile.
`OraclePartitionSelector` accepts `training_queries` and has no held-out parameter. It
enumerates the fixed four-atom subset lattice, caches duplicate partition signatures,
constructs nominal/envelope models, exact-audits training policies, requires active
compression and a cell in which one lifted training policy graph reaches multiple
`D4` state orbits, and returns the canonical minimum.
The frozen input contains the canonical `H=2` and strict bridge `H=1` training queries;
their 20-state support union closes to 192. The result selects the two `h=1` atoms and
has eight total/seven active cells. The symmetry audit requires bridge witnesses
`(0,2,2,2)` and `(0,2,4,2)` to share one cell but not one `D4` orbit, occur jointly in
the bridge's lifted decision graph, and both select `AWAY`.

For LMB, `ExactBehavioralQuotientBuilder` accepts only the exact kernel and 25 covered
states. It refines status cells by exact action behaviours to trace `3 -> 5 -> 5`,
deduplicates equal-signature ground actions, freezes uniform distinct-action
concretizers, and constructs singleton quotient entries. It accepts no query, reward
weights, risk threshold, train/held-out label, predicate grammar, or automorphism group.

`Phase3AConstructionRunner` constructs both domain objects, freezes their coverage,
partition, adapter, and RAPM identities, and then evaluates the registered train plus
held-out rows with the same four-stage path: unrestricted J0, concretizer-restricted
ground Jkappa, nominal abstract proposal plus exact audit, and independent ground lift.
It requires exact reward and exact failure equality on every row. Reuse claims are
limited to the registered two-domain held-out suite: G2048 changes initial support and
horizon; LMB changes reward basis, horizon, and risk. Its success tuple is
`PHASE3A_SLICE_PASS/PHASE3_AGGREGATE_NOT_RUN`; profile validation failures use
`PHASE3A_INVARIANT_VIOLATION` outside the CEGAR result enum.

`ExactOneStepBehavioralSynthesizer` accepts only a structural kernel view, frozen
coverage, reward-feature/terminal registries, and semantic-action rules. It refines
terminal-kind blocks by complete exact one-step feature/failure/successor behaviour to
a fixed point. Its callable signature has no query, horizon, reward weights, risk,
ground oracle, value table, selected action, or policy argument.
`ConstructionDependencyAudit` checks that API/data flow and statically audits source
imports for the behavioural builder and portable planner. It fails if forbidden
Q/value/refinement/ground-planning dependencies enter those boundaries. This is not an
assertion that every orchestration module in the Phase 3B process belongs to a closed
import DAG.

`PortableRAPMWriter` writes a closed canonical representation with all data required by
abstract planning and later model replay: coverage and `coverage_id`, state catalog,
partition, nominal model, exact envelope, semantic/ground action catalogs, frozen
concretizer, reward features, `normalizer_rules`, and `goal_ids`. The state catalog carries a frozen
`planning_kind in {active,terminal,failure,success}`; cells may not mix active and
terminal states, and every active cell must have at least one model action, so an empty
common-action intersection cannot be misread as successful termination.
The portable payload does not contain `BuildEpoch`; the external epoch binds
`portable_rapm_id` and `coverage_id`, while the model ID is derived only from its own
payload. `PortableRAPMLoader` rejects missing registries, external ground references,
unresolved/content-ID mismatches, noncanonical rationals, mixed planning kinds, or an
actionless active cell.

Portable query schema v1 binds exact cell `rho0`, horizon, raw and normalized reward
weights, normalizer/proof ID, `delta`, and goal to the model. It supports only the
`default` structural stopping goal and rejects other goal semantics. The top-level
normalizer registry is a nonempty list uniquely sorted by `proof_id`; every rule has
exactly `kind=nonnegative_feature_caps_v1`, `reward_basis`, and `feature_caps` in addition
to its proof ID. The basis is the complete registered feature set uniquely sorted by
name, with a nonnegative exact raw weight for every feature including zeros. Caps are
uniquely name-sorted registered features; each positive-basis-weight feature has a
cap record, every cap record has a nonnegative per-step and/or total value with at least
one non-null, and zero-weight features need not have a cap record. A
query requires a registered proof and a complete raw-weight vector exactly equal to
that proof's basis, plus a positive normalizer. The loader computes
`sum_k w_k min(H*per_step_cap_k,total_cap_k)` over the present caps, requires the
declared normalizer to be at least that bound, and requires normalized weights to equal
`raw/normalizer` exactly. This is not general reward or goal extensibility.
`FreshProcessAbstractPlanner` is launched once per occurrence inside a Linux bubblewrap
mount/network namespace. It receives staged copies of only `portable.py`,
`portable_planner.py`, and `portable_runtime.py`, the current read-only model/query, and
an initially empty writable output directory; the checkout and other requests are not
mounted. Python uses `-S`, and a content-addressed runtime attestation records inputs,
namespace status, loaded module origins, and output hashes.

`QueryRoute` has exactly `ABSTRACT_CERTIFIED`, `LOCAL_GROUND_RECOVERY`,
`FULL_GROUND_FALLBACK`, `REBUILD_REQUIRED`, and `INFEASIBLE_QUERY`. The router may
construct `LocalGroundFrontier` only after a failed full-plan certificate. Its nodes are
the earliest policy-reachable failures; support is limited to their cell members and
the exact successor dependencies needed to recompute those model entries. Phase 3B
validates the interface but every passing campaign row is `ABSTRACT_CERTIFIED`.

`WorkloadAccounting` records the implemented noninterchangeable exact fields: build
covered states, ground state-action pairs/outcomes, behavioural rounds and model bytes;
per-occurrence model/query load counts and bytes; abstract composed candidates,
frontier points and selected decision nodes; portable-envelope and live ground-
certificate reachable pairs; local-ground candidates; full-fallback invocations and
candidates; evaluation-only J0 composed candidates; and reconciliation totals. A
later preregistered scalar `CostFunctional` may map them to `C_world/C_ground` and the
first break-even prefix. Phase 3B freezes no such conversion, so scalar costs and
break-even are `null` and it sets `WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

### Contract 0.8.0 local-recovery interfaces

Phase 3C adds `DirectProofInventory`, `LocalFrontierExtractor`,
`AuthorizedGroundSliceBuilder`, `RedactedBoundaryView`, `IsolatedLocalRepairRuntime`,
`LocalOverlay`, `HybridPolicyStitcher`, and `HybridExactAuditor`. These interfaces are
query-occurrence scoped; none may mutate `PortableRAPM` or `BuildEpoch`.

```text
DirectProofInventory.from_failed_audit(base_model, query, proposal)
  -> {direct_bad_nodes, propagated_bad_diagnostics, proof_dependency_edges}

LocalFrontierExtractor.earliest_direct(inventory)
  -> LocalGroundFrontier

AuthorizedGroundSliceBuilder.build(frontier, exact_index,
                                   selected_action_ancestor_dependencies)
  -> {LocalRecoveryAuthorization,
      FrontierOnlyGroundSlice,
      RedactedBoundaryView}

IsolatedLocalRepairRuntime.solve(slice_path, slice_sha256,
                                 boundary_path, boundary_sha256,
                                 request_path, request_sha256)
  -> LocalRepairResult + RuntimeAttestation

HybridPolicyStitcher.stitch(base_policy, local_overlay)
  -> HybridPolicyGraph

HybridExactAuditor.audit(base_model, overlay, hybrid_policy, query)
  -> PostRecoveryCertificate
```

The extractor never substitutes recursive root bound failure for a direct residual.
The slice builder records an exact reason for every action: the registered fixture has
32 frontier pairs/128 outcomes and 8 selected-action ancestor pairs/32 outcomes, hence
`40 < 48` pairs and `160 < 192` outcomes versus the same-query all-action graph and
`40 < 144` covered pairs. The isolated runtime mounts only the 32-pair frontier ground
slice plus content-addressed request/redacted-boundary inputs and staged local
runtime code and an empty output; the project checkout, full portable model, ground
oracle/J0, full coverage catalog, builder/refiner cache, and other requests are absent.
The mounted slice is sanitized to opaque IDs and Bellman branches; payloads, access
logs, and accounting remain trusted-side. The request binds occurrence and capability
hashes. The boundary view contains only IDs, certified handoff bounds, the unrestricted
reward upper bound, and regret/risk tolerances. A result must certify both value and
risk.

`LocalOverlay` binds base model byte hash/ID, BuildEpoch, query and occurrence. It
contains exactly the minimal eight-state local view with 16 available state-action
pairs/64 outcomes and 8 frozen patch decisions for the
registered run, including different legal actions for aliased reachable members, and
sets `grammar_used=false`. A different base, query, coverage, action
outside authorization, conflicting decision, or whole-policy replacement is rejected.
The stitcher requires at least one reachable local decision and at least one reachable
unpatched abstract decision; here the root and rare `((2,3),)` decisions stay abstract.
A base mutation returns `REBUILD_REQUIRED`, not a new local overlay.

The post-auditor must reproduce `3/64`, `397/20000`, `317/16000`, and zero regret before
the evaluation interface may call J0 (`99/5000`). The router then emits
`LOCAL_GROUND_RECOVERY`, with zero fallback/rebuild. The second registered `H=1,
delta=0` occurrence remains `ABSTRACT_CERTIFIED` and cannot create a local request.
Independent interface replay reconstructs every input, repeats isolated execution and
stitch/audit, verifies base-byte invariance and exact counters, and rejects coordinated
re-hashing attacks. Runtime/manifest hashes attest content integrity, not public-key
identity.

### Contract 0.9.0 general local-recovery interfaces

Phase 3D is additive to the v1 Phase 3C slice and boundary schemas:

```text
load_frozen_phase3c_world(verified_phase3c_bundle)
  -> FrozenPhase3CWorld(RAPM, BuildEpoch, source provenance,
                       source_locality, source_authorization,
                       local_pre_certificate, frozen_U_all,
                       complete_binding_ground_action_catalogue,
                       zero-build binding counters)

causal_circuit_from_failed_proof(proof_graph)
  -> CausalProofCircuit

find_slack_aware_causal_family(circuit, obligations, evaluation_cap,
                               recoverable_earliest_antichain)
  -> SlackAwareCausalFamily

compile_sparse_recovery_inputs(source_boundary, authorized_v1_slice,
                               target_frontier, admissible_domain, compiler_caps)
  -> {SparseFrontierGroundSlice,
      SparseRobustAffineCapability,
      TrustedCompilationEvidence}

GeneralLocalRuntime.solve(capability_path, slice_path, request_path)
  -> GeneralLocalSolverResult + GeneralLocalRuntimeAttestation

HybridPolicyStitcher.stitch(base_policy, result.overlay)
  -> HybridPolicyGraph
PatchedAuditKernelView(base_kernel, exact_overlay_pairs)
  -> patch_step_restricted_kernel_view
HybridSoundAuditor.audit(base_envelope, patch_step_restricted_kernel_view,
                         overlay, hybrid_policy, query, frozen_U_all)
  -> PostRecoveryCertificate

IndependentPhase3DVerifier.reconstruct_and_exact_lift(bundle)
  -> EvaluationOnlyExactHybridResult + J0Comparison
```

The public Phase 3D runner accepts the source through `--phase3c-bundle`; passing an
in-memory rebuilt `Phase3CWorld` is an invariant violation. The loader's finite
structural-ID scan can bind serialized state/action IDs, but it cannot call
`construct_phase3c_world`, `SuiteBuildCoverage.from_queries`/transition closure, a
partition/quotient/RAPM builder, or `kernel.step`. Abstract and hybrid auditors receive
the source pre-certificate's frozen
action-unrestricted reward upper bound, so the operational runner does not invoke a
ground `U_all` routine. The loader also preserves the Phase 3C locality and
authorization documents and constructs a complete 144-action binding-time catalogue.
Causal selection, ancestor legality, and capability-cost lookups use that frozen
catalogue; they cannot trigger pre-authorization ground calls. Only certificate failure
creates an authorized slice. The operational post-auditor receives
`PatchedAuditKernelView`, which permits transition steps only for exact overlay pairs;
unpatched decisions stay in the RAPM envelope. Verifier reconstruction and exact lift
use a private evaluation-only context and are not operational interfaces.

`SlackAwareCausalFamily` records baseline root values/deficits, tied active
realizations, every evaluated discharge set, selected earliest-antichain family,
evaluation cap/count, completeness, and one of `CERTIFICATE_ALREADY_PASSES`,
`CAUSAL_FAMILY_FOUND`, `NO_CAUSAL_COVER`, or `SEARCH_CAP_REACHED`. A cap hit does not
widen authority automatically.

The trusted compiler may read the complete Phase 3C source boundary and authorized
slice. It emits an exact-field-allowlisted worker capability and keeps graph rows,
identities, domain equivalence tables, and necessity witnesses in trusted evidence.
For safe-chain it compiles four nodes/twenty realization rows to one input, zero exits,
one reward-min form, and one risk-max form. Although the source boundary is stored in
the bundle, the runtime attestation permits only three read-only input files:
capability, sparse slice, and occurrence request. Artifact presence never implies
worker access.

`GeneralLocalSolver` accepts only deterministic finite-horizon Markov assignments. It
enumerates every authorized member-action Cartesian product for each localized-cell
subset, evaluates sparse root forms, and Pareto-prunes complete root points. Selection
is minimum localized-cell cardinality, maximum root reward lower, minimum root failure
upper, then canonical signatures. Limits cover subset evaluations, policy assignments,
frontier points, dominance comparisons, affine terms, and rational bits. Results are
`LOCAL_RECOVERY_CERTIFIED`, `LOCAL_RECOVERY_AUTHORIZED_EXHAUSTED`, or
`LOCAL_RECOVERY_SEARCH_CAP_EXHAUSTED` with exact counters.

The registered safe-chain call exhausts 257 assignments. Its `24/96` figure is the
authorized capability scope, not performed transition work. Trusted materialization
steps 16 frontier pairs and observes 64 positive-probability outcomes; the restricted
sound post-audit steps eight overlay pairs, for exactly 24 operational ground steps,
with zero accounting/out-of-scope steps. It patches eight decisions and yields reward
lower `3/64`, sound failure upper `397/20000`, and regret upper zero. The operational
post-certificate sets exact-hybrid reward/failure to `null` with status
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`; the runner is forbidden to exact-lift.
The standalone verifier performs that reconstruction/lift only in its evaluation lane,
obtains exact failure `317/16000` with eight patched and twelve abstract decisions, and
then compares with J0. The synthetic call exhausts 25 and yields `1,1/25`. The profile
and independent interface replay are:

```bash
acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d
python3 scripts/verify_phase3d.py artifacts/phase3d
```

## Pseudocode / schema

```text
protocol DomainProtocol:
  structural_key() -> CanonicalJSON
  canonical_query_distribution(name) -> ExactDistribution[State]
  validate_query_distribution(rho0) -> None
  legal_actions(state) -> ordered tuple[Action]
  outcomes(state, action) -> ordered tuple[Outcome]
  semantic_action(state, action) -> SemanticAction
  concretizer(state, semantic_action) -> ExactDistribution[Action]
  reward_features(outcome) -> map[str,Rational]
  reward_upper_bound(query) -> (Rational normalizer_value, proof_id)
  goal(goal_id, state) -> terminal/supplemental-reward semantics
  strategic_features(state) -> map[str,Rational]
  state_key(state), action_key(action) -> bytes/string

RAPMBuilder.build(structural_config, query_support, grammar, budgets):
  canonical_declaration = validate_and_order(query_support)
  coverage = transition_closure(canonical_declaration.states,
                                all_legal_actions_and_outcomes)
  coverage_spec = BuildCoverageSpec(
      mode="query_support_transition_closure",
      initial_support_sha256=sha256(canonical_declaration_with_exact_masses),
      covered_state_count=count(coverage),
      reuse_outside_coverage_forbidden=true)
  build_id = hash(structural_id, coverage_spec, source_identity)
  return RAPM(..., coverage, coverage_spec, build_id)

validate_query_coverage(rapm,q):
  require supp(q.rho0) subseteq rapm.covered_states
  otherwise reject before planning or rebuild with a new coverage descriptor

SuiteBuildCoverage.from_queries(kernel,Q_train):
  declared = canonical_set(union positive_support(q) for q in Q_train)
  covered = transition_closure(declared, all legal actions/outcomes)
  return immutable_suite_descriptor_and_inventory(declared,covered)

construct_phase3a(Q_train):
  coverage = SuiteBuildCoverage.from_queries(kernel,Q_train)
  if G2048:
    table = GroundOracleTable.build(coverage,relative_survivor,train_profile)
    construction = OraclePartitionSelector.select(table,Q_train)
  if LMB:
    construction = ExactBehavioralQuotientBuilder.build(kernel,coverage)
  return freeze(coverage,construction.partition,construction.adapter,
                construction.quotient_models)

evaluate_phase3a(frozen,Q_heldout):
  for q in Q_heldout:
    frozen.coverage.validate_query_coverage(q)
    row = compare_J0_Jkappa_exact_audit_and_ground_lift(frozen,q)
    require row.exact_reward_gap == 0 and row.exact_failure_gap == 0

optional exact-symmetry adapter for a registered profile:
  ordered_group_elements(profile_id) -> ordered tuple[GroupElement]
  transform_state(profile_id, group_element, state) -> State
  transform_action(profile_id, group_element, action) -> Action
  exact_group_quotient_profile(profile_id) -> ExactGroupQuotientProfile

ExactGroupQuotientBuilder.build(complete_state_time_graph, profile):
  verify group closure and state/action/kernel automorphisms
  construct complete equal-horizon state orbits
  construct deterministic canonicalizers and stabilizers
  construct action orbits and distinct inverse-action concretizers
  verify representative-independent point dynamics and singleton envelopes
  return ExactQuotient or EXACT_D4_QUOTIENT_INVARIANT_VIOLATION

RefinementEngine.step(cell,q):
  witness = exact_auditor.counterexample(cell,q)
  candidates = grammar.separating_predicates(witness)
  evaluate candidates once by child-partition signature
  accept first candidate in frozen ranking that passes acceptance rule/budgets
  otherwise return exact terminal status and mark cell

run_aliased_safe_chain(profile,q):
  require profile.ground_structural_key == g2048_select_safe_chain_2x2_v0
  require complete_coverage_count == 192
  partition, counters = profile.base_encoder(coverage), (leaves=10, rate=0)
  while true:
    proposal = NominalPlanner.solve(partition,q)
    audit, witnesses = ExactAuditor.audit_and_extract_all(proposal,q)
    if audit.certified: return CERTIFIED
    evaluations = rank_jointly(all_separating_candidates(witnesses,profile.grammar))
    accepted = RefinementEngine.accept_first_valid(evaluations,counters,full_v0_budget)
    append RefinementIteration(...)
    partition, counters = accepted.output_partition, accepted.counters_after

ExactOneStepBehavioralSynthesizer.build(kernel_view,coverage,registries,adapter):
  partition = terminal_kind_partition(coverage)
  repeat partition = refine_by_full_one_step_behaviour(partition) until stable
  audit builder API/data-flow and source imports for forbidden dependencies
  model = PortableRAPMWriter.freeze(partition,coverage,registries,adapter)
  return externally_bind_build_epoch(model.model_id,model.coverage_id), model

FreshProcessAbstractPlanner.run(request):
  model = PortableRAPMLoader.load_and_verify(request.path,request.sha256)
  query = PortableQueryV1.load_and_verify(request.query_path,request.query_sha256,model)
  require query.goal_id == default and model.coverage.contains(query.cell_rho0.support)
  require query.normalizer_proof_id in model.normalizer_rules
  require query.raw_weights == selected_rule.reward_basis
  require nonnegative(query.raw_weights) and query.normalizer >= proved_bound(query)
  require query.normalized_weights == query.raw_weights / query.normalizer
  require bwrap_mount_and_network_namespace and python_site_disabled
  require current_model_query_read_only and output_initially_empty
  require project_and_other_requests_not_mounted
  proposal = NominalPlanner.solve(model.nominal,query)
  attest runtime, inputs, module origins, and output
  return freeze(FreshProcessQueryResult(proposal))

evaluate_frozen_phase3b_proposals(all_results):
  require every workload proposal was produced before J0 starts
  for result in all_results:
    certificate = ExactAuditor.audit_with_authoritative_ground_envelope(result)
    lift = PolicyLifter.evaluate_on_ground(result)
    J0 = GroundConstrainedOracle.solve_same_query(result.query)
    assign route from certificate

route_failed_plan(result):
  require not result.certificate.certified
  inventory = DirectProofInventory.from_failed_audit(result)
  return LocalGroundFrontier.from_earliest_direct_bad_nodes(inventory)
```

For the safe-chain adapter, `transform_action` applies the same cell transform to both
unordered pair endpoints and the survivor, then sorts only the endpoints by canonical
cell key; it never loses which transformed endpoint is the survivor.

## Invariants

- Domain outcomes have positive probability, unique canonical successors after coalescing, and total mass one.
- Returned and concretized actions are legal in the concrete state.
- Canonical ordering removes hash-map/filesystem nondeterminism.
- Builders and auditors consume the exact kernel independently; the auditor does not trust nominal residuals.
- RAPM coverage is explicit build metadata, not a structural field or hidden query
  side effect. The mode, declaration hash, state count, and no-outside-reuse flag enter
  `build_id`, and every query passes coverage validation before planning.
- Status and accounting fields are populated on success, fallback, infeasibility, and failure.
- A structural ID changes when the spawn law changes but not when only `rho0`, horizon,
  delta, or reward coefficients change. `rho0` changes the query ID and the current
  descriptor-specific build ID; other query-only fields do not change coverage.
- Every selected ground or abstract policy is deterministic; stochastic frozen
  concretization is serialized as model semantics, never as policy mixture weights.
- The safe-chain exact-profile concretizer weights distinct action IDs, not group
  elements; duplicate images are removed before normalization.
- Exact-group cells contain complete orbits at one remaining horizon and cannot mix
  failure, terminal, and nonterminal semantics.
- A policy graph is keyed by `(ground_state_id, remaining_horizon)` or
  `(cell_id, remaining_horizon)` and assigns exactly one action to each reachable key.
  Converging histories reuse the same key and cannot select different actions.
- The aliased profile has the same ground structural/query/coverage identities as its
  exact-baseline input but distinct profile, semantic-adapter, grammar, partition,
  build, and run IDs.
- Its iteration indices are contiguous, each input partition equals the previous
  output, and counters advance exactly `10/0 -> 11/4 -> 12/8` in leaves/rate bits.
- Phase 3A builder signatures contain no held-out query argument or dependency; the
  evaluation layer cannot mutate a frozen coverage, partition, adapter, or RAPM.
- Phase 3A compression checks use active states/cells (`68/7`, `18/3`); total graph
  counts (`192/8`, `25/5`) and terminal aggregation are reported separately.
- Cross-automorphism audits use complete physical groups: G2048 state-action orbits
  `18 -> 14` abstract pairs and LMB `16 -> 4`; mixed cells must be active and reached.
- Phase 3B exposes one immutable external build epoch and portable RAPM ID per domain;
  no query field or result appears in the builder API/data flow. Epoch and model IDs are
  separate: only an extensional model-payload change alters the latter.
- A fresh planner request contains exactly a portable-model path/hash and portable-query-
  v1 path/hash. Its runtime attestation proves the per-occurrence bubblewrap boundary,
  `-S`, allowed input/output files, and observed module origins.
- Local ground recovery is unreachable before certificate failure and cannot widen its
  recorded frontier without a new failure/dependency proof.
- All workload cost fields are additive and route-specific; evaluation-only oracle
  cost is never merged into the operational abstract or ground comparator path.

## Acceptance tests

- Contract tests run unchanged against both domains.
- Query validation rejects unregistered or structurally incompatible changes.
- Build construction starts from the exact explicit `QuerySpec` support, reaches the
  full all-action transition closure, and records a count equal to the serialized
  distinct covered-state inventory.
- Changing one initial probability, support state, coverage mode, or recorded covered
  count changes or invalidates `build_id`; none changes `structural_id` by itself.
- A query support outside the recorded closure is rejected before model lookup,
  planning, audit, or certificate reuse.
- Query validation rejects a canonical normalizer reused after reward coefficients or reward/bonus/goal semantics change.
- The safe-chain `D4` query validates eight distinct canonical states of exact mass
  `1/8`; changing only that distribution preserves its structural ID but changes its
  query and coverage-specific build identities.
- Canonical serialization round-trips exact rationals and stable IDs.
- Duplicate/no-op predicates and all tie-break levels have unit tests.
- An injected nominal-model error cannot escape exact envelope audit.
- The policy validator rejects duplicate state/cell-horizon keys with different actions
  and accepts shared descendants only when their selected action is identical.
- Safe-chain contract tests enumerate every `D4` element and legal action, compare exact
  transformed kernels after successor coalescing, and reject a single perturbed image.
- Canonicalizer tie alternatives produce identical action-orbit IDs; a mock stabilizer
  with duplicate action images still yields uniform mass over distinct inverse actions.
- The exact-group builder refuses to emit a quotient if any reward/cost width is nonzero,
  any transition uncertainty set is nonsingleton, or any representative changes the
  induced tuple.
- The safe-chain profile reports strict compression of both reachable state-time nodes
  and total legal state-action pairs using ground and abstract counts from the same
  complete graph.
- The action-frame adapter returns the thirteen base G2048 atoms plus exactly six
  registered geometry atoms, uses zero for all six when the frame is undefined, and
  leaves boundary labels/concretizers byte-identical to the ordinary boundary adapter.
- Aliased-profile integration tests prove the witness extractor, rather than a fixture
  constant, selects the two golden cells; swapping action order, geometry truth,
  candidate rank, or either partition link fails the semantic hash or verifier.
- The final ordinary CEGAR result is `CERTIFIED` with reward `3/64`, exact lifted risk
  `317/16000`, sound risk `397/20000`, regret zero, eight pointwise certificates, and
  no fallback. It never carries `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` or
  `known_group_exact_homomorphism`.
- `OraclePartitionSelector` unit tests prove no held-out argument is accepted, subset
  enumeration/tie-breaking is canonical, the selected atom IDs are the two `h=1`
  atoms, and the G2048 partition is `192 -> 8` with active `68 -> 7`. They also prove
  both training audits certify and the bridge exact row is reward `13/400`, failure
  `199/5000`, and sound `U_F=1/25`.
- `ExactBehavioralQuotientBuilder` reproduces the LMB fixture's `25 -> 5`, trace
  `3 -> 5 -> 5`, singleton envelopes, active `18 -> 3`, and uniform deduplicated
  equal-signature action support. The lifted training graph reaches members from
  multiple physical orbits inside each of its three active cells.
- Phase 3A integration evaluates the registered two-domain held-out suite without
  changing construction hashes, reproduces all V0-027 rationals, and requires both
  exact reward and exact failure gaps zero. It rejects an uncovered support, a held-out
  construction dependency, a terminal-only mixed cell, or a full-Phase-3 pass label.
- Synthesizer signature/type tests reject `QuerySpec`, Q/value/frontier/policy objects;
  builder API/data-flow and static import audits reject forbidden dependencies at the
  behavioural-builder/portable-planner boundaries.
- A portable-model canonical round trip is byte-identical and a deliberately removed
  feature, normalizer rule, action realization, envelope entry, coverage member,
  planning kind, or goal
  field fails
  the loader before planning.
- A re-signed active cell with no action, mixed planning kinds, non-`default` v1 goal,
  incomplete/unsorted/duplicate/negative reward basis, unsorted/duplicate/unknown
  feature caps, a missing positive-basis cap, an unregistered or cross-basis proof, a
  bound-violating normalizer, or inconsistent raw/normalized weights fails validation.
- The Phase 3B integration starts fresh processes for eleven distinct ground queries
  whose projections include at least eight distinct portable queries and four per
  domain, with a multi-step row in each; all reuse one model ID per domain, certify
  abstractly, and agree with independent J0/lift evaluation.
- Each process uses Linux `bwrap`, sees only the three staged application modules plus
  system libraries and its read-only current model/query, starts with `-S`, has no
  project/other-request mount, and attests an initially empty writable output.
- It reproduces G2048 behavioural trace/counts `2 -> 9 -> 10 -> 10`, `192 -> 10`,
  `144 -> 17` and LMB `3 -> 5 -> 5`, `25 -> 5`, `40 -> 4`.
- Router tests reject a local-ground frontier on a certified plan, an unreachable or
  non-earliest node, and any uncharged widening to a full ground solve.
- Accounting tests reconcile every additive counter component, preserve evaluation-
  only J0 separately, require scalar cost/break-even `null`, and emit all three required
  `*_NOT_RUN` Gate statuses.
- The independent verifier rebuilds both authoritative kernels, coverage closures,
  behavioural models, and G2048/LMB authority normalizer-rule registries; it reprojects
  queries, requires the LMB canonical/match-only/terminal-clear-only bases to be
  `(1,1),(1,0),(0,1)` and rejects cross-use of their proof IDs, recomputes portable-
  envelope and live exact
  ground audits, lifts with serialized `kappa`, runs J0, checks IDs/cross-links/counters,
  and can replay the isolated planner.
- Phase 3D interface tests forbid the Phase 3C constructor,
  `SuiteBuildCoverage.from_queries`/transition closure,
  partition/quotient/RAPM builders, `kernel.step` during binding/pre-authorization, and
  operational unrestricted-upper recomputation; they preserve embedded source model,
  epoch, run, manifest, locality, authorization, and pre-certificate bytes/provenance.
  They require the complete 144-action binding catalogue to serve causal/ancestor
  lookups, and reconcile operational ground access as `16+8=24` step calls with 64
  recorded materialization outcomes, zero accounting/out-of-scope steps, and zero
  operational exact lifts. Evaluation-side tests then recompute all active ties/slack,
  reject a causal search cap as noncertified, prove sparse extensional equivalence/
  minimality over the finite domain, enforce the three-file mount allowlist, reproduce
  257/25 assignments, and exact-lift `8+12` decisions to failure `317/16000` before J0.

## Out of scope

Network services, mutable online model updates, learned adapters, asynchronous planners, plugin-specific APIs, unstable language-object serialization as an artifact format, discovery of an unknown symmetry group from data, an API that relabels Phase 3A exact-model construction as oracle-free unknown-quotient discovery, treating the Phase 3B exact behavioural builder as learned predicate invention or an implemented local hybrid, or treating the Phase 3D finite solver as dependent-horizon complete, workload-economic, learned, or a full Gate.

## Known failure modes

Noncanonical state keys, uncoalesced duplicate successors, accidental float coercion, stale build caches, missing coverage fields in a build key, reuse outside transition closure, domain logic leaking into the generic planner, inconsistent state/action transforms, stabilizer multiplicity bias, a hard-coded aliased split schedule, overwriting a prior refinement iteration, held-out fields entering a constructor, and computing Phase 3A compression from terminal aggregation alone.

## Open risks

The exact in-memory frontier/envelope representation may need optimization after Phase 0.5; any replacement must preserve these external records and proof dependencies. Phase 3A proves the exact-model/oracle cross-automorphism control; Phase 3B freezes portable planning; Phase 3C freezes the first isolated repair; and Phase 3D freezes slack-aware causal, sparse capability, and joint capped solver interfaces. Human predicate reconstruction, dependent-horizon recovery, workload economics/dynamic routing, and full Phase 3/5 runners remain open.
