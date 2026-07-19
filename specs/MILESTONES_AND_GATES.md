# Milestones and Gates

## Definitions

- **Gate:** a pass/fail condition frozen before evaluating the relevant test set.
- **Charged fallback:** a ground solve whose calls, expansions, wall time, and trigger location are included in totals.
- **Accepted split:** a nonduplicate predicate that separates the witness, passes the improvement rule, and fits every budget.
- **Phase 0.5:** the exact two-domain vertical slice; it is not a performance or novelty claim.
- **Exact-group validation status:** a positive-control build failure outside the CEGAR
  result enum; safe-chain uses `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`.
- **Aliased-profile validation status:** malformed profile construction, replay, or
  golden-contract evidence uses `ALIASED_CEGAR_INVARIANT_VIOLATION`; ordinary planning
  and refinement endings still use only the eight CEGAR statuses.

## Normative decisions

### Phase 0

Phase 0 freezes this ledger and all nine specs, exposes versioned schemas/interfaces, verifies the inherited Laplace snapshot independently, and provides deterministic test/build entry points. It does not claim a quotient-planning result.

### Phase 0.5 gate

Each benchmark must produce one reproducible bundle following this uninterrupted chain:

```text
authoritative tiny simulator
-> explicit QuerySpec support declaration
-> complete all-action transition closure and coverage-specific build ID
-> complete reachable-state enumeration
-> J0 constrained ground oracle
-> deliberately coarse initial partition
-> nominal abstract world model
-> independently derived exact sound envelope
-> uncertified contingent policy
-> explicit counterexample witness
-> one deterministic accepted atomic-predicate split
-> replanning on the refined model
-> certified full-plan regret and failure bound
   OR fully charged constrained ground fallback
-> complete artifact and hash manifest
```

For every Phase 0.5 fixture, the support declaration comes from `QuerySpec`, not an
implicit domain initial law. The closure follows all legal actions and all
positive-probability successors to a fixed point. Before partition/model construction,
the run freezes `mode=query_support_transition_closure`, the canonical declaration hash
including exact masses, closure count, and `reuse_outside_coverage_forbidden=true` in
the build identity. Crossing the state cap retains the existing incomplete/stress-only
semantics; silently truncating coverage is forbidden.

Every registered Phase 0.5 vertical-slice fixture executes its required construction
chain. The special permission to continue to a split after J0 has already proved
infeasibility applies only to `g2048_select_canonical_2x2_v0`; no other fixture may
inherit that override by virtue of being a Phase 0.5 run. This named exception tests
construction mechanics, counterexample generation, deterministic splitting,
constrained fallback, infeasibility propagation, and artifact completeness. A candidate
is acceptable when it separates the witness and either reduces the maximum implicated
audit width by at least 20% or newly certifies at least one previously uncertified
reachable `(z,h)` pair, without exceeding rate/leaves budgets.

This is not the production rule. A production query with an already-established exact J0 infeasibility proof returns `INFEASIBLE_QUERY` before refinement. The shortcut requires an exact proof for the identical structural/build/kernel identity and query hash; cached evidence from different dynamics or with a different `rho0`, horizon, reward, goal, delta, or normalizer is insufficient. The cost of establishing the proof, plus any validation/cache-lookup cost in the current run, remains charged and cannot be presented as a free conclusion. Artifacts distinguish `phase05_vertical_slice` from `production_query` execution so the exception cannot leak into cost or algorithm claims.

Full V0 budgets per instance: 64 leaves, 63 accepted splits, 256 rate bits, 2,048 candidate evaluations, 32 exact fallback/oracle invocations, and 50,000 reachable states. Phase 0.5 overrides only leaves to 8, splits to 7, candidate evaluations to 128, and fallback/oracle invocations to 4. `lambda_depth=1` is the executable V0 rate-cost default.

