# V0 Decision Ledger

**Status:** normative source of truth  
**Ledger version:** 0.7.0
**Last updated:** 2026-07-20

## Authority

Normative authority is, from highest to lowest:

1. this ledger;
2. the nine files in `specs/`;
3. the answered **Safe-Chain D4 Quotient Baseline** decision in `markdown/GPT_d4_quotient_decision.md`;
4. the answered **Normative Follow-up Decisions** in `markdown/GPT_followup_questions.md`;
5. the **Normative Decision Addendum** embedded in `markdown/GPT_question.md`;
6. the V0 normative section of `markdown/PRECONSTRUCTION_AUDIT.md` (the section beginning “二、对Codex十二个问题作唯一选择” through “七、Codex现在应该生成什么”);
7. `markdown/Roadmap.md` and later vision or positioning text.

Lower-authority text is historical context when it conflicts with a higher-authority source. A normative change requires a new dated ledger row that names what it supersedes and the affected interfaces, proofs, tests, Gates, and stored artifacts. Existing rows are never silently rewritten; spelling-only corrections may be noted in the change log.

Items 3–7 are local, Git-ignored provenance sources; the published ledger and nine
specifications are self-contained and remain authoritative when those local files are
absent from a public checkout.

## Frozen decisions

| ID | Date | Scope | Status | Decision | Supersedes / resolves | Affected interfaces and tests |
|---|---|---|---|---|---|---|
| V0-001 | 2026-07-19 | Authority | FROZEN | The authority order above is binding. The ledger and nine specs, not chat prose, define V0. | Conflicting priority statements in planning discussions. | Documentation lint; artifact `contract_version`; every Gate. |
| V0-002 | 2026-07-19 | Problem class | FROZEN | V0 is finite-state, finite-horizon, fully observable, symbolic, with finite state-dependent primitive action sets and an exact enumerable kernel. Remaining horizon is part of the planning state. | Broader POMDP, learned-model, infinite-horizon, and SMDP ambitions. | `DomainProtocol`; enumeration tests; J0–J2 only. |
| V0-003 | 2026-07-19 | Reuse boundary | FROZEN | The reusable object is a `RAPM`; a `QuerySpec=(rho0,H,w,g,delta)` produces a per-query contingent policy graph. Reuse permits varying initial distribution, `H<=Hmax`, registered reward weights/goals, and `delta in {0,0.05,0.10}`; primary `delta=0.05`. Structural changes listed in `specs/RESEARCH_CONTRACT.md` require rebuild. | Earlier output that bundled a solved policy into the reusable model. | `RAPM`, `QuerySpec`, cache-key tests, break-even accounting. |
| V0-004 | 2026-07-19 | Abstract model | FROZEN | Every RAPM contains a nominal point model for proposal/ranking and an independently constructed exact sound envelope for audit. Nominal accuracy is never a certificate. | Point-model versus interval-model ambiguity. | `NominalModel`, `SoundEnvelope`; envelope-containment and independence tests. |
| V0-005 | 2026-07-19 | Actions | FROZEN | V0 uses one-step primitive semantic actions, a frozen auditable `psi_x`, and frozen (possibly stochastic) `kappa_x`. A cell exposes only semantic actions present in every member. First-hit options and SMDP durations are excluded. | First-hit/action-abstraction entanglement. | Domain action adapter; common-action counterexample test; J1/J2 comparison. |
| V0-006 | 2026-07-19 | Policy class | FROZEN | The V0 abstract selector and J0 comparator are deterministic finite-horizon Markov policies; randomness may enter through `kappa`, `rho0`, and the environment. Any randomized-policy extension requires a ledger change and a matched J0 comparator. | Previously implicit policy randomization convention. | Policy schema; constrained-frontier oracle tests; certificate theorem statement. |
| V0-007 | 2026-07-19 | Regret | FROZEN | Certification compares the lifted complete plan with the action-unrestricted ground constrained optimum. `U_all` ranges over every legal ground action, while `L_pi` evaluates the lifted policy. Accept only when `U_all-L_pi <= epsilon_regret=0.05` for normalized total return in `[0,1]`, at every certified initial support point. | Certificates only within the concretizer-restricted policy class; one-step dominance. | Unrestricted-envelope DP; lifted-policy DP; J0 truth comparison; descendant-coverage test. |
| V0-008 | 2026-07-19 | Reward scale | FROZEN | Each query records a proved normalization constant and evaluates normalized total return in `[0,1]`. Canonical Phase 0.5 uses `Rmax=H` for G2048 and `Rmax=2N/3` for LMB. A query whose registered weights lack a valid bound is rejected, not silently clipped. | Unspecified meaning of “reward normalization to [0,1]”. | Reward registry; `QuerySpec` validation; certificate and artifact checks. |
| V0-009 | 2026-07-19 | Constraint | FROZEN | Failure is absorbing and charged once on entry: `c_t=1{x_t notin F, x_{t+1}=F}`. Thus expected cumulative cost equals failure probability by horizon. Planning maintains nondominated `(L_R,U_F,subpolicy)` frontiers; final feasibility uses only sound `U_F`. | Chance-constraint versus cumulative-cost ambiguity. | Failure transition tests; constrained DP; risk-certificate tests. |
| V0-010 | 2026-07-19 | Fallback | FROZEN | Uncertified/stalled/budget-exhausted work invokes the same constrained ground problem with the same query. All time, expansions, calls, and locations are charged. If no ground policy satisfies the constraint, return `INFEASIBLE_QUERY`. | Unconstrained or uncharged fallback. | Fallback API; accounting schema; infeasible fixture. |
| V0-011 | 2026-07-19 | Quotients/evidence | FROZEN | Production V0 is a nested hard partition with a set-valued exact envelope. Q-signature is diagnostic and homomorphic quotient is an exact baseline. Evidence labels are exactly `oracle_truth`, `exact_sound`, `statistical_high_probability`, and `diagnostic_only`; V0 certificates are `exact_sound`. | Ambiguous “quotient” and evidence terminology. | Artifact enums; rejection of mislabeled results; J0–J2 reports. |
| V0-012 | 2026-07-19 | CEGAR | FROZEN | Refinement has the eight terminal/result states in `specs/MILESTONES_AND_GATES.md`; duplicate/no-op checks use canonical rational predicates and partition signatures. Ranking is audit-width reduction per rate cost with the frozen tie order. Grammar-incomplete or stalled cells force fallback until rebuild. | Missing termination and nondeterministic split selection. | Refinement API; duplicate/no-op/tie-break tests; rebuild invalidation. |
| V0-013 | 2026-07-19 | Budgets | FROZEN | Full V0: 64 leaves, 63 accepted splits, 256 bits, 2,048 candidate evaluations, 32 exact fallback/oracle invocations, and 50,000 reachable states. Phase 0.5: 8 leaves, 7 splits, 128 candidate evaluations, 4 exact fallback/oracle invocations; the 256-bit rate cap and 50,000-state cap remain unless a stricter fixture cap is declared. V0 rate accounting uses `lambda_depth=1`. | Unbounded refinement/oracle use and unspecified executable depth-rate coefficient. | Budget object; boundary tests; charged-stop artifacts. |
| V0-014 | 2026-07-19 | G2048 | FROZEN | Canonical explicit-merge rules, conditional two-tile initial distribution, spawn probabilities, `R/Hmax`, action survivor, reward, rank cap, and post-spawn failure order are defined only in `specs/BENCHMARK_GRAMMAR.md`. Dead-end on the final transition still enters failure before horizon truncation. | Earlier incomplete/ordering variants. | G2048 simulator golden tests; distribution-mass and transition-order tests. |
| V0-015 | 2026-07-19 | LMB | FROZEN | Canonical LMB starts with empty buffer, arity 3, `B=N/3`, `H=N`, automatic match before overflow, and the frozen reverse-construction verifier. Stress instances without a solvability guarantee are separately labelled. | Missing generation and bonus semantics. | LMB simulator/generator replay tests; success/failure-order tests. |
| V0-016 | 2026-07-19 | State cap | FROZEN | Crossing 50,000 reachable states yields `STATE_CAP_EXCEEDED`, `STRESS_ONLY`, and `complete=false`. Enumeration may stop with an explicit lower bound and diagnostic prefix, but that prefix is never reported as a complete/exact enumeration and the result cannot carry `exact_sound`. | Silent truncation or statistical downgrade. | Enumerator cap test; Gate inclusion filter; evidence-label validator. |
| V0-017 | 2026-07-19 | Phase 0.5 | FROZEN | Each benchmark must execute the complete vertical slice in `specs/MILESTONES_AND_GATES.md`, including one explicit witness and one deterministic accepted split, ending in a certificate or fully charged constrained fallback. | Skeleton-only interpretation of Phase 0.5. | Two end-to-end acceptance tests and artifact/hash validation. |
| V0-018 | 2026-07-19 | Numerical representation | FROZEN | Canonical benchmark probabilities, thresholds, rewards, and rate inputs are stored as reduced rationals; floating views are derived. Exact-sound checks operate on exact values where the implementation supports them and never round a failed inequality into success. | Unspecified float-threshold canonicalization. | Rational serialization; predicate-ID equality; probability-mass tests. |
| V0-019 | 2026-07-19 | G2048 regression roles | FROZEN | Preserve `g2048_select_canonical_2x2_v0` unchanged with role `infeasibility_and_soundness_regression`. It remains the exact risk-audit, charged-fallback, and `INFEASIBLE_QUERY` regression and cannot support a positive claim of nontrivial safe G2048 quotient planning. Add the separately keyed `g2048_select_safe_chain_2x2_v0`, display name `G2048-Select Safe-Chain 2×2`, with intended evaluation role `nontrivial_safe_planning_and_quotient_certificate`. The role grants claim eligibility only after an actual exact quotient certificate; it is not a result label or advance guarantee. | Resolves choice Q1 and the positive-fixture part of `V0-RISK-001` without changing the canonical regression. | Structural/query registry; build IDs; experiment rows; positive and infeasible G2048 labels. |
| V0-020 | 2026-07-19 | G2048 safe-chain fixture | FROZEN | `g2048_select_safe_chain_2x2_v0` uses a 2x2 orthogonal board, ranks 1 through 6, `Hmax=6`, one explicit adjacent equal-rank merge with chosen survivor, cap at rank 6, one post-merge spawn with rank law `P(1)=99/100`, `P(2)=1/100`, uniform empty-cell position, and absorbing post-spawn dead-end failure checked before horizon truncation. Its canonical query is the uniform distribution over the eight distinct `D4` images of `[[1,1],[2,0]]`, `H=2`, `delta=1/20`, and canonical merge reward. Dynamics/action fields are structural; `rho0`, horizon, delta, and reward coefficients are query fields. J0 must reproduce optimal survival `4901/5000`, failure `99/5000`, and wrong-first-survivor survival `1/10000`. | Adds a separately keyed exception to V0-014's canonical spawn/query defaults; V0-014 remains unchanged for `g2048_select_canonical_2x2_v0`. | G2048 kernel/config registry; D4 orbit test; J0 policy/failure golden test; query/build hash separation; quotient-certificate experiment. |
| V0-021 | 2026-07-19 | Known infeasibility | FROZEN | The mandatory split before fallback on `g2048_select_canonical_2x2_v0` is a Phase 0.5 vertical-slice test exception only. Production execution with an already-established exact J0 infeasibility proof for the identical structural/build/kernel identity and `QuerySpec` returns `INFEASIBLE_QUERY` immediately, without refinement. Unknown, merely suspected, structurally mismatched, or query-mismatched infeasibility does not permit this shortcut. | Resolves Q1-split and prevents the construction-mechanics test from becoming a production algorithm rule. | Phase 0.5 fixture harness; production query engine; early-exit provenance; fallback/refinement accounting tests. |
| V0-022 | 2026-07-19 | Policy class ratification | FROZEN | Reaffirm V0-006: ground and abstract selectors are deterministic finite-horizon Markov policies. Only `rho0`, the environment kernel, and build-time-frozen `kappa` may be stochastic. V0 forbids randomized ground policies, randomized abstract selection, query-time mixtures, and frontier convexification. A later extension must revise both comparator sides together. | Resolves Q2 and removes any residual interpretation that stochastic `kappa` is policy randomization. | Ground/abstract policy schemas; frontier construction; J0/J2 comparison; artifact validators. |
| V0-023 | 2026-07-19 | Reward normalization ratification | FROZEN | Reaffirm V0-008 for canonical rewards: `Rmax_G2048(q)=H` and `Rmax_LMB(q)=2N/3`, so normalized regret divides the ground value gap by the corresponding bound. These formulas may not be reused after changing reward-basis weights, merge/match reward, terminal bonus, or goal reward; every such query must declare and validate its own deterministic `Rmax(q)`. | Resolves Q3 and limits the scope of the canonical normalization formulas. | Query validator/normalizer registry; artifact proof; regret computation; noncanonical-reward rejection tests. |
| V0-024 | 2026-07-19 | Safe-chain exact D4 quotient | FROZEN | `g2048_select_safe_chain_2x2_v0` is the `exact_D4_orbit_quotient_certificate_baseline`. Enumerate its complete reachable state-time graph for `h in {0,1,2}` and quotient only equal-stage states by full `D4` orbits. Verify legal actions, reward, one-time failure cost, kernel, rank/spawn/failure, and terminal semantics are `D4` automorphisms. Use row-major lexicographic canonicalization (empty rank `0`) and the frozen group order `e,r,r^2,r^3,m,rm,r^2m,r^3m`, where `r` is clockwise quarter-turn, `m` is vertical-axis reflection, and `r^k m` applies `m` then `r^k`; define a semantic action as the canonical action's orbit under the canonical state's stabilizer; and freeze `kappa_x` as the uniform distribution over the **distinct**, deduplicated inverse ground-action set, never over group elements with multiplicity. The exact abstract reward/cost/transition must be representative-independent, its transition uncertainty set singleton, and all sound-envelope widths zero. The group/action-transform profile is structural/build-owned, while the reachable state-time graph, materialized orbit quotient, plan, and proof are query-scoped; `rho0/H` do not enter the structural key. This profile performs no CEGAR split: any violated exact-quotient invariant terminates with baseline-validation status `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`, not refinement or fallback. Passing it requires strict state/action graph compression and supports only a known-group exact state-action symmetry quotient/value/risk/policy-preservation claim, not automatic discovery, predicate/refinement, shared coordinates, or learning. Any future `g2048_select_safe_chain_aliased_partition_v0` is a separate refinement profile and may not replace or modify this baseline. | Resolves `V0-RISK-002` and supersedes the unresolved abstract-profile note in `markdown/GPT_followup_questions.md`; it does not alter V0-020 ground/query semantics or the original canonical Phase 0.5 split fixture. | D4 action/state transforms; reachable state-time graph; canonicalizer/stabilizer/action-orbit builder; concretizer; exact quotient/envelope; J0/lift comparison; artifacts and claim validator. |
| V0-025 | 2026-07-19 | Coverage-limited build ownership | FROZEN | `rho0` remains a `QuerySpec` field and never becomes structural environment semantics. The Phase 0.5 RAPM build receives the query's explicit positive-mass support and constructs its full transition closure under every legal action and every positive-probability successor. Its coverage descriptor is frozen as `mode=query_support_transition_closure`, `initial_support_sha256` over the canonical ordered `rho0` declaration including exact masses, `covered_state_count`, and `reuse_outside_coverage_forbidden=true`. `structural_id` excludes `rho0`; `query_id` includes the full query; and `build_id` includes `structural_id`, the complete coverage descriptor, and source identity. Thus changing `rho0` leaves `structural_id` unchanged but changes the descriptor-specific `build_id` and `query_id`; the current cache does not infer extensional equivalence between different support declarations. A candidate query must be validated against the recorded closure before planning, and any support outside it is rejected or rebuilt under a new coverage descriptor. Optional domain initial-distribution methods are named query factories only; they cannot seed a build implicitly, and `structural.json` contains no `initial_law`. | Resolves `V0-RISK-003` and narrows V0-003's reuse statement for the implemented coverage-limited V0 profile without moving query semantics into the structural key. | `QuerySpec`; `RAPMBuilder`; build/query/structural IDs; coverage validator; config/run artifacts; cache-reuse and out-of-coverage tests. |
| V0-026 | 2026-07-19 | Safe-chain aliased CEGAR positive control | FROZEN | `g2048_select_safe_chain_aliased_partition_v0` is an independent refinement **profile key**, not a new ground structural key: it reuses the `g2048_select_safe_chain_2x2_v0` kernel, canonical `D4`-uniform `H=2, delta=1/20` query, and complete 192-state query-support transition closure, while committing separate partition, grammar, semantic-adapter, build, run, and artifact hashes. Its fixed ten-cell base encoder puts every failure state in one terminal cell and maps each active state by `(empty_count, sorted nonzero rank histogram)`; this preregistered base encoder has incremental refinement rate zero but its ten leaves and all construction/accounting costs are charged. The profile uses `RefinementBudget.full_v0()`, `abstraction_source=deliberately_aliased_boundary_actions`, the deliberately non-`D4`-equivariant `canonical:first`/`canonical:last` boundary labels, and deterministic singleton `kappa`. Grammar `g2048.action_frame_geometry.v1` contains exactly `first_survivor_adjacent_nonmerged_count`, `first_pair_horizontal`, `first_survivor_row`, `first_survivor_column`, `nonmerged_row`, and `nonmerged_column`, totalized to zero when `FIRST` has no unique occupied nonmerged cell. The registered target is `first_survivor_adjacent_nonmerged_count|<=|1/2`; with one threshold and six features its incremental rate is four bits per local application. The frozen `(nominal reward, nominal failure, L_pi, U_F, normalized regret upper)` sequence is `(201/6400,5059/8000,51/3200,19999/20000,99/3200)` before refinement, `(3/64,21187/80000,3/64,5099/10000,0)` after the first split, and `(3/64,317/16000,3/64,397/20000,0)` after the second. Exact audit witness extraction and the full V0 joint candidate ranking, never a hard-coded split schedule, must select that predicate first in histogram cell `(1,1,2)` and then in `(1,2,2)`, giving `10 -> 11 -> 12` leaves and eight charged refinement bits. The second split immediately returns `CERTIFIED` with no fallback: lifted reward `3/64`, exact lifted failure `317/16000`, sound failure upper bound `397/20000 < 1/20`, and normalized regret upper bound zero at the distribution and at all eight initial support points. J0 failure remains `99/5000`; the lifted-risk gap is `1/80000` and envelope conservatism is `3/80000`. A third split of `(2,2,2)` is future tightening-only work and is forbidden in the main run after certification. Ordinary planning/refinement endings use the existing eight CEGAR statuses; malformed profile construction or replay terminates separately as `ALIASED_CEGAR_INVARIANT_VIOLATION`. Every active histogram cell happens to be one complete `D4` orbit, so the demonstrated defect is the mismatch between a coarse state cell and the order-dependent, non-equivariant boundary-action labels. The claim is only that exact counterexamples can select and apply a preregistered current-state geometry atom to repair this deliberate action/partition aliasing enough for a sound constrained certificate; it is not automatic predicate invention, state-quotient or unknown-symmetry discovery, exact risk/policy preservation, shared grammar, or learning. | Makes the future profile mentioned by V0-024 executable without changing the exact-`D4` baseline, and supersedes the nonnormative sketch in `markdown/GPT_d4_quotient_decision.md` wherever that sketch called the profile a new structural key or left its partition/action/refinement semantics open. | Aliased-profile registry and identity; action-frame feature adapter; base partition; exact witness extractor; multi-step CEGAR runner; full-V0 budget/rate accounting; iteration artifacts and independent verifier; claim filter and golden tests. |
| V0-027 | 2026-07-19 | Phase 3A true-state-alias oracle positive control | FROZEN | Contract `0.6.0` registers `phase3a_true_state_alias_oracle_control_v0` / execution profile `phase3a_true_state_alias_oracle_control` as a two-domain **construction slice**, with the exact fixtures, train/held-out split, algorithms, goldens, and acceptance rules below. It must demonstrate an active cell in which one lifted training policy graph jointly reaches states from multiple complete known-automorphism orbits, train-built RAPM reuse across the registered two-domain held-out suite, at least `5x` **active-state** compression, strict state-action compression, exact-sound certification, zero exact reward gaps, and zero exact failure gaps. Passing returns `PHASE3A_SLICE_PASS` and simultaneously `PHASE3_AGGREGATE_NOT_RUN`; malformed construction or replay returns `PHASE3A_INVARIANT_VIOLATION`. This is an exact-model/oracle upper-bound control, not the full Phase 3 Gate and not evidence of predicate invention, oracle-free unknown-quotient discovery, shared coordinates, CEGAR recovery, multiresolution planning, or scale generality. | Directly addresses V0-026's limitation that every active histogram cell was already one `D4` orbit, without upgrading the Phase 3 aggregate claim or changing any earlier profile. | Suite coverage; oracle/behavioural builders; semantic actions and lift; train/held-out registry; symmetry-nontriviality audit; J0/Jkappa/J2 rows; contract-0.6 artifacts, statuses, claim filter, and golden tests. |
| V0-028 | 2026-07-20 | Reusable world-model objective and Phase 3B portable campaign | FROZEN | Contract `0.7.0` makes the primary objective explicit: compile a coverage-bounded ground process once into an auditable RAPM, perform repeated multi-step contingent planning primarily inside that portable abstract world model, and recover ground distinctions locally only when the independent value/risk certificate cannot certify the current plan. Quotients, predicates, CEGAR, and ground solvers are construction, repair, audit, and fallback subsystems rather than the scientific endpoint. The immediate profile is `phase3b_portable_rapm_campaign_v0`: build each domain RAPM from the complete one-step reward-feature/failure/terminal/successor behaviour only, with no `Q*`, value, selected-policy, query reward/risk/horizon, or held-out evaluation signature; serialize it; then use a fresh planner process that can read only the portable RAPM and the cell-level portable projection bound to a `QuerySpec` to plan at least eight distinct registered queries across both domains, at least four per domain and at least one `H>=2` query in each domain. J0 is evaluation/fallback truth and cannot enter construction or the fresh-process planner. Passing returns `PHASE3B_PORTABLE_RAPM_PASS` together with `PHASE3_AGGREGATE_NOT_RUN`, `LOCAL_HYBRID_GATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`. It proves only no-Q/value-signature construction, portability, repeated in-coverage reuse, abstract-primary multi-step planning, and exact-sound certification on the registered campaign; it does not prove automatic predicate invention, local hybrid repair, amortized break-even, full Phase 3/5, scale, or learning. | Supersedes lower-authority framing that treated quotient discovery or CEGAR itself as the endpoint. It is additive to V0-024 through V0-027: their fixtures, goldens, statuses, and narrow historical claims remain unchanged and may not be retroactively relabelled as Phase 3B evidence. | `WorkloadSpec`; `BuildEpoch`; portable RAPM schema/loader; exact behavioural synthesizer; fresh-process planner; construction-dependency audit; route and cost accounting; Phase 3B registry, artifact bundle, verifier, claim filter, and acceptance tests. |

