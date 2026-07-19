# Artifact Schemas

## Definitions

- **Artifact bundle:** the append-only directory for one run.
- **Manifest:** canonical inventory of every file, SHA-256 digest, byte size, media/schema type, and logical role.
- **Provenance:** exact source/build/query/configuration identifiers needed to reproduce a value.
- **Proof dependency:** a referenced cell/action/horizon/envelope entry used by a certificate.

## Normative decisions

Every Phase 0.5 run bundle contains at least:

```text
manifest.json
run.json
config/structural.json
config/query.json
ground/enumeration.json
ground/j0_frontier.json
rapm/partition_before.json
rapm/nominal_before.json
rapm/envelope_before.json
audit/pre_refinement.json
refinement/witness.json
refinement/candidates.json
refinement/accepted_split.json
rapm/partition_after.json
rapm/nominal_after.json
rapm/envelope_after.json
result/policy_graph.json
result/certificate_or_fallback.json
metrics.json
events.jsonl
```

The separate safe-chain exact-`D4` positive-control bundle contains the common run,
query, enumeration, J0, policy, metrics, events, and manifest records plus at least:

```text
ground/state_time_graph.json
symmetry/profile.json
symmetry/automorphism_checks.json
symmetry/state_orbits.json
symmetry/canonicalizers.json
symmetry/action_orbits.json
symmetry/concretizers.json
rapm/nominal_exact.json
rapm/envelope_exact.json
audit/representative_independence.json
audit/value_policy_preservation.json
result/exact_d4_certificate.json
```

It does not fabricate Phase 0.5 witness, candidate, accepted-split, or fallback records;
their absence is required under this execution profile.

The aliased safe-chain positive-control bundle uses the common run, structural/query,
enumeration, J0, metrics, events, and manifest records plus this append-only topology:

```text
config/profile.json
audit/alias_source_diagnostic.json
rapm/partition_00.json
rapm/nominal_00.json
rapm/envelope_00.json
audit/audit_00.json
refinement/iterations/001/witness.json
refinement/iterations/001/candidates.json
refinement/iterations/001/accepted_split.json
rapm/partition_01.json
rapm/nominal_01.json
rapm/envelope_01.json
audit/audit_01.json
refinement/iterations/002/witness.json
refinement/iterations/002/candidates.json
refinement/iterations/002/accepted_split.json
rapm/partition_02.json
rapm/nominal_02.json
rapm/envelope_02.json
audit/audit_02.json
result/policy_graph.json
result/cegar_certificate.json
```

Iteration directories are one-based, three-digit, contiguous, immutable, and link the
exact input stage `00/01` partition/model/audit IDs to the accepted split and output
stage `01/02` partition/model/audit IDs. Each `witness.json` identifies the winning
exact counterexample and references the complete auditor-produced witness inventory;
`candidates.json` contains every generated separating candidate, score,
tie-break component, rejection reason, and deterministic rank. A later iteration never
overwrites or summarizes away an earlier one. The final certificate links both
iteration IDs and every reachable proof dependency. No fallback or symmetry-orbit
artifact is present.

The Phase 3A true-state-alias oracle construction slice uses contract `0.6.0` and this
separate topology:

```text
suite/benchmark_registry.json
suite/query_registry.json
suite/split_and_seed_ledger.json
coverage/g2048.json
coverage/lmb.json
ground/g2048_oracle_table.json
oracle/g2048_partition_construction.json
oracle/lmb_behavioral_construction.json
rapm/g2048.json
rapm/lmb.json
evaluation/j0_jkappa_j2_rows.jsonl
evaluation/policy_graphs.json
evaluation/symmetry_nontriviality.json
evaluation/reuse.json
result/phase3a_slice_report.json
metrics.json
events.jsonl
```

`manifest.json` and detached `manifest.sha256` cover the complete inventory. This
profile has no CEGAR witness/split chain and no exact-`D4` orbit-certificate topology;
its cross-automorphism evidence belongs in the evaluation audit, not in a fabricated
known-group construction claim.

The Phase 3B portable world-model campaign uses contract `0.7.0` and this append-only
topology:

```text
run.json
workload/spec.json
workload/query_registry.json
build/epochs.json
build/g2048/portable_rapm.json
build/lmb/portable_rapm.json
campaign/portable_queries.jsonl
campaign/portable_plans.jsonl
campaign/policy_graphs.json
audit/certificates.jsonl
evaluation/j0_rows.jsonl
evaluation/reuse.json
accounting/work_counters.json
result/phase3b_report.json
metrics.json
events.jsonl
```

