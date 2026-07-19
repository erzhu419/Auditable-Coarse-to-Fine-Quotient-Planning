# Benchmark and Predicate Grammar

## Definitions

**G2048-Select** is an explicit single-pair merge process, not slide-2048. A board cell is empty or has rank `j in {1,...,R}`, representing value `2^j`. A legal ground action `(u,v,d)` selects orthogonally adjacent equal-rank cells and survivor `d in {u,v}`.

**Layered Matching Buffer (LMB)** has a visible blocker DAG, typed tiles, buffer capacity `K`, and match arity three. A tile is eligible iff all its blockers are removed.

An atomic predicate is `f(x)<=theta` or `f(x)>theta`; a tree path forms conjunctions. Predicate ID is `feature_name | operator | reduced_rational_threshold`.

## Normative decisions

### G2048-Select

The original canonical family remains the source of the infeasibility regression:

| Board | `R` | `Hmax` | Spawn support and probabilities |
|---|---:|---:|---|
| `2x2` | 6 | 6 | `P(1)=9/10`, `P(2)=1/10` |
| `3x3` | 8 | 8 | `P(1)=4/5`, `P(2)=3/20`, `P(3)=1/20` |

Initial distribution: choose two distinct cells uniformly without replacement, independently draw their ranks, and condition by rejection on at least one legal merge. The whole candidate board is resampled; initial failure mass is zero.

This canonical initial distribution is a registered `QuerySpec` default, not a ground
dynamics field. Phase 0.5 passes its exact ordered declaration explicitly to the build;
the builder never rediscovers it by calling a domain default.

Transition order is fixed: enumerate legal pairs; select pair and survivor; remove both; place rank `min(j+1,R)` at survivor; emit raw reward `2^(j+1)/2^(R+1)`; if any cell is empty, spawn exactly one rank and choose its empty position uniformly; then enter absorbing failure iff no legal merge remains. The dead-end check occurs on every transition, including the last transition before horizon truncation. Invalid actions are absent from `A(x)`.

The named `2x2` configurations are:

| Structural key | Spawn law | Role |
|---|---|---|
| `g2048_select_canonical_2x2_v0` | `P(1)=9/10`, `P(2)=1/10` | `infeasibility_and_soundness_regression` |
| `g2048_select_safe_chain_2x2_v0` | `P(1)=99/100`, `P(2)=1/100` | `nontrivial_safe_planning_and_quotient_certificate` |

The canonical key retains the conditional two-tile initial query above and every existing transition rule. It must not be cited as evidence for a positive safe-planning result.

`g2048_select_safe_chain_2x2_v0`, display name **G2048-Select Safe-Chain 2×2**, uses the same `2x2` geometry, `Hmax=6`, orthogonal adjacency, ranks `1` through `6`, chosen-survivor one-pair merge, rank cap, one-spawn timing, uniform empty-cell spawn position, post-spawn failure rule, final-transition ordering, and invalid-action semantics. Only its registered spawn-rank law differs as shown in the table.

Its canonical query has `H=2`, `delta=1/20`, and canonical merge-reward coefficients. Let `x_base=((1,1),(2,0))`; `rho0` is uniform over the eight distinct rotations/reflections in its square-dihedral `D4` orbit. Geometry, rank cap, `Hmax`, adjacency, merge/spawn/failure rules, and ground actions belong to the structural key. `rho0`, `H<=Hmax`, `delta`, and reward coefficients belong to `QuerySpec`.

The required exact J0 regression is:

```text
optimal first action:
  retain the new rank-2 tile adjacent to the existing rank-2 tile
optimal survival through H=2:
  (99/100)^2 + (1/100)^2 = 4901/5000
optimal failure by H=2:
  99/5000 < 1/20
wrong-first-survivor survival through H=2:
  1/10000
```

The second action is contingent on the observed first spawn. These exact values, including the action distinction, are golden oracle requirements rather than estimates.

For its positive-control profile, safe-chain is the
`exact_D4_orbit_quotient_certificate_baseline`, not a deliberately coarse CEGAR
fixture. Enumerate the complete reachable state-time graph from its eight-state query
support for remaining horizons `h in {0,1,2}` and partition it into full equal-stage
`D4` orbits. The registered group action transforms board cells, selected equal-rank
pairs, and survivor cells together; transformed action identity sorts the unordered
pair endpoints by cell key and retains the transformed survivor. Legal-action images, reward, failure cost, and
coalesced exact transition probabilities must commute with every group element.

Canonical boards use row-major lexicographic minimum (empty rank `0`) over the eight
transforms and break canonicalizer ties by
`e,r,r^2,r^3,m,rm,r^2m,r^3m`, with clockwise `r(i,j)=(j,1-i)`, vertical reflection
`m(i,j)=(i,1-j)`, and `r^k m` applying `m` first. At a canonical board, a
semantic action is the orbit of its canonical-frame ground action under the board's
stabilizer. At a concrete board, the concretizer is uniform over the deduplicated set
of distinct inverse ground actions in that orbit. It is never uniform over group
elements before deduplication. This baseline performs no CEGAR split; any failed
automorphism, representative-independence, support, or value-preservation check returns
`EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` and invalidates the exact-baseline label.