## V0-027 registered construction slice

The Phase 3A suite coverage mode is
`suite_support_union_transition_closure`: canonicalize the set union of positive-mass
supports from **training queries only**, hash that set without query order or masses,
and close it under every legal action and positive-probability outcome. The descriptor
also records support-state count, closure count, exact state cap, the admissibility rule
`positive_support_subset_of_covered_states`, and
`reuse_outside_coverage_forbidden=true`. Held-out queries may be released only after
the coverage, partition, semantic adapter, and RAPM identities are frozen. They may be
evaluated only when their support is contained in that coverage; changing any held-out
reward, horizon, delta, distribution, ordering, or presence cannot change construction.

The G2048 control reuses `g2048_select_safe_chain_2x2_v0`. Training contains two
queries with canonical merge reward and `delta=1/20`: the canonical rank-1
`D4`-uniform `H=2` query and the `H=1` strict cross-`D4` bridge query defined below.
Their 20-state support union closes to 192 states. Actions use the `D4`-equivariant relative-
survivor labels `TOWARD` and `AWAY`, with `kappa` uniform over distinct legal actions
carrying the selected label. An unrestricted exact ground-oracle table is computed on
the training closure for `h in {1,2}` and the training reward/risk profile. The fixed
candidate atom set is selected semantic action at `delta` and maximum normalized
reward at each horizon; exhaustive cardinality-first/canonical-ID subset selection,
followed by ordinary exact full-plan audit, must select exactly the two `h=1` atoms.
The resulting state partition has 8 cells with size multiset
`{124,16,12,8,8,8,8,8}`, hence total `192/8=24x`; the exact full-model behavioural
baseline has 10 cells. Among 68 active states, nine complete `D4` state orbits are
aggregated into seven active cells, so the gate compression is `68/7>5`; two cells cross
orbit boundaries and at least one is reached by a registered training policy. The complete
active `D4` state-action orbit count is 18, while the candidate has 14 abstract
cell-action entries; all 144 active ground state-action pairs also map into those 14.