`manifest.json` and detached `manifest.sha256` cover this inventory. `build/epochs.json`
contains the one-step construction traces, external coverage/model bindings, explicit
forbidden-input booleans, and portable round-trip evidence. The independent verifier
supplements those declarations with builder API/data-flow replay and static source
audits. `evaluation/reuse.json` plus the portable-plan stream contain fresh-process
isolation and unchanged-model evidence. Because local hybrid recovery is not run, the
report records an empty/not-run local frontier summary; the bundle does not fabricate a
local-repair trace. This evidence does not claim a closed import DAG for the entire
Phase 3B runner.

For single-query profiles, `run.json` records schema/contract/spec versions and hashes,
run/fixture/build/query IDs, `structural_key`, `benchmark_role`, `execution_profile`,
domain, status, evidence tier, seed/tape IDs, UTC timestamps, command, code revision and
dirty-state digest, runtime/dependency lock hash, platform, and parent reference-
manifest hashes. Phase 3A replaces the singular fixture/build/query fields with its
suite registry plus per-domain coverage/RAPM and per-row query IDs. The
execution profile is one of `phase05_vertical_slice`, `production_query`,
`exact_d4_quotient_baseline`, `aliased_cegar_positive_control`,
`phase3a_true_state_alias_oracle_control`, or `phase3b_portable_rapm_campaign`.
Aliased bundles use `contract_version=0.5.0`; Phase 3A bundles use
`contract_version=0.6.0`; Phase 3B bundles use `contract_version=0.7.0`. An older
contract version cannot opt into a newer execution profile, result eligibility, or
artifact schema.

Every Phase 0.5/production per-query coverage-limited build records `build_coverage` in
`run.json` with exactly:
`mode=query_support_transition_closure`, `initial_support_sha256` over the canonical
ordered positive-mass `rho0` declaration including exact masses,
`covered_state_count`, and `reuse_outside_coverage_forbidden=true`. The serialized
closure inventory resolves that count. `build_id` commits to the structural ID, this
complete descriptor, and source identity; `query_id` independently commits to the full
query. `config/structural.json` contains no `initial_law`, while `config/query.json`
records the selected distribution and its registration/provenance.

Phase 3A coverage records instead contain the distinct suite descriptor
`mode=suite_support_union_transition_closure`,
`declared_support_set_sha256`, `declared_support_state_count`,
`covered_state_count`, `exact_state_cap`,
`admissible_query_support_rule=positive_support_subset_of_covered_states`, and
`reuse_outside_coverage_forbidden=true`. The support hash is over the canonical union
of **training** positive-support states and intentionally excludes query order and
probability masses. Each coverage document serializes that declared set, the complete
closure, all legal transitions, exact kernel hash, and content-addressed `coverage_id`.
Held-out query records reference but never alter this object.

Every single-query execution profile also records `known_exact_j0_status`, the matching
J0 proof dependency (if known), that proof's structural ID, build ID, kernel hash, and query hash, and
`phase05_test_override`. The override may be true only for the named
canonical G2048 Phase 0.5 regression and means that the mandatory construction split
is being exercised despite already-known infeasibility. A production query may never
set this override. The establishment and validation costs of a reused J0 proof remain
visible in accounting.

For a single-query bundle, `config/query.json` records `normalizer_value` and
`normalizer_proof_id` separately.
Result and metric records report raw ground regret, the exact `Rmax(q)`, and normalized
regret. Every G2048 result also carries `claim_eligibility`: the canonical infeasibility
fixture is `infeasibility_only`; the safe-chain fixture is only
`known_group_exact_quotient_eligible_after_certification`. Neither role nor eligibility may be
serialized as `CERTIFIED` without the actual proof dependencies.

An aliased run additionally records `profile_key`, `profile_id`, `base_encoder_id`,
`semantic_adapter_id`, `grammar_id`, and
`abstraction_source=deliberately_aliased_boundary_actions`.
Its `structural_key` remains `g2048_select_safe_chain_2x2_v0`; the profile key is never
serialized into `config/structural.json` as physical dynamics. Its claim eligibility is
`action_frame_aliasing_cegar_only` and cannot be replaced by
the exact-`D4` eligibility or source label.