Refinement returns exactly one of `CERTIFIED`, `SPLIT_ACCEPTED`, `NO_SEPARATING_PREDICATE`, `ALL_SPLITS_REJECTED`, `REFINEMENT_BUDGET_EXHAUSTED`, `RATE_BUDGET_EXHAUSTED`, `GROUND_FALLBACK`, or `INFEASIBLE_QUERY`. No-separator marks `grammar_incomplete=true`; all-rejected marks `refinement_stalled=true`; either forces later reachable queries to fallback until a grammar-version rebuild.

### Safe-chain exact D4 positive-control gate

`g2048_select_safe_chain_2x2_v0` is a separate no-refinement acceptance profile, not an
additional mandatory-split Phase 0.5 fixture. Its uninterrupted chain is:

```text
complete reachable state-time enumeration
-> exhaustive D4 state/action/kernel automorphism tests
-> complete equal-stage D4 orbit partition
-> deterministic canonicalizers and stabilizers
-> stabilizer-orbit semantic actions
-> uniform distinct-inverse-action concretizers
-> representative-independent exact quotient
-> singleton/zero-width sound envelope
-> constrained abstract solve and ground lift
-> exact J0 value/risk/action-restriction comparison
-> exact quotient certificate and complete artifacts
```

The gate passes only if every reachable state-time value is preserved (exact rational
equality, or declared absolute numerical error at most `1e-12`), lifted and J0
constrained return/risk agree, failure is `99/5000`, `Delta_action=0`, reward/cost
widths are zero, transition uncertainty is singleton, `|Z|<|R|`, and the total abstract
state-action-pair count is strictly smaller than its ground counterpart. It contains
zero refinement steps and zero fallback calls. Any failure terminates with the baseline-validation
status `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`; that status is intentionally outside
the refinement engine's eight-result enum.

### Safe-chain aliased CEGAR positive-control gate

`g2048_select_safe_chain_aliased_partition_v0` is a separate full-V0 refinement
profile over the unchanged safe-chain structural key and query. It is neither a third
mandatory-split Phase 0.5 benchmark nor a mutation of the exact-`D4` profile. Its chain
is:

```text
complete 192-state query-support transition closure
-> ten-cell failure-plus-active-histogram base partition
-> non-equivariant canonical:first/last singleton concretizers
-> nominal proposal and independent exact full-plan audit
-> extract all reachable counterexamples
-> jointly rank all six-feature grammar candidates
-> accept four-bit local split in histogram (1,1,2)
-> replan, audit, extract, and rank again
-> accept four-bit local split in histogram (1,2,2)
-> replan and certify aggregate plus all eight initial support points
-> emit two linked iteration records and zero fallback
```

The base encoder contributes ten charged leaves and zero incremental refinement bits;
the profile uses the full-V0 budget and finishes at twelve leaves/eight bits. Exact
ranking evaluates 16 then 10 unique child signatures, so the final candidate-evaluation
counter is 26 rather than merely counting the two accepted proposals. The gate
requires the exact golden sequence in V0-026. It stops immediately after the second
split with reward `3/64`, exact lifted failure `317/16000`, sound
`U_F=397/20000<1/20`, and regret zero. J0 failure `99/5000`, risk gap `1/80000`, and
envelope conservatism `3/80000` are reported rather than erased. A third `(2,2,2)`
split is not part of this gate.

### Frozen later Gates

- **Phase 3 oracle quotient:** median compression at least `5x`, 95th-percentile normalized regret at most 1%, zero additional constraint violations, at least 80% tiny-instance pass rate.
- **Phase 3 human grammar:** median compression at least `2x`, mean normalized regret at most 5%, zero additional violations, at least 70% pass rate. If the oracle quotient fails, stop the quotient mainline.
- **Phase 5:** exact certificate coverage at least 70%, fallback at most 30%, normalized regret at most 2%, zero additional violations, median ground-node reduction at least `3x`, multi-resolution method on the fixed-level Pareto frontier in at least 75% of configurations, and break-even queries at most 20.
- **Phase 6 proposer:** coverage within one percentage point of deterministic CEGAR, zero additional violations, at least 30% fewer exact candidate evaluations, and at least `1.25x` end-to-end speedup; otherwise it is an ablation.
- **Phase 7 transfer:** the algorithm layer requires at least `2x` compression, at most 5% regret, and zero additional violations in both domains. Shared grammar must reach at least 80% of domain-specific Pareto hypervolume. Shared coordinates require no more than two percentage points regret degradation and at least 80% retained compression.