The bridge query places mass `3/25` on each of the eight `D4` images of
`(1,1,2,0)`, mass `1/200` on each of the four images of `(2,2,2,0)`, and mass
`1/400` on each of the eight images of `(2,2,4,0)`; these masses sum to one. Its
explicit witnesses `(0,2,2,2)` and `(0,2,4,2)` are not in the same `D4` orbit, but
must occupy the same selected oracle cell, both occur on the bridge query's lifted
policy graph, and both select `AWAY`. This is the mandatory G2048 proof that the
reported active alias is a jointly policy-reachable cross-automorphism state alias.

The registered G2048 evaluation rows are:

| Split | Query key | J0 = Jkappa = lifted reward | J0 = Jkappa = lifted failure | Sound `U_F` |
|---|---|---:|---:|---:|
| train | `g2048.rank1_uniform.h2` | `3/64` | `99/5000` | `199/10000` |
| train | `g2048.strict_cross_d4_bridge.h1` | `13/400` | `199/5000` | `1/25` |
| held-out | `g2048.rank2_uniform.h2` | `3/32` | `99/5000` | `99/5000` |
| held-out | `g2048.mixed_points.h2` | `9/128` | `99/5000` | `397/20000` |
| held-out | `g2048.rank1_point.h2` | `3/64` | `99/5000` | `199/10000` |
| held-out | `g2048.rank1_uniform.h1` | `1/32` | `0` | `0` |