An `exact_d4_quotient_baseline` run additionally records
`abstraction_source=known_group_exact_homomorphism`, group/profile version and hash,
the total order of all eight group-element IDs, complete reachable state-time graph
hash, and the exact state/action orbit inventories. Every orbit cell records remaining
horizon, canonical state, all member states, all canonicalizing transforms, the chosen
transform, and stabilizer. Every semantic action records its deduplicated canonical
action-ID set and, for every member state, the deduplicated distinct inverse ground-
action IDs plus exact uniform probabilities. Recording only group-element weights is
invalid.

Automorphism evidence exhaustively records legal-action image, reward, one-time failure
cost, terminal semantics, and coalesced exact-kernel comparisons. The exact quotient
record stores every representative-induced tuple, their equality proof, point nominal
entry, singleton transition set, and equal lower/upper reward and cost. The certificate
stores every reachable ground/abstract value equality, constrained root return/risk,
failure `99/5000`, `Delta_action=0`, and all proof dependencies. The only terminal
statuses for this profile are `CERTIFIED` and
`EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`; the latter is a validation failure, not a
refinement status.

The registered group/action-transform profile is structural/build-owned. The complete
state-time graph, materialized orbit quotient, policy, and certificate are query-owned
and record the query hash; their presence does not move `rho0` or `H` into the
structural key.

Enumeration stores status, complete reachable count by depth, canonical state IDs, transitions/kernel hash, failure/success sets, and cap handling. J0 stores the exact nondominated reward/risk frontier, selected feasible policy or infeasibility, and oracle accounting.

The audit record stores query, reachable `(cell,h)` pairs, `U_all`, `L_pi`, `U_F`, pointwise and `rho0`-aggregated bounds, all dependencies, and certification failures. The witness includes both ground states, cell, semantic action (or missing-common-action marker), horizon, channel, and exact discrepancy.

Split artifacts store predicate/rational ID, witness separation, path predicates, child member/signature hashes, each rejection reason, score components, deterministic rank, budgets before/after, and acceptance status. Result artifacts distinguish `CERTIFIED`, `GROUND_FALLBACK`, and `INFEASIBLE_QUERY`, including all charged fallback locations and costs.

For the aliased profile, `partition_00.json` records all 192 state IDs, one failure
cell, nine active `(empty_count, nonzero-rank histogram)` cells, ten starting leaves,
and zero incremental base-encoder rate. `config/profile.json` records exactly six
action-frame grammar features, their total-zero convention, the sole `1/2` threshold
per feature, and the four-bit rate derivation. `ground/enumeration.json` additionally
resolves every covered ID to its state value/status, stores all 144 distinct
state-action transitions in the all-action closure, and exposes a closure-kernel hash
bound by `build_id`. The two witness inventories contain 35 and 19 positive-gap pairs;
the 120 and 64 separating witness/predicate proposals reduce to 16 and 10 unique
child-signature evaluations. All 26 are charged to the candidate budget, while the
quality-passing counts are 3 and 2. Iterations must record counters
`10/0 -> 11/4 -> 12/8` and accepted predicate
`first_survivor_adjacent_nonmerged_count|<=|1/2`, first for histogram `(1,1,2)` and
then `(1,2,2)`. The result records all three golden audit stages, exact lifted failure
`317/16000`, J0 failure `99/5000`, risk gap `1/80000`, final `U_F=397/20000`, envelope
conservatism `3/80000`, zero regret, eight pointwise certificates, and zero fallback.
Content IDs form a DAG: child documents never receive a backlink after hashing; the
accepted-split document embeds the uniquely resolving iteration record, and the final
certificate references both iteration IDs and the final audit proof root.

For Phase 3A, `run.json` records profile key
`phase3a_true_state_alias_oracle_control_v0`, status `PHASE3A_SLICE_PASS` or
`PHASE3A_INVARIANT_VIOLATION`, and the separate field
`full_phase3_gate_status=PHASE3_AGGREGATE_NOT_RUN`. Exact certificate quantities keep
the controlled evidence labels `oracle_truth` or `exact_sound`; the construction-slice
scope belongs in profile/status fields and does not create a fifth evidence tier.

The suite registry fixes two G2048 training rows plus four held-out rows, and one LMB
training row plus two held-out rows.
`query_registry.json` states `construction_inputs=train queries only` and
`heldout_queries_used_in_partition_selection=false`. `g2048_partition_construction`
stores the complete four-atom candidate trace, selected two `h=1` atoms, partition
signature, both training audits, and ten-cell exact-behavioural comparison. The LMB construction stores
`query_values_used=false`, trace `3 -> 5 -> 5`, final cell sizes, and the exact
behavioural semantic-action rule. RAPM records contain complete member IDs, nominal
entries, every ground realization in the sound envelope, partition signature, and
compression.

