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

`run.json` records schema/contract/spec versions and hashes, run/fixture/build/query IDs,
`structural_key`, `benchmark_role`, `execution_profile`, domain, status, evidence tier,
seed/tape IDs, UTC timestamps, command, code revision and dirty-state digest,
runtime/dependency lock hash, platform, and parent reference-manifest hashes. The
execution profile is one of `phase05_vertical_slice`, `production_query`,
`exact_d4_quotient_baseline`, or `aliased_cegar_positive_control`.
Bundles emitted under the new profile use `contract_version=0.5.0`; an older contract
version cannot opt into its execution profile, result eligibility, or artifact schema.

Every coverage-limited build records `build_coverage` in `run.json` with exactly:
`mode=query_support_transition_closure`, `initial_support_sha256` over the canonical
ordered positive-mass `rho0` declaration including exact masses,
`covered_state_count`, and `reuse_outside_coverage_forbidden=true`. The serialized
closure inventory resolves that count. `build_id` commits to the structural ID, this
complete descriptor, and source identity; `query_id` independently commits to the full
query. `config/structural.json` contains no `initial_law`, while `config/query.json`
records the selected distribution and its registration/provenance.

Every run also records `known_exact_j0_status`, the matching J0 proof dependency (if
known), that proof's structural ID, build ID, kernel hash, and query hash, and
`phase05_test_override`. The override may be true only for the named
canonical G2048 Phase 0.5 regression and means that the mandatory construction split
is being exercised despite already-known infeasibility. A production query may never
set this override. The establishment and validation costs of a reused J0 proof remain
visible in accounting.

`config/query.json` records `normalizer_value` and `normalizer_proof_id` separately.
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
- Changing a reward coefficient without changing `normalizer_proof_id` or proving a
  valid replacement `normalizer_value` fails verification.
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

## Out of scope

Long-term object-store layout, public data-release licensing policy, binary performance traces as normative evidence, statistical confidence-set schemas, artifacts claiming an automatically discovered group from the supplied `D4` profile, and aliased artifacts claiming that their preregistered geometry atom was invented automatically.

## Known failure modes

Self-referential manifests, partially written bundles, absolute host paths, noncanonical JSON ordering, missing dirty-worktree provenance, orphan policy/proof nodes, an incomplete coverage descriptor, a support hash over noncanonical data, reuse outside the recorded closure, incomplete orbit inventories, stabilizer-element multiplicity masquerading as distinct-action probability, overwritten aliased iterations, incomplete candidate inventories, and cross-profile result labels.

## Open risks

Large exact state/transition artifacts may require deterministic chunking or compression after Phase 0.5; logical hashes and schema semantics must remain stable. V0-026 now freezes the aliased safe-chain multi-iteration topology; any later chunking must preserve its logical inventories, links, order, and hashes and still cannot reuse the exact-`D4` result label.