The registered `D4` group and state/action transforms belong to the structural/build
profile. The complete reachable state-time graph and its orbit materialization are
specific to the canonical `rho0,H=2` query; they do not move those query fields into the
structural key or establish coverage for a different query.

For both G2048 profiles and LMB, Phase 0.5 materializes
`query_support_transition_closure`: start with the explicit positive-mass query support,
follow every legal action and positive-probability outcome to a fixed point, and record
`mode=query_support_transition_closure`, `initial_support_sha256`, distinct
`covered_state_count`, and `reuse_outside_coverage_forbidden=true` in the coverage-specific
build identity. Structural fixture serialization contains no `initial_law`; changing a
registered query distribution preserves the structural identity but produces a new
query and coverage descriptor.

The separately registered refinement profile
`g2048_select_safe_chain_aliased_partition_v0` reuses the safe-chain ground
`structural_key`, canonical query, and full transition closure; the name is a
`profile_key`, not a second physical environment. Its authoritative closure contains
exactly 192 states. The fixed base partition has ten cells: all absorbing failure
states share one terminal cell, while each active state is keyed by the pair
`(empty_count, sorted multiset of nonzero ranks)`. There are nine such active
histograms. Each happens to be exactly one `D4` state orbit, so this base partition is
not evidence of a previously unknown state quotient.

This profile deliberately uses the order-dependent boundary vocabulary
`canonical:first` and `canonical:last`, meaning the first and last distinct actions in
the kernel's authoritative order. Their concretizers are deterministic singleton
distributions; when only one primitive action exists the labels are deduplicated. This
adapter is intentionally not `D4`-equivariant and never inherits the exact baseline's
stabilizer-orbit actions.

Its preregistered action-frame geometry grammar contains exactly six total current-state
features:

```text
first_survivor_adjacent_nonmerged_count
first_pair_horizontal
first_survivor_row
first_survivor_column
nonmerged_row
nonmerged_column
```

`FIRST` fixes the action frame. If its merge pair leaves exactly one occupied cell
outside the pair, rows and columns are zero-based row-major coordinates,
`first_pair_horizontal` is the pair-orientation indicator, and
`first_survivor_adjacent_nonmerged_count` is one iff the `FIRST` survivor and that
nonmerged cell are orthogonally adjacent. All six features are zero for terminal
states, states without `FIRST`, or states without exactly one occupied nonmerged cell.
They inspect neither outcomes nor spawn probabilities, policies, values, rollouts, or
J0. The single registered threshold per feature is `1/2`; the target predicate is
`first_survivor_adjacent_nonmerged_count|<=|1/2`. With six feature choices and one
threshold its rate is `1+ceil(log2 6)=4` bits per local application.

### LMB

Initial buffer is empty; arity is 3; `B=N/3`; `H=N`. A step removes one eligible tile, inserts its type, immediately removes a triple and awards one match reward when present, then checks overflow (`occupancy>K`) before checking board-clear success. Clear success adds `B`. Overflow enters absorbing failure.

Canonical tiny parameters are `N in {6,9,12}`, `T in {2,3,4}`, `K in {3,4,5}`, `D in {1,2,3}`. Solvable layouts are reverse-constructed: create type counts divisible by three; find a complete clearing order by randomized backtracking while preserving capacity and per-type completion; assign at most `D` layers; give noninitial tiles one or two blockers that occur earlier in the order and are shallower; reject cycles, excess depth, or invalidated order; replay the authoritative simulator. Store the order only as generation evidence. Non-guaranteed layouts are `STRESS_ONLY`.

### Predicate grammar

The minimum cross-domain strategic basis is capacity slack `S_cap=(K-occupancy)/K` (for G2048, empty cells divided by board cells), match-debt summaries for arity `m_j`, normalized branching `log(1+|A|)/log(1+Amax)`, immediate release liquidity `L1`, unlock depth `U`, and relaxed conversion distance `C` clipped at `H`. The primary shared-algorithm claim permits finite, preregistered domain atoms; Phase 0.5 additionally registers G2048 `min_rank`, `max_rank`, and `rank_sum`, and LMB buffer/object/action counts. These are current-state structural measurements, never oracle or rollout values. A later shared-grammar claim must exclude them. Domain adapters must document exact feature semantics and total terminal-state conventions.

Thresholds come only from training data: distinct-value adjacent midpoints, at most 16 per feature (otherwise frozen quantiles), plus preregistered semantic constants such as `0`, `1/K`, `2/K`, and `1/2`. Rate is `1+ceil(log2|F|)+ceil(log2|Theta_f|)+lambda_depth*depth`.