`symmetry_nontriviality.json` stores complete physical-automorphism group sizes, active
ground counts, physical state and state-action orbit counts, mixed active cells, their
per-training-policy reached orbit sets with resolving policy-graph IDs and exact
state-time-node inventories, and ground/abstract pair counts. A passing
cell records at least two distinct physical orbits reached inside it by the same lifted
training policy graph. Goldens
are G2048 total `192 -> 8`, active `68 -> 7`, active physical state orbits `9 -> 7`,
physical state-action orbits `18 -> 14`, and ground pairs `144 -> 14`; LMB total
`25 -> 5`, active `18 -> 3`, total physical state orbits `13 -> 5`, active orbits
`10 -> 3`, physical state-action orbits `16 -> 4`, and ground pairs `40 -> 4`.
The `5x` acceptance threshold is computed from active states/cells (`68/7` and `18/3`),
not inflated by terminal/failure aggregation.

The G2048 record also serializes the explicit witness pair `(0,2,2,2)` and
`(0,2,4,2)`, the facts that the pair shares one selected oracle cell but not a `D4`
orbit, both members occur on the strict bridge policy graph, and both lifted semantic
actions are `AWAY`. The query registry records that bridge as a training query; its
exact row is reward `13/400`, failure `199/5000`, and sound `U_F=1/25`.

Each J0/Jkappa/J2 row records exact rewards and failures, action-restriction,
state-alias-selector, and full gaps separately for both reward and failure, sound reward
lower/failure upper/regret upper, and a resolving policy-graph ID. All registered Phase 3A
rows require every segment and full exact gap to be zero. `reuse.json` proves that every query
in a domain references its one frozen coverage/RAPM and that held-out support is within
training coverage. Its claim is only across the registered two-domain held-out suite:
G2048 varies initial support/distribution and horizon; LMB varies reward basis, horizon,
and risk. The final report serializes both supported and unsupported claims and may not
generalize either domain to all four variation types.

For Phase 3B, `workload/spec.json` freezes the workload ID, ordered query IDs,
per-domain coverage roots/rules, expected count, allowed routes, normalizer proof IDs,
and build epochs before planning. A passing registry has eleven distinct ground query
IDs (six G2048, five LMB), at least eight distinct portable query IDs and four per
domain, and an `H>=2` query in each domain. Byte-equivalent portable projections are
reported but do not satisfy the portable-query threshold.

Each epoch commits to structural ID, exact kernel/coverage hashes, feature/terminal
registries, semantic adapter/concretizer, one-step synthesizer, contract/schema version,
source revision, and the resulting coverage/model IDs. It is an external provenance
binding, not a portable-model field. A model ID hashes only its own extensional payload,
so an epoch change changes that ID only if the payload changes. Portable RAPMs are
closed: coverage and `coverage_id`, every partition member and its
`active/terminal/failure/success` planning kind, nominal/exact-envelope entry,
semantic/ground action catalogs, exact concretizer, reward features, and `goal_ids`
resolve inside the model, together with the top-level `normalizer_rules` registry. It
is a nonempty list sorted by unique `proof_id`; each record contains
exactly `proof_id`, `kind=nonnegative_feature_caps_v1`, `reward_basis`, and
`feature_caps`. `reward_basis` contains every registered feature exactly once, sorted by
name, with a canonical nonnegative rational raw weight including explicit zeros. Cap
records are sorted by unique registered feature name and contain exactly `name`,
`per_step_cap`, and `total_cap`; each record has at least one non-null canonical
nonnegative cap, every positive-basis-weight feature has a record, and zero-weight
features need not have one. No
native object or absolute host path is needed to plan.