Here rank-2 uses the `D4` orbit of row-major board `(2,2,3,0)`, while mixed-points is
the equal mixture of `(1,1,2,0)` and `(2,2,3,0)`. Every row has exact lifted reward
lower bound equal to J0 and normalized regret upper bound zero.

The LMB control is the deterministic generated fixture
`lmb_generated_n6_t2_k3_d2_seed0_v0`, with tile types `(0,1,0,1,1,0)`, blockers
`(empty,{0},{0},empty,empty,{0})`, capacity 3, and arity 3. Its training query is uniform over
the nine registered active `(removed_mask,buffer)` pairs
`(11,(1,2)), (13,(2,1)), (19,(1,2)), (21,(2,1)), (25,(1,2)), (35,(2,1)),
(41,(2,1)), (49,(2,1)), (7,(2,1))`, with canonical match-plus-clear reward, `H=3`,
`delta=1/20`, and `Rmax=4`. This support closes to 25 states: 18 active, six failure,
and one success.

LMB construction does not inspect query values. Exact partition refinement starts from
active/failure/success status and repeatedly represents each action by its exact reward-
feature vector, one-time failure probability, termination probability, and successor-
cell distribution. Equal-signature distinct ground actions are one semantic action and
receive uniform concretizer mass. The cell-count trace is `3 -> 5 -> 5`; final cell
sizes are `{9,6,5,4,1}`, all realization envelopes are singleton, and 18 active states
become three active cells, so the gate compression is `18/3=6`; total compression is
`25/5=5`. Forty ground state-action pairs become four abstract entries. The complete
physical automorphism group has four elements: its 13 state orbits become five behavioural cells, its ten
active state orbits become three active cells, and its 16 state-action orbits become
four semantic cell-actions. In every active cell, the same lifted training policy graph
jointly reaches states from more than one physical automorphism orbit. In particular,
states `(11,(1,2))` and
`(13,(2,1))` are not automorphic but occupy the same exact behavioural cell.

