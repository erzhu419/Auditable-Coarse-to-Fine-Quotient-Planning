# Benchmark and Predicate Grammar

## Definitions

**G2048-Select** is an explicit single-pair merge process, not slide-2048. A board cell is empty or has rank `j in {1,...,R}`, representing value `2^j`. A legal ground action `(u,v,d)` selects orthogonally adjacent equal-rank cells and survivor `d in {u,v}`.

**Layered Matching Buffer (LMB)** has a visible blocker DAG, typed tiles, buffer capacity `K`, and match arity three. A tile is eligible iff all its blockers are removed.

An atomic predicate is `f(x)<=theta` or `f(x)>theta`; a tree path forms conjunctions. Predicate ID is `feature_name | operator | reduced_rational_threshold`.

A **full one-step behavioural signature** is the exact tuple of registered reward-
feature values, entered-failure/terminal kind, and successor probabilities into the
current partition for one legal action. It is model-construction data, not a predicate,
Q/value signature, or human strategic coordinate.

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

The Phase 3A profile over the same safe-chain kernel uses a different, `D4`-equivariant
semantic vocabulary. A legal survivor is `TOWARD` iff it is orthogonally adjacent to
at least one occupied cell outside the selected merge pair, and `AWAY` otherwise.
Available labels are deduplicated, and `kappa_x` is uniform over the distinct legal
actions carrying a label. This adapter is fixed from current-state incidence and
occupancy; it reads no transition outcome, value, policy, or held-out query.

G2048 Phase 3A training contains two registered queries. The first,
`g2048.rank1_uniform.h2`, is the canonical safe-chain `D4`-uniform distribution with
`H=2`. The second, `g2048.strict_cross_d4_bridge.h1`, has `H=1` and places mass
`3/25` on each of the eight `D4` images of `(1,1,2,0)`, `1/200` on each of the four
images of `(2,2,2,0)`, and `1/400` on each of the eight images of `(2,2,4,0)`.
Both use canonical merge reward and `delta=1/20`; the bridge uses `Rmax=1`. Their
20-state support-union closure contains 192 states. The train-oracle atom registry
contains exactly `selected_semantic_action@delta` and `maximum_normalized_reward` at
each of `h=1,2`. The cardinality-first exact-audit selector must choose the two `h=1`
atoms and produce eight cells. These atoms are oracle signatures, not members of the
human predicate grammar.

The bridge's explicit witnesses `(0,2,2,2)` and `(0,2,4,2)` must be in one oracle
cell but different `D4` state orbits; both must occur in the bridge policy graph and
select `AWAY`. Its exact row is reward `13/400`, failure `199/5000`, and sound
`U_F=1/25`. This query belongs to construction/training, not held-out reuse.

Only after that partition and RAPM are frozen, evaluate:

```text
g2048.rank2_uniform.h2 : uniform D4 orbit of (2,2,3,0), H=2
g2048.mixed_points.h2 : 1/2 (1,1,2,0) + 1/2 (2,2,3,0), H=2
g2048.rank1_point.h2  : point mass at (1,1,2,0), H=2
g2048.rank1_uniform.h1: training distribution with H=1
```

All retain the registered canonical reward and `delta=1/20`; their contents cannot
generate atoms, thresholds, labels, coverage, or a partition. Their goal ID is the
`default` structural stopping goal.

Phase 3B reuses these six distinct G2048 query definitions as a workload only after a
new query-neutral behavioural RAPM has frozen. Its builder starts from failure/terminal
kind and refines with every legal action's complete one-step canonical merge-reward
feature, entered-failure flag, and successor-cell distribution. It uses neither the
Phase 3A oracle atoms nor any query/Q/value/policy field. Four of the six queries have
`H=2`, so the campaign contains genuine multi-step contingent planning rather than
only one-step diagnostics. Its authority normalizer registry contains the single proof
`g2048.canonical.merge_le_1_per_step.total_le_h.v1`, kind
`nonnegative_feature_caps_v1`, with complete reward basis `(merge=1)`,
`merge.per_step_cap=1`, and
`merge.total_cap=null`.

### LMB

Initial buffer is empty; arity is 3; `B=N/3`; `H=N`. A step removes one eligible tile, inserts its type, immediately removes a triple and awards one match reward when present, then checks overflow (`occupancy>K`) before checking board-clear success. Clear success adds `B`. Overflow enters absorbing failure.