Portable query-stream requests contain the model ID and canonical cell-level
projection of the ground request: `rho0`, `H`, raw and normalized reward weights,
normalizer/proof ID, `delta`, and goal. Schema v1 accepts only the `default` structural
stopping goal. Its `normalizer_proof_id` must resolve in the model. Raw weights are
required to equal that rule's complete `reward_basis` exactly, so a proof cannot cross
reward bases. Every positive-weight feature must have a cap under that proof, the
normalizer must be at least
`sum_k w_k min(H*per_step_cap_k,total_cap_k)` over available caps, and normalized
weights equal `raw/normalizer` exactly. Portable plan records and `evaluation/reuse.json` record a new process
occurrence flag/positive process-ID observation, exact permitted input files,
content-addressed runtime attestation, and output digests. The attestation covers a Linux bubblewrap
mount/network namespace with staged `portable.py`, `portable_planner.py`, and
`portable_runtime.py`, read-only current model/query files, an initially empty writable
output, unmounted checkout/other requests, and Python `-S` module origins.
Portable results contain the frontier/selected multi-stage deterministic Markov policy
and RAPM/query IDs. Only after every proposal freezes are exact-sound certificates and
routes written under `audit/`, with J0/lift rows under `evaluation/`; those records are
never inputs to the behavioural-builder data flow and are not mounted into a fresh
planner namespace.

Routes are exactly `ABSTRACT_CERTIFIED`, `LOCAL_GROUND_RECOVERY`,
`FULL_GROUND_FALLBACK`, `REBUILD_REQUIRED`, and `INFEASIBLE_QUERY`. A local route must
resolve a preceding failed certificate, the earliest policy-reachable failed-node
antichain, cell members, and exact successor dependencies. A Phase 3B pass has only
`ABSTRACT_CERTIFIED` rows and zero local/fallback charges.

`accounting/work_counters.json` stores build covered-state/state-action/outcome counts,
behavioural rounds and model bytes; per-occurrence model/query loads and bytes;
abstract candidate/frontier/decision counts; portable-envelope and live ground-audit
reachable pairs; local-ground candidates; fallback invocations/candidates;
evaluation-only J0 candidates; and reconciliation totals. These exact fields are
noninterchangeable. Because Phase 3B has no frozen scalar cost functional,
`scalar_break_even` is null and no scalar world/ground totals are asserted.
The final report
pairs `PHASE3B_PORTABLE_RAPM_PASS` with `PHASE3_AGGREGATE_NOT_RUN`,
`LOCAL_HYBRID_GATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

JSON exact numbers are encoded as `{ "numerator": int, "denominator": positive_int }`; derived decimal displays are nonauthoritative. Opaque pickle/native-object dumps are never the sole source artifact.

## Pseudocode / schema

```text
manifest entry:
  path: normalized relative path
  sha256: lowercase hex
  bytes: nonnegative integer
  role: controlled enum
  schema: name@version or media type

metric:
  name, exact_value_or_decimal_view, unit
  evidence_label, provenance_ids
  included_in_gate, exclusion_reason

run decision context:
  structural_key, benchmark_role, execution_profile
  known_exact_j0_status, known_exact_j0_proof_id
  known_exact_j0_structural_id, known_exact_j0_build_id
  known_exact_j0_kernel_hash, known_exact_j0_query_hash
  phase05_test_override, claim_eligibility

build coverage:
  mode = query_support_transition_closure
  initial_support_sha256
  covered_state_count
  reuse_outside_coverage_forbidden = true

query normalization:
  normalizer_value, normalizer_proof_id
  raw_regret, normalized_regret

exact D4 context:
  abstraction_source, group_profile_id, group_profile_hash
  ordered_group_element_ids, complete_state_time_graph_hash
  state_orbit_ids, action_orbit_ids

exact D4 action realization:
  state_id, semantic_action_id, stabilizer_element_ids
  distinct_inverse_ground_action_ids
  exact_uniform_probability = 1 / count(distinct_inverse_ground_action_ids)

exact D4 validation result:
  automorphism_checks, representative_independence_checks
  envelope_widths, transition_singleton_checks
  per_state_time_value_equalities, constrained_value_risk_equality
  action_restriction_gap
  ground_state_time_count, abstract_state_time_count
  ground_state_action_pair_count, abstract_state_action_pair_count
  status

aliased CEGAR context:
  profile_key, profile_id, base_encoder_id
  semantic_adapter_id, grammar_id, abstraction_source
  ground_structural_id, build_id, query_id, coverage_id
  base_leaf_count=10, base_incremental_rate_bits=0
  budget_profile=full_v0

aliased refinement iteration:
  index, input_partition_id, input_audit_id
  complete_witness_ids, complete_ranked_candidate_ids
  accepted_split_id, output_partition_id, output_audit_id
  leaves_before, leaves_after, rate_before, rate_after