## Pseudocode / schema

```text
run_phase_0_5(domain, fixture, q):
  support = explicit_positive_mass_support(q.rho0)
  coverage = all_action_transition_closure(support)
  coverage_spec = freeze_coverage_descriptor(q.rho0, coverage)
  enumerate_or_state_cap()
  solve_J0_same_query()
  if J0 is already infeasible:
    assert fixture.structural_key == g2048_select_canonical_2x2_v0
    assert execution_profile == phase05_vertical_slice
  rapm = build(coarse_partition, coverage, coverage_spec)
  proposal = nominal_plan(rapm,q)
  audit = exact_audit(proposal,q)
  assert not audit.certified
  witness = select_counterexample(audit)
  split = deterministic_accept(witness, budgets)
  assert split.status == SPLIT_ACCEPTED
  result = replan_and_audit_or_charged_fallback()
  validate_bundle_and_hashes(result)

production_query(rapm,q):
  if not support_is_within_recorded_coverage(rapm,q.rho0):
    reject RAPM reuse; rebuild or use charged ground path
  if exact_J0_infeasibility_proof_exists_for_identical(
       rapm.structural_id, rapm.build_id, rapm.kernel_hash, q.query_hash):
    return INFEASIBLE_QUERY without refinement
  return normal_audit_refine_or_fallback(rapm,q)

run_safe_chain_exact_D4(fixture,q):
  R = enumerate_complete_state_time_graph(fixture,q)
  assert verify_all_D4_automorphisms(R)
  quotient = build_complete_equal_stage_D4_orbits(R)
  quotient.add_stabilizer_action_orbits()
  quotient.freeze_uniform_distinct_inverse_action_concretizers()
  if not quotient.all_exact_invariants_hold():
    return EXACT_D4_QUOTIENT_INVARIANT_VIOLATION
  abstract_result = solve_and_lift(quotient,q)
  assert exact_equal_to_J0(abstract_result,q)
  return CERTIFIED

run_safe_chain_aliased_cegar(profile,q):
  assert profile_key != structural_key
  assert closure_count == 192
  partition = failure_plus_active_histograms()  # ten leaves, zero base rate
  counters = full_v0_counters(leaves=10, rate_bits=0)
  while true:
    proposal = nominal_plan(partition,q)
    audit, witnesses = exact_audit_and_extract_all(proposal,q)
    if audit.certified: return CERTIFIED
    candidate = frozen_joint_rank(all_separating_candidates(witnesses))
    partition, counters = accept(candidate, counters)
```

## Invariants

- Budget exhaustion never returns an uncertified quotient policy.
- Known exact infeasibility short-circuits refinement under production. Permission to
  override that shortcut is keyed only to `g2048_select_canonical_2x2_v0` under
  `phase05_vertical_slice`, not to Phase 0.5 fixtures in general.
- The proof used by that shortcut resolves the current structural ID, build ID, kernel
  hash, and query hash; no component may be wildcarded.
- `STATE_CAP_EXCEEDED` implies `complete=false`, `STRESS_ONLY`, exclusion from exact Gates, and an explicit lower bound; no capped prefix may masquerade as a complete enumeration.
- A Gate numerator and denominator include fallback according to the frozen accounting rules.
- Gate configurations and thresholds are frozen before test access.
- Every Phase 0.5 build ID commits to its coverage mode, canonical initial-declaration
  hash, exact closure count, and no-outside-reuse flag; `structural_id` still excludes
  `rho0`.
- The safe-chain exact profile never invokes the refinement engine or ground fallback;
  every orbit cell is complete at one remaining horizon and every exact model entry is
  representative-independent.