Canonical tiny parameters are `N in {6,9,12}`, `T in {2,3,4}`, `K in {3,4,5}`, `D in {1,2,3}`. Solvable layouts are reverse-constructed: create type counts divisible by three; find a complete clearing order by randomized backtracking while preserving capacity and per-type completion; assign at most `D` layers; give noninitial tiles one or two blockers that occur earlier in the order and are shallower; reject cycles, excess depth, or invalidated order; replay the authoritative simulator. Store the order only as generation evidence. Non-guaranteed layouts are `STRESS_ONLY`.

Phase 3A registers `lmb_generated_n6_t2_k3_d2_seed0_v0` with tile types
`(0,1,0,1,1,0)`, blockers `(empty,{0},{0},empty,empty,{0})`, capacity 3, and the
ordinary arity-three/clear-bonus rules. Its training support is the nine
`(removed_mask,buffer)` pairs in V0-027, uniformly weighted; the canonical training
query has `H=3`, `delta=1/20`, and `Rmax=4`. The support closure has 25 states.

LMB's Phase 3A builder uses no predicate grammar and no query values: it minimizes the
complete exact controlled model by reward-feature/failure/termination/successor-cell
action signatures. Registered held-out evaluations are match-only `H=3,delta=0,Rmax=2`
and canonical `H=2,delta=0,Rmax=4`, on the same nine-state support. They are evaluation
inputs only. The match-only row uses proof ID
`lmb.match_only.matches_le_n_over_3.v1`; because its coefficients differ from the
canonical benchmark, it may not reuse the canonical `2N/3` proof ID.

Accordingly, reuse is claimed only across the registered two-domain held-out suite:
G2048 supplies initial-support/distribution and horizon variation, while LMB supplies
reward-basis, horizon, and risk variation. The grammar contract does not imply that
either domain was tested on every variation axis.

Phase 3B adds two LMB workload queries on the same registered support after its
query-neutral behavioural RAPM is frozen: `lmb.alias9.canonical.h3.delta10` with
canonical weights, `H=3`, and `delta=1/10`; and
`lmb.alias9.terminal_clear_only.h3` with `match=0`, `terminal_clear=1`, `H=3`,
`delta=1/20`, `Rmax=2`, and proof ID
`lmb.terminal_clear_only.clear_bonus.v1`. The latter may not inherit either the
canonical `2N/3` or match-only proof by name. Together with the Phase 3A three, this
gives five LMB workload queries. LMB construction uses the unweighted registered basis
`(match,terminal_clear)`, one-time failure/terminal kind, and exact successor
distribution only; query coefficients, horizon, and `delta` are unavailable. All five
use the `default` structural stopping goal; “terminal-clear-only” changes reward
weights, not goal semantics. Portable query schema v1 rejects any non-`default` goal.
The LMB authority registry contains the three proof IDs already named by the canonical,
match-only, and terminal-clear-only rows. Each is kind
`nonnegative_feature_caps_v1` and binds exactly one complete sorted reward basis:

```text
lmb.canonical.matches_plus_clear_le_2n_over_3.v1 : (match=1, terminal_clear=1)
lmb.match_only.matches_le_n_over_3.v1            : (match=1, terminal_clear=0)
lmb.terminal_clear_only.clear_bonus.v1           : (match=0, terminal_clear=1)
```

All three carry the same sorted caps:
`match=(per_step_cap=1,total_cap=N/3)` and
`terminal_clear=(per_step_cap=B,total_cap=B)`, with `B=N/3`. A proof ID does not relax
feature registration or authorize a different reward basis or goal; in particular,
these three proof IDs cannot be cross-used.

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

full_one_step_behaviour(Pi,x,a):
  return (registered_reward_feature_vector(x,a),
          entered_failure_probability, terminal_or_success_kind,
          exact_successor_distribution_over(Pi))
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
- Phase 3A's relative-survivor labels commute with all `D4` transforms, and its LMB
  behavioural labels are determined solely by the frozen exact kernel/refinement.
- Held-out query fields never enter either Phase 3A feature/action registry or
  construction signature.
- Phase 3B behavioural signatures retain the complete unweighted registered feature
  basis and contain no horizon, risk, reward weights, Q/value, or selected-policy field.
- All six/five Phase 3B query definitions are read only after the per-domain build
  epoch and portable model identity freeze.