aliased final result:
  iteration_ids, policy_id, certificate_dependency_ids
  lifted_reward=3/64, lifted_failure=317/16000
  sound_failure_upper=397/20000, normalized_regret_upper=0
  j0_failure=99/5000, risk_gap=1/80000
  envelope_conservatism=3/80000, pointwise_certified_count=8
  fallback_invocations=0, status=CERTIFIED

Phase 3A suite coverage:
  mode=suite_support_union_transition_closure
  declared_support_set_sha256, declared_support_state_count
  covered_state_count, exact_state_cap
  admissible_query_support_rule=positive_support_subset_of_covered_states
  reuse_outside_coverage_forbidden=true

Phase 3A result:
  profile_key, coverage_ids, rapm_ids, construction_hashes
  train_query_ids, heldout_query_ids, heldout_used_for_construction=false
  active_ground_counts, active_cell_counts, physical_orbit_counts
  mixed_active_cells, policy_reachable_mixed_active_cells, explicit_nonorbit_pairs
  J0_Jkappa_J2_exact_rows, exact_reward_gaps, exact_failure_gaps
  status=PHASE3A_SLICE_PASS
  full_phase3_gate_status=PHASE3_AGGREGATE_NOT_RUN

Phase 3B portable campaign:
  profile_key=phase3b_portable_rapm_campaign_v0
  workload_id, ordered_query_ids, build_epoch_ids, portable_rapm_ids
  construction_dependency_audit, portable_roundtrip_audit
  fresh_process_results, independent_J0_lift_rows, query_routes
  status=PHASE3B_PORTABLE_RAPM_PASS
  full_phase3_gate_status=PHASE3_AGGREGATE_NOT_RUN
  local_hybrid_gate_status=LOCAL_HYBRID_GATE_NOT_RUN
  workload_economics_gate_status=WORKLOAD_ECONOMICS_GATE_NOT_RUN

portable normalizer rule:
  proof_id: unique nonempty string; rules sorted by proof_id
  kind: nonnegative_feature_caps_v1
  reward_basis: complete sorted unique (registered feature name, nonnegative weight)
  feature_caps: sorted unique registered feature names
    name, per_step_cap: rational|null, total_cap: rational|null

workload prefix cost:
  C_world[n] = c(W_build) + sum_i<=n c(W_load_i + W_abstract_plan_i + W_audit_i
                                      + W_local_ground_i + W_full_fallback_i)
  C_ground[n] = sum_i<=n c(W_same_query_ground_i)
  evaluation_only_j0 is separate
  Phase3B: c, C_world, C_ground, N_break_even = null (Gate NOT_RUN)