The registered LMB evaluation rows are:

| Split | Query key | J0 = Jkappa = lifted reward | J0 = Jkappa = lifted failure | Sound `U_F` |
|---|---|---:|---:|---:|
| train | `lmb.alias9.canonical.h3` | `1` | `0` | `0` |
| held-out | `lmb.alias9.match_only.h3` | `1` | `0` | `0` |
| held-out | `lmb.alias9.canonical.h2` | `1/4` | `0` | `0` |

The changed match-only reward basis uses the separate deterministic bound `Rmax=2`
with proof ID `lmb.match_only.matches_le_n_over_3.v1`; it must not reuse the canonical
match-plus-clear `2N/3` proof ID. The canonical LMB rows retain `Rmax=4` and the
canonical proof.

For both domains, every registered row must have `J0=Jkappa=lifted` reward and failure,
zero action-restriction and state-alias-selector gaps independently for both reward and
failure, a complete exact audit, and a contingent deterministic Markov policy with its
frozen concretizer. The bundle must expose construction traces, the cross-automorphism
audit, coverage/RAPM reuse identities, every evaluation row, and the unsupported-claim
list. Exact-model construction may identify equivalences not supplied as a group
action; under V0-027 that fact is described only as **cross-automorphism oracle/model-
oracle state aliasing**, never as discovery of an unknown quotient.