## Pseudocode / schema

```text
generate_lmb(seed, N,T,K,D):
  multiset = counts_multiple_of_three(...)
  order = capacity_feasible_backtracking(multiset)
  dag = assign_verified_blockers(order, max_depth=D)
  assert authoritative_replay(dag, order) == CLEAR
  return instance, private_generation_evidence

candidate_predicates(training_states):
  values = exact feature values
  thresholds = midpoints_or_frozen_quantiles(values) union semantic_constants
  return canonical reduced-rational predicates
```

## Invariants

- Both simulators are authoritative, exact, and make terminal/failure order explicit.
- G2048 transition probability mass is one and contains exactly one spawn when space exists.
- Safe-chain state/action transforms preserve legality, reward, one-time failure cost,
  terminal semantics, and the exact kernel under every registered `D4` element.
- A guaranteed LMB instance replays to clear under its private generation order.
- Test data never generates grammar thresholds or feature choices.
- `M_fail`/robust planning margin is evaluation-only, never a human-grammar predicate.
- Every Phase 0.5 RAPM state set is the full all-action transition closure of the
  explicit query support, and reuse outside that recorded closure is forbidden.

## Acceptance tests

- Golden one-step transitions cover rank cap, survivor choice, spawn/no-space, last-step dead-end, match-before-overflow, and clear bonus.
- Initial G2048 distribution is normalized and every support state has a legal merge.
- Structural benchmark JSON omits `initial_law`; query JSON owns the exact distribution,
  and its canonical declaration hash plus recomputed closure count match `build_id`.
- The safe-chain `D4` orbit contains exactly eight distinct states with mass `1/8` each; exact J0 reproduces failure `99/5000`, and the wrong-first-survivor survival is `1/10000`.
- The complete safe-chain state-time graph is closed under all eight transforms; no
  quotient cell crosses remaining horizons, mixes terminal/nonterminal states, or
  aliases failure with nonfailure.
- Different valid canonicalizers induce the same stabilizer action orbit, and every
  deduplicated inverse concretizer action is legal with exact uniform mass.
- The exact quotient strictly reduces both complete reachable state-time count and total
  legal state-action-pair count before a “strict compression” claim is accepted.
- The aliased profile reconstructs the 192-state closure and ten-cell base partition,
  verifies that each active histogram cell is one complete `D4` orbit, but uses only
  the registered boundary labels and singleton concretizers during CEGAR.
- Its exact witness extractor and full candidate ranking select
  `first_survivor_adjacent_nonmerged_count|<=|1/2` first in active histogram
  `(1,1,2)` and then in `(1,2,2)`; both applications split eight states into `4+4`
  and cost four bits.
- LMB generation is deterministic by seed and replay-verifies its evidence.
- Predicate IDs collapse mathematically equal rational thresholds.
- Train/validation/test/OOD identities are disjoint and hash-stable.

## Out of scope

Slide-2048, hidden LMB layouts, visual inputs, arbitrary logical split formulas, oracle-derived `M_fail` predicates, exposing LMB solution evidence to the planner, and treating the registered `D4` group as an automatically discovered abstraction.

## Known failure modes

Rejection sampling or LMB backtracking may be slow for hostile parameters; generation must terminate with an explicit failure, not a malformed instance. Some coarse cells have no common action. An incomplete support closure or cache reuse under a different coverage descriptor is unsound. A non-equivariant survivor transform, unstable canonicalizer tie order, or averaging over stabilizer elements without deduplicating actions destroys the exact `D4` baseline. Conversely, silently replacing the aliased profile's deliberately non-equivariant boundary labels with the exact `D4` actions removes the intended counterexample and changes the profile identity.

## Open risks

The canonical `2x2` initial distribution and post-spawn failure rule make every positive-horizon query infeasible at the registered risk thresholds. Exactly, first-step survival is `27/410`, hence failure is `383/410 > 0.10`; see resolved `V0-RISK-001`. Phase 0.5 must preserve this result through charged J0 fallback/infeasibility rather than weakening a rule. The separately keyed safe-chain fixture now supplies the nontrivial feasible ground query, but cannot support a positive quotient claim until its implementation, J0 golden regression, and quotient audit pass.

`V0-RISK-002` is resolved by the exact `D4` profile in V0-024. Its remaining risk is
implementation conformance: a successful certificate is not automatic until all group,
action, representative-independence, zero-width, and J0-preservation tests pass. The
formerly future aliased safe-chain CEGAR fixture is now frozen by V0-026 as a separate
profile over the same ground structure; it cannot modify or borrow the result label of
the known-symmetry baseline.

Exact domain-wide definitions of unlock depth and relaxed conversion distance must also be versioned with their adapter before Phase 3 grammar comparisons; Phase 0.5 may use only already-total registered features.