```

The manifest hashes every other file, then a detached `manifest.sha256` hashes canonical `manifest.json` to avoid self-reference.

## Invariants

- Every referenced ID resolves inside the bundle or to a content-addressed parent manifest.
- Hashes are computed after files close; bundle mutation invalidates verification.
- `exact_sound` metrics have exact-kernel/envelope proof dependencies.
- `STRESS_ONLY` metrics set `included_in_gate=false` with the state-cap reason.
- Fallback accounting reconciles component totals and end-to-end totals.
- A `phase05_test_override=true` bundle has the exact canonical regression key and
  `execution_profile=phase05_vertical_slice`; the verifier rejects every other use.
- `claim_eligibility` constrains claims but never determines the result status.
- A known-infeasible production shortcut requires exact equality between the proof's
  structural ID, build ID, kernel hash, and query hash and the current run's identities.
- Policy nodes are globally unique by `(ground_state_id, remaining_horizon)` or
  `(cell_id, remaining_horizon)`; converging paths reference the same deterministic
  action rather than storing history-dependent duplicates.
- An exact-`D4` orbit inventory is complete, contains one remaining horizon per cell,
  and keeps failure/terminal semantics separate from nonterminal cells.
- Exact-`D4` concretizer probabilities are computed after action-ID deduplication; their
  support is legal and sums to one exactly.
- `execution_profile=exact_d4_quotient_baseline` has zero refinement/split/fallback
  events, zero reward/cost widths, singleton transition uncertainty, and the frozen
  known-group claim source.
- A certified exact-`D4` bundle has strictly fewer abstract state-time nodes and total
  abstract state-action pairs than the corresponding complete ground graph.
- `structural_id` excludes `rho0`; `build_id` includes the complete coverage descriptor;
  and the recorded count equals the number of distinct serialized closure states.
- No build, audit, or certificate dependency may resolve a state outside the declared
  coverage, and no structural artifact may carry an `initial_law`.
- An aliased bundle has exactly two contiguous refinement iterations; each input
  partition hash resolves to the preceding base/output partition and its counters
  increase by one leaf and four bits.
- The winning aliased candidate is derivable from the stored complete witness/candidate
  inventories by the frozen ranking. Supplying the target cell as hidden runner input,
  omitting a losing candidate, or storing only the winner invalidates the claim.
- `CERTIFIED` terminates the aliased iteration chain. Its event log has two accepted
  splits, no third split, and no fallback; exact-`D4` orbit/action artifacts are absent.
- A failed aliased construction/replay reports
  `ALIASED_CEGAR_INVARIANT_VIOLATION`, sets positive-claim inclusion false, and cannot
  carry the golden `CERTIFIED` result or ordinary fallback evidence.
- A Phase 3A bundle has one immutable suite coverage and RAPM ID per domain; every
  held-out row points to those identities and no held-out query ID appears in a
  construction dependency list.
- Phase 3A compression acceptance uses active states/cells. Mixed-cell evidence is
  active and jointly reached across at least two physical orbits by one lifted training
  policy graph; terminal aggregation is separately reported.
- `PHASE3A_SLICE_PASS` always co-occurs with `PHASE3_AGGREGATE_NOT_RUN`, exact reward
  and failure gaps zero, and the complete unsupported-claim list.
- A Phase 3B bundle contains one immutable external epoch/RAPM binding per domain; all
  eleven query rows reference those identities and no query/evaluation input enters the
  behavioural-builder API/data flow. Epoch and model IDs remain distinct.
- Every portable dependency resolves inside the model/query pair. Every occurrence has
  a separate runtime attestation for the three staged application modules, read-only
  current inputs, empty writable output, unmounted checkout/other requests, `-S`, and
  isolated mount/network namespaces.
- A passing Phase 3B plan/result stream contains only `ABSTRACT_CERTIFIED`; the report's
  local-frontier summary is not-run/empty and local/fallback costs are exactly zero.
- Work-counter components reconcile exactly, keep evaluation-only J0 separate, require
  scalar totals/break-even null, and cannot infer `*_NOT_RUN` statuses from counters.

## Acceptance tests

- Schema validation passes for all required Phase 0.5 fixture bundles.
- Removing, modifying, or adding an unmanifested required file fails verification.
- Cross-reference validation reaches every certificate dependency and policy child.
- Rational values round-trip without loss and canonical denominators are positive/coprime.
- Gate filter cannot include `STATE_CAP_EXCEEDED`, nominal-only, or diagnostic-only results.
- A production bundle with a matching known-infeasible J0 proof exits before any split,
  whereas the explicitly labelled canonical Phase 0.5 bundle contains the mandatory
  split and charged same-query fallback.
- A one-field mismatch in the J0 proof's structural/build/kernel/query identity rejects
  the shortcut and is visible in verification output.
- Changing a reward coefficient while retaining `normalizer_proof_id` fails exact
  `reward_basis` equality regardless of the replacement normalizer; a separately
  registered rule/proof is required.
- Two paths assigning different actions to the same state/cell and remaining horizon
  fail policy-graph verification.
- Safe-chain artifact verification reconstructs every orbit, canonicalizer, stabilizer,
  action orbit, distinct inverse-action set, and exact uniform mass from the registered
  group profile rather than trusting stored summaries.
- Removing one orbit member, changing the group tie order, retaining a duplicate action
  image, recording a nonzero envelope width, or adding a split/fallback event fails the
  exact-`D4` bundle.
- A failed automorphism or J0 equality has status
  `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`, `included_in_positive_claim=false`, and cannot carry
  `exact_sound` certificate metrics.
- Recomputing transition closure from `config/query.json` reproduces
  `initial_support_sha256`, `covered_state_count`, and every covered state ID.
- Changing an initial mass/support state while retaining `build_id`, deleting the
  no-outside-reuse flag, falsifying the count, adding `initial_law` to structural
  config, or referencing an uncovered state fails bundle verification.
- Aliased-profile verification independently rebuilds the 192-state closure, ten base
  cells, boundary concretizers, six-feature grammar, both `4+4` splits, all candidate
  ranks, linked partitions, final lifted policy, and all golden exact rationals.
- Deleting or reordering an iteration, mutating action order/feature truth/rate, hiding
  a candidate, changing `317/16000` to the J0 risk, adding a third split/fallback, or
  using an exact-`D4` source/result label fails verification.
- Phase 3A verification checks the exact required-path set, contract/profile/status
  tuple, canonical training support-set descriptors (20 G2048 and nine LMB states),
  192/25 closure inventories, 8/5 partitions, active compression `68/7` and `18/3`,
  physical state-action orbit counts `18 -> 14` and `16 -> 4`, and same-policy jointly
  reached mixed active cells. The strict G2048 bridge pair must share one cell, differ in `D4`
  orbit, be jointly policy-reachable, and select `AWAY`.
- Recomputing all nine registered evaluation rows reproduces the V0-027 rewards,
  failures, sound bounds, zero exact reward/failure gaps, and deterministic policy
  graphs. Reordering or mutating held-out query records cannot change either
  construction/RAPM hash.
- A Phase 3A bundle fails if it uses a held-out field during construction, counts only
  a terminal mixed cell, reports total rather than active compression as the threshold
  witness, claims reuse outside the registered two-domain held-out suite, or omits
  `PHASE3_AGGREGATE_NOT_RUN`.
- Phase 3B verification independently rebuilds both authoritative kernels, coverage
  closures, and one-step fixed points; builder API/data-flow plus static source audits
  reject Q/value/frontier/policy/query dependencies at the construction/planner
  boundaries; canonical round trips reproduce portable model hashes.
- Removing a portable feature/normalizer-rule/envelope/action/concretizer/coverage/planning-kind/goal field or
  adding an unresolved ground reference makes both loader and verifier fail.
- Duplicate/unsorted proof IDs or feature names, an incomplete/negative basis, unknown
  features, a wrong rule kind, negative caps, a missing positive-basis cap, an
  unregistered/cross-basis query proof, an under-bound normalizer, or
  `normalized != raw/normalizer` fails validation.
- The verifier reprojects all queries; recomputes portable-envelope and live exact
  ground audits, serialized-`kappa` lifts, and J0; validates IDs, cross-links and exact
  counter fields; independently rebuilds the G2048/LMB authority normalizer registries;
  requires the LMB canonical/match-only/terminal-clear-only proofs to bind respectively
  to `(match,terminal_clear)=(1,1),(1,0),(0,1)` without cross-use; and can replay six
  G2048 and five LMB requests in isolated fresh
  processes. It checks one
  unchanged RAPM per domain, G2048 `192/10`, `144/17`, trace `2/9/10/10`, LMB
  `25/5`, `40/4`, trace `3/5/5`, multi-step coverage in both, all exact-sound
  certificates, and independent J0/lift equality.
- A nonempty local frontier, local/full-fallback charge, missing isolation evidence,
  construction reference to evaluation, or absent `PHASE3_AGGREGATE_NOT_RUN`,
  `LOCAL_HYBRID_GATE_NOT_RUN`, or `WORKLOAD_ECONOMICS_GATE_NOT_RUN` fails the pass.
- Recomputing work counters preserves every route component and null scalar fields; a
  post-hoc conversion cannot replace the economics-not-run label.

## Out of scope

Long-term object-store layout, public data-release licensing policy, binary performance traces as normative evidence, statistical confidence-set schemas, artifacts claiming an automatically discovered group from the supplied `D4` profile, aliased artifacts claiming that their preregistered geometry atom was invented automatically, Phase 3A artifacts claiming oracle-free discovery or a full Phase 3 Gate, and Phase 3B artifacts claiming learned/predicate discovery, an executed local hybrid, workload break-even, or full Phase 3/5 Gates.

## Known failure modes

Self-referential manifests, partially written bundles, absolute host paths, noncanonical JSON ordering, missing dirty-worktree provenance, orphan policy/proof nodes, an incomplete coverage descriptor, a support hash over noncanonical data, reuse outside the recorded closure, incomplete orbit inventories, stabilizer-element multiplicity masquerading as distinct-action probability, overwritten aliased iterations, incomplete candidate inventories, cross-profile result labels, held-out IDs in construction dependencies, and terminal aggregation masquerading as active compression.

## Open risks

Large exact state/transition artifacts may require deterministic chunking or compression after Phase 0.5; logical hashes and schema semantics must remain stable. V0-027 freezes the Phase 3A construction-slice topology. V0-028 adds a portable world-model/fresh-process campaign topology; local-hybrid traces, workload-economics evidence, and the statistical full-Phase-3/5 artifact layouts remain later work.