The reuse statement is indivisible and limited to **across the registered two-domain
held-out suite**: G2048 tests changes in initial support/distribution and horizon while
holding reward basis and risk fixed; LMB tests reward-basis, horizon, and risk changes
while holding initial support fixed. It does not assert that either domain was tested
under all four change types or that arbitrary in-coverage queries preserve value.

## V0-028 registered world-model campaign

The Phase 3B execution profile is `phase3b_portable_rapm_campaign`. Its authority is a
frozen `WorkloadSpec`, not a succession of isolated query runs. The record contains a
canonical workload ID, domain/structural IDs, build-coverage seed set and closure rule,
an ordered campaign query registry, expected query count, admissible routes, normalizer
proofs, and the exact build epoch. The frozen campaign has eleven distinct ground query
IDs (six G2048, five LMB), at least eight distinct portable query IDs, at least four
distinct portable queries per domain, and an `H>=2` query in each domain.
Byte-equivalent portable projections, cache hits, J0 probes, and construction-only rows
do not count toward the portable-query threshold.

A `BuildEpoch` is the immutable external provenance tuple of structural/kernel identity,
complete coverage, reward-feature and terminal/failure registries, semantic
action/concretizer identity, behavioural-synthesis algorithm, contract/schema version,
source revision, and the resulting coverage/model IDs. One RAPM per domain is built and
frozen once and then bound by that epoch. The epoch is not embedded in the portable
model: `portable_rapm_id` is derived only from the portable RAPM payload. Changing an
epoch component creates a new epoch and pays a new build cost, but changes the model ID
only when the extensional portable payload changes. Evaluation-query order, reward
weights, risk threshold, and horizon cannot mutate either object.

The Phase 3B synthesizer starts from terminal-kind blocks and refines them to a fixed
point using the complete exact **one-step** tuple

```text
(registered reward-feature vector,
 entered-failure indicator,
 terminal/success kind,
 successor-block probability distribution)
```

for every legal ground action, with equal action behaviours deduplicated into semantic
actions and distinct-action concretizers frozen. It may inspect the exact one-step
kernel over declared coverage. It may not inspect `Q*`, a value/frontier table, selected
actions or policies, query reward weights, `delta`, `H`, held-out results, or a
value-derived signature. This is exact behavioural world-model synthesis, not learned
model induction or human predicate invention. The serialized RAPM itself carries
coverage plus `coverage_id`, a state catalog with `planning_kind`, partition, nominal
model, exact envelope, frozen concretizer, reward-feature registry,
`normalizer_rules`, and `goal_ids`. `normalizer_rules` is a nonempty proof-ID-sorted
registry. Each unique proof has `kind=nonnegative_feature_caps_v1`, a complete unique
`reward_basis` sorted by registered feature name with nonnegative rational raw weights
(including zero-weight features), and a unique feature-name-sorted cap list. Every
positive-basis-weight feature has a nonnegative rational `per_step_cap` and/or
`total_cap`; every cap record has at least one non-null value, while zero-weight
features need not have a cap record.
The no-forbidden-input evidence is builder API/data flow plus static source audits of
the behavioural builder and portable planner; it is not a closed import-DAG claim for
the entire Phase 3B runner.

After serialization, every query occurrence gets a fresh process in a bubblewrap
mount/network namespace. It sees only staged `portable.py`, `portable_planner.py`, and
`portable_runtime.py`, the current read-only RAPM/query files, system Python libraries,
and an initially empty writable output directory. The project checkout, ground kernel,
builder cache, and previous/other-domain requests are not mounted; Python starts with
`-S`, and a content-addressed runtime attestation records namespace, input,
module-origin, and output evidence. Portable query v1 binds the ground request's cell
distribution, horizon, raw and normalized rewards, normalizer/proof ID, risk, and
`default` goal. Because the schema supports only that structural stopping goal, v1
rejects every other goal rather than silently ignoring goal semantics. It constructs
the nominal abstract contingent plan without the ground kernel or a builder-owned
in-memory object. The query validator requires registered reward-feature names, a
registered `normalizer_proof_id`, nonnegative raw weights, a positive normalizer, and a
raw-weight vector exactly equal to that proof's `reward_basis`. Thus a proof ID cannot
be reused for a different reward basis. Every positive-weight feature requires a cap.
For proof `p`,

```text
B_p(q) = sum_k w_k * min({H * per_step_cap_k if present,
                           total_cap_k if present})
normalizer >= B_p(q)
normalized_weight_k = w_k / normalizer.
```