- Phase 3B dependency evidence is scoped to builder API/data flow and static source
  audits of the behavioural builder/portable planner, not a closed import DAG for the
  whole campaign runner.

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
- The Phase 3A G2048 build reproduces the 20-state training-support union, total
  `192 -> 8`, active `68 -> 7`, the two selected `h=1` oracle atoms, physical
  state-action orbits/abstract entries `18 -> 14`, and the bridge's two non-`D4`
  witnesses jointly policy-reachable in one cell with action `AWAY` and exact row
  `(reward,failure,U_F)=(13/400,199/5000,1/25)`.
- The registered LMB fixture reproduces its serialized tile/blocker layout, 25-state
  closure, behavioural trace `3 -> 5 -> 5`, five total/three active cells, active
  compression `18/3`, physical state-action orbits/abstract entries `16 -> 4`, and the
  same training graph reaches members from multiple physical orbits inside every active
  cell, including the explicit nonautomorphic pair `(11,(1,2))`, `(13,(2,1))`.
- The Phase 3B G2048/LMB fixed points are unchanged when workload order, query weights,
  horizon, or `delta` changes, and an injected oracle/value/policy signature at the
  builder/planner boundary fails the API/data-flow or static source audit.
- Their fixed-point traces and state/action counts are respectively
  `2 -> 9 -> 10 -> 10`, `192 -> 10`, `144 -> 17` for G2048 and
  `3 -> 5 -> 5`, `25 -> 5`, `40 -> 4` for LMB.
- The Phase 3B registry has six G2048 and five LMB distinct queries, includes multi-step
  rows in both domains, validates every query-specific normalizer and the fixed
  `default` goal, and retains one unchanged portable RAPM per domain.
- Independent verification reconstructs the above G2048/LMB normalizer-rule registries
  from the authoritative kernels rather than trusting serialized model summaries.

## Out of scope

Slide-2048, hidden LMB layouts, visual inputs, arbitrary logical split formulas, oracle-derived `M_fail` predicates, exposing LMB solution evidence to the planner, treating the registered `D4` group as an automatically discovered abstraction, treating Phase 3A's oracle atoms/exact behavioural signatures as invented human predicates, or describing Phase 3B complete one-step minimization as automatic predicate invention, learned dynamics, or local hybrid repair.

## Known failure modes

Rejection sampling or LMB backtracking may be slow for hostile parameters; generation must terminate with an explicit failure, not a malformed instance. Some coarse cells have no common action. An incomplete support closure or cache reuse under a different coverage descriptor is unsound. A non-equivariant survivor transform, unstable canonicalizer tie order, or averaging over stabilizer elements without deduplicating actions destroys the exact `D4` baseline. Conversely, silently replacing the aliased profile's deliberately non-equivariant boundary labels with the exact `D4` actions removes the intended counterexample and changes the profile identity. Phase 3A additionally fails if a held-out query influences its atom subset or if cross-orbit evidence comes only from the collapsed terminal cell.

## Open risks

The canonical `2x2` initial distribution and post-spawn failure rule make every positive-horizon query infeasible at the registered risk thresholds. Exactly, first-step survival is `27/410`, hence failure is `383/410 > 0.10`; see resolved `V0-RISK-001`. Phase 0.5 must preserve this result through charged J0 fallback/infeasibility rather than weakening a rule. The separately keyed safe-chain fixture now supplies the nontrivial feasible ground query, but cannot support a positive quotient claim until its implementation, J0 golden regression, and quotient audit pass.

`V0-RISK-002` is resolved by the exact `D4` profile in V0-024. Its remaining risk is
implementation conformance: a successful certificate is not automatic until all group,
action, representative-independence, zero-width, and J0-preservation tests pass. The
formerly future aliased safe-chain CEGAR fixture is now frozen by V0-026 as a separate
profile over the same ground structure; it cannot modify or borrow the result label of
the known-symmetry baseline.

Exact domain-wide definitions of unlock depth and relaxed conversion distance must also be versioned with their adapter before Phase 3 grammar comparisons; Phase 0.5 may use only already-total registered features.

V0-027 now supplies a cross-automorphism exact-model/oracle positive control in both
domains. It does not settle whether a human or learned grammar can recover comparable
cells without oracle values or complete model minimization.

V0-028 removes Q/value signatures from the portable campaign builder, but it still
assumes exact complete one-step dynamics on tiny coverage. Learning those dynamics,
inventing readable predicates, and repairing a failed certificate locally remain open.