- `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` cannot be converted into an accepted split,
  ordinary fallback, or positive-result exclusion.
- The aliased gate uses only ordinary CEGAR statuses, and neither its profile identity
  nor its events can appear in an exact-`D4` bundle.
- A malformed aliased build/replay returns `ALIASED_CEGAR_INVARIANT_VIOLATION`; it is
  not converted into a normal counterexample, accepted split, or fallback.
- The aliased runner never receives the two target cells as a schedule; their order is
  a reproducible consequence of exact witnesses and the frozen joint ranking.

## Acceptance tests

- One end-to-end test per required fixture proves its registered Phase 0.5 chain; every
  vertical-slice fixture that requires a mandatory split records that split explicitly.
- Boundary tests exercise every budget at limit and limit-plus-one.
- Each of the eight result states has a reachable fixture or unit test.
- State-cap test rejects `exact_sound` and preserves the untruncated status.
- Manifest validation detects any modified artifact.
- Recomputed all-action closure matches the recorded count, and changing `rho0`
  changes the query and coverage-specific build IDs without changing structural ID.
- An uncovered query state is rejected before abstract planning or certificate reuse.
- The safe-chain gate exhaustively tests state-orbit validity, action-orbit
  canonicalizer independence, distinct legal concretizer support, automorphisms,
  representative independence, envelope collapse, exact value/risk preservation, and
  zero restriction gap, plus strict state-time and state-action compression.
- Injecting one non-equivariant kernel/action-transform entry or one duplicate-weighted
  concretizer action reaches `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` without a split.
- The aliased profile starts with exactly ten cells, accepts exactly two `4+4` local
  splits at four bits each, links partitions `10 -> 11 -> 12`, and ends `CERTIFIED`
  with no fallback; missing, reordered, or hard-coded witness/candidate evidence fails.
- All eight initial point audits reproduce final `U_F=397/20000` and regret zero;
  independent lifting reproduces `317/16000`, not the J0 risk.

## Out of scope

Implementing Phase 1–7 in the Phase 0.5 milestone, claiming their Gates from smoke fixtures, crediting the supplied `D4` positive control with automatic quotient/predicate discovery, or crediting the aliased profile with predicate invention or unknown-symmetry discovery.

## Known failure modes

The coarse policy can be immediately infeasible, no predicate may separate the witness, every useful split may exceed rate, and an accepted split may still end in charged fallback. These are valid measured outcomes, but Phase 0.5 still requires a fixture with one accepted split. An implicit default support, incomplete all-action closure, or coverage-free cache key is unsound. In the exact `D4` gate, incomplete orbit closure, action-transform errors, stabilizer multiplicity bias, or nonzero envelopes are hard validation failures and are never repaired by refinement. In the aliased gate, replacing the deliberate boundary adapter with equivariant actions, forcing a third split after certification, or hiding the final risk gap changes the registered experiment.

## Open risks

Resolved `V0-RISK-001` proves that the frozen canonical `2x2` G2048 query is ground-infeasible for every registered positive risk threshold (`383/410` first-step failure). The Phase 0.5 expected ending for that regression remains mandatory refinement followed by fully charged fallback and `INFEASIBLE_QUERY`, not a safe quotient certificate. Resolved `V0-RISK-002` freezes the separately keyed safe-chain route as a no-split exact `D4` positive control; implementation must not silently tune either fixture or infer CEGAR success from that control.

Resolved `V0-RISK-003` is enforced by explicit query-support transition closure and a
coverage-specific build identity. This resolution does not claim unrestricted reuse
across arbitrary initial distributions.

V0-026 closes the small feasible aliased-CEGAR positive-control contract. It does not
close the later empirical question of automatically generating strategic predicates or
discovering useful quotients on larger fixtures.

Later Gate denominators and statistical aggregation details also need a preregistered analysis plan before Phase 3 test evaluation; the threshold values above are already frozen.