This instantiates only registered Phase 3B reward features/proofs and the v1 `default`
goal; it does not provide arbitrary reward or goal support. G2048 binds its canonical
proof to `(merge=1)`. LMB binds its canonical, match-only, and terminal-clear-only
proofs respectively to the complete bases `(match,terminal_clear)=(1,1),(1,0),(0,1)`;
the three LMB proof IDs are not interchangeable. Only after every workload
proposal is frozen does an independent exact auditor inspect the authoritative ground
kernel/envelope; J0 and lifting run on that same evaluation side. Audit/J0/lift outputs
may not flow back into construction or the portable planner.

Query routing is frozen as `ABSTRACT_CERTIFIED`, `LOCAL_GROUND_RECOVERY`,
`FULL_GROUND_FALLBACK`, `REBUILD_REQUIRED`, or `INFEASIBLE_QUERY`. The first route is
the normal route. A local route is authorized only after an abstract proposal exists
and its exact certificate fails. Its **local ground frontier** is the set of earliest
policy-reachable `(cell,h)` nodes whose reward-regret or failure proof obligation fails;
ground inspection/repair is limited to those cells and the exact successor dependencies
needed to recompute their entries. Uncovered states, changed semantics, an exhausted or
grammar-incomplete repair, or a failed same-query ground solve routes explicitly to
rebuild, charged full fallback, or infeasibility. Phase 3B records this route contract
but exercises only `ABSTRACT_CERTIFIED`; therefore it reports
`LOCAL_HYBRID_GATE_NOT_RUN` rather than claiming local repair.

Workload work is kept separate and additive. Given a preregistered scalar
`CostFunctional c` on the recorded work-counter vectors, the first `n` queries in the
frozen order obey

```text
C_world(n) = c(W_build(epoch))
             + sum_i<=n c(W_load(i) + W_abstract_plan(i) + W_audit(i)
                          + W_local_ground(i) + W_full_fallback(i))
C_ground(n) = sum_i<=n c(W_same_query_ground(i))
N_break_even = min {n>=1 : C_world(n) <= C_ground(n)}, or NOT_REACHED.
```

Evaluation-only J0 comparison work is reported separately and cannot be hidden in or
credited against either operational path. Phase 3B emits implementation-level,
noninterchangeable exact counters: build coverage, ground state/action/outcome and
refinement counts plus model bytes; per-occurrence model and query loads/bytes,
abstract composed candidates/frontier/decision nodes, portable-envelope and live
ground-certificate reachable pairs, zero local/fallback activity, and evaluation-only
J0 composed candidates, with reconciliation totals. It has no frozen `c`; therefore
scalar costs and `N_break_even` are
`null`, not `NOT_REACHED`, and it returns `WORKLOAD_ECONOMICS_GATE_NOT_RUN`. A later
economics Gate must freeze `c`, hardware, and repetition policy before opening results.

A Phase 3B pass requires portable round-trip identity, fresh-process isolation, builder
API/data-flow and static-source dependency checks, one unchanged RAPM identity per domain,
G2048 `192 -> 10` cells and `144 -> 17` state-action pairs with refinement trace
`2 -> 9 -> 10 -> 10`, LMB `25 -> 5` and `40 -> 4` with trace `3 -> 5 -> 5`,
abstract-primary planning and exact-sound
certification for every registered campaign query, and independent verification that
rebuilds both kernels/coverage/behavioural models and their authoritative G2048/LMB
normalizer registries, reprojects queries, recomputes the
portable-envelope audit and serialized-concretizer lift/live exact audit/J0, validates
IDs/cross-links/counters, and can replay the isolated planner.
The terminal status tuple is exactly
`PHASE3B_PORTABLE_RAPM_PASS/PHASE3_AGGREGATE_NOT_RUN/LOCAL_HYBRID_GATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.
This additive campaign does not alter any V0-024--V0-027 result or claim boundary.

## Implementation defaults (not new scientific claims)

These defaults select the first Phase 0.5 fixtures without changing the benchmark families: G2048 uses `g2048_select_canonical_2x2_v0` with query horizon 1; LMB starts with the smallest canonical `N=6, T=2, K=3, D=1, H=6` generated layout. The deliberately coarse LMB initializer separates terminal status and `remaining_object_count<=5/2`. The preregistered mandatory refinements are G2048 `rank_sum<=3` and LMB `action_count<=3/2`; they are domain atoms for the shared-algorithm slice, not evidence for a shared-grammar claim. A run may use another canonical tiny fixture, but its full structural parameters, initial partition, and grammar version belong in the build key and manifest. The implemented `g2048_select_safe_chain_2x2_v0` exact-known-symmetry positive control uses the V0-024 orbit quotient and no CEGAR split. The V0-026 aliased profile reuses that ground structure and query but deliberately replaces its abstraction/action profile; it is a full-V0 refinement positive control, not a retroactive replacement for either Phase 0.5 fixture or the exact-`D4` run. An individual run becomes positive-claim eligible only after its profile-specific bundle verifies.

For the canonical V0-026 replay, the two audits enumerate exactly 35 and 19 positive-gap
unordered realization pairs. Their six-feature cross-products contain 120 and 64
separating proposals and canonicalize to 16 and 10 distinct child-partition signatures.
All 26 exact provisional candidate evaluations count against the full-V0 candidate
budget; only 3 and 2 pass the 20%/new-certification quality rule. The bundle serializes
all 192 covered state values and all-action transitions, binds their kernel hash into the
build ID, and uses an acyclic dependency order from witness and candidate inventories to
accepted split, iteration record, output-stage proof, and final certificate.

## Open risks (not normative changes)

| ID | Date | Scope | Status | Finding | Normative effect | Affected interfaces and tests |
|---|---|---|---|---|---|---|
| V0-RISK-001 | 2026-07-19 | Canonical G2048 feasibility | RESOLVED | Under the frozen `2x2` conditional initial law, the initial equal rank is 1 with probability `81/82` and 2 with `1/82`. A rank-1 merge survives the post-spawn dead-end check only when rank 2 spawns in one of two adjacent empty cells, probability `(1/10)(2/3)=1/15`; a rank-2 merge cannot match the spawn. Thus first-step survival is `27/410` and failure is `383/410 ~= 0.934146`, exceeding every registered `delta`. Every `H>0` canonical primary/sensitivity query is therefore J0-infeasible. | Resolved by V0-019 through V0-021: preserve this instance as an infeasibility regression, add a separately keyed feasible safe-chain fixture, retain the mandatory split only in the Phase 0.5 harness, and short-circuit production queries whose exact infeasibility is already known. | Canonical and safe-chain G2048 golden tests; Phase 0.5 expected-status artifact; production early-exit test; experiment labels. |
| V0-RISK-002 | 2026-07-19 | Safe-chain abstract profile | RESOLVED | V0-020 froze the ground kernel, query, and J0 truth but initially left the D4-equivariant semantic-action adapter, quotient partition, and refinement profile open. The Phase 0.5 `canonical:first/last` adapter is not D4-equivariant across the orbit. | Resolved by V0-024: use the exact state-time `D4` orbit partition, stabilizer-orbit semantic actions, and distinct-inverse-action uniform concretizer; this known-symmetry profile has no CEGAR split. Positive claims still require the actual exact certificate and remain limited to the frozen claim boundary. | D4 equivariance and canonicalizer-independence tests; exact quotient construction; safe-chain certificate artifact. |
| V0-RISK-003 | 2026-07-19 | Query-owned initial support | RESOLVED | The earlier Phase 0.5 prototype exposed a domain default initial distribution, seeded transition closure from it without an explicit coverage identity, and risked making query-owned `rho0` look structural. | Resolved by V0-025 and its implementation: closure starts from explicit `QuerySpec` support, the coverage mode/support hash/count and no-outside-reuse rule enter `build_id`, structural artifacts omit `initial_law`, and out-of-coverage reuse is forbidden. The optional domain default is only a query-construction convenience. | Domain/query interfaces; enumeration/build coverage; structural/query/build hashing; cache-reuse and distribution-mutation tests. |

## Change log

- **2026-07-19 — 0.1.0:** Transcribed and closed the V0 construction contract from the Normative Decision Addendum and the V0 preconstruction audit. Added the deterministic policy-class and reward-normalization implementation clarifications needed for executable tests.
- **2026-07-19 — state-cap wording:** Aligned V0-016 with the addendum's “may not be silently truncated” rule: an explicitly incomplete, stress-only prefix with a lower bound is permitted; an apparently exact capped result is not.
- **2026-07-19 — risk note:** Recorded the exact incompatibility between canonical G2048 first-step failure probability and the frozen risk-threshold family; no normative semantics changed.
- **2026-07-19 — 0.2.0:** Incorporated the answered Normative Follow-up Decisions. Preserved the canonical infeasibility regression, froze the separately keyed safe-chain fixture and exact J0 values, limited mandatory split-after-known-infeasibility to the Phase 0.5 harness, and ratified deterministic policies and reward-normalizer scope.
- **2026-07-19 — safe-chain implementation risk:** At ledger 0.2.0, recorded that the new ground fixture did not itself choose a D4-equivariant abstract action/partition profile; V0-024 subsequently froze that profile and resolved the design gap, while actual certification remains implementation- and evidence-gated.
- **2026-07-19 — query-ownership implementation risk:** At ledger 0.3.0, recorded the prototype's implicit `rho0`-seeded coverage as an implementation conformance gap; V0-025 subsequently froze and implemented explicit coverage-limited ownership.
- **2026-07-19 — 0.3.0:** Froze the safe-chain known-symmetry positive control as an exact `D4` state-time orbit quotient with stabilizer-orbit semantic actions, a deduplicated distinct-inverse-action uniform concretizer, representative-independent point dynamics, zero-width envelopes, no CEGAR split, a dedicated invariant-violation status, and a narrow claim boundary. Resolved `V0-RISK-002`; any aliased CEGAR benchmark remains separately keyed future work.
- **2026-07-19 — 0.4.0:** Froze the implemented Phase 0.5 build as explicit query-support transition-closure coverage. Added coverage mode/support hash/count and no-outside-reuse to `build_id`, preserved query-owned `rho0` and the unrestricted structural identity boundary, and resolved `V0-RISK-003`.
- **2026-07-19 — 0.5.0:** Froze the separately keyed safe-chain aliased CEGAR positive control over the unchanged safe-chain ground structure/query: complete 192-state coverage, ten-cell histogram base partition, order-dependent boundary actions, a six-feature action-frame grammar, two auditor-selected four-bit geometry splits, exact golden bounds, immediate sound certification, zero fallback, multi-iteration artifacts, and a claim boundary that excludes automatic predicate/state/symmetry discovery and exact risk preservation.
- **2026-07-19 — 0.6.0:** Froze the Phase 3A two-domain true-state-alias oracle construction slice: train-only suite coverage and construction, held-out evaluation on unchanged RAPMs, G2048 `192 -> 8`, exact LMB behavioural `25 -> 5`, same-policy-graph joint reachability across complete known-automorphism orbits, exact audit goldens, and explicit `PHASE3_AGGREGATE_NOT_RUN`/no-predicate-invention/no-unknown-discovery boundaries.
- **2026-07-20 — 0.7.0:** Re-centred the project on one coverage-bounded auditable abstract world model used for repeated contingent planning. Froze `WorkloadSpec`, immutable `BuildEpoch`, certificate-gated route semantics, the local-ground frontier, additive workload/break-even accounting, and the two-domain no-Q/value-signature fresh-process Phase 3B portable-RAPM campaign. Preserved V0-024--V0-027 as historical positive controls with unchanged claims.
