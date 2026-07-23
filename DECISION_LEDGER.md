# V0 Decision Ledger

**Status:** normative source of truth

**Ledger version:** 1.15.0
**Last updated:** 2026-07-23

## Authority

Normative authority is, from highest to lowest:

1. this ledger;
2. the files in `specs/`;
3. the answered **Safe-Chain D4 Quotient Baseline** decision in `markdown/GPT_d4_quotient_decision.md`;
4. the answered **Normative Follow-up Decisions** in `markdown/GPT_followup_questions.md`;
5. the **Normative Decision Addendum** embedded in `markdown/GPT_question.md`;
6. the V0 normative section of `markdown/PRECONSTRUCTION_AUDIT.md` (the section beginning “二、对Codex十二个问题作唯一选择” through “七、Codex现在应该生成什么”);
7. `markdown/Roadmap.md` and later vision or positioning text.

Lower-authority text is historical context when it conflicts with a higher-authority source. A normative change requires a new dated ledger row that names what it supersedes and the affected interfaces, proofs, tests, Gates, and stored artifacts. Existing rows are never silently rewritten; spelling-only corrections may be noted in the change log.

Items 3–7 are local, Git-ignored provenance sources; the published ledger and
specifications are self-contained and remain authoritative when those local files are
absent from a public checkout.

## Frozen decisions

| ID | Date | Scope | Status | Decision | Supersedes / resolves | Affected interfaces and tests |
|---|---|---|---|---|---|---|
| V0-001 | 2026-07-19 | Authority | FROZEN | The authority order above is binding. The ledger and specifications, not chat prose, define V0. | Conflicting priority statements in planning discussions. | Documentation lint; artifact `contract_version`; every Gate. |
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
| V0-029 | 2026-07-20 | Phase 3C certificate-triggered local recovery | FROZEN | Contract `0.8.0` registers `phase3c_certificate_triggered_local_recovery_v0` / execution profile `phase3c_certificate_triggered_local_recovery`. One immutable, query-neutral eleven-cell stage-1 aliased safe-chain RAPM answers two in-coverage queries: canonical `H=1, delta=0` stays `ABSTRACT_CERTIFIED`; canonical `H=2, delta=1/20` first fails its full-plan certificate and then alone routes to `LOCAL_GROUND_RECOVERY`. Frontier extraction uses atomic selected-action `DirectBad` residuals and their proof-dependency DAG, never recursively accumulated ancestor `Bad`: the frozen frontier is the two reachable `h=1` cells with 12 states and 32 state-action pairs/128 outcomes. The strict-ancestor dependency is only the selected abstract action's concretizer support (8 pairs/32 outcomes), so total authorization is `40<48` pairs and `160<192` outcomes versus the same-query all-action graph, and `40<144` covered pairs. The isolated repair process mounts only the 32-pair frontier slice plus a redacted abstract boundary. Its unique cardinality-minimal query-owned overlay reopens only the eight-state `(empty=1,hist=((1,1),(2,2)))` cell, with 16 available local state-action pairs/64 outcomes and 8 frozen patch decisions; root and rare `(2,3)` decisions remain abstract. The base RAPM bytes/ID and `BuildEpoch` are invariant: the overlay is not a rebuild, while any base mutation is `REBUILD_REQUIRED`. Post-repair sound failure is `397/20000 < 1/20`, exact lifted failure `317/16000`, reward `3/64`, normalized regret upper zero; J0 failure `99/5000` is evaluation-only after the hybrid policy/certificate freeze. Full fallback and rebuild counts are zero. Passing returns `PHASE3C_LOCAL_RECOVERY_PASS`, `LOCAL_HYBRID_GATE_PASS`, `PHASE3_AGGREGATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`. `grammar_used=false`; this is not predicate invention, unknown-quotient discovery, economics, full Phase 3/5, scale, learning, or generality evidence. SHA-256 manifests establish artifact integrity, not public-key authenticity. | Executes the local route frozen abstractly by V0-028 while preserving every Phase 3B result and label. It resolves the ambiguity that recursively propagated root bounds could masquerade as the earliest local cause, and forbids whole-model replacement or hidden J0/fallback under a local label. | `DirectBad` proof DAG and frontier; authorized-slice/minimal-overlay schemas; isolated local runtime; hybrid stitcher/post-auditor; immutable-base and route certificates; exact counters; independent replay; coordinated-forgery tests; Phase 3C claim filter and statuses. |
| V0-030 | 2026-07-20 | Phase 3D general local-recovery Gate | FROZEN | Contract `0.9.0` registers `phase3d_general_local_recovery_v0` / execution profile `phase3d_general_local_recovery` and resolves `V0-RISK-004..006` within a precise finite scope. First, build an exact reward-min/risk-max Bellman circuit for the failed selected plan, retain every tied active extremizer, and exhaustively search ambiguity-discharge sets under a declared cap; only the current earliest `DirectBad` antichain is recoverable in one transaction. The safe-chain minimal causal family contains only the common eight-state cell: baseline `U_F=5099/10000`, deficit `4599/10000`, common singleton `397/20000`, common gain `9801/20000`; the rare singleton remains `10197/20000`, gain `1/20000`, and is excluded. Authorization shrinks from Phase 3C's `40/160` state-action/outcome records to `24/96`, of which the worker slice is `16/64`. Second, the trusted side compiles the complete four-node/twenty-realization selected-policy boundary into a worker-only `SparseRobustAffineCapability`: one cell-level input port, zero exits, one reward-min form and one risk-max form, with source graph, realization rows, identities and deletion/equivalence witnesses retained only in trusted evidence. Compilation is extensionally sufficient and representation-minimal over the fully enumerated finite admissible port domain; it does not claim an information-theoretically shortest encoding. Third, the stdlib isolated worker jointly enumerates all deterministic assignments across every authorized cell/member, aggregates each cell as `(min reward,max risk)`, Pareto-prunes only complete root points, and exhausts all lower and selected-cardinality subsets before returning a cardinality-minimal result. Every exponential enumeration has explicit caps, counters, and distinct cap-exhausted status. Safe-chain exhausts 257 assignments and reproduces reward `3/64`, sound failure `397/20000`, exact lifted failure `317/16000`, 8 patches and 12 retained abstract decisions with the base RAPM/BuildEpoch unchanged. An independent two-cell/two-member control exhausts 25 assignments, localizes both cells, and reaches `(reward,risk)=(1,1/25)` under thresholds `(3/4,1/20)` while the old independent minimum-risk rule returns value zero. Passing returns `PHASE3D_GENERAL_LOCAL_RECOVERY_PASS/GENERAL_LOCAL_RECOVERY_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`. Deeper causally dependent horizons require a full post-audit and a new occurrence-bound transaction; this is not one-shot multi-layer completeness, automatic predicate/quotient discovery, economics, full Phase 3/5, scale, learning, or cross-domain empirical generality. | Resolves the three explicit limitations left by V0-029 without relabelling its historical result or mutating its v1 schemas. | `CausalProofCircuit`; slack/active causal-family search; sparse capability compiler/evidence; cap-aware global local solver/runtime; safe-chain and algebraic trade-off controls; Phase 3D artifacts, independent verifier, attack tests, statuses and claim filter. |
| V0-031 | 2026-07-20 | Frozen Phase 3C to Phase 3D boundary | FROZEN | Phase 3D is an operational consumer of a **fully verified, frozen Phase 3C artifact bundle**, not another world-model construction run. Before planning it verifies and embeds the source run, manifest, local pre-certificate, locality, authorization, serialized RAPM and `BuildEpoch`, and binds their registries to immutable structural objects without ground transition evaluation. The source pre-certificate supplies the frozen action-unrestricted reward upper bound; the operational path may reevaluate selected-policy sound bounds but may not recompute `U_all`. Source locality/authorization also determines current authority: the 16 current frontier pair IDs are a strict subset of the source 32 frontier IDs, while the 8 reverse-dependency pair IDs exactly equal the source 8. Namespace binding may collect the complete 144-action catalogue without stepping the kernel; thereafter causal scoring, ancestor legality and capability cost use only that frozen catalogue, with no new ground-action or ground-step calls before authorization. Counters are zero for `construct_phase3c_world`, transition closure, partition, quotient and portable-RAPM construction. After abstract proof failure, authorized frontier materialization performs exactly 16 steps and the patch-restricted sound post-audit exactly 8, for 24 operational steps total, zero accounting steps and zero steps outside the authorized frontier or patched cells. `24/96` denotes authorized capability scope, not 96 re-executed outcomes. The operational post-certificate records reward lower bound `3/64`, failure upper bound `397/20000`, null exact-hybrid fields and `EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`; exact hybrid lift is forbidden there. Only the standalone independent verifier's evaluation lane may rebuild authoritative semantics, lift exactly to risk `317/16000` with 8 patched/12 retained abstract decisions, and invoke J0; none of that is operational world-model/query cost. | Additively clarifies V0-030's source boundary and closes the implementation loopholes in which a runner could rebuild Phase 3C, infer authority, recount via ground access, or perform an uncharged exact lift while reporting zero rebuild work; it preserves V0-030's historical mathematics and does not change V0-028--V0-030 results, goldens, or claim scope. | `FrozenPhase3CWorld` loader; `acfqp-phase3d --phase3c-bundle`; frozen-upper audit API; frozen action catalogue/providers; source locality/authorization and base/provenance artifacts; operational access counters; patched-audit view; null exact-field schema; forbidden-builder/transition/lift tests; byte-preservation and independent-verifier forgery tests. |

| V0-032 | 2026-07-20 | Phase 3E accounted dynamic routing | FROZEN | Contract `1.0.0` registers profile `phase3e_accounted_dynamic_routing_v0`. It keeps the reusable-world-model objective of V0-028 primary and adds a result-blind, estimate-before-execute routing contract: complete native `WorkVectorV1` accounting is distinct from the eight-axis shared `ComparisonProfileV1`; only marginal local-attempt versus direct-fallback strict componentwise dominance may select local; all identities, caps, cardinalities, uppers, decisions, work and attestations are full domain-separated SHA-256 objects; trusted replay, not worker claims, derives budgets; negative causal outcomes forbid local; actual comparison is recomputed from exact native work; host full-solver replay is removed from operational 3B/3C/3D paths; terminal class/code, retry and denominator semantics are explicit. No scalar or break-even is frozen. Until the complete registry, migrations, typed verifiers, access-order guards, all failure paths and independent replay pass, official execution remains forbidden and both workload-economics and counter-completeness Gates remain `NOT_RUN`. | Resolves Phase 3E follow-up FQ1--FQ13 and supersedes the unresolved design choices in the Phase 3E preconstruction question packet; it does not relabel contracts 0.4--0.9 or their historical artifacts. | `WorkVectorV1`; `CounterRegistryV1`; `ComparisonProfileV1`; full content-ID registry; typed route/cap/cardinality/attestation/terminal schemas; Phase 3B--3D lane migration; Phase 3E consumer runner; access-order, failure-path, replay and Gate tests. |
| V0-033 | 2026-07-21 | Phase 3E P0 accounting, continuation, executor and occurrence closure | FROZEN | The contract-`1.0.0` implementation profile gains four additive fail-closed rules. (1) Operational verification accounting is two-stage: seal an immutable common-prefix or route-execution core; freeze the exact semantic and registered nonsemantic verification obligations; materialize their operational suffix only from the bound source `CounterRecordV1` objects; and bind the reducer-correct aggregate, exact entries, attestations, manifest and receipt. Omission, padding, duplication, substitution, stale context, pre-freeze verification or evaluation-lane leakage is invalid. Terminal classification and the aggregate `WORK_VECTOR`/`ACTUAL_PROJECTION` replay it consumes are invocation-typed standalone evaluation work, so they certify a previously closed operational aggregate without recursively charging themselves into it. (2) Continuation planners may not supply authority for already executed work. The one-decision runner owns the selected-route `WORK_VECTOR` result, charges its verification once, and the occurrence controller transports that exact authority into transaction-2 or fresh-fallback authorization and the next common-prefix proof; cheaper same-shaped substitution fails. (3) The sealed profile rejects an already-instantiated route callable. A prepared decision binds an inert `ExecutorRecipeV1` and `RuntimeTreeManifestV1` content ID; only after typed route freeze may a single-use trusted factory resolve and byte-verify the preregistered runtime-tree CAS, create a private read-only lease, construct the selected executor and invoke it. Snapshot creation belongs to build/rebuild, never route preselection; live-checkout fallback, symlinks, extra files, altered bytes, foreign recipes, pre-freeze construction and reuse fail closed. (4) Every selected-route exception with one uniquely replayable native-work ownership chain is caught at occurrence scope, where all prior successful decision pairs and the exact failed common-prefix/partial-marginal pair are aggregated, replayed, and closed as one denominator-preserving `ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE` with typed terminal authority. Ambiguous mixed ownership fails closed outside this scoped closure until all-path failure accounting is implemented. The occurrence closure produces neither plan nor infeasibility credit. These four closures remove the previously listed scoped P0 implementation gaps but do not open official execution, scalar economics, or either Gate. | Additively resolves the four P0 implementation gaps recorded after V0-032 without weakening its FQ1--FQ13 rules, changing historical 0.x claims, or treating accounting infrastructure as strategic-abstraction/generalization evidence. | `phase3e_two_stage_accounting_v1`; invocation-typed semantic verification/counters; runner-owned selected-work authority and continuation adapters; `phase3e_sealed_executor_v1`; runtime-tree/recipe domain IDs; occurrence failure terminal/authority and aggregate replay; omission/padding/substitution/TOCTOU/pre-freeze/route-failure attack tests. |
| V0-034 | 2026-07-21 | Phase 3E model-only RAPM consumer and sound-audit boundary | FROZEN | Query-time control now starts from an integrity-verified Phase 3C manifest and opens only a model/query source lease: `manifest -> model-only RAPM contingent plan -> rectangular exact-sound Bellman audit`. No ground domain, state, action, kernel, concretizer, frozen-world binder, local executor, or fallback executor may be opened while that audit is being constructed and replayed. `PASS` completes the model-only stage with `ground_binding_required=false`; only a typed `FAIL` may set `ground_binding_required=true`, and even that result authorizes rather than performs later ground binding. The frozen H1 control has `(U_R,L_R,U_F,regret,delta)=(1/32,1/32,0,0,0)` and `PASS`; the H2 recovery query has `(3/64,3/64,5099/10000,0,1/20)` and `FAIL`. This corrects the prior consumer path that bound all 192 ground states before the abstract audit. Both FQ7 roles are implemented: `ABSTRACT_AUDIT` strictly replays the exact model-only source/plan/proof/audit chain without full replanning, while exact-cache replay remains deliberately weaker, plan-frozen and valid only while retaining the opaque, typed `GROUND_FALLBACK/INFEASIBLE_CERTIFIED` semantic authority from a complete search; serialized cache bytes alone are neither a planner-free early lookup nor a durable cross-process exact proof. Every new source/plan/policy/proof/audit/cache/orchestration/result content ID is assigned through the central Phase 3E domain-tag registry. Official execution, scalar economics and both Gates remain locked. | Additively repairs the query-time ordering gap left by V0-031--V0-033 and implements the first manifest-to-model-only plan/audit producer. It does not weaken V0-021's identity rule, claim durable cached infeasibility, finish the FAIL-to-route package, or prove automatic model synthesis/generalization. | `phase3e_rapm_consumer_v1`; `portable_sound_audit_v1`; `phase3e_model_only_v1`; retained-runtime `phase3e_exact_cache_v1`; FQ7 semantic verifiers; central content-domain registry; H1/H2 goldens; poisoned-ground-import/access tests; canonical replay and identity-splice attacks. |
| V0-035 | 2026-07-21 | Phase 3E verified model-first continuations | FROZEN | The V0-034 model-first boundary gains four additive, non-official continuations. (1) Ground binding is an opaque live capability opened only by retained, context-identical `ABSTRACT_AUDIT=FAIL` semantic authority; raw audit bytes, hashes, attestations, `PASS`, foreign results and foreign contexts are rejected before ground access. From that capability, the H2 selected plan and portable Bellman rows are translated directly into the Phase 3D causal estimate without replanning, rerunning the abstract auditor, calling the kernel, materializing a slice, compiling, or launching a worker; the unchanged golden authority is 16 frontier pairs, 8 strict-ancestor pairs and 24 allowed pairs. (2) H1 `PASS` can close as typed `PLAN_CERTIFICATE/ABSTRACT_CERTIFIED` only while retaining the exact `ABSTRACT_AUDIT=PASS` result and a replayable native `WorkVectorV1`; ground binding/execution is forbidden and zeros must be observed native records. (3) A fresh `python -I` producer performs the model-only plan/audit once, emits replayable native work, and the host does not replan, but its embedded blocker tuple makes it explicitly partial and non-official: abstract candidate/dominance families, global content-ID hash accounting, an honest failed-prefix route kind, sealed runtime tree/resource cap/event-trace authority, external audit authority, and complete visible mount/import-byte accounting remain incomplete. (4) A proof-derived synthetic benchmark converts a failed transaction-1 post-audit into exact failed obligations and a strictly deeper frontier, then exercises the real two-transaction occurrence state machine, distinct work vectors and reducer-correct occurrence aggregate; its cardinality/upper semantic-authority bridge is test-only, so it is not production ground-derived transaction-2 evidence. None of these changes proves automatic RAPM synthesis, unknown strategic quotient/predicate discovery, generalization, sealed production isolation, complete accounting, durable early cache, rebuild/retry, or economics. Official execution, scalar/break-even and both Gates remain locked. | Additively closes the verified `FAIL` handoff, no-replanning H2 estimate bridge, strict accounted H1 terminal boundary, and a state-machine-level dependent-transaction control left by V0-034. It narrows but does not remove the production obligations listed below. | `phase3e_ground_handoff_v1`; verified-model Phase 3D estimate bridge; `phase3e_abstract_pass_closure_v1`; `phase3e_model_only_executor_v1` and fresh isolated runtime; `phase3e_dependent_frontier_v1`; PASS/FAIL/raw-authority/foreign-context, no-replan/no-ground-access, native-work, process-failure, trace-forgery and two-transaction identity/aggregation tests. |
| V0-036 | 2026-07-21 | Phase 3E model-failure route bridge and live-authority integrity | FROZEN | V0-035 is extended without changing the reusable-world-model objective or opening an official Gate. (1) The isolated H2 failure has its own `ABSTRACT_FAILED_PREFIX` WorkVector kind and retained two-stage accounting authority. That exact prefix and the exact ground handoff are translated without replanning into the frozen Phase-3D proof/frontier, production safe-chain cardinalities, marginal uppers and strict route decision, yielding one `PreparedPhase3ERunV1` and one inert selected post-freeze factory; the nonselected route is rejection-only. Preparation remains explicitly non-official until ground-handoff, route-construction, abstract-audit event-grain and global content-hash work are natively charged, and those blocker labels may not be removed. (2) A fixed seven-role independent bundle replays only the model-failure prefix from an independently loaded Phase-3C source snapshot with a final TOCTOU recheck; it cannot claim selected-route, terminal or occurrence closure. (3) Planner-free exact-cache preflight derives structural/query/build/kernel/manifest/threshold/proof/search identities from verified sources and distinguishes `IDENTICAL_MATCH/NO_MATCH/INVALID`, but it always leaves `authorizes_infeasibility=false` until a durable kernel-bound complete-search proof payload and independent verifier exist. (4) Runtime authority is exact live capability, not a module token copied inside a frozen dataclass. Semantic/protocol results, prepared estimates, transaction/fallback/local provenance, occurrence/campaign/cache/workload handles retain an internal mint, exact member identity and replayed fingerprint; copy, replace, serialization, field substitution and cross-role reuse fail closed. These are trust-boundary and control-flow closures, not automatic RAPM synthesis, unknown strategic abstraction discovery, cross-domain generalization, counter completeness or economics. | Supersedes V0-035's obsolete statements that the honest failed-prefix kind and FAIL-to-prepared consumer were missing, and repairs a general copied-token authority flaw discovered during adversarial review. It does not erase V0-035's partial-runtime caveats or upgrade its synthetic transaction-2 control. | `phase3e_model_failure_consumer_v1`; `phase3e_bundle_v1`; planner-free `phase3e_exact_cache_v1`; prepared-estimate full-field mint and post-freeze derivative; live semantic/protocol and continuation authorities; copy/replace/cross-role/TOCTOU/identity-splice attacks; nonofficial-blocker regression tests. |
| V0-037 | 2026-07-21 | Phase 3E scoped local closure, preparation accounting and transport boundary | FROZEN | V0-036 gains four additive, non-official closures. (1) The canonical H2 model-failure preparation has an immutable native event trace with exactly 4 causal-candidate evaluations, 18 protocol checks, 3 integrity checks and 5 cap checks. Its incremental WorkVector is separate from the failed-prefix source, and its reducer-derived aggregate is retained only as post-core evidence with `occurrence_charge_status=RETAINED_POST_CORE_NOT_YET_OCCURRENCE_CHARGED`; content-ID hash invocations, I/O and accounting-materialization self-work are explicitly excluded, so neither vector may be represented as an occurrence charge. (2) The selected LOCAL execution now closes through scoped `PLAN_CERTIFICATE/LOCAL_GROUND_RECOVERY` terminal and logical-occurrence aggregation. A fixed 54-role selected-route bundle independently replays canonical bytes, role/path topology, source lease, typed IDs, preparation trace/work, route-upper arithmetic and strict selection, access/freeze order, reducer merges, selected-upper compliance, terminal and occurrence topology. Its highest claim is exactly `VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY`; transport bytes cannot mint live semantic authority or a semantic plan certificate because the local ground proof inputs and post-audit replay inputs are not serialized. (3) Bounded rebuild/new-epoch/single-retry objects and work aggregation are control-plane mechanics only; they do not prove a semantically authorized operational rebuild/retry campaign. (4) The canonical H2 transaction 1 now ends in sound `POST_AUDIT=CERTIFIED`, so the failed-post-audit prerequisite for transaction 2 is false and a real transaction 2 is unreachable on that fixture. Production transaction-2 evidence therefore requires a separately registered dependent-horizon fixture whose genuine ground post-audit fails and yields a distinct deeper frontier and fresh semantic authorities; the existing proof-derived synthetic transaction-2 remains only a state-machine control. These closures do not demonstrate automatic RAPM synthesis, unknown strategic abstraction discovery, cross-domain generalization, scalar economics or counter completeness. | Supersedes V0-036's statements that model-failure terminal/occurrence and selected-route bundle replay were wholly absent, and narrows its generic transaction-2 blocker to a fixture-design obligation. It does not remove the global hash/I/O, durable proof, semantic-transport, workload or synthesis blockers. | `phase3e_model_failure_preparation_accounting_v1`; `phase3e_model_failure_occurrence_v1`; `phase3e_selected_route_bundle_v1`; bounded rebuild/retry control objects; exact event-count/reducer/noncharging tests; fixed-role, source-splice, TOCTOU and resigned-attack bundle tests; canonical-H2 transaction-2 feasibility audit. |
| V0-038 | 2026-07-21 | Automatic feature-realized reusable LMB RAPM vertical slice | FROZEN | Register implementation profile `lmb_feature_realized_reusable_rapm_v1`. Its production API accepts exactly an exact `LMBKernel` and frozen `SuiteBuildCoverage`; it internally constructs the complete canonical eleven-feature registry and bound spec, so a caller cannot encode query bits by choosing a feature subset. Restricted registries run only through the explicit non-production negative-control API and cannot mint a production claim. Production exhausts all `2^11=2048` subsets under cap 4096, generates exact rational adjacent-value midpoint `<=` atoms, and realizes the complete exact behavioural target. The 25-state golden selects `action_count`, thresholds `3/2,5/2`, and `25 -> 5` total / `18 -> 3` active cells with singleton envelope. Registry/spec/certificate constants and independent implementation digest are frozen; parsers require canonical JSON types, runtime verification rejects nested proxy/type substitution, and independent replay rebuilds target partition/trace/adapter/model, candidate trace/tree/certificate, realized quotient and portable model/registry. Negative controls support both `TARGET_SEPARATED_FEATURE_ALIASED` and `TARGET_MERGED_FEATURE_SEPARATED`; the distinct 36-state seed-0 control has target 11/action-count 7 cells and both witness directions. One portable RAPM serves two fresh-process in-coverage QuerySpecs. This is automatic selection inside a fixed grammar under an exact ground behavioural target, not target-free/oracle-free unknown-quotient or feature invention, learning, scale/generalization, or a full Gate. All official/scalar/Gate locks remain unchanged. | Repairs the original caller-selected-registry loophole and transport/runtime/source-anchor weaknesses without changing the 25-state positive result or V0-038's exact-target-dependent claim. | `feature_synthesis.py`; canonical two-input production API; explicit negative-control API/verifier; frozen implementation digest; exact transport/runtime graph validation; bidirectional witnesses; deterministic/golden/fresh-process/attack tests. |
| V0-039 | 2026-07-21 | Direct target-free exact homomorphic LMB synthesis | FROZEN | Register construction profile `lmb_direct_exact_homomorphism_v1` with `execution_profile=production_full_grammar_v1`. Its two-input production API internally freezes the full eleven-feature state grammar and one-feature action grammar (`completes_match`) and enumerates all `2^11*2=4096` state/action-subset candidates. Construction imports neither V0-038 nor the behavioural target builder and accepts no `BehavioralActionSignature`, behavioural quotient target, QuerySpec, J0, Q/value/policy, planning or held-out channel. For each candidate it directly checks label-set equality in every state cell, identical raw one-step reward/failure/termination/successor signatures before any within-label action mixture, and cross-state same-label signature equality against the exact ground kernel. Selection minimizes state-feature count, action-feature count, split count, state names, action names and partition ID. The 25-state golden returns `EXACT_DIRECT_HOMOMORPHISM`, selects state `action_count`, action `completes_match`, thresholds `3/2,5/2`, compresses total/active `25/18 -> 5/3`, emits four abstract entries and a singleton envelope. The complete trace records 4096 candidates and typed `LABEL_SET_MISMATCH`, `WITHIN_STATE_ACTION_ALIAS` and `CROSS_STATE_LABEL_DYNAMICS_MISMATCH` evidence. Restricted exact controls return `RESTRICTED_CONTROL_EXACT_FOUND` with no model/certificate; incomplete grammar returns `NO_EXACT_DIRECT_HOMOMORPHISM`; insufficient cap returns `CANDIDATE_CAP_EXHAUSTED` with `CANDIDATE_CAP_INSUFFICIENT`. Controls have a separate role-locked verifier; the production verifier rejects restricted-control provenance, incomplete canonical registries and duck-typed result objects. A fresh process still constructs after poisoning the behavioural module; evaluation-only behavioural comparison later agrees exactly. Artifacts, frozen state/action implementation digests, transport/runtime types, source imports and independent full rebuild are attacked; one unchanged portable RAPM serves two fresh-process in-coverage queries. The claim is direct exact homomorphism synthesis inside fixed human state/action grammars and exact finite coverage. It is not feature invention, partial/learned dynamics, unknown-domain/scalable discovery, held-out/cross-domain generalization or a full Phase 3/3E/economics/counter Gate. All official/scalar/Gate locks remain unchanged. | Removes V0-038's construction-time behavioural target/signature dependence for this one LMB coverage while retaining its fixed-grammar, exact-kernel scope and without relabelling V0-038 or any Phase 3E result. | `direct_feature_synthesis.py`; state/action registries and semantic adapter; direct obligation/witness/trace/certificate schemas; canonical producer and role-separated controls; independent production/control verifiers; poison-import, source-digest, transport/proxy/resign, golden, two-query and evaluation-only comparison tests. |
| V0-040 | 2026-07-22 | Non-blocking prior-guided held-out exact-audit control | FROZEN | Contract `1.3.0` registers production prior profile `source_unanimous_exact_v1`. `build_structural_hypothesis_prior_v1` derives, and never accepts from the caller, one preferred hypothesis only when every distinct source evidence record is exact and all sources name the identical V0-039 feature-subset hypothesis. Canonical sources are mask-11 and mask-13 LMB support closures; the held-out target is mask 7, with target task and coverage IDs absent from sources while the structural kernel intentionally remains shared. Broad catalogue support is metadata only (`broad_support_metadata_only=true`, `executed_candidate_schedule=false`); production audits exactly one target proposal. The proposal is not authority: only `exact_target_ground_homomorphism_audit_v1` may publish the quotient/portable RAPM. The positive control records source-offline exact calls/unique/eligible rows `14/14/14`, target `21/7/7`, one target candidate evaluation and zero interactions; fixes `global_minimality_verified=false`; and reuses one target RAPM for two in-coverage queries. `nonproduction_external_control_v1` is role-separated; its empty hypothesis records `3/3/7`, returns `PRIOR_MISMATCH_FALLBACK_REQUIRED`, publishes no model/certificate and never claims infeasibility. Production/control profile renaming, leakage, tampering, duck types and coherent re-signing fail independent rebuild. This is proposal-versus-certificate authority and telemetry evidence only, not learned ranking, an executed wide tail, sample reduction, feature invention, minimality or transfer/generalization. `SAMPLE_EFFICIENCY_GATE_NOT_RUN` is explicitly non-blocking (`sample_efficiency_gate_blocks_mainline=false`); all prior official/scalar/economics/counter locks remain unchanged. | Adds the user's sample-tax concern as a non-blocking authority/telemetry sidecar without delaying the main construction path or pretending that V0-040 implements the future tax-reduction operator. | `prior_guided_discovery_v1.py`; `SAMPLE_EFFICIENCY_PROTOCOL.md`; source/prior/proposal/audit/accounting/certificate/result schemas; production/control builders, runners and verifiers; source-unanimity, coverage-leakage, mismatch, counter, transport and re-sign attacks. |
| V0-041 | 2026-07-22 | Generated typed-coordinate exact LMB synthesis | FROZEN | Contract `1.4.0` registers `lmb_structural_typed_expression_dsl_v1`. The two-input production API accepts only exact `LMBKernel` and frozen `SuiteBuildCoverage`, with no QuerySpec, reward weights, behavioural target/signature, J0, Q/value/policy, held-out data or caller-selected feature subset. From raw LMB primitives and fixed typed production templates it canonically instantiates exactly eight state and four state-action expression ASTs; the module/registry contains neither V0-039 named feature `action_count` nor `completes_match`. Production exhausts all `2^8*2^4=4096` subset candidates and applies direct exact label-set, pre-mixture action-alias and cross-state same-label dynamics obligations. The canonical result `EXACT_GENERATED_HOMOMORPHISM` selects `cardinality(legal_actions)` and `buffer_at_type(buffer_counts,selected_tile_type)`, thresholds `3/2,5/2`, compresses total/active `25/18 -> 5/3`, emits four singleton entries and one portable RAPM. Typed ASTs, registry/spec, trace, evaluator/enumerator/compiler/audit digests and certificate are content-addressed and independently rebuilt. The cap-one control evaluates zero of 4096; the state-only control evaluates 256 and returns no exact model; neither publishes a certificate. This advances the mainline from named coordinates to generated programs inside a fixed human DSL, but retains full exact dynamics and finite coverage and proves neither unknown-semantic invention, partial/learned dynamics, scale/generalization nor sample efficiency. Official execution remains false; scalar/break-even null; workload-economics, counter-completeness and sample-efficiency Gates remain `NOT_RUN`, with the last non-blocking. | Removes the V0-039 named-feature input for this exact finite LMB slice while preserving its direct homomorphism authority and every earlier claim boundary. | `generated_coordinate_synthesis_v1.py`; typed expression/registry/spec/tree/witness/trace/certificate schemas; generated semantic adapter; complete 4096 search; independent verifier; API/source, AST/type, cap/no-exact, trace/content/digest attacks. |

| V0-042 | 2026-07-22 | Query-neutral observation-log partial RAPM | FROZEN | Contract `1.5.0` registers profile `lmb_deterministic_observation_partial_rapm_v0`. Production constructor and verifier accept exactly an immutable `ObservationLogManifestV1`, frozen `FrozenCoordinateProposalV1`, deterministic/stationary `DeterministicObservationProfileV1`, and `PreregisteredObservationAuthorityV1`; they receive no kernel or QuerySpec. The external trust-root allowlist contains canonical authority ID `5aac3e8f1e7b8b2af4cafe50a8b54c25c21008d2b9fccd4aaaeebc3ab79df825`, which binds the exact structural/environment/profile/acquisition coverage, eight literal registered states, eleven complete legal rows/action catalogues, seven event receipts/observations, log and twenty-cell evidence ledger before query registration. Only `offline_source/OFFLINE_LOGGED_OBSERVATION=7`; all other nineteen lane/class cells are native zero. Seven ground rows are observed deterministic singletons and four remain unit-unknown. The Portable model internally reconstructs cell/state/action links, state-action-derived ground-row IDs, complete concretizer and realization coverage, observed/missing partitions, and exact concretizer-weighted realization ambiguity; V0-042 concretizers are uniform over distinct ground actions and semantic reward/destination names are unique. Every ambiguity carries joint continuation/terminal-success/terminal-failure atoms with `continuation+terminal=1`, `failure<=terminal`, no independent marginal-box interpretation, active-cells-plus-external continuation scope, and nonaliasing active/nonterminal/nonfailure external successors. The model binds `semantics_horizon_cap=6`, claims neither transition closure nor exact quotient, and requires outside-catalogue support or excess horizon to rebuild/fallback. Acquisition and construction QuerySpec inputs are separately zero; construction exact-kernel/generative/synthetic counts are zero. This is conditional, in-memory exact-graph authority (`in_memory_exact_graph_required=true`, `transport_authority_claimed=false`): hashes prove integrity/binding, while observer honesty, catalogue completeness, stationarity and public authenticity remain external assumptions. Coordinates remain manually preregistered `legal_action_count`/`completes_match`; this result is not automatic coordinate synthesis, a planner/plan certificate, infeasibility proof, learned model, generalization/sample-efficiency result, or an aggregate/official/economics/counter Gate. `SAMPLE_EFFICIENCY_GATE_NOT_RUN` remains non-blocking and every prior lock remains unchanged. | Removes V0-041's construction-time exact-kernel requirement only for this conditional partial-model build, without promoting observations or content hashes to endogenous truth and without changing any exact V0-038--V0-041 claim. | `observation_partial_rapm_v1.py`; acquisition/authority/log/profile/evidence/ambiguity/Portable-build schemas; four-input builder/verifier; exact nested-type and source-graph reconstruction; literal no-kernel fixture; catalogue deletion/fabrication/replay/relabel/external-alias/duck/re-sign/realization-only/nonuniform/duplicate-name attacks; 7-observed/4-missing joint-simplex goldens. |
| V0-043 | 2026-07-22 | Conditional robust audit of a supplied partial-RAPM plan | FROZEN | Contract `1.6.0` registers implementation schema `1.1.0` and profile `partial_fixed_plan_robust_audit_v0`. The auditor first independently reconstructs the exact allowlisted V0-042 source graph/model, then consumes content-addressed query thresholds and one externally supplied deterministic finite-horizon contingent abstract plan; it has no kernel, transition API, ground solver, planner, J0 or feasibility oracle. The plan covers every active cell at each contiguous stage and obeys `H<=6`. Canonical return proof `6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98` binds the canonical LMB `N=6` structural/environment/log/semantics/observation-authority/acquisition-manifest identities, exact weights `match=1,terminal_clear=1`, at most two matches plus terminal-clear bonus upper two, and `R_max=4`; it is not derived from the selected model/partition. Normalized-regret tolerance is restricted to `{0,1/20}`, risk tolerance to `{0,1/20,1/10}`, and `rho0` consists of exact registered active ground states. The unrestricted comparator is only an upper bound built from every registered ground-action row. Fixed-plan Bellman replay charges the joint unknown simplex once, requires pointwise regret at every initial support state, distributional risk, and no reachable unknown/external continuation with remaining horizon above one. The normal outcomes are exactly `CERTIFIED_FIXED_PLAN` or `FAILED_PROOF_FRONTIER`; the latter carries an earliest `NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1`, never infeasibility, local-recovery authority or causal necessity/sufficiency. `unresolved_exposure_sum` and per-destination reachability uppers are not probabilities. The H3 observed-path control has unrestricted upper `4`, plan reward interval `[4,4]`, maximum support regret `0`, failure `0`, 33 unrestricted proof rows and certifies despite unrelated missing rows. The H1 missing-state negative regression has unrestricted upper `3`, plan lower `0`, normalized regret `3/4`, failure upper `1` and earliest `(t=0,h=1,UNRESOLVED_POLICY_PATH_DISTINCTION)` frontier. Low-mass pointwise-regret, external-escape and known-threshold negative regressions must also fail certification. Malformed, stale, self-signed, duck-typed or coherently re-signed source/proof/plan/result objects terminate as `PartialSoundAuditInvariantViolation`, not as a normal negative regression. The certificate is conditional on V0-042's external in-memory trust root and proves only the supplied fixed plan, not planning, optimality, infeasibility, repair authorization, exactness/closure, learning/generalization, sample saving, official execution or any Gate. All existing official/scalar/economics/counter/sample locks remain unchanged. | Adds the first model-only robust audit consumer for the V0-042 partial RAPM without changing V0-042 construction or claiming that a planner or local-recovery route exists. | `partial_sound_audit_v1.py`; thresholds/return-proof/plan/obligation/unrestricted-upper/bounds/support-regret/certificate/frontier/result schemas; source-first audit and exact verifier replay; positive, negative-regression and invariant-violation tests. |
| V0-044 | 2026-07-22 | Bounded partial-model contingent-plan proposal | FROZEN | Contract `1.7.0` registers implementation schema `1.0.0` and profile `partial_model_contingent_plan_proposal_v0`. The six-input producer first reconstructs the complete V0-042 source/model, then reads one V0-043 threshold object; the verifier adds only the claimed result. Production exposes no kernel, transition callback/interface, J0, ground solver, feasibility oracle, second query or caller cap. For per-stage assignment count `S=product_z |Abar(z)|`, it enumerates all `S^H` deterministic complete plans under fixed cap 65536 and internally audits each with V0-043. Selection is hierarchical: candidates whose internal V0-043 replay returns `CERTIFIED_FIXED_PLAN` maximize reward lower then minimize failure upper then plan ID; if none, risk-feasible candidates use the same order; otherwise minimize failure upper then maximize reward lower then plan ID. This tier is only an internal proposal-ranking signal. The proposal is never certificate authority and the selected plan always requires independent V0-043 audit; feasible, infeasible-query and optimal-ground-policy claims remain false. Production cap-profile ID is `9176c40aec0b6ecb3c7645a61363cefa32d9d13396ab33ee70fb0238f171932b`. Over-cap returns `CAP_EXHAUSTED` after one source reconstruction and exact count but before candidate work, with zero evaluations/audits, empty summaries, `NOT_APPLICABLE` selection and no plan. The private caller-cap path is a named nonproduction control rejected by the public verifier. H3 freezes `S=2`, `8/8` candidates, 8 audits, 9 source reconstructions, tier-1 selection, selected plan ID `1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc`, reward `4/4`, failure `0/0` and matching independent V0-043 certificate. H1 reuses the same model/build with distinct threshold/result IDs, enumerates two candidates, selects minimum-risk fallback with reward `0/3`, failure upper 1 and a nonauthorizing unresolved V0-043 frontier. The cap-4 control predicts eight candidates but audits zero. Trace work counts are finite model-work/sample-tax telemetry, not interactions, samples, savings or economics; external-transition and ground-search calls remain zero. This is bounded abstract proposal, not certificate/feasibility/infeasibility/J0/ground optimality, exact closure/quotient, coordinate invention, causal/local/fallback authority, learning/generalization/scale, sample saving/economics, official execution or any Gate. All locks remain unchanged. | Closes the finite partial-model plan-producer gap left after V0-043 without changing V0-042 construction or transferring V0-043 certificate authority into the producer. | `partial_model_planner_v1.py`; action-domain/candidate-summary/trace/result/cap-profile artifacts; production proposer and full-replay verifier; tier/tie-break, H3/H1/two-query/cap, source-first/API/import, content/duck/re-sign and authority-boundary tests. |
| V0-045 | 2026-07-22 | Observation-only typed-coordinate partial RAPM and typed consumer chain | FROZEN | Contract `1.8.0` registers `lmb_query_free_observed_typed_coordinate_synthesis_v0`. Its three-input producer and four-input verifier consume only the exact allowlisted V0-042 log/profile/authority. A closed observation-only evaluator materializes all eight state and four action AST values over eight states and eleven legal rows, exhausts all `4096` subset candidates, uses only seven observed rows for congruence, preserves four missing rows as unknown, and selects `cardinality(legal_actions)` plus `buffer_at_type(buffer_counts,selected_tile_type)`. The integer action coordinate compiles to boolean atom `<=3/2`; the existing nonempty `tuple[bool,...]` `PartialSemanticActionV1` schema is unchanged. The selected model has six total/four active cells, five abstract entries/actions, six realizations, seven point rows and one four-row `UNOBSERVED_UNKNOWN` entry. `FrozenTypedCoordinateValueTableV2`, `FrozenTypedCoordinateProposalV2` and the V2 pure builder are internal deterministic derivation objects, not independent authority; only full `ObservedTypedPartialRAPMResultV1` reconstruction may authorize a consumer. The typed V0-044 path replays V0-045 once, freezes the verified model, enumerates/audits all plans without repeating source synthesis per candidate, and remains proposal-only. Independent typed V0-043 replay is the sole plan-certificate authority and explicitly binds synthesis-result/certificate, proposal, build, model, thresholds and plan. H3 enumerates `8/8` plans and independently certifies reward `4`, failure `0`; H1 enumerates two, returns reward `[0,3]`, failure upper one and a nonauthorizing unresolved frontier. This is fixed-DSL discovery over already-symbolized logged states/actions, not raw symbolization, unknown-DSL invention, neural/learned latent dynamics, exact quotient, statistical consistency, generalization, sample saving or an aggregate Gate. The next Gate is separately authorized minimal query-local evidence, immutable versioned overlay/refinement, replan/re-audit and promotion checks. Every official/scalar/economics/counter/sample lock remains unchanged. | Replaces the former “V0-045 not implemented” frontier and connects observation-only construction to typed V0-044/V0-043 consumers without changing historical manual V0-042--V0-044 artifacts or transferring certificate authority into the pure builder or planner. | `observed_typed_coordinate_synthesis_v1.py`; V2 typed table/proposal/builder extension; typed planner/audit wrappers; full 4096 replay; V1-schema, source/digest, missing/availability, H3/H1 and authority-boundary regressions. |
| V0-046 | 2026-07-22 | Certificate-triggered query-local exact-row refinement | FROZEN | Contract `1.9.0` registers `lmb_h1_query_local_exact_row_refinement_v0`. The producer requires the complete V0-045 result, canonical H1 typed V0-044 proposal/selected plan, and independently failed typed V0-043 result; a bare frontier cannot authorize access. Under fixed H1, `delta=0`, fixed plan/concretizer and row-completion evidence semantics, the one reachable obligation contains four missing rows of weight `1/4`; every leave-one-out failure upper is `1/4>0`, so the separate authority requests exactly four rows with zero preparation kernel/search calls and no global-minimum claim. The frozen exact LMB executor validates kernel source/configuration and all legal-action catalogues before exactly four authorized operational transition calls and zero extra-row access. All four outcomes are reward/failure/terminal zero, with one registered and three external successors. The V0-045 base stays byte-identical; a new query-owned `QueryScopedPartialRAPMV2` changes observed/missing coverage `7/4 -> 11/0`, remains non-query-neutral/non-promotable/non-closed/non-exact, and binds the complete failure/evidence chain. Rebased abstract planning enumerates/audits two plans with zero further kernel calls; independent audit certifies reward/failure/regret `0/0/0`. Promotion remains `RETAIN_QUERY_LOCAL_OVERLAY_ONLY`. Full independent replay is byte-identical. This is only an H1 row-completion positive control, not general causal minimality, multi-step recovery, learned acquisition/dynamics, base promotion, generalization, scale, economics or sample saving; all aggregate locks remain unchanged and sample efficiency remains non-blocking. | Closes the immediate Gate left by V0-045 without mutating or relabelling the reusable base and without turning the nonauthorizing V0-043 frontier into authority. | `query_local_refinement_v1.py`; `QueryScopedPartialRAPMV2`; typed audit union; exact row-necessity/request/evidence/overlay/rebase/planner/audit/promotion/result artifacts; canonical H1 and full-replay regressions; `specs/QUERY_LOCAL_EVIDENCE_REFINEMENT.md`. |
| V0-047 | 2026-07-22 | Multi-step query-local RAPM evolution | FROZEN | Contract `1.10.0` registers `lmb_h2_multistep_query_local_exact_refinement_v0`. The runner requires the full V0-045 result, canonical H2 typed V0-044 proposal/selected plan, independently failed V0-043 audit, and exact canonical LMB kernel; callers cannot supply row/state lists, caps, alternate frontiers, solvers, target plans or promotion choices. Round one derives four equal-exposure rows with zero preparation ground access and executes exactly four transitions, exposing one registered and three external active states. Boundary expansion derives those three states from evidence, makes exactly three direct complete action-catalogue calls, registers nine rows with zero transition replay/search, and reevaluates the exact V0-045 coordinates; every new state reuses signature `(3,)` and labels `(False,)/(True,)`. The first immutable query-owned `QueryScopedPartialRAPMV3` has `11/9` observed/missing rows. Four-plan model-only replanning plus independent audit moves the frontier from `time 0,h=2` to `time 1,h=1`. Exact numeric ties use frozen semantic-schedule ordering before plan ID. Round two preserves `3 selected-plan risk / 9 unrestricted value / 9 distinct` roles and executes exactly nine transitions, yielding three safe one-match and six terminal-failure rows. The final V3 epoch binds its predecessor, has `20/0` registered coverage and cumulative 13 transition calls; four-plan model-only replanning and independent audit certify reward/failure/regret `1/0/0`, with zero planner/auditor kernel and direct-ground-optimizer calls. The V0-045 base remains byte-identical; V3 remains non-query-neutral, nonpromotable, non-exact and not globally transition-closed. This proves a two-round within-query refinement loop, not general causal minimality, cross-query promotion, learned/statistical dynamics, generalization, economics or sample saving. All aggregate locks remain unchanged and sample efficiency remains non-blocking. | Closes the immediate multi-step Gate left by V0-046 while preserving its H1 artifact and the V0-045 reusable base. It creates a measured acquisition trace for, but does not implement or justify, a future sample-tax operator/meta-prior. | `multistep_query_refinement_v1.py`; `QueryScopedPartialRAPMV3`; typed audit union; two evidence rounds, boundary expansion, semantic tie rule, V3 model epochs, planner/audit/telemetry/result artifacts; omission/role/promotion/full-replay regressions; `specs/MULTISTEP_QUERY_LOCAL_REFINEMENT.md`. |
| V0-048 | 2026-07-22 | Preregistered cross-query promotion and held-out reuse | FROZEN | Contract `1.11.0` registers `lmb_preregistered_h1_cross_query_promotion_v0`. Before any V0-047 result or kernel is supplied, the protocol freezes a distinct H1 target at LMB state `removed_mask=11,buffer=(1,2)`, absent from V0-045 and distinct from the H2 source; the frozen source runner has no target/protocol input. Promotion independently replays the complete V0-047 chain and selects all 20 final rows, 13 exact evidence records and three boundary catalogues with zero target filtering. A separate `PreregisteredReusablePartialRAPMV4` preserves nonneutral acquisition provenance, authorizes reuse only for the target state/horizon cap one, and leaves V0-045 byte-identical; unrestricted reuse, closure and exact-quotient claims remain false. The kernel-free held-out consumer enumerates/audits two plans and certifies reward/failure/regret `1/0/0` with zero warm target transition/catalogue/optimizer calls. An evaluation-only cold trace uses one direct catalogue and three transitions (one safe match, two failures), exactly matching promoted evidence; source `13+3`, promotion replay `13+3`, warm `0+0`, and cold `3+1` lanes remain separate. Source amortization and an end-to-end cold planner are absent, so no statistical generalization or sample-efficiency claim opens and every aggregate lock remains unchanged. | Closes the first authentic source/target-separated scoped-promotion control without relabelling query-directed acquisition as neutral or selecting only target-favourable rows. | `cross_query_promotion_v1.py`; `PreregisteredReusablePartialRAPMV4`; preregistration/protocol/eligibility/promotion/threshold/planner/audit/cold-trace/telemetry/result artifacts; target-blind API, complete-promotion, scope-escalation, method-level access, canonical-ID and full-replay tests; `specs/CROSS_QUERY_PROMOTION.md`. |
| V0-049 | 2026-07-22 | Preregistered held-out family and matched vector amortization | FROZEN | Contract `1.12.0` registers `lmb_preregistered_h1_heldout_family_amortization_v0`. Before source acquisition the protocol freezes three distinct H1 targets at LMB masks `11/19/35` and ten logical occurrences ordered `1,2,3,1,2,3,1,2,3,1`; all targets are absent from V0-045 and the source runner remains target blind. The unchanged V0-048 complete-source verifier retains all 20 final rows, 13 exact evidence records and three boundary catalogues with zero filtering, then a separate V5 epoch authorizes only the three target states and H1 while preserving nonneutral acquisition provenance. Ten kernel-free warm routes each certify reward/failure/regret `1/0/0` with `0+0` target ground work, two plan candidates and three audits. Ten source-blind cold direct planners each execute `3+1`, exhaust three actions and match the warm certificate and source evidence exactly. Source-inclusive warm `(13,3)` first componentwise dominates cold `(3N,N)` at diagnostic prefix 5; including promotion evaluation `(26,6)` moves that diagnostic relation to prefix 9. These are vector relations, not official scalar break-even or sample-efficiency results. | Closes the finite multi-occurrence scoped-reuse, source-amortization and end-to-end cold-baseline Gate left by V0-048 while exposing repeated exact certificate work as the next measured tax candidate. | `heldout_family_amortization_v1.py`; `PreregisteredReusablePartialRAPMV5`; family query/occurrence/protocol/eligibility/promotion, warm/cold pair, native work, prefix, telemetry and result artifacts; API isolation, method tracing, scope/accounting forgery, canonical-ID and full-replay tests; `specs/HELDOUT_FAMILY_AMORTIZATION.md`. |
| V0-050 | 2026-07-22 | Exact identity-bound certificate memoization | FROZEN | Contract `1.13.0` registers `lmb_identity_bound_certificate_memoization_v0`. The unchanged V0-049 workload is paired with an initially empty append-only memo arm. Each occurrence still enumerates two plans and issues two candidate-role plus one independent-selected-role audit requests. The exact semantic key binds model/source/promotion, observation authority, query, thresholds/return proof, plan, planner/tie-break, auditor implementation and role; selected certification also binds its planner result. Occurrence identity is excluded only from the semantic key and remains mandatory in each use receipt. Nine trusted misses populate, for each of three queries, two candidate-plan entries under the candidate role plus one selected-certificate entry; 21 exact hits reduce full-audit executions from 30 to nine while all 20 candidates, ten selected certificates, zero target-ground calls and matched no-reuse/cold artifacts remain unchanged. Runtime authority is owner-bound and independent verification replays all 30 append-only transitions. | Closes only the exact-repeat proof-computation Gate exposed by V0-049. Cross-identity incremental proof, persistent reuse, sample-tax reduction, total-work/economics and generalization remain open. | `certificate_memoization_v1.py`; memo semantics/key/attestation/entry/use-receipt/cache/work/prefix/execution/telemetry/control artifacts; role, invalidation, empty-cache, owner-authority, trace, canonical-ID and independent-replay tests; `specs/CERTIFICATE_MEMOIZATION.md`. |
| V0-051 | 2026-07-22 | Identity-bound incremental proof-dependency DAG | FROZEN | Contract `1.14.0` registers `lmb_identity_bound_incremental_proof_dag_v0`. Seven unique H1 contexts over the unchanged V5 model change exactly one of `rho0`, regret tolerance, or risk tolerance. Every context retains two candidate requests and one independent selected-plan certificate. Eight domain-separated nodes `U/P/C/D/E/F/G/R` expose explicit semantic facets and parent dependencies; changed descendants are re-derived and every final root is freshly query/threshold/plan/role bound. Existing V0-043 threshold-bound rows are never neutral nodes and are rematerialized only at `R`. Request-, occurrence-, and global-reset controls freeze `168/0`, `112/56`, and `62/106` compute/hit totals; only `112-62=50` avoided constructions are attributed to cross-context reuse. All 21 roots match unchanged monolithic V0-043 audits, zero target ground calls are made, append-only owner-bound execution and independent replay fail closed under dependency, identity, role, trace and cache attacks. | Closes only the registered H1 changed-query/threshold proof-factoring Gate left by V0-050. H>1 recurrence, persistent caching, sample-tax/sample-efficiency, total-work/economics, model/reward changes and generalization remain open. | `incremental_proof_dag_v1.py`; DAG semantics/registry/context/key/node/receipt/store/change-closure/work/prefix/execution/telemetry/control artifacts; exact legacy equivalence, invalidation, topology, role, source, cache, owner, canonical-ID and independent-replay tests; `specs/INCREMENTAL_PROOF_DAG.md`. |
| V0-052 | 2026-07-23 | H2 stage-local temporal proof DAG | FROZEN | Contract `1.15.0` registers schema `1.0.0`, profile `lmb_h2_stage_local_bellman_proof_dag_v0`, and status `CERTIFIED_REGISTERED_H2_STAGE_LOCAL_BELLMAN_RECURRENCE_CONTROL`. It consumes the unchanged V0-047 final query-local H2 V3 model, never the promoted V5 H1 model. Four candidate requests execute in Gray order `A0A0,A0A1,A1A1,A1A0`, followed by a role-distinct independent selected certificate for `A0A0`. Eleven slots expose `U1->U0`, `P1->P0`, `C0->C1`, `D<-(U0,P0,C0,C1)`, `E/F<-D`, `G<-(C0,C1)`, and a freshly complete-plan/request/role-bound `R` over all lower nodes. Lower identities carry only their required stage-local facets; legacy plan-/threshold-bound V0-043 rows remain at `R`. Request-reset, plan-partitioned and global controls freeze `55/0`, `45/10`, and `35/20` compute/hit totals; exactly `45-35=10` avoided constructions are attributable to cross-plan temporal reuse. | Closes only the registered frozen-model H2 stage-local recurrence control after V0-051. It is not another world-model promotion, generic H>1, cross-query/threshold/model/reward incremental proof, persistent cache, closed-loop repair, sample reduction/efficiency, economics or official execution. | `h2_temporal_incremental_proof_dag_v1.py`; H2 temporal protocol/semantics/node/receipt/cache/work/prefix/execution/control artifacts; unchanged V0-047 source reconstruction; five legacy-equivalent roots; topology/stage/plan/role/source/cache/owner attacks; canonical-ID tests; `specs/H2_TEMPORAL_PROOF_DAG.md`. |

For V0-051, the affected public interface expressly includes the content-addressed
`IncrementalProofDAGProtocolV1` and its `protocol_id`, in addition to the node,
receipt, execution, control-result and independent-verifier artifacts named above.
Its five canonical IDs are frozen in `specs/INCREMENTAL_PROOF_DAG.md`.

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

## V0-029 registered local-recovery slice

Contract `0.8.0` is additive to the Phase 3B portable campaign. It freezes one
query-neutral stage-1 aliased safe-chain base model with 11 cells, rather than rebuilding
a model for the query that needs repair. Both registered occurrences bind exactly the
same coverage, portable RAPM bytes/ID, semantic adapter, and external `BuildEpoch`:

| Query | Pre-repair route | Required outcome |
|---|---|---|
| canonical safe-chain, `H=1, delta=0` | `ABSTRACT_CERTIFIED` | no frontier, no local work |
| canonical safe-chain, `H=2, delta=1/20` | failed certificate | `LOCAL_GROUND_RECOVERY` then certified hybrid |

Let `DirectBad(pi,q)` be the reachable state-time cell nodes whose selected abstract
action has an atomic realization/envelope proof residual relevant to the failed reward
or failure obligation. A node that is uncertified only because a descendant residual
propagates into its recursively accumulated bound is not in `DirectBad`. The local
frontier is the earliest antichain of `DirectBad` in the explicit proof-dependency DAG,
not the earliest nodes of a recursively defined `Bad`. This distinction is normative:
otherwise every downstream failure would incorrectly authorize reopening the root.

For the registered `H=2` failure, the complete direct inventory and earliest antichain
are the two policy-reachable `h=1` cells with histograms `((1,1),(2,2))` and `((2,3),)`,
containing 8 and 4 states. Their ground frontier has all 32 legal state-action pairs and
128 positive-probability outcomes. Incoming root recomputation needs only the selected
abstract action's concretizer support: 8 pairs and 32 outcomes, not all 16 root actions.
Total authorization is therefore `40 < 48` pairs and `160 < 192` outcomes versus the
same query's complete all-action graph, and `40 < 144` covered pairs. It cannot extend
coverage, expose the full kernel/model, or include J0. The isolated local process mounts
only the 32-pair/128-outcome frontier slice; the 8-pair ancestor support is exposed only
through a redacted abstract boundary view. The worker's three exact inputs are an
occurrence-bound request, a sanitized frontier slice containing only opaque IDs and
Bellman branch data, and the boundary view. The latter carries the unrestricted reward
upper bound and regret/risk tolerances, so local acceptance must pass both value and
risk obligations. State/action payloads, access logs, accounting, the RAPM/kernel,
coverage and J0 are not worker inputs. Runtime evidence binds all three hashes and the
request/occurrence IDs. Base invariance is checked against the actual serialized RAPM
and `BuildEpoch` bytes, not merely a logical-object hash.

Candidate evaluation must return the unique cardinality-minimal overlay that makes the
same complete-plan certificate pass. It changes only the eight-state
`(empty=1,hist=((1,1),(2,2)))` cell, whose local view has 16 available state-action
pairs and 64 positive-probability outcome records, and freezes exactly 8 patch
decisions that use different legal ground actions across aliased reachable members. The
other four-state rare cell remains an
abstract boundary decision because its residual no longer prevents the distributional
certificate. The stitched policy also keeps the root decision abstract; consequently a
fully ground policy or a patch that merely serializes J0 cannot pass the hybrid Gate.
The overlay is occurrence/query owned and binds its base model ID; it neither mutates
nor creates a replacement `BuildEpoch` or base RAPM. A complete-model change routes to
`REBUILD_REQUIRED`.

Post-stitch independent exact-sound audit must obtain reward `3/64`, sound failure
upper `397/20000 < 1/20`, exact lifted failure `317/16000`, and normalized regret upper
zero. Only after the overlay, hybrid policy graph, and post-audit certificate freeze may
the evaluation layer compute J0 failure `99/5000`; the exact hybrid-to-J0 risk gap is
`1/80000` and envelope conservatism is `3/80000`. Local fallback/rebuild invocations are
zero. Phase 3C records exact build/load/plan/pre-audit/frontier/slice/local-plan/stitch/
post-audit/fallback/rebuild and evaluation-only J0 counters separately; it freezes no
scalar cost functional.

The independent verifier rebuilds the kernel, coverage, stage-1 base model and both
queries; checks byte/ID invariance; replans; reconstructs the failed-proof DAG,
`DirectBad` inventory and minimal authorization; reruns the isolated local process;
reconstructs the overlay and hybrid graph; repeats post-audit; and only then evaluates
J0. It also recomputes every content ID, cross-link, counter, and manifest entry.
Coordinated re-signing must not conceal a certified-to-local route mutation, missing or
non-earliest witness, under/over-authorized slice, patch outside the target cell,
conflicting action, lost abstract decision, base mutation, reused or false isolation
attestation, early J0, hidden fallback/rebuild, forged post-audit, changed query, coverage
extension, or counter mismatch. The SHA-256 manifest is a deterministic integrity
index, not a public-key provenance signature.

The success tuple is exactly
`PHASE3C_LOCAL_RECOVERY_PASS/LOCAL_HYBRID_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.
Because the repair mechanism does not invoke a predicate grammar, artifacts record
`grammar_used=false`. The slice demonstrates only certificate-triggered strict local
recovery and an abstract/ground hybrid plan over an immutable reusable world model; it
does not demonstrate predicate invention, discovery of an unknown quotient, workload
break-even, full Phase 3/5, scale, learning, or cross-domain generality.

## V0-030 registered general local-recovery Gate

Contract `0.9.0` keeps the reusable eleven-cell Phase 3C RAPM and its selected abstract
policy fixed. It changes only the proof-directed recovery transaction. The exact
Bellman circuit evaluates reward lower bounds with `min`, failure upper bounds with
`max`, and initial mass with expectation. A counterfactual discharge swaps a recoverable
node to the optimistic dual operator solely to test causal sufficiency; it is never a
final certificate. Search retains every tied extremizer and may take a zero-root-gain
intermediate step, so tied diamond branches are not lost. A cap hit returns
`SEARCH_CAP_REACHED` with no provisional authorization. The candidate set is the
earliest `DirectBad` antichain. If a descendant becomes causal after a patch, the system
must complete the full post-audit and open a new occurrence-bound transaction.

The trusted compiler symbolically eliminates every non-frontier selected-policy node.
Its worker capability contains exactly acceptance thresholds, cell-level frontier
defaults, scalar abstract exits referenced by authorized local branches, and sparse
affine root forms. Root reward is the minimum form and root failure is the maximum
form. All source nodes, roots, selected actions, realization rows, ground identities,
and minimality witnesses remain outside the worker. The compiler completely enumerates
the declared finite deterministic cell domains, folds constants, chooses a
minimum-cardinality affine-form cover, proves extensional equality on that domain, and
stores a deletion witness for every retained form/port. Form expansion, domain
assignments, form-subset search, cell policies, slice rows and rational growth are
explicitly capped and counted; incomplete work cannot carry the minimal-capability
label.

For each authorized cell subset, the isolated solver enumerates one legal deterministic
action per member, evaluates scalar exits, forms the robust cell pair by member-wise
`min/max`, and only then computes and Pareto-prunes complete root points. It examines
subsets by cardinality, exhausts every subset and assignment at the first feasible
cardinality, then selects maximum reward, minimum risk, and the canonical policy
signature. `LOCAL_RECOVERY_AUTHORIZED_EXHAUSTED` is a complete negative result only for
the mounted antichain, fixed base policy and scalar exits;
`LOCAL_RECOVERY_SEARCH_CAP_EXHAUSTED` proves neither infeasibility nor minimality.

The safe-chain positive control freezes the causal and capability reductions and the
same post-hybrid values listed in V0-030. The separate algebraic control is required
because the safe-chain optimum happens also to be minimum-risk: two equal-mass cells,
two members per cell and low/high action pairs `(0,0)` and `(1,1/25)` use reward floor
`3/4` and failure ceiling `1/20`. Only localizing both cells and selecting all four high
actions passes, while the Phase 3C independent minimum-risk rule fails value. The
independent verifier reconstructs the authoritative circuit, capability, joint search,
overlay and post-audit; content re-signing cannot replace semantic reconstruction.

## V0-031 frozen operational source boundary

The operational Phase 3D entry point is

```text
acfqp-phase3d --phase3c-bundle <verified-phase3c-bundle> --output <phase3d-bundle>
```

It first verifies the complete Phase 3C source bundle, then binds its canonical
serialized RAPM and `BuildEpoch` bytes, source `run.json`, source `manifest.json`, and
the local-query row from `audit/pre_recovery.jsonl`. It also consumes the verified
source `evaluation/locality.json` and `recovery/authorization.json`; all five provenance
documents are embedded byte-identically as `source_phase3c_*` documents beside the
source RAPM and epoch. The pre-certificate is the
content-addressed authority for the frozen action-unrestricted reward upper bound.
Phase 3D may recompute selected-policy lower/risk bounds against the frozen RAPM and may
perform its certificate-triggered local transaction, but it may not rebuild the
partition, quotient, RAPM, coverage closure, or action-unrestricted ground upper bound.

Current recovery authority is not inferred from newly opened ground dynamics. The
verified source authorization fixes the admissible identity namespace: the 16 current
causal-frontier state/action IDs must form a strict subset of the 32 source frontier
IDs, and the 8 current reverse-dependency IDs must equal the 8 source reverse-dependency
IDs exactly. The corresponding `24/96` state-action/outcome count is the authorized
capability scope: `16/64` materializable frontier scope plus `8/32` frozen reverse
dependency. It does not state that all 24 pairs or 96 outcomes are executed again.

Binding may enumerate the finite structural state/action ID namespace solely to attach
serialized IDs to registered immutable objects and collect the complete 144-action
catalogue. It never invokes `SuiteBuildCoverage.from_queries`, performs no kernel
transition, and does not infer a replacement model. After binding, causal scoring,
ancestor legality and capability costs read only that frozen catalogue: they issue no
new ground-action or ground-step call before local authorization. Only after the full
abstract-plan certificate fails may trusted code expose the exact causally authorized
slice. Materializing that 16-pair frontier performs exactly 16 ground steps and observes
64 positive-probability outcomes. The post-certificate uses a patch-restricted kernel
view and performs exactly 8 additional steps, one for each patched decision. Therefore
the operational path performs exactly 24 ground-step calls in total, zero additional
steps for accounting, and zero steps outside the authorized frontier or patched cells.

The operational post-audit certifies reward lower bound `3/64` and failure upper bound
`397/20000`. Its exact-hybrid reward/failure fields are null and its status is exactly
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`; the operational runner neither lifts
the complete hybrid policy through the ground kernel nor reports an exact retained-
abstract count. It records the overlay's 8 patch decisions but leaves
`abstract_decision_count` null. The standalone independent verifier has a separate
evaluation-only lane. It may
rebuild authoritative semantics, perform the exact lift, reproduce failure
`317/16000`, count 8 patched and 12 retained abstract decisions, and then invoke J0.
These values retain V0-030's historical mathematical result but are not operational
post-certificate work.

The Phase 3D bundle preserves the source RAPM and `BuildEpoch` byte for byte and embeds
the source run, manifest, local pre-certificate, locality and authorization documents so
their content IDs and SHA-256 links can be audited without the source directory. In
contrast, the standalone verifier deliberately rebuilds the authoritative kernel/model
and recomputes semantic results to reject a coordinated, consistently re-hashed
forgery. That verifier rebuild, including verifier-side exact lift, ground work or J0,
is an evaluation-only oracle and cannot be charged to or described as the operational
Phase 3D path.

## V0-032 accounted dynamic-routing contract

Contract `1.0.0` registers `phase3e_accounted_dynamic_routing_v0`. This profile is a
consumer of a frozen reusable RAPM and failed full-plan proof. It is not a replacement
scientific objective: repeated contingent planning must still occur primarily inside
the reusable abstract world model, and ground distinctions may be reopened only when
the current value/risk proof cannot certify the plan.

### Accounting and comparison

`WorkVectorV1` is the complete native record. It preserves route/stage provenance,
explicit observed zeroes and distinct operational, evaluation, provenance and
diagnostic lanes. Failed local, fallback, rebuild and verification work remain separate
records. Native `local.*` and `fallback.*` leaves may never be flattened merely to make
routes comparable.

Route selection uses `comparison_profile_shared_resources_v1` with exactly these axes:

| Axis | Unit | Reducer |
|---|---|---|
| `kernel_transition_calls` | calls | sum |
| `nonkernel_compute_events` | registered events | sum |
| `process_launches` | launches | sum |
| `read_bytes` | bytes | sum |
| `staged_bytes` | bytes | sum |
| `output_bytes` | bytes | sum |
| `peak_mounted_bytes` | bytes | max |
| `peak_working_bytes` | bytes | max |

Bellman, candidate, compiler, solver, audit, integrity and protocol events map with
coefficient one to `nonkernel_compute_events`; kernel-transition calls and process
launches remain separate. Byte traffic is split into read, staged and output sums,
while mounted and working bytes are separate maxima. Every operational charged leaf
maps exactly once to one additive or peak axis. Evaluation, provenance, diagnostic and
verified derived-only leaves do not enter route uppers, but remain in campaign
accounting.

At one decision point selection compares only `U_local_attempt` with
`U_direct_fallback`. Work already spent on abstract planning, the failed proof, frozen
frontier, preregistered cardinalities, upper construction and decision verification is
charged once as `common_prefix_work` and excluded from both marginal uppers. Local is
permitted only under strict componentwise dominance: local is no larger on every axis
and strictly smaller on at least one. Equality, incomparability, missing/invalid/stale
uppers, unverified cardinality or profile mismatch selects fallback. A contingent
local-plus-fallback upper is diagnostic only. Failed-local work is never rolled back;
fallback after local failure opens a new decision point and preserves both native work
records plus their derived logical-occurrence sum.

### Typed identities and budgets

New contract-1.0 content IDs are the full 64-hex-character digest
`SHA256(domain-tag || 0x00 || canonical-json)`. Canonical JSON is UTF-8 with sorted
keys, reduced rationals, schema-defined array order, no NaN/Infinity and exact field
sets. Domain tags are role-specific and include route upper, comparison profile,
counter registry, cardinality evidence, route cap, frontier, causal evidence, decision
point and transaction. Legacy truncated IDs remain historical and cannot identify a
contract-1.0 authority.

Every `RouteUpperBoundEnvelopeV1` binds preregistration, protocol, comparison profile,
counter registry, structure, query, selected plan, threshold, BuildEpoch, logical
occurrence, attempt, decision point, transaction/index, frontier, causal evidence, cap,
cardinality, formula, route/upper kind and schema version. Local upper frontier,
causal and transaction fields are required. A direct-fallback upper may use an explicit
typed `NOT_APPLICABLE` value for frontier and causal evidence, never a missing field.
Changing any bound identity invalidates the upper; an old frontier upper cannot cross a
transaction boundary.

Trusted replay derives budgets from the preregistered cap profile, unique native work
and consecutive transaction indices; `BUDGET_REMAINS` and `BUDGET_EXHAUSTED` worker
strings are untrusted. A logical occurrence permits at most two local transactions,
indexed `1,2`. The official hard caps per transaction are:

```text
causal candidates                         32
materialization ground steps              16
materialization positive outcomes         64
slice cells / members                      64 / 4096
slice actions / successor rows             65536 / 262144
cell policies / expanded forms             65536 / 65536
domain assignments / form subsets          65536 / 65536
local subset evaluations                   16
local policy assignments                   1024
root frontier points                       128
dominance comparisons                      65536
affine term evaluations                    65536
rational bits                              512
post-audit ground steps / outcomes          8 / 32
```

A tight route upper is recomputed from pre-execution cardinality, an exact integer
formula and the hard cap; the hard cap itself cannot masquerade as the tight upper. A
second transaction requires a completed failed post-audit, a different content-addressed
deeper frontier and fresh causal/cardinality/cap/upper/decision artifacts. Local cap
exhaustion forbids local and routes to fallback. Fallback cap exhaustion closes the
attempt as a noncertificate and never proves infeasibility.

`FOUND` alone permits marginal local/fallback comparison. `CAP_EXHAUSTED`,
`NO_SOUND_COVER` and `LOCAL_CAP_IMPOSSIBLE` set `local_allowed=false`, retain an
explicit reason and require fallback. No later cheap local estimate may reopen local.

### Actual work, attestations and terminal closure

The only actual-work pipeline is exact `CounterRecordV1` validation to canonical
`WorkVectorV1`, followed by the frozen `ActualProjectionProfileV1` to
`ComparisonVectorV1`. Result references must equal the objects the verifier reads and
recomputes. Actual work exceeding the selected upper on any axis is
`UPPER_BOUND_VIOLATION/PROTOCOL_FAILURE`.

A naked set of verified IDs is insufficient. `TypedVerificationAttestationV1` binds
artifact ID/schema/role, route context, structural/query/plan/threshold/epoch,
occurrence/attempt/decision/transaction, semantic verifier/profile/result, verification
work record and protocol step. Role-specific verifiers recompute cached infeasibility,
abstract audit, causal result, cardinality, upper, decision, local result, post-audit,
fallback result, work vector, actual projection and terminal classification. The same
ID cannot serve incompatible roles. Operational verification and standalone evaluation
verification have separate counter records and lanes.

Every terminal artifact has `terminal_scope`, `terminal_class` and `terminal_code`:

```text
PLAN_CERTIFICATE:
  ABSTRACT_CERTIFIED | LOCAL_GROUND_RECOVERY | FULL_GROUND_FALLBACK
INFEASIBILITY_CERTIFICATE:
  CACHED_EXACT_INFEASIBLE | FULL_GROUND_EXACT_INFEASIBLE
ATTEMPT_CLOSURE_NONCERTIFICATE:
  INTEGRITY_FAILURE | PROTOCOL_FAILURE | REBUILD_REQUIRED |
  FALLBACK_CAP_EXHAUSTED | ATTEMPT_BUDGET_EXHAUSTED
```

A complete hash chain proves byte/reference integrity, not feasibility, risk, value or
infeasibility. Every registered logical occurrence remains in closure, certification
coverage and future economics denominators. Integrity/protocol failure invalidates an
official run; a final noncertificate fails certificate coverage.

An envelope ends one route attempt, not necessarily its campaign occurrence. The V0
default forbids rebuild. An explicitly registered policy may permit one rebuild and at
most two route attempts per logical occurrence. Rebuild retains all old work, creates a
new BuildEpoch and attempt under the same occurrence, and rebinds every upper/profile/
frontier/attestation. Future economics divides by logical occurrences, not attempts,
and charges all failed local, fallback, rebuild and retry work to that occurrence.

### Counter registry, replay migration and access order

`acfqp_counter_registry_v1` is the only official registry. It contains common abstract
Bellman/audit/integrity/protocol/hash work; local causal/materialization/compiler/solver/
post-audit work; fallback state/action/kernel/outcome/Bellman work; rebuild kernel/
outcome/partition work; cap checks/rejections; process launches; read/staged/output
bytes; and mounted/working-byte peaks. Attempts, successes/failures, exit results,
serialized-byte subsets, bytes hashed and generic branch evaluations are derived-only
or non-costed and must satisfy their reconciliation equations. Every required zero is
native (`value=0`, `observed=true`, nonempty recorder ID); absence never means zero.

Operational Phase 3B/3C/3D modes remove host full solver/planner/J0 replay. Phase 3B
does not rerun the portable planner, unrestricted ground upper or J0 for operational
validation. Phase 3C/3D trust the isolated worker result subject to schema, binding,
cap replay and sound operational post-audit; any full independent reconstruction is
evaluation-only. Old bundles retain their historical claims but cannot supply official
economics actual work. Operational and evaluation work-vector IDs remain separate.

The Phase 3E consumer runner is strictly estimate-before-execute. Before freezing the
route decision it may read only the frozen RAPM/BuildEpoch, failed certificate,
selected plan, action catalogue, frontier/proof metadata, preregistered cardinalities
and cap/formula/profile registries. It may not step the kernel, enumerate ground
outcomes, materialize a slice, compile a capability, launch a route worker, stitch,
post-audit or launch fallback. All local/fallback execution counters and attributable
process launches are zero before decision freeze. A fallback-selected route has zero
local execution and no local capability/worker/stitch/audit artifacts. Any access-order
violation is `ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE` and invalidates an
official run.

No scalar is frozen. `official_scalar_cost` and `official_N_break_even` remain null;
legacy `ops+bytes/4096` cannot substitute. Vector prefix/worst-order mechanics may run,
but `worst_order_N_break_even<=20` and all scalar crossing claims remain `NOT_RUN` until
a later scalar ledger revision.

FQ1--FQ13 close the design, not the Gates. Official execution stays forbidden and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN` plus `COUNTER_COMPLETENESS_GATE_NOT_RUN` remain until
the registry covers every route/failure, no-full-replay migration, typed semantic
verification, exact projection, trusted cap replay, terminal/campaign closure,
access-order attacks and independent verification all pass.

## V0-033 Phase 3E P0 closure rules

V0-033 closes four scoped implementation boundaries in the V0-032 consumer without
changing its scientific target, eight-axis route rule, cap values, or locked Gate
state.  "Closed" below means that the named interface has a typed, replayable path;
it does not mean that all official routes, counters, hashes, terminals, or the reusable-
world-model research objective are complete.

### Non-cyclic operational accounting and evaluation replay

Every two-stage accounting instance starts from an exact `RecordedWorkV1` core. The
core is sealed as either `COMMON_PREFIX` or `ROUTE_EXECUTION`, and its context,
decision/transaction reference, route/scope/subject, profiles, WorkVector,
ComparisonVector, projection proof, and complete source-record tuple enter the core
identity. Before any charged verification executes, a `VerificationChargePlanV1`
freezes a canonical contiguous list of semantic obligations and optional registered
nonsemantic checks. Each obligation binds its role, artifact, verifier/profile,
counter-record ID, context, lane, and strictly later protocol step.

The suffix is reconstructed only from the exact authority-bearing verification
results and nonsemantic records named by that plan. The aggregate applies each
registered sum or max reducer exactly once. `VerificationChargeManifestV1` and
`VerificationChargeReceiptV1` then bind the core, plan, source records, semantic and
nonsemantic attestations, suffix, aggregate and projection identities. Missing,
duplicate, substituted, padded, pre-plan, stale-context or wrong-lane evidence is a
protocol error. A historical `>=` counter check cannot claim this rule.

If continuation-package validation stops after some operational verifier calls but
before a complete charge plan/receipt can be minted, the already observed work must
not disappear.  The only admissible occurrence evidence for that case is
`PARTIAL_ACCOUNTED_COMMON`, backed by a
`RunnerPartialCommonAccountingEvidenceV1`.  It replays the exact common core, every
available authority-bearing operational semantic result, every registered
nonsemantic `CounterRecordV1`, their context/decision-point bindings, and the
sum/max-reduced suffix and aggregate.  Empty evidence, duplicate records, overlap with
the core, unknown counter paths, a foreign registry, a wrong lane, or a stale context
is invalid.  It may occur only as the final unpaired common component of the rejected
occurrence path; using it as an earlier or route-paired successful prefix is invalid.
This object is fail-closed accounting for a rejected package; it is not a successful
`VerificationChargeReceiptV1`, does not authorize a continuation, and may not invent
or pad work that was never durably observed.

Nonsemantic verification authority is a closed typed registry, not a caller-supplied
tuple of content IDs. `ACCESS_TRACE_RECONCILIATION` replays the typed access log,
freeze, protocol profile, decision, execution and native work;
`EXECUTION_VECTOR_INTEGRITY`, `NATIVE_AGGREGATION`,
`AGGREGATE_UPPER_COMPLIANCE`, and `CONTINUATION_WORK_VECTOR_AUTHORITY` likewise replay
their concrete typed inputs. The attested evidence-ID tuple is derived only after that
replay. Every semantic and nonsemantic plan source must be disjoint from the sealed
core's CounterRecord IDs, as well as mutually unique, so one record cannot pay for both
core execution and verification suffix.

Terminal classification does not recurse into the operational cost it certifies. Its
invocation, and the aggregate `WORK_VECTOR`/`ACTUAL_PROJECTION` replay supplied to it,
use the standalone evaluation lane and the registered evaluation semantic-check
leaves. Operational route and common-prefix verifiers continue to use operational
leaves. Attestation lane, binding lane and source `CounterRecordV1` lane must agree;
changing the invocation lane changes the attestation identity.

At occurrence-result construction, the controller replays the ordered raw components
into the claimed occurrence aggregate, matches every completed run to its exact
common/marginal pair, reconstructs the local transaction list, recomputes the closure
from the final execution, and re-verifies occurrence and failed-route terminal
authority. A reordered or rehashed component list, foreign run/context, stale
transaction, relabelled closure, or carried-forward authority is invalid even when all
individual content IDs are well formed.

### Runner-owned continuation authority

The one-decision runner mints the authoritative selected-route `WORK_VECTOR` result
from its exact native execution vector and charges that original verification in the
route suffix. A transaction-2 or post-local fallback planner describes only the fresh
structural candidate and its new authorities; it cannot supply or replace prior
execution-work authority. The occurrence controller takes the exact result from the
completed runner history and treats that old result as immutable evidence rather than
recharging its old verifier invocation. The next common prefix nevertheless pays one
fresh registered `CONTINUATION_WORK_VECTOR_AUTHORITY` protocol check that verifies the
occurrence/attempt/decision/transaction and artifact binding. Any omitted check or
cheaper, foreign, stale, or same-shaped substituted vector fails continuation
authorization.

### Content-addressed post-freeze executor construction

The sealed executor profile binds `runtime_tree_id` and `executor_recipe_id` in the
prepared decision. `ExecutorRecipeV1` is serializable intent, not a callable. Runtime
files are snapshotted during build/rebuild into `RuntimeTreeCASV1`; the manifest binds
the exact sorted regular-file set, each size and SHA-256 digest. Runtime symlinks,
special or extra entries, changed bytes, foreign CAS keys and live-checkout fallback
are invalid.

Before route selection, the exact manifest and registered runtime cap profile derive
one content-addressed `RuntimeFactoryCardinalityV1`.  It freezes file count, total
bytes, canonical manifest-document bytes, and the exact factory counter-upper formula,
with `measured_before_execution=true` and
`depends_on_actual_route_work=false`.  Each sealed candidate route binds its
route-specific runtime-cardinality ID in its own cardinality-source chain, so both
compared local and fallback uppers reserve the factory's hash, integrity, protocol,
cap, read/stage, mounted and working-capacity terms before the decision freezes.  After
selection, the factory rechecks the exact selected source/upper chain.  A global hard
cap, a post-run measurement, or an unbound manifest count cannot substitute for this
source.

The registered safe-chain sealed-fallback cap is stage-reserved rather than enlarged
after execution.  Its route-wide `control.cap_checks` cap and upper are `5815`: the
manifest-derived factory owns reserve `3`, leaving worker share `5812`.  A route-wide
cap of `5812` with the same reserve leaves worker share `5809` and must preregister a
cap-rejection path; it cannot certify a successful `5815`-check execution beneath a
`5812` upper.  This additive sealed profile uses key
`phase3e_sealed_ground_fallback_route_caps_v1`, schema
`acfqp.sealed_ground_fallback_route_cap_profile.v1`, and domain
`acfqp:sealed-ground-fallback-route-cap-profile:v1`.  The historical unsealed
`reserved_route_cap_checks=0` representation continues to omit the new field and
preserves key `phase3e_ground_fallback_caps_v1`, schema
`acfqp.ground_fallback_cap_profile.v1`, domain
`acfqp:ground-fallback-cap-profile:v1`, and its prior content ID.

Only the selected route's single-use `SealedPostFreezeExecutorFactoryV1` may be
invoked, and only after a typed `RouteDecisionFreezeAttestationV1`. It replays the CAS
manifest, copies the exact bytes into a private read-only lease, mints an unforgeable
post-freeze construction grant, asks the registered trusted constructor for the
concrete executor, invokes it, and rechecks the leased tree before returning. The
unselected factory is not invoked; a preconstructed legacy callable cannot make a
sealed-profile claim.

On success, `SealedExecutorConstructionReceiptV1` binds the exact factory
`WorkVectorV1`/`ComparisonVectorV1`, its complete counter-record set, runtime/recipe/
constructor/freeze identities, and `postconstruction_access_event_log_id`.  The latter
must equal the final selected-route access log carried by the returned
`Phase3ERunResultV1`; a receipt sealed against an earlier or foreign log is invalid.
The separate execution merge proof then binds the factory and delegate native-work
sources to the returned merged route work.

On failure, the sealed profile must retain an exact two-source decomposition rather
than only a merged partial vector.  `SealedExecutorFailureMergeProofV1` binds the route
subject/kind; the factory partial WorkVector, ComparisonVector and projection proof;
either all three delegate partial IDs or three explicit typed nulls; and the merged
partial WorkVector, ComparisonVector and projection proof.  Replay applies the
registered reducers exactly, with mounted and working capacity added where factory
and delegate lifetimes coexist, then normalizes the route closure to one failed and
zero successful attempts.  `SealedExecutorFailureEvidenceV1` additionally binds the
runtime tree, recipe, cap/constructor registries, freeze, precise registered failure
stage, merge-proof ID, and `postfailure_access_event_log_id`.  Any missing component,
mixed null/ID delegate triple, changed subject, foreign stage/registry, guessed work,
or access-log mismatch fails closed.

This failure-merge rule is currently an exact in-process failed-route and occurrence
replay contract.  It does not yet create a separate FQ7 semantic role/attestation or a
manifest-level independent-verifier authority; neither may be claimed until that
remaining verifier path is implemented.

### Occurrence-scoped failed-route terminal

`Phase3ERouteExecutionFailedV1` remains route evidence, not a campaign label. The
occurrence runner catches it, preserves every prior successful common/marginal pair,
adds the exact failed common-prefix and partial route/verification aggregate, and
reconstructs one `Phase3EOccurrenceWorkAggregateV1`. A typed
`Phase3EOccurrenceFailureTerminalV1` is the selected-route-exception detail: it binds
that aggregate, the failed evidence, decision/upper/freeze/access identities,
transaction history and component counts.  The final occurrence authority is the
separate `Phase3EOccurrenceTerminalArtifactV1`, verified under
`SemanticRole.OCCURRENCE_TERMINAL`; it binds the aggregate, ordered component refs,
detail ID, runtime/recipe provenance, exact counts and all three denominators.  The same
outer artifact also covers the separately typed `FALLBACK_CAP_EXHAUSTED` occurrence
detail. Only successful full replay mints this outer terminal authority.

The selected-route-exception closure is exactly
`ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE`; the cap detail closes as
`ATTEMPT_CLOSURE_NONCERTIFICATE.FALLBACK_CAP_EXHAUSTED`. Both have
plan/infeasibility counts `0/0`, noncertificate count `1`, and remain in closure,
certification-coverage and future-economics denominators. Neither can become
`INFEASIBLE_QUERY` or a plan certificate.

These mechanisms close only the four scoped interfaces that were previously labelled
P0.  In particular, the implementation still exposes
`unassigned_postfreeze_operational_leaves=(common.hash_invocations)` and
`ALL_PATH_NATIVE_HASH_INSTRUMENTATION`: planner invocation, authority-package
construction and rejection, all route/terminal branches, serialization/I/O, and every
integrity/protocol/hash operation must eventually emit complete native records and
content-addressed evidence on success and failure.  The new runtime-cardinality,
success-receipt, failure-decomposition, and partial-common rules prevent disappearance
or substitution where evidence is already available; they do not certify an unwired
path or manufacture missing records.  `ABSTRACT_AUDIT`, identical-query cached
infeasibility, rebuild/retry, a live dependent transaction-2 benchmark, an upstream
RAPM plan/audit producer, a manifest-level independent verifier, and workload
economics also remain incomplete. Consequently the following values remain normative:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## V0-034 model-only RAPM consumer and sound-audit authority boundary

V0-034 repairs the upstream order of the Phase 3E consumer.  Query-time work now begins
by verifying the frozen Phase 3C bundle topology, manifest bytes, semantic hash,
`BuildEpoch`, portable RAPM and the registered portable query.  The admitted object is
a content-addressed read-only model/query source lease.  Planning, contingent-policy
selection, rectangular action-realization coverage, unrestricted reward-upper
recursion, selected-policy reward-lower/failure-upper recursion and audit replay all
operate on the serialized portable RAPM and query alone.

The resulting control flow is normative:

```text
verified manifest
  -> model-only RAPM/query lease
  -> selected contingent plan
  -> rectangular exact-sound Bellman proof
  -> AbstractPlanAuditV1
       PASS -> ground_binding_required=false
       FAIL -> ground_binding_required=true, but no ground binding yet
```

Before the audit outcome is frozen, this chain may not import or instantiate the ground
domain, ground states/actions, kernel, concretizer, frozen Phase 3C world binder, local
executor or fallback executor.  A `FAIL` is the first artifact that may authorize a
later ground namespace lease; it does not itself materialize a frontier, compile a
capability, run a worker, stitch a patch, post-audit a hybrid plan or invoke fallback.
This is the first implementation slice that directly enforces the project's central
sentence at the query-time boundary.  In particular, it corrects the previous helper
path that verified a manifest and then bound all 192 ground states before deciding
whether the complete abstract plan already certified.

The canonical model-only goldens are:

| Query | Nominal proposal `(reward,failure)` | Sound audit `(U_R,L_R,U_F,regret,delta)` | Outcome | Ground boundary |
|---|---:|---:|---|---|
| `g2048.safe_chain.h1.delta0.abstract_control` | `(1/32,0)` | `(1/32,1/32,0,0,0)` | `PASS` | remains closed |
| `g2048.safe_chain.h2.delta05.local_recovery` | `(3/64,21187/80000)` | `(3/64,3/64,5099/10000,0,1/20)` | `FAIL` | later binding authorized, not executed |

Both previously registered FQ7 roles are now implemented, but with different authority
strength.  `ABSTRACT_AUDIT` accepts only strict semantic replay of the exact model-only
source, selected plan, Bellman proof and audit bindings; its verifier does not rerun the
full contingent planner or open ground semantics.  `EXACT_CACHED_INFEASIBILITY` accepts
only exact identity replay against a retained, typed
`GROUND_FALLBACK/INFEASIBLE_CERTIFIED` result whose complete-search semantic authority
is still live.  The latter profile is intentionally plan-frozen because the current
route/attestation context requires a real `selected_plan_id`.  Its serialized source and
cache-proof objects are content-addressed transport, not self-sufficient authority:
losing the retained typed runtime source invalidates the lookup.  Therefore this slice
must not be described as V0-021's planner-free early cache, a durable cross-process
infeasibility proof, or a reason to invent a dummy selected plan.

All newly introduced IDs use registered central domain tags, including RAPM source
lease, selected contingent plan, portable policy binding, portable sound Bellman proof,
abstract audit, plan-frozen cache binding, verified exact-infeasibility source, cached
proof, model-only orchestration binding and model-only result.  Same JSON under another
role/domain is non-interchangeable, and model-only parent identities are constructed
byte-for-byte compatibly with the later ground binder so a `FAIL` cannot silently change
structural, query, build-epoch, manifest or portable-RAPM identity.

This slice establishes a real reusable-model-first control boundary; it does not show
that the RAPM was synthesized automatically, that unknown strategic predicates or
quotients were discovered, that the representation generalizes across domains, or that
the full Phase 3E occurrence is operationally complete.  Remaining work is explicitly:

1. run the contingent planner in an isolated, native-accounted operational lane and
   close `PASS` as a fully accounted typed `ABSTRACT_CERTIFIED` occurrence terminal;
2. transform the exact `FAIL` result into the complete ground-bound
   `PreparedPhase3ERunV1` package and execute the selected Phase 3E route;
3. add a planner-free preflight identity and durable independently replayable exact
   infeasibility source for the V0-021 early-cache rule;
4. execute a real dependent transaction-2 benchmark with a deeper frontier derived
   from the failed transaction-1 post-audit;
5. implement operational rebuild/retry and the remaining terminal branches;
6. wire all-path native hash/I/O/protocol accounting; and
7. complete the independent manifest-level full-bundle verifier.

Consequently the locked state is unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## V0-035 verified model-first continuations

V0-035 preserves the project's central direction verbatim:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

The model-only result is now connected to both legitimate continuations without
weakening that order.  On `FAIL`, opening the ground namespace requires the retained
`SemanticVerificationResultV1` for the exact `ABSTRACT_AUDIT=FAIL`, not a serialized
audit, its content ID, a detached attestation, or a caller assertion.  The authority,
model-only result, source lease, selected plan, Bellman proof, route context,
structural/query/BuildEpoch/manifest/RAPM identities and later frozen world must all
match.  `PASS`, foreign authority and spliced identity chains fail before the ground
binder is imported or called.  The resulting ground lease is deliberately opaque and
process-local.

The H2 continuation then decodes the already frozen contingent plan and translates the
portable sound-proof rows into the existing Phase 3D `AbstractPolicyAudit` boundary.
It does not rerun the portable planner or abstract auditor and, during estimate
preparation, does not call ground actions/transitions, materialize an authorized slice,
compile a capability or launch a local worker.  Causal-family/frontier construction is
therefore still a proof-metadata estimate.  It reproduces the frozen H2 root bounds
`(U_R,L_R,U_F,regret)=(3/64,3/64,5099/10000,0)`, four reachable policy-bound rows, and
the Phase 3D capability cardinalities:

```text
frontier_state_actions = 16
reverse_dependency_state_actions = 8
allowed_state_actions = 24
```

This is a verified `FAIL -> causal estimate` bridge, not yet the complete
`estimate -> PreparedPhase3ERunV1 -> selected route` production consumer.

On H1 `PASS`, a separate strict closure can emit
`PLAN_CERTIFICATE/ABSTRACT_CERTIFIED` and close the logical occurrence only when it
retains the context-identical `ABSTRACT_AUDIT=PASS` semantic result and exact native
`RecordedWorkV1`.  The official counter registry, comparison and actual-projection
profiles replay that work; route-inapplicable local, fallback and rebuild leaves are
explicit observed native zeros rather than missing values.  Ground binding and route
executors are rejection-only inputs at this boundary.  Work-vector and terminal
classification verification remain standalone evaluation work, while the occurrence
sum references the operational model-only vector.

The first native producer for that closure runs the portable planner and sound audit
once in a fresh `python -I` process and returns a canonical event trace, result and
replayable `WorkVectorV1`; the host validates transport and bindings without replanning.
This producer remains explicitly partial and non-official.  The following exact
counter-coverage blocker tuple is part of its result and may not be hidden or weakened:

```text
ABSTRACT_CANDIDATE_AND_DOMINANCE_FAMILIES_NOT_REGISTERED
CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED
FAILED_MODEL_ONLY_PREFIX_HAS_NO_DISTINCT_ROUTE_KIND
RUNTIME_TREE_AND_RESOURCE_CAP_NOT_SEALED
WORKER_EVENT_TRACE_HAS_NO_SEALED_ATTESTATION
WORKER_RESULT_REQUIRES_EXTERNAL_SEMANTIC_AUDIT_AUTHORITY
VISIBLE_RUNTIME_MOUNT_AND_IMPORT_BYTES_NOT_FULLY_ACCOUNTED
```

In particular, `python -I` is fresh-process isolation, not a claim of the sealed
runtime-tree/CAS, mount namespace, resource cap and trace-attestation contract already
required elsewhere in Phase 3E.  A sound model-only `FAIL` is preserved as a
noncertificate result and trace, but no false `ABSTRACT_ONLY_CERTIFICATE` WorkVector is
minted while the registry lacks an honest failed-prefix route kind.

Finally, the profile `phase3e_dependent_postaudit_transaction_two_v0` establishes a
proof-derived dependent-transaction regression.  Exact reward/risk/regret failure
obligations are extracted from the failed transaction-1 post-audit and content-addressed
into a distinct, deeper frontier; old-frontier upper and decision reuse are rejected.
The test executes the real occurrence runner and route executors through transaction
indices `(1,2)`, retains distinct first-failed and second-successful native WorkVectors,
and derives one reducer-correct occurrence aggregate.  The frontier selector reads only
immutable proof artifacts and rational bounds, not a kernel or J0.  However, the
synthetic cardinality and route-upper inputs still use a test-only semantic-authority
bridge.  This proves the continuation state machine and work aggregation, not a
production semantic-authority, ground-derived dependent transaction 2.

The concrete remaining official obligations are:

1. complete all-path native, content-ID hash, I/O and runtime-mounted-byte accounting,
   and replace the partial model-only process with sealed runtime-tree/cap/trace
   authority;
2. register and charge an honest model-only failed-prefix route kind before carrying its
   work into route selection;
3. produce transaction 2 from a real failed ground post-audit with production
   cardinality, upper and route-decision semantic authorities;
4. implement rebuild/retry and every remaining terminal/failure branch with full work;
5. add a planner-free preflight identity and durable independently replayable exact
   infeasibility proof;
6. connect the verified H2 estimate through `PreparedPhase3ERunV1`, route selection and
   selected execution without duplicate planning/auditing; and
7. complete the independent manifest-level full-bundle verifier.

Automatic RAPM synthesis, unknown strategic abstraction discovery and cross-domain
generalization remain subsequent scientific work after this infrastructure is honest;
this slice must not be cited as their evidence.  The lock values remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

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
| V0-RISK-004 | 2026-07-20 | General local value-risk search | RESOLVED BY V0-030 | The contract-0.8 worker proves both value and risk for the registered fixture, but selects each reopened state's deterministic action by the frozen minimum-risk/maximum-reward order. It does not yet jointly enumerate Pareto action combinations across a general multi-cell frontier, so a future instance could contain a certifiable trade-off that this solver conservatively misses. | V0-030 adds exact global deterministic assignment composition, root-only Pareto pruning, explicit caps/statuses and the two-cell/two-member trade-off regression. Completeness is limited to the mounted antichain and fixed abstract policy/exits. | `GeneralLocalSolver`; value-risk frontier composition; candidate accounting; merged-successor and trade-off tests. |
| V0-RISK-005 | 2026-07-20 | General DirectBad causal minimality | RESOLVED BY V0-030 | `DirectBad` is now restricted to Bellman residuals in the actually failed value/risk channel, and raw successor TV alone is insufficient. It does not yet propagate certificate slack or an explicit active worst-case derivation, so a large proof DAG may authorize a relevant residual that has no material contribution to the root deficit. | V0-030 adds exact slack, all tied active extremizers, inclusion-minimal causal families, cap status and inactive/rare/tied-branch regressions. One transaction is restricted to the earliest antichain; deeper recovery requires re-audit and a new transaction. | `CausalProofCircuit`; causal-family search; activation/slack witnesses; locality verifier. |
| V0-RISK-006 | 2026-07-20 | Boundary capability minimization | RESOLVED BY V0-030 | The isolated worker receives no ground identities, payloads, RAPM, kernel, coverage, J0, or accounting, but its redacted boundary still contains every selected-policy abstract realization row needed by the current exact recursion rather than a proven minimum set of handoff scalar bounds. | V0-030 replaces the worker boundary with a finite-domain-minimal sparse affine capability plus trusted equivalence/deletion evidence. The claim is representation-relative, not information-theoretic. | `SparseRobustAffineCapability`; trusted compiler; strict worker parser; scalar-exit and redaction attacks. |

## V0-036 model-failure route bridge and live-authority rule

V0-036 preserves the central objective verbatim: the reusable RAPM is the primary
planning surface, and ground distinctions are opened only after a complete
contingent plan fails its value/risk proof.  The H2 path is now:

```text
verified Phase-3C source snapshot
  -> isolated model-only plan and exact-sound audit
  -> ABSTRACT_FAILED_PREFIX with retained two-stage work authority
  -> opaque ground handoff
  -> no-replanning proof/frontier translation
  -> verified local/fallback cardinalities and uppers
  -> strict marginal route decision
  -> exactly one selected post-freeze executor factory
```

This is a real control-flow bridge, not an official accounting claim.  The
prepared consumer must retain, verbatim, the following nonempty blocker set:

```text
GROUND_HANDOFF_OPERATIONAL_WORK_NOT_NATIVE_ACCOUNTED
MODEL_FAILURE_ROUTE_PREPARATION_OPERATIONAL_WORK_NOT_NATIVE_ACCOUNTED
ABSTRACT_AUDIT_REPLAY_NOT_EVENT_GRAIN_ACCOUNTED
CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED
```

Changing that set, or setting `official_execution_allowed=true`, invalidates the
authority before route execution.  A host restriction that prevents the selected
bubblewrap worker from opening its namespace is a failed-route/noncertificate event,
not evidence that the selected route completed.

The independent H2 bundle is deliberately prefix-scoped.  Its manifest contains a
fixed role set, independently reloads the Phase-3C source bytes, rejects missing,
extra, duplicated, cross-role, symlink or traversal entries, and performs a final
source recheck.  It reports selected route, terminal and occurrence as `NOT_RUN`.
Likewise, exact-cache preflight is an identity authority only: even an identical
eight-coordinate match cannot certify infeasibility until the cache stores a durable
complete-search proof and an independent verifier replays it.

Finally, a private module token is no longer sufficient runtime authority.  Every
authority-bearing result that can open ground state, select/continue a route, classify
a terminal, retry a campaign, or seed a cache must be the exact internally minted live
instance.  The mint binds all downstream-consumed members and a canonical fingerprint;
the consumer rechecks both.  A dataclass copy that happens to retain a token, an
equal-content replacement object, an in-place mutable-document change, or a cross-role
attestation is inert.  This rule does not alter serialized artifact schemas: serialized
bytes remain evidence that a fresh verifier must replay, never a transportable live
capability.

The current unresolved official obligations are exactly the runner's published
`UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS`: all-path native hash/I/O/runtime
instrumentation, sealed model-only cap/trace authority, native model-failure route
preparation accounting, production ground-derived transaction two, rebuild/retry and
remaining terminals, model-failure terminal/occurrence closure, durable exact proof
payload/verifier, and selected-route complete-bundle replay.  The synthetic dependent
transaction remains a state-machine control only.  Automatic RAPM synthesis, unknown
strategic abstraction discovery, cross-domain generalization and learned proposals
remain later research stages rather than claims inferred from this infrastructure.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## V0-037 scoped local closure, preparation accounting and transport rule

The project objective remains verbatim:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

V0-037 closes a bounded H2 control/accounting slice; it does not claim that the
system has automatically synthesized that world model.  The exact canonical H2
preparation trace records:

```text
local.causal_candidate_evaluations = 4
common.protocol_checks = 18
common.integrity_checks = 3
control.cap_checks = 5
```

Those counts form a separate incremental native WorkVector.  Its reducer-derived
aggregate with the already observed failed prefix is retained as diagnostic/post-core
evidence.  Both objects are bound by
`occurrence_charge_status=RETAINED_POST_CORE_NOT_YET_OCCURRENCE_CHARGED`; the original
failed-prefix WorkVector remains the sealed common core.  Content-ID hash invocations,
I/O/mount work, ground-handoff construction and accounting materialization/sealing are
outside this trace.  Therefore this partial native trace neither removes the broad
V0-036 preparation blocker nor permits the incremental or aggregate WorkVector to be
inserted into the current occurrence total.

For the registered successful LOCAL path, the scoped runner now produces a typed
`PLAN_CERTIFICATE/LOCAL_GROUND_RECOVERY` terminal and a reducer-replayed logical-
occurrence aggregate.  Its independent selected-route transport has exactly 54 fixed
roles.  It reopens the Phase-3C source, validates canonical bytes and all fixed
role/schema/domain/path bindings, replays the preparation trace and native work,
recomputes cardinality-bound route uppers and strict marginal selection, verifies
access/freeze order, factory/delegate and verification-suffix merges, selected-upper
compliance, terminal topology and occurrence references, and performs final immutable
read-set checks.  Its normative success label is only:

```text
VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY
```

It must also state `semantic_certificate_status=NOT_MINTED_FROM_TRANSPORT`.  The bundle
does not serialize the complete local ground-proof inputs or the independent post-audit
ground replay needed to recreate live semantic authority.  A transport verifier may
therefore verify the terminal artifact's topology but may not mint or independently
assert its semantic plan certificate.

The bounded rebuild/new-`BuildEpoch`/single-retry path now exercises identity, attempt,
budget and reducer-correct occurrence mechanics.  It remains a control-plane profile:
it does not demonstrate a semantically authorized operational rebuild, rebuilt RAPM,
or successful retry certificate.  Likewise, the canonical H2 LOCAL transaction 1 now
ends at sound `POST_AUDIT=CERTIFIED`.  Under the frozen state machine, transaction 2 is
permitted only after a failed post-audit; it is therefore genuinely unreachable on
this fixture rather than merely unimplemented.  A production transaction-2 Gate needs
a separately registered dependent-horizon fixture that produces a real ground
post-audit failure, a distinct deeper frontier, fresh cardinality/upper authorities and
a new selected execution.  The proof-derived synthetic transaction-2 remains only a
control of state-machine and aggregation mechanics.

The remaining work still includes all-path native content-hash and I/O/runtime
instrumentation, durable exact-infeasibility proof replay, serialized semantic proof
inputs for an independent certificate verifier, a genuine dependent-horizon
transaction-2 fixture, operational rebuild semantics, the full workload and the
automatic RAPM-synthesis/generalization research program.  Therefore:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## V0-038 automatic feature-realized reusable LMB RAPM rule

V0-038 is the first narrow vertical slice that realizes the central objective through
automatic selection inside a human-readable feature language:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

The registered implementation profile is
`lmb_feature_realized_reusable_rapm_v1`.  Its public construction boundary is exactly:

```text
synthesize_lmb_feature_rapm_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage,
)
```

This production entry point internally constructs the complete canonical eleven-
feature `FeatureRegistryV1` and its coverage-bound `SynthesisSpecV1`.  It accepts no
registry/spec argument, so a caller cannot condition the production outcome on a
query bit by choosing a subset that happens to return exact versus nonexact.  Restricted
grammars are available only through
`synthesize_lmb_feature_rapm_negative_control_v1`; that explicitly non-production API
has its own verifier and cannot mint the production claim.

The frozen coverage may have been prepared from registered training queries, but no
query object crosses this synthesis boundary.  The allowed channels are the exact
one-step transition kernel, frozen structural kernel, frozen training coverage, and
registered current-state features.  The forbidden channels are `QuerySpec`, J0,
Q-values, value/frontier, policy and held-out data.  The module may not import the
planning, J0/Q/value/policy, held-out/evaluation-oracle or Phase-3A construction layers
to recover those channels indirectly.  The exact ground-model behavioural oracle
implemented by `build_exact_behavioral_quotient` is explicitly allowed and is the
realization target; V0-038 has not removed that target/signature dependence.

The canonical LMB V1 feature registry contains exactly these eleven sorted names:

```text
action_count
branching_count
buffer_occupancy
capacity_slack
capacity_slack_count
immediate_release_liquidity
match_debt_mean
match_debt_min
match_debt_nonzero_types
max_match_debt
remaining_object_count
```

Every definition binds an exact-rational value kind, semantic description, semantics
ID, threshold-generator ID and implementation-source SHA-256.  The frozen V1
registry/spec/certificate schemas, domains, information-channel lists, target,
generator, ordering, selector, claim and lock constants are strict content-addressed
authorities; coherent re-signing cannot substitute them.  The adapter implementation
digest is also anchored to an independently frozen V1 constant and checked before a
registry can be created.  Typed-document parsers preserve JSON list/string distinctions
instead of relying on Python sequence coercion, while the result and independent
verifier require exact nested runtime types for the target, partition, quotient,
portable build/registry/model and certificate.  Transport-equivalent proxy objects
therefore cannot smuggle altered runtime behaviour behind honest bytes.  V1 begins
from a terminal-
kind base partition (`active`, `failure`, `success`) and exhaustively enumerates all
feature subsets in increasing feature count and lexicographic feature-name order.  The
full registry therefore produces exactly `2^11=2048` candidates, below the frozen
`candidate_cap=4096`.  For each feature in a subset, V1 sorts all distinct values on
active covered states and creates one reduced-rational `feature <= midpoint` atom for
every adjacent pair.  Those atoms are applied in canonical order to every splittable
active cell; empty branches are not recorded.

The target is the complete exact controlled one-step behavioural quotient over the
same frozen coverage.  It is query-neutral but still an exact ground-behaviour
realization obligation, not a learned or partial dynamics target.  A candidate is exact
only when its complete partition signature equals that target.  Among exact candidates
the selector minimizes, in order:

```text
feature_count
applied_split_count
lexicographic selected feature names
final_partition_id
```

The canonical fixture must select `selected_features=(action_count,)`, generate
thresholds `(3/2,5/2)`, apply two splits, and reproduce:

```text
ground states -> quotient cells          25 -> 5
active ground states -> active cells     18 -> 3
target_partition_id == realized_partition_id
sound envelope is singleton
```

The feature registry, synthesis spec, predicate atoms/tree, candidates/witnesses,
complete candidate trace and realization certificate use domain-separated full
SHA-256 identities; the resulting portable RAPM keeps its ordinary `rapm:<sha256>`
identity.  Independent verification reruns the full registry-bound enumeration and
rebuilds the behavioural target partition, refinement trace, semantic adapter and
quotient model; it also rebuilds the candidate trace, predicate tree, certificate,
realized partition/quotient, and portable model plus portable registry.  Thus coherent
re-signing of a truncated trace, changed semantics/selection rule, target
trace/adapter/model, realized partition/model, portable registry, Gate field or claim
scope fails replay.

If the registered grammar cannot realize the target, V1 returns
`NO_EXACT_FEATURE_REALIZATION`.  It binds the selected failed candidate and a typed
partition-mismatch pair witness, and publishes no predicate tree, realized partition,
quotient model, portable RAPM or certificate.  The witness vocabulary is bidirectional:
`TARGET_SEPARATED_FEATURE_ALIASED` means the feature partition merges states separated
by the target; `TARGET_MERGED_FEATURE_SEPARATED` means it separates states merged by
the target.  Oversplitting is therefore a diagnosed negative realization, not an
invariant failure and never a positive exact result.

A separate negative control must not be confused with the 25-state golden above.  It
uses the seed-0 LMB canonical initial distribution, has 36 covered states, an exact
behavioural target with 11 cells and an `action_count`-only candidate with 7 cells.
The candidate is incomparable with the target: its complete trace contains both
witness kinds, while the selected unresolved witness is
`TARGET_MERGED_FEATURE_SEPARATED`.

An exact restricted subset can also be exercised only through the negative-control
entry point.  Whether that control returns exact or nonexact cannot alter the canonical
production registry, production trace or production verifier expectation.

For positive reuse evidence, the one serialized feature-realized portable RAPM is
loaded unchanged by fresh Python planner subprocesses for two distinct QuerySpecs
inside the same frozen coverage: the registered `H=3`, match-plus-clear,
`delta=1/20` query and an `H=2`, match-only, `delta=1/10` query.  This proves two-query
in-coverage portability of the abstract model; it is not a preregistered held-out
generalization result or a sealed production-runtime claim.

The precise scientific claim is therefore: given this preregistered LMB current-state
feature grammar and exact finite training coverage, the system automatically selects a
minimal feature coordinate set and generated rational threshold atoms that exactly
realize the query-neutral controlled-behaviour world model, then reuses the resulting
portable RAPM for two in-coverage planning queries.  Because exact realization is
supervised by the complete exact ground behavioural target/signature, V0-038 is not
oracle-free unknown-quotient discovery.  It also does not invent features, learn
incomplete dynamics, discover an unknown-domain grammar, establish scalable or cross-
domain synthesis, validate held-out generalization, or pass the aggregate Phase 3,
Phase 3E, counter-completeness, workload-economics, transfer or learning Gates.

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## V0-039 direct target-free exact homomorphic LMB synthesis rule

V0-039 is additive to V0-038.  It keeps the same central world-model objective but
removes the earlier construction-time requirement to first build an exact behavioural
target partition/signature and then match a feature partition to it.  The registered
profile is `lmb_direct_exact_homomorphism_v1`, with execution profile
`production_full_grammar_v1` and claim kind
`DIRECT_EXACT_HOMOMORPHISM_INSIDE_FIXED_GRAMMAR`.

Its production API is exactly:

```text
synthesize_direct_lmb_homomorphism_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage,
)
```

The function internally constructs the complete canonical state/action registries and
bound synthesis spec.  It accepts no caller-selected registry, behavioural target,
`BehavioralActionSignature`, `QuerySpec`, J0, Q/value/frontier/policy, planning result
or held-out input.  The module imports neither `feature_synthesis` nor
`abstraction.behavioral`, `core` or planning modules.  A fresh-process test poisons the
behavioural module before importing the direct constructor and still obtains the
canonical result.  Raw one-step signatures are computed internally from the exact
kernel only as proof obligations and typed evidence; no precomputed target partition
or signature labels candidate success.

The fixed state grammar contains the same eleven V0-038 current-state coordinates.
The fixed action grammar contains exactly `completes_match`, equal to one iff the
selected tile's type currently has buffer count two.  State and action adapters have
separate frozen source SHA-256 values under one implementation epoch.  Runtime source
must match both independent anchors before construction.  Production enumerates every
state subset and both action-feature subsets, hence exactly
`2^11 * 2^1 = 4096` candidates under cap 4096.  State atoms use every adjacent-value
reduced-rational midpoint with `<=`; action subsets induce semantic labels and a
uniform concretizer over distinct matching ground actions.

Each candidate is accepted only after direct exact state-action homomorphism checks:

1. every active state in a state cell exposes the identical semantic-label set;
2. before any stochastic mixture, all ground actions aliased to one label in one state
   have identical exact reward-feature, failure, termination and successor-cell
   distributions; and
3. the same semantic label has the identical exact one-step signature across every
   state in the cell.

Failures retain domain-separated typed witnesses
`LABEL_SET_MISMATCH`, `WITHIN_STATE_ACTION_ALIAS` or
`CROSS_STATE_LABEL_DYNAMICS_MISMATCH`.  The selector minimizes, in order, state-feature
count, action-feature count, split count, state-feature names, action-feature names and
partition ID.

The canonical 25-state result is:

```text
status = EXACT_DIRECT_HOMOMORPHISM
selected_state_features = (action_count,)
selected_action_features = (completes_match,)
state_thresholds = (3/2, 5/2)
required/evaluated candidates = 4096/4096
ground/active states = 25/18
quotient/active cells = 5/3
abstract entries = 4
envelope_is_singleton = true
action_alias_checked_before_mixture = true
```

The complete positive trace contains all 4096 candidates and all three witness kinds.
An explicit non-production restricted-grammar API is retained for negative and cap
controls.  A restricted grammar with no exact candidate returns
`NO_EXACT_DIRECT_HOMOMORPHISM` and no model/certificate.  Insufficient cap returns
`CANDIDATE_CAP_EXHAUSTED`, evaluates zero candidates and binds exactly one
`CANDIDATE_CAP_INSUFFICIENT` witness.  A restricted grammar that happens to find an
exact homomorphism returns `RESTRICTED_CONTROL_EXACT_FOUND` but deliberately publishes
no quotient, portable model or certificate and is rejected by the production
verifier.  Negative controls are verified only by a separate role-locked control
verifier.  The production verifier additionally rejects restricted-control provenance,
incomplete canonical registries and duck-typed result objects; re-signing a control
result cannot promote it into production evidence.

State/action registries, spec, predicate tree, semantic labels/signatures, witnesses,
candidates, complete trace and certificate are domain-separated content-addressed
artifacts.  Parsers require canonical JSON field types, runtime graphs require exact
nested types, and coherent re-signing, proxy objects, trace deletion and implementation-
source substitution fail.  The independent verifier reconstructs the full production
enumeration, selected tree/partition/action adapter, quotient, portable model/registry
and certificate.  Only after construction, an evaluation-only import of the old exact
behavioural oracle confirms identical partition and model; that comparison is not
construction or certificate authority.  One unchanged portable RAPM also serves the
same two distinct in-coverage queries in fresh planner processes.

The precise V0-039 claim is direct exact state-action homomorphism synthesis from
preregistered human-readable state/action grammars on one exact finite LMB coverage,
without a construction-time behavioural target/signature.  It still uses the complete
exact ground kernel and fixed grammars.  It therefore does not invent feature
semantics, learn partial dynamics, discover an unknown-domain grammar at scale, prove
held-out or cross-domain generalization, or pass any aggregate Phase 3, Phase 3E,
counter-completeness, workload-economics, transfer or learning Gate.

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## V0-040 source-unanimous prior and held-out exact-audit rule

V0-040 is a sidecar control, not a detour that blocks the construction line. Its
production API first exact-audits a single existing V0-039 hypothesis on every source
coverage. Only unanimous exact evidence can construct profile
`source_unanimous_exact_v1`; the caller cannot pass a preferred production hypothesis.
Canonical source supports are mask 11/buffer `(1,2)` and mask 13/buffer `(2,1)`.
The target is mask 7/buffer `(2,1)` and must have distinct task and coverage IDs absent
from the source prior. Sharing the exact LMB structural kernel is intentional and does
not create a cross-domain claim.

The prior binds the complete 4096-candidate catalogue and positive broad-support mass,
but its authoritative flags are:

```text
profile = source_unanimous_exact_v1
broad_support_metadata_only = true
executed_candidate_schedule = false
```

Thus one source-unanimous candidate is proposed and exactly one candidate is audited on
the target. The proposal records that it is not acceptance authority. The only
acceptance authority is the independently replayed exact target ground homomorphism
audit. A positive result publishes the exact quotient and portable RAPM with
`global_minimality_verified=false`; source work remains offline and target work remains
separate:

```text
source exact calls / unique rows / eligible rows = 14 / 14 / 14
target exact calls / unique rows / eligible rows = 21 / 7 / 7
source/target interaction samples = 0 / 0
target candidate evaluations = 1
```

An external preferred hypothesis exists only under
`nonproduction_external_control_v1`, its distinct builder, runner and verifier. The
empty-hypothesis control records target `3/3/7`, returns
`PRIOR_MISMATCH_FALLBACK_REQUIRED`, requires normal ground discovery or direct
optimization, publishes no model/certificate and cannot claim infeasibility. Re-signing
or renaming external evidence cannot make it production evidence.

The companion sample-efficiency sidecar distinguishes environment interaction,
generative-oracle sampling, exact-kernel queries, offline observations and synthetic
model rollouts. V0-040's narrower exact-control accounting does not claim a complete
five-class operational WorkVector, sample reduction, or an executed tax-reduction
operator. That operator is deliberately deferred until the main algorithm reveals its
real bottleneck.

## V0-041 generated typed-coordinate exact synthesis rule

The new mainline production API is:

```text
synthesize_generated_lmb_homomorphism_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage,
)
```

It sees no QuerySpec, reward weights, target quotient/signature, J0, Q/value/policy,
held-out data or caller-selected features. A frozen typed production-template DSL starts
from raw LMB primitives `legal_actions`, `remaining_tiles`, `buffer_counts`,
`buffer_capacity`, `selected_tile_type` and integer literals. It deterministically
instantiates eight state and four state-action expression ASTs. Neither the source nor
the registry contains V0-039's named feature identifiers.

Every state-program/action-program subset pair is evaluated under the direct exact
homomorphism obligations, giving 4096/4096 candidates. The deterministic selector
chooses:

```text
state AST = cardinality(legal_actions)
action AST = buffer_at_type(buffer_counts, selected_tile_type)
thresholds = (3/2, 5/2)
ground/active = 25/18
quotient/active = 5/3
abstract entries = 4
singleton envelope = true
```

The typed expressions, canonical DSL registry, synthesis spec, predicate tree,
semantic adapter, witnesses, complete candidate trace and certificate are separately
content-addressed. Frozen evaluator, enumerator, compiler and audit digests bind the
implementation. The independent verifier reconstructs all 4096 candidates, the
selected quotient and portable model. A cap-one control evaluates zero; a state-only
control evaluates 256 and returns `NO_EXACT_GENERATED_HOMOMORPHISM`; both publish no
model/certificate.

The precise new claim is generation and exact selection of compositional coordinate
programs inside one fixed human-designed DSL. Full exact dynamics, exact finite
coverage and the human production templates remain. Unknown-semantic invention,
partial/learned dynamics, scale, held-out/cross-domain generalization and sample
efficiency remain open.

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```


## V0-042 query-neutral observation-log partial RAPM rule

The production API is exactly:

```text
build_observation_partial_rapm_v1(
    observation_log,
    coordinate_proposal,
    semantics_profile,
    observation_authority,
)
```

The independent verifier receives those four exact inputs plus the claimed result. No
kernel, QuerySpec, planner, value, policy, J0, behavioural target or held-out result is
an input. The source graph is usable only when the authority ID belongs to the frozen
external allowlist and every identity beneath it matches. An acquisition manifest
freezes eight literal states, eleven legal ground rows/action catalogues and seven
one-to-one receipts/observations before query registration; it is not constructed from
a selected initial-state closure. Acquisition and construction each record zero query
inputs. The evidence matrix is exactly:

```text
offline_source / OFFLINE_LOGGED_OBSERVATION = 7
all other 19 lane/class cells = native zero
```

The derived Portable model contains seven observed deterministic singleton rows and
four missing unit-unknown rows. Its constructor is itself an authority boundary: it
recomputes the state partition, semantic-action/cell links, state-action-derived ground-
row IDs, concretizer support, complete concretizer/realization pairs, observed/missing
support partitions, and every exact concretizer-weighted realization ambiguity. A
caller cannot preserve the allowlisted source ID while changing only model bytes to
erase missing evidence. Concretizers are uniform over distinct ground actions. Reward-
cap, known-reward, reward-interval, known-successor and successor-interval semantic
names are unique.

Every ground and realization ambiguity has explicit joint outcome atoms for active-
cell/external continuation, terminal success and terminal failure. Its simplex enforces
`known_continuation + known_terminal + unknown = 1`, `failure <= terminal`, and exactly
one allocation of unknown mass; successor/failure/terminal marginal intervals are
projections, never independent boxes. The external successor ID cannot alias a
registered state and represents only an active, nonterminal, nonfailure continuation.
The model binds `semantics_horizon_cap=6`, registered-catalogue support only, and no
transition-closure claim.

This authority is deliberately conditional. `in_memory_exact_graph_required=true` and
`transport_authority_claimed=false`; content IDs prove canonical-byte integrity and
binding, not observer honesty, complete catalogue truth, deterministic stationarity or
public-key authenticity. New fixtures require an explicit allowlist/contract revision.
The fixed manual coordinate proposal is not automatic coordinate synthesis, and the
partial RAPM is not a plan, plan certificate, exact quotient, infeasibility proof,
learned dynamics, held-out/generalization result, or sample-saving result.

## V0-043 conditional robust fixed-plan audit rule

The production and verifier surfaces are exactly:

```text
audit_partial_fixed_plan_v1(
    observation_log,
    coordinate_proposal,
    semantics_profile,
    observation_authority,
    partial_build_result,
    thresholds,
    contingent_plan,
)

verify_partial_fixed_plan_audit_v1(
    observation_log,
    coordinate_proposal,
    semantics_profile,
    observation_authority,
    partial_build_result,
    thresholds,
    contingent_plan,
    claimed_result,
)
```

Before reading any threshold or plan field, the consumer runs the complete V0-042
source-graph/model reconstruction. It imports no domain kernel or planner and makes zero
external-transition-authority and ground-search calls. Thresholds and the plan are
downstream query-scoped objects, so V0-043 is not a query-neutral construction result.
The supplied selector is deterministic, has exactly stages `0..H-1`, assigns one legal
semantic action to every active cell at each stage, and satisfies `H<=6`.

The sole registered reward-scale authority is:

```text
proof_id = 6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98
formula = canonical-lmb-n6-return-upper-v1
reward basis = match:1, terminal_clear:1
maximum match events = 2
terminal-clear bonus upper = 2
R_max = 4
normalized-regret tolerances = {0,1/20}
risk tolerances = {0,1/20,1/10}
goal_id = default (exact string, content-bound by thresholds_id)
```
`FrozenPartialAuditThresholdsV1` supports exactly this goal. A foreign string,
non-string value or string-like duck is `PartialSoundAuditInvariantViolation`, not a
second QuerySpec or a newly supported goal.


The proof binds the canonical structural, environment-instance, observation-log,
semantics-profile, observation-authority and acquisition-manifest identities. It does
not derive reward scale from the chosen partition or model. Initial support is an exact
unit-mass distribution over registered active ground-state IDs; a cell ID cannot stand
in for a ground state. Each initial support state receives its own unrestricted reward
upper, supplied-plan reward lower and normalized-regret obligation. All support-point
obligations must pass. Distribution regret is diagnostic only; risk is evaluated under
the full initial distribution.

The unrestricted comparator evaluates every registered ground-action row under
`partial-joint-simplex-unrestricted-ground-upper-v1`; it is an upper bound, not J0 or an
optimal value. The fixed-plan table uses
`partial-joint-simplex-fixed-plan-bellman-v1`. A row allocates shared unknown mass once
over terminal failure/success, registered active continuation or external continuation.
Per-destination reachability uppers may reuse that mass only to find possible proof
obligations and are not probabilities or Bellman mass. An unknown row or known external
continuation reachable under the supplied plan with remaining horizon above one fails
the separate selected-plan external-coverage obligation.

A complete result has exactly one of two normal outcomes:

- `CERTIFIED_FIXED_PLAN` binds the source model, thresholds, supplied plan, registered
  return proof, unrestricted and policy bounds, every reachable obligation and every
  support-point regret row. It claims neither planning, optimality nor infeasibility.
- `FAILED_PROOF_FRONTIER` binds the earliest failed proof stage and one reason from
  `EXTERNAL_COVERAGE_ESCAPE`, `UNRESOLVED_POLICY_PATH_DISTINCTION`, or
  `KNOWN_FIXED_PLAN_THRESHOLD_FAILURE`. Its frontier is only a
  `NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1`: `local_recovery_authorized=false`, causal
  necessity/sufficiency false and infeasibility false. `unresolved_exposure_sum` is a
  sum of representative proof exposures, not a probability.

The canonical positive control supplies an H3 observed-path plan. Its unrestricted
reward upper is 4, policy reward interval `[4,4]`, distribution and maximum support-
point normalized regret are zero, failure interval is `[0,0]`, external coverage passes,
and 33 unrestricted proof rows yield `CERTIFIED_FIXED_PLAN` despite four unrelated
missing source rows. The canonical H1 missing-state negative regression has unrestricted
upper 3, policy lower 0, normalized regret `3/4`, failure upper 1 and earliest
`(time=0,remaining=1,UNRESOLVED_POLICY_PATH_DISTINCTION)` frontier.

Three further negative regressions are mandatory. A 99/100 observed plus 1/100 missing
H1 distribution has diagnostic normalized regret `3/400<1/20` and risk `1/100`, but its
bad support point has regret `3/4`, so value certification fails. The same mixture at
H2 fails external coverage even though risk still passes. A selected singleton but
known-suboptimal H3 plan yields `KNOWN_FIXED_PLAN_THRESHOLD_FAILURE`; unselected missing
rows do not convert threshold failure into an unresolved or causal claim.

Source-row deletion, unregistered/changed return proof, foreign model/plan identity,
horizon overflow, mutable or duck nested objects, altered bounds/frontier, erased
unknown mass and coherent re-signing are invariant violations
(`PartialSoundAuditInvariantViolation`). They may not be reported as a normal negative
regression, failed frontier, infeasibility result or local-recovery authority. V0-043
does not implement plan search or route execution and opens no official, scalar,
economics, counter-completeness, sample-efficiency, Phase 3 or Phase 3E Gate.

## V0-044 bounded partial-model contingent-plan proposal rule

Contract `1.7.0`, implementation schema `1.0.0`, freezes profile
`partial_model_contingent_plan_proposal_v0`. The production and verifier surfaces are:

```text
propose_partial_model_plan_v1(
    observation_log,
    coordinate_proposal,
    semantics_profile,
    observation_authority,
    partial_build_result,
    thresholds,
)

verify_partial_model_plan_proposal_v1(
    observation_log,
    coordinate_proposal,
    semantics_profile,
    observation_authority,
    partial_build_result,
    thresholds,
    claimed_result,
)
```

The complete V0-042 source graph and partial model are reconstructed before any
threshold field is read. Production has no kernel, transition callback/interface,
`J0`, ground solver, feasibility oracle, second QuerySpec or caller-supplied cap. The
consumed V0-043 threshold ID content-binds exact `goal_id="default"`; foreign or non-
string goals fail before enumeration and do not create a second QuerySpec or goal
profile. The private
`_propose_partial_model_plan_nonproduction_cap_control_v1(..., candidate_cap=)` is a
named control only and is not a production interface.

For every active cell `z`, construction freezes its complete semantic-action domain.
Let

```text
S = product over active z of |Abar(z)|
candidate_count = S^H
```

A candidate is one deterministic global assignment at every stage `0..H-1`; it assigns
exactly one semantic action to every active cell. Within cap, all candidates are
enumerated, converted to V0-043 `FrozenContingentAbstractPlanV1`, and audited with the
registered V0-043 thresholds. Candidate summaries bind the audit result and exact
reward, risk, regret and external-coverage diagnostics.

Selection has exactly three tiers:

1. `INTERNAL_V0043_AUDIT_PASS_REWARD_MAX`: restrict to internal
   `CERTIFIED_FIXED_PLAN`; maximize `policy_reward_lower`, minimize
   `policy_failure_upper`, then minimize `plan_id`.
2. `RISK_FEASIBLE_REWARD_MAX`: only if tier 1 is empty, restrict to
   `policy_failure_upper <= delta` and use the same key.
3. `MIN_FAILURE_RISK_FALLBACK`: only if both earlier tiers are empty; minimize
   `policy_failure_upper`, maximize `policy_reward_lower`, then minimize `plan_id`.

The `INTERNAL_` prefix is normative. It is a deterministic selection signal, not
certificate authority. `PartialModelPlanProposalResultV1` always freezes:

```text
proposal_is_certificate_authority = false
selected_plan_requires_independent_v0043_audit = true
feasible_plan_claimed = false
infeasible_query_claimed = false
optimal_ground_policy_claimed = false
claim_kind = MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL
```

The artifact graph contains `PartialPlannerCellActionDomainV1`,
`PartialPlannerCandidateSummaryV1`, `PartialModelPlannerTraceV1`,
`PartialModelPlanProposalResultV1`, the selected V0-043 plan when present, and a
domain-separated cap profile. Production freezes:

```text
candidate_cap = 65536
cap_profile_id = 9176c40aec0b6ecb3c7645a61363cefa32d9d13396ab33ee70fb0238f171932b
caller_cap_allowed = false
production_claimed = true
```

If `candidate_count > 65536`, source/context verification and exact counting still run,
but candidate enumeration/audit does not begin. The typed result is `CAP_EXHAUSTED`,
with zero evaluated candidates, zero fixed-plan audits, empty summaries,
`selection_mode=NOT_APPLICABLE`, incomplete enumeration and no selected plan or
certificate. A private control cap must satisfy `1 <= cap < 65536`, records
`caller_cap_allowed=true` and `production_claimed=false`, and cannot pass the public
production verifier.

Trace telemetry obeys:

```text
fixed_plan_audit_count = candidate_evaluated_count
source_graph_reconstruction_count = 1 + fixed_plan_audit_count
external_transition_authority_calls = 0
ground_search_calls = 0
work_economics_claimed = false
```

These counters measure exact model-side enumeration/reconstruction/audit work. They are
not environment interactions, generative samples, sample savings, a complete WorkVector
or workload economics.

The frozen goldens are:

```text
H3 observed: S=2; candidates=8/8; audits=8; reconstructions=9
  selection=INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
  selected_plan_id=1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc
  reward L/U=4/4; failure L/U=0/0; all regret diagnostics=0
  internal and independent V0-043 outcomes=CERTIFIED_FIXED_PLAN

H1 missing: same model/build, distinct threshold/result IDs; candidates=2
  selection=MIN_FAILURE_RISK_FALLBACK; reward L/U=0/3; failure upper=1
  risk_feasible=false; audit=FAILED_PROOF_FRONTIER
  reason=UNRESOLVED_POLICY_PATH_DISTINCTION; local authorization=false

private H3 cap-4 control: required=8; CAP_EXHAUSTED
  evaluated/audits/reconstructions=0/0/1; summaries=(); selected_plan=null
  production_profile=false; public verifier rejects
```

The verifier independently reconstructs source/model, enumerates every within-cap
candidate, replays every internal V0-043 audit, reapplies tier and tie-break rules, and
compares the canonical document. Candidate/ordering/selection/plan-ID tampering,
threshold/source/model/result substitution, duck nested objects, coherent re-signing,
kernel/ground/caller-cap API injection, or promotion of a control result fails closed as
`PartialModelPlannerInvariantViolation`.

V0-044 proves only bounded exhaustive model-only proposal on the registered finite
control. It does not itself certify a plan, prove feasible/infeasible, reproduce `J0`
or a ground optimum, establish exact quotient/closure, invent coordinates, authorize
causal localization/local recovery/fallback, demonstrate learned/statistical dynamics,
generalization, cross-domain transfer, scalability, sample reduction or economics, or
open official execution/Phase 3/Phase 3E/aggregate Gates. Cap 65536 is a hard bound, not
a scalability result. Every official/scalar/economics/counter/sample lock remains
unchanged.

## V0-045 observation-only typed-coordinate partial-RAPM rule

Contract `1.8.0` freezes profile
`lmb_query_free_observed_typed_coordinate_synthesis_v0`. Construction accepts exactly
the allowlisted V0-042 observation log, deterministic profile and observation
authority; verification adds only the claimed full V0-045 result. It receives no
query, kernel, behavioural target, V0-041 result, selected subset, candidate cap,
planner, audit, value/risk object, policy, J0, ground solver or callable adapter.

The internal evaluator recreates the fixed eight-state/four-action typed language under
a distinct observation-source registry, materializes values for all eight states and
eleven legal rows, and exhausts `4096/4096` state/action-subset pairs. Missing rows are
not equality, mismatch or negative evidence. Observed congruence is checked before
mixture, label availability must be identical for every state in a cell, and the
non-vacuity rules require observed aliasing, null-conflict separation, point evidence
and strict compression. The frozen selector returns state program
`cardinality(legal_actions)`, action program
`buffer_at_type(buffer_counts,selected_tile_type)`, and boolean midpoint atom `<=3/2`.
The resulting six-cell/four-active model has five abstract entries/actions, six
realizations, seven point rows, four missing rows and one `UNOBSERVED_UNKNOWN` entry.

`FrozenTypedCoordinateValueTableV2`, `FrozenTypedCoordinateProposalV2` and
`build_observation_partial_rapm_from_typed_values_v2` extend V0-042's internal pure
derivation without changing `PortablePartialRAPMV1` or the V1 nonempty
`tuple[bool,...]` semantic-action label. Raw integers are compiled to boolean midpoint
atoms; empty action programs use a boolean universal sentinel. The pure V2 builder is
not authority because its value table and opaque trace identities are caller-held.
Only complete `ObservedTypedPartialRAPMResultV1` replay reconstructs source values,
all candidates, selection, proposal, build, model, telemetry and certificate.

The typed V0-044 proposer accepts the full V0-045 result, replays it once before
threshold access, freezes the verified model, and then exhausts plans with the common
verified-model V0-043 core. Its canonical H3 trace has one V0-045 replay, zero internal
source replays and eight typed candidate audits; H1 has one replay, zero internal
source replays and two audits. Retained synthesis is not a per-plan source-extraction
loop: the planner works on one fixed symbolic partial model.
The typed proposal remains nonauthorizing. Independent typed V0-043 replays the full
V0-045 chain again for the selected plan and emits a wrapper binding synthesis result,
synthesis certificate, proposal, build, model, thresholds, plan and unchanged V0-043
audit. H3 certifies reward/failure `4/0`; all-missing H1 returns reward interval `[0,3]`,
failure upper one and a nonauthorizing `UNRESOLVED_POLICY_PATH_DISTINCTION` frontier.

This closes fixed-DSL discovery only over an already-symbolized, externally trusted
finite observation graph. It does not claim raw or neural representation learning,
unknown primitives/operators/DSL, exact/true latent dynamics, observer truth,
statistical consistency, held-out/cross-domain generalization, scale or sample saving.
V0-046 freezes that failed chain, proves and charges the exact H1 four-row scope,
constructs an immutable query-owned overlay, and replans/re-audits without mutating the
base. V0-047 separately extends this authority to a two-round H2 path with
evidence-derived active boundary registration and coordinate reuse. Preregistered
multi-query/held-out promotion is the next Gate. A failed frontier is diagnostic and
cannot itself authorize access or mutate the reusable base.

Frozen key IDs are: synthesis result
`4834efc30b9ae292e33f83932525195df1997ae31f7c7898b452b6175815ded2`, partial model
`1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18`, H3 planner
result `4201c591132a6245df3a4989c7d9c9a9c2b9bab67132e679762b31ef2b1d3b6f`, H3 typed
audit `24f4c930b0349fd90fc636efc787f5f39115abaf8e2824ebcced68473b917a87`, H1 planner
result `f9006103939f33ee744fd994e00240018ab445c75df1c4c23fba82d479bc6513`, and H1
frontier `9d6f0803f365643d623368cdfed6b6666c5c8a00e3fd77fbdf41b00d1f354cab`.
The full identity table is normative in `specs/OBSERVED_TYPED_COORDINATE_SYNTHESIS.md`.
All existing official/scalar/economics/counter/sample locks remain unchanged.

## V0-046 query-local exact-row refinement rule

Contract `1.9.0` freezes profile `lmb_h1_query_local_exact_row_refinement_v0`. The
production runner accepts the full V0-045 observation-only result, canonical H1
thresholds, complete typed V0-044 proposal, independently failed typed V0-043 result,
and exact canonical LMB kernel. It accepts no row subset/cap, alternative frontier,
transition callback, J0/ground solver result, target policy, or promotion decision.
The verifier adds only the claimed complete result.

The row authority first replays the complete source/planner/audit chain and requires
the frozen H1 `UNRESOLVED_POLICY_PATH_DISTINCTION`. Its one reachable obligation has
mass upper one and four missing uniform concretizer rows. Each row’s leave-one-out
failure upper is `1/4`, above `delta=0`; all four are therefore individually necessary
inside the fixed-plan, fixed-concretizer row-completion family. Request preparation
uses no kernel/search call, authorizes exactly four calls, and explicitly declines a
global experiment-minimum claim. A bare failed frontier remains nonauthorizing.

Acquisition binds the exact LMB structure and kernel source digest
`fa38ca4724420cc9834a50ee83b57a97721434404a9e76f0994b1aecb22b5323`, validates every
registered legal-action catalogue, then calls only the four requested ground rows.
Operational counts are four exact calls/four positive rows/zero extra rows; environment
interactions, generative samples and synthetic evidence rollouts are zero. One
successor is registered and three are external; all four rewards, failures and terminal
flags are zero.

The base remains ID
`1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18`.
A new overlay context/BuildEpoch constructs query-owned model
`7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df`, replaces exactly
the four missing rows, recomputes semantic realizations, and changes coverage from
`7/4` to `11/0`. It remains query-local, non-promotable, not transition-closed and not
an exact quotient. Threshold rebasing preserves query semantics. Abstract planning
enumerates/audits two plans without further kernel access; independent audit issues
certificate `ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303`
with reward/failure/regret zero.

Primary IDs are:

```text
kernel authority = 2bb62669839fbde2cb4703c1ff71b71eb95cddcfdba5b3102a1833c5258164a0
request = 1ff845f3eecc05a098b3437c7e4b8356bcd28ea1dd0d4cc4ace8e52bc382cd2c
bundle = 17c8783b3ab489322359bb9ed7e463c4540e9ed1d4d6036d639c1cc9a6bc8543
overlay BuildEpoch = ff0a14c296c8d5d122ff0f635ad8909dcfd2294274c99c3ac1da0412e8d947d2
overlay model = 7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df
plan proposal = 9a408b15377b10bf6450d91c0e1e26d9e7dd9ac129abc7462ce15ca69187ad3c
certificate = ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303
result = 8c37b241d15b06f05dfe34189b37e324addd2c93605d4c718868d8a0544cf057
```

`RETAIN_QUERY_LOCAL_OVERLAY_ONLY` permits reuse only in the identical bound context;
base promotion and multi-query/held-out promotion Gates remain false. Independent
verification replays source, failure, exact evidence, overlay, planning and audit and
requires byte-identical output. Evaluation replay does not alter the four-call
operational record and does not establish complete Phase 3E accounting.

This proves one authentic certificate-triggered local model-evolution loop, not general
causal minimality, multi-step external-boundary recovery, raw symbolization, unknown-
DSL invention, learned/statistical dynamics, promotion, generalization, scale,
economics, or sample saving. V0-047 below now executes the distinct multi-step Gate;
V0-046 remains the immutable H1 regression and is not relabelled as a multi-step or
promotable result.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-047 multi-step query-local RAPM-evolution rule

Contract `1.10.0` freezes profile
`lmb_h2_multistep_query_local_exact_refinement_v0`. Production receives only the full
V0-045 result, canonical H2 typed V0-044 proposal, independently failed typed V0-043
audit, and exact canonical LMB kernel. The public runner has no caller row/state/cap,
alternate frontier, transition callback, J0/ground optimizer, target-policy or
promotion input. A bare failed frontier remains nonauthorizing.

The first authority binds the selected-plan realization at the earliest
`time_index=0, remaining_horizon=2` obligation. Its four missing rows each have
concretizer probability and row-exposure upper `1/4`. It freezes exactly four rows,
records zero preparation kernel/search work, makes no global-minimum claim, and permits
exactly four operational transition calls. The complete outcomes reveal one registered
and three distinct external nonterminal successors.

Those three boundary states are derived from the evidence bundle. Exactly one complete
legal-action catalogue is requested per state: three direct boundary catalogue calls,
nine new rows, zero transition replay and zero ground search. The exact V0-045 selected coordinate
programs are evaluated on every new state/action. All three states reuse coordinate
signature `(3,)`; all expose semantic labels `(False,)` and `(True,)`. This is
within-query reuse, not held-out validation or a newly invented coordinate.

`QueryScopedPartialRAPMV3` is a separate content domain for query-local registered
states/action catalogues. Both epochs require `query_neutral=false`,
`transition_closure_claimed=false`, `exact_quotient_claimed=false`,
`plan_certificate_claimed=false`, `infeasibility_claimed=false`,
`base_model_mutated=false`, and `promotion_authorized=false`. The first epoch binds
the V0-045 base and round-one chain, contains 20 registered rows, and has coverage
`11 observed / 9 missing`.

First-epoch planning enumerates four complete deterministic H2 plans with no kernel
access. After the original numerical value/risk hierarchy, exact ties use
`NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1`; only identical semantic schedules
fall through to `plan_id`. Independent audit must move the earliest failed frontier to
`time_index=1, remaining_horizon=1` and set external-coverage failure false.

The second authority may run only after that epoch, proposal, and independent failed
audit are frozen. It binds the union of three selected-plan rows with positive risk
exposure and nine unrestricted value challengers under zero regret. The native role
counts remain `3 risk / 9 value / 9 distinct`; deleting either role invalidates the
request. Exactly nine transition calls produce three nonfailure match-reward-one rows
and six terminal failures.

The final V3 epoch binds the first as `previous_model_id`, retains 20 registered rows,
and has `20 observed / 0 missing` plus cumulative 13 transition calls. This is not a
global closure claim: nonterminal external successors at horizon truncation remain
outside the catalogue. Final model-only planning evaluates four plans and independent
audit must certify reward lower/upper `1/1`, failure lower/upper `0/0`, normalized
regret zero and external coverage.

Frozen work counts are:

```text
round-one transition calls = 4
direct boundary catalogue calls = 3
round-two transition calls = 9
cumulative transition calls = 13
step-internal legality checks = 13 (included in transition calls)
model-only replanning passes = 2
candidate plan audits = 8
planning/audit kernel calls = 0
direct ground-optimization calls = 0
sample_efficiency_claimed = false
```

The independent verifier replays the entire V0-045 chain, H2 source proposal/audit,
both requests/bundles, boundary catalogues, coordinate evaluation, both V3 epochs,
both planning/audit passes, telemetry, and final result. It rejects caller scope,
omission, role removal, semantic tie/hash substitution, base mutation, promotion,
foreign models, and coherent re-signing. Evaluation replay does not alter operational
counts.

V0-047 proves the first authentic multi-step within-query refinement loop only. It does
not prove general causal minimality, unknown-DSL or raw symbolization, learned/
statistical dynamics, transition closure, exact quotient, cross-query/held-out reuse,
base promotion, generalization, scale, economics, or sample saving. The next Gate is
preregistered cross-query/held-out reuse and promotion with leakage controls and matched
acquisition traces; any Laplace-style operator or KG-OP-style meta-prior follows those
measurements rather than being inferred from this positive control.

Canonical identities and acceptance attacks are normative in
`specs/MULTISTEP_QUERY_LOCAL_REFINEMENT.md`.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-048 preregistered cross-query promotion rule

Contract `1.11.0` freezes profile
`lmb_preregistered_h1_cross_query_promotion_v0`. The protocol is constructed
before any V0-047 result or exact kernel is supplied. It binds the canonical H2
source thresholds and a distinct H1 target state
`removed_mask=11, buffer=(1,2), active`, which is absent from the V0-045
observation registry. The source runner's exact eight parameters contain no target
or promotion input.

Promotion must independently replay the complete V0-047 source and select the
entire final V3 model. Frozen eligibility counts are:

```text
complete promoted rows = 20
source exact evidence rows = 13
source boundary catalogues = 3
target rows = 3
target-filtered rows = 0
promotion replay transition / direct catalogue calls = 13 / 3
```

The result is a separate `PreregisteredReusablePartialRAPMV4` epoch. The V0-045
base remains unchanged. Source acquisition remains explicitly non-query-neutral;
promotion authorizes reuse only for the preregistered state and horizon cap one.
V4 must keep promotion true but unrestricted reuse, transition closure, exact
quotient, embedded certificate, and infeasibility claims false.

The held-out consumer receives no kernel, transition callback, ground solver, J0,
target override, or caller cap. It evaluates two deterministic H1 plans and the
independent audit certifies:

```text
reward lower / upper = 1 / 1
unrestricted reward upper = 1
failure lower / upper = 0 / 0
normalized regret = 0
external coverage = true
warm target transition / catalogue calls = 0 / 0
direct ground optimizer = 0
```

The evaluation-only cold evidence trace makes one direct target catalogue call and
three transition calls. Its one safe-match and two failure outcomes exactly match
the promoted source evidence; three step-internal legality checks are included in
the transition work. It is not an end-to-end cold planner.

The telemetry preserves four native lanes:

```text
source acquisition = 13 transitions + 3 catalogues
promotion replay = 13 transitions + 3 catalogues
warm target = 0 transitions + 0 catalogues
cold evaluation = 3 transitions + 1 catalogue
```

Source amortization is not included. `sample_efficiency_claimed=false`, official
scalar/break-even remain null, and the sample-efficiency Gate remains non-blocking
and unrun. V0-048 proves one preregistered scoped cross-query reuse/promotion path,
not unrestricted promotion, statistical generalization, learned dynamics, feature
invention, scale, economics, or sample saving. The next Gate is a preregistered
family of held-out occurrences with promotion amortization and matched end-to-end
cold baselines.

Canonical identities and all acceptance attacks are normative in
`specs/CROSS_QUERY_PROMOTION.md`.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-049 preregistered held-out family amortization rule

Contract `1.12.0` freezes profile
`lmb_preregistered_h1_heldout_family_amortization_v0`. Before any source result or
kernel is supplied, preregistration freezes three H1 queries at LMB states
`removed_mask=11,19,35`, all absent from V0-045, and the ten-occurrence order
`1,2,3,1,2,3,1,2,3,1`. The V0-047 source runner has no family input. The cold direct
planner has no promotion or source-result input.

The unchanged V0-048 authority independently replays the complete V0-047 source and
builds the exact singleton V4 parent. Family promotion must retain all 20 final rows,
all 13 exact evidence records and all three boundary catalogues. The three targets
jointly account for nine complete rows and target-filtered row count remains zero.

`PreregisteredReusablePartialRAPMV5` is a separate immutable epoch rather than an
in-place V4 widening. It binds the complete V4 parent, family protocol, eligibility
proof, exactly three authorized initial-state IDs and horizon cap one. V5 keeps:

```text
query_neutral = true inside registered family scope
acquisition_query_neutral_attested = false
promotion_scope_query_neutral_attested = true
promotion_authorized = true
base_model_mutated = false
unrestricted_reuse_claimed = false
transition_closure_claimed = false
exact_quotient_claimed = false
```

Each warm occurrence has no kernel or ground optimizer. It evaluates two semantic
plans and performs three fixed-plan audits, then certifies reward/failure/regret
`1/0/0` with target transition/catalogue calls `0/0`. Each cold occurrence begins
from its QuerySpec and canonical kernel only, requests one complete catalogue,
executes three transitions, observes three internal legality checks, evaluates all
three ground actions and invokes one direct ground optimizer. It also returns exact
`1/0/0`. Source catalogue/evidence comparison occurs only after the cold result is
frozen, and all ten warm/cold pairs must match exactly.

Native work is frozen by lane:

```text
source acquisition operational = 13 transitions + 3 catalogues
promotion replay evaluation = 13 transitions + 3 catalogues
warm target operational total = 0 transitions + 0 catalogues + 20 candidates + 30 audits
cold direct operational total = 30 transitions + 10 catalogues + 30 candidates + 10 optimizers
```

For prefix `N`, source-inclusive warm acquisition is `(13,3)`, verification-inclusive
diagnostic acquisition is `(26,6)`, and cold direct acquisition is `(3N,N)`. The first
strict warm componentwise-dominance prefixes are diagnostic `5` and `9`, respectively.
They are not scalar break-even fields:

```text
official_scalar_cost = null
official_N_break_even = null
sample_efficiency_claimed = false
tax_operator_selected = false
dominant_tax_axis = null
```

Exact-kernel calls remain distinct from environment interactions and samples. The
three-state deterministic family and seven repeated occurrences do not establish
statistical generalization or sample efficiency. V0-049 does establish that, after
target ground acquisition becomes zero, repeated warm certification still executes
20 plan candidates and 30 audits. The next Gate shall test an identity-bound
certificate memoization/incremental-proof intervention against a matched no-reuse
control, with invalidation on model/query/threshold/plan changes and independent
evaluation replay. No such operator is claimed here.

Canonical identities and all acceptance attacks are normative in
`specs/HELDOUT_FAMILY_AMORTIZATION.md`.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-050 exact identity-bound certificate memoization rule

Contract `1.13.0` freezes schema `1.0.0`, profile
`lmb_identity_bound_certificate_memoization_v0`, and success status
`CERTIFIED_IDENTITY_BOUND_PROOF_REUSE_CONTROL`. V0-049 remains the strict no-reuse
control. The memo arm retains the same V5 model, three queries, ten occurrences, two
plan candidates per occurrence, selection/tie-break and independent selected-plan
certificate, but its isolated append-only store starts empty. It receives no kernel,
source refinement result, cold result, or no-reuse result.

Every occurrence makes two `CANDIDATE_RANKING_AUDIT` requests and one
`INDEPENDENT_SELECTED_PLAN_CERTIFICATE` request. The roles are different cache-key
coordinates. Candidate ranking may consume a certified result or failed-proof
frontier; the selected role must contain a complete fixed-plan certificate. Equal
inner bytes cannot erase this independence boundary.

The exact memo key binds:

- memo/auditor semantics and registered auditor/planner source digests;
- structural, environment, base, source, protocol, promotion, eligibility and V5
  model identities;
- observation log, semantics profile and observation authority;
- target query, threshold binding, complete thresholds and return-bound proof;
- complete contingent plan and planner/tie-break semantics;
- proof role and the selected planner-result identity when applicable.

Logical occurrence ID is deliberately outside this semantic key so an exact repeat
may hit, but every lookup emits a fresh receipt binding current occurrence/query,
sequence/ordinal, role, key/entry/payload, source miss and cache pre/post states.
Changing only a registered occurrence may therefore hit; changing any semantic field
above invalidates reuse.

On a miss, the trusted runner executes the complete auditor once and freezes the
execution attestation, complete audit payload, optional certificate, one append-only
insertion and current receipt. On a hit it revalidates the live planner context,
requires exact key equality and references an earlier trusted miss. Conflicts,
cross-role entries, stale/poisoned content, malformed IDs, overwrite/reorder attempts,
unregistered occurrences and owner-copy replay fail closed rather than degrading to
an apparently successful miss.

The owner-bound runtime execution and independent verifier replay the trace from the
canonical empty state and reconcile all work from 30 receipts. The frozen totals are:

```text
logical audit requests = 30 in each arm
plan candidates = 20 in each arm
selected-plan certificates = 10 in each arm
no-reuse complete audits = 30
memo complete audits = 9
memo misses / inserts / hits / lookups = 9 / 9 / 21 / 30
final cache entries = 9
target transition / catalogue calls = 0 / 0 in each arm
no-reuse audit prefix = 3,6,9,12,15,18,21,24,27,30
memo audit prefix = 3,6,9,9,9,9,9,9,9,9
```

All threshold bindings, planner artifacts, outer audit artifacts, selected
certificates and cold direct reward/failure/regret results remain exact matches. The
21 avoided full audits establish a narrow `21/30=7/10` proof-computation reduction.
They do not establish total-work or wall-clock improvement because lookup,
validation, hashing, receipts, I/O and standalone evaluation replay remain explicit
nonnegative work.

The claim boundary is frozen:

```text
incremental_proof_claimed = false
cross_identity_reuse_claimed = false
persistent_cross_process_cache_claimed = false
sample_tax_operator_claimed = false
sample_efficiency_claimed = false
statistical_generalization_claimed = false
overall_workload_economics_claimed = false
```

A future cross-query or changed-threshold proof-reuse Gate requires a new
identity-bound proof-dependency DAG plus a re-derivation artifact that identifies
reusable obligations and recomputes every affected descendant. It may not relax the
V0-050 exact key or relabel exact memo hits as a sample-tax result.

Canonical identities and all acceptance/attack tests are normative in
`specs/CERTIFICATE_MEMOIZATION.md`.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-052 H2 stage-local temporal proof-DAG rule

Contract `1.15.0` freezes schema `1.0.0`, profile
`lmb_h2_stage_local_bellman_proof_dag_v0`, and success status
`CERTIFIED_REGISTERED_H2_STAGE_LOCAL_BELLMAN_RECURRENCE_CONTROL`. Its source is the
unchanged V0-047 final query-local H2 V3 result/model
`9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42` /
`a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315`.
The V0-048/V0-049 promoted V4/V5 H1 models are forbidden substitutes. The selected
Gray-`00` plan remains
`0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb`.
This is a proof layer over a frozen RAPM, not another promotion.
Its semantics identity pins the exact V0-043 audit, partial-model planner, V0-047
multi-step, and V0-051 predecessor source digests listed in the normative H2 spec.

The protocol freezes four candidate-role requests in Gray order
`A0A0,A0A1,A1A1,A1A0`, then one separately keyed independent-selected request for
`A0A0`. Eleven exact slots form this ordered graph:

```text
U1 -> U0
P1 -> P0
C0 -> C1
D  <- U0,P0,C0,C1
E,F <- D
G  <- C0,C1
R  <- U1,U0,P1,P0,C0,C1,D,E,F,G
```

Every lower key binds the exact source and only its consumed stage/action/support,
recurrence-parent and fixed query/reward/risk/threshold facets. It does not absorb the
complete plan, request or role. `R` always binds the full plan, query, thresholds,
request and proof role; the selected root additionally binds the selected result.
Existing V0-043 plan-/threshold-bound rows and final result are admissible only at
`R`, never as lower temporal facts.

The exact stage-1 and stage-0 action-change cones are respectively
`P1,P0,C1,D,E,F,G,R` and `P0,C0,C1,D,E,F,G,R`. On `A1A1->A1A0`, the previously
computed stage-1 `A0` `P1` node is a historical hit, but its current descendants are
still derived under their exact parents.

All three arms resolve 55 logical slots. Request reset computes/hits `55/0`. Four
independent plan-ID cache partitions compute/hit `45/10`, because the final selected
request can return only to the Gray-`00` lower facts. One initially empty global DAG
computes/hits `35/20`. Cumulative request prefixes are:

```text
request reset:    11,22,33,44,55 computes / 0,0,0,0,0 hits
plan-partitioned: 11,22,33,44,45 computes / 0,0,0,0,10 hits
global DAG:       11,19,27,34,35 computes / 0,3,6,10,20 hits
```

Global per-slot compute/hit totals are `U1 1/4`, `U0 1/4`, `P1 2/3`, `P0 4/1`,
`C0 2/3`, `C1 4/1`, `D/E/F/G 4/1` each, and `R 5/0`. Only
`45-35=10` avoided constructions are attributed to cross-plan reuse; `55-35` also
contains same-plan candidate-to-selected reuse. Node counts are not transition
samples, total work or wall time.

Production performs zero target transition, catalogue, acquisition, refinement,
promotion and ground-optimizer calls. The independent verifier rebuilds the unchanged
V0-047 authority, all five authoritative roots and all three traces. It rejects wrong
source epoch/model, stage/action/plan/query/threshold/reward/role substitutions,
legacy-row injection below `R`, edge/cycle/affected-descendant attacks, cache prewarm/
overwrite/reorder/rollback, owner-copy and content-domain attacks.

Passing permits exactly:

```text
registered_h2_stage_local_bellman_recurrence_claimed = true
```

Generic H>1, cross-query, changed-threshold/model/reward, persistent cache, closed-loop
repair, sample reduction/efficiency, workload economics and official execution remain
false/null/`NOT_RUN`. V0-052's six canonical IDs are frozen in the normative spec and
must match independent replay. The next construction Gate must connect the authentic V0-047 first-to-final
V3 overlay row change to local model-facet invalidation, replanning and re-audit.
Normative identities and attacks are in `specs/H2_TEMPORAL_PROOF_DAG.md`.

All aggregate locks remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-051 identity-bound incremental proof-dependency DAG rule

Contract `1.14.0` freezes schema `1.0.0`, profile
`lmb_identity_bound_incremental_proof_dag_v0`, and success status
`CERTIFIED_IDENTITY_BOUND_INCREMENTAL_PROOF_DAG_CONTROL`. V0-050's exact memo key
and canonical artifacts remain unchanged. The content-addressed
`IncrementalProofDAGProtocolV1` freezes the ordered seven contexts, adjacent change
kinds, `H=1`, the two-candidate-plus-one-selected request cardinality, V0-049 family
binding and preregistration before execution. Its `protocol_id` binds every execution
and result.

The new control uses seven unique H1 contexts over the V0-049 V5 promotion; adjacent
contexts change exactly one of
`rho0`, regret tolerance, or risk tolerance. Each context enumerates two candidate
plans and separately certifies the selected plan, for 21 proof requests.

The registered proof graph is:

```text
U unrestricted Bellman arithmetic
P selected-policy Bellman arithmetic
C reachable proof obligations
D initial-support/root metrics <- U,P,C
E regret verdict               <- D
F risk verdict                 <- D
G external-coverage verdict    <- C
R full role-bound audit root   <- U,P,C,D,E,F,G
```

Trusted code derives neutral keys only from the registered semantic facets and exact
parent IDs. Every root binds the current query, complete thresholds, plan, request
and proof role; selected roots also bind the planner-result ID. Candidate roots never
authorize selection. Existing V0-043 obligations, bound/unrestricted/support rows and
robust bounds all contain `thresholds_id`; they are forbidden as neutral evidence and
must be freshly rematerialized by `R`. Every root result is byte-identical to the
unchanged monolithic V0-043 audit for the same request.

The frozen minimal invalidation closures in the global-DAG arm are:

```text
rho0 change   -> C,D,E,F,G,R
regret change -> E,R
risk change   -> F,R
```

Plan changes close `P,C,D,E,F,G,R`; model, horizon, reward, return-proof, formula,
authority or pinned source changes close all nodes. Numeric equality cannot excuse a
changed descendant. The request- and occurrence-reset controls intentionally recompute
supersets of these closures.

The exact matched totals are:

```text
requests / logical resolutions = 21 / 168 per arm
request reset computes / hits   = 168 / 0
occurrence reset                = 112 / 56
global DAG                      = 62 / 106
global U 1/20, P 2/19, C 6/15, D 6/15,
       E 10/11, F 10/11, G 6/15, R 21/0
```

Only `112-62=50` avoided node constructions are attributed to cross-context reuse;
`168-62` also includes within-context factoring. No scalar, wall-clock, I/O, lookup,
hash, total-work, or sample interpretation is licensed.

Receipts bind monotonic sequence, reset scope, context/request/role, node key/kind,
parents/output and cache pre/post states. Stores begin empty and are append-only.
Affected-descendant reuse/omission, missing/extra edges, cycles, wrong topology,
threshold-row
injection, role substitution, source/model/plan/authority mutation, prewarm/import,
overwrite, reorder, rollback, stale parent, cross-domain and owner-copy attacks fail
closed. Independent evaluation rebuilds the parent, runs 21 unchanged legacy audits,
replays all three stores, and requires byte-identical documents.

The sole new positive claim is:

```text
registered_h1_changed_query_incremental_proof_claimed = true
```

General/H>1/model-or-reward incremental proof, persistent cache, sample-tax/operator,
sample efficiency, total-work/wall-clock, official execution, scalar and break-even
claims remain false, null, or `NOT_RUN`. Canonical identities and attacks are
normative in `specs/INCREMENTAL_PROOF_DAG.md`.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```


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
- **2026-07-20 — 0.8.0:** Froze the Phase 3C certificate-triggered local-recovery slice over one immutable eleven-cell aliased safe-chain RAPM. Distinguished direct proof residuals from propagated ancestor uncertainty; froze the 12-state/32-pair frontier, 8-pair selected-action ancestor dependency, strict 40-pair/160-outcome total authorization, isolated cardinality-minimal eight-state/eight-decision overlay, retained abstract decisions, post-repair exact/sound goldens, evaluation-only J0 order, independent replay/forgery obligations, and explicit no-rebuild/no-fallback/narrow-claim statuses without changing Phase 3B.
- **2026-07-20 — 0.9.0:** Froze the Phase 3D general local-recovery Gate: exact slack/active causal-family search over the earliest `DirectBad` antichain; `40/160 -> 24/96` safe-chain authorization; finite-domain-minimal sparse affine worker capability; cap-aware joint deterministic value-risk search; the 257-assignment safe-chain and 25-assignment two-cell/two-member trade-off controls; full post-audit, independent replay/forgery obligations and explicit remaining one-shot/economics/discovery boundaries. Resolved `V0-RISK-004..006` without changing V0-029.
- **2026-07-20 — 0.9.1:** Added V0-031 to freeze Phase 3D as a verified consumer of the Phase 3C RAPM/BuildEpoch, pre-certificate upper bound, locality and authorization. Operational rebuild, closure, quotient/RAPM construction, post-binding pre-authorization ground access, `U_all` recomputation and exact hybrid lifting are forbidden and zero-counted. The binding-time 144-action catalogue supplies causal/ancestor checks; the current `16+8` authority is proven against the source `32+8`; materialization and patch-restricted sound audit perform exactly `16+8=24` steps. The operational certificate keeps exact fields null, while independent verifier reconstruction, exact lift (`317/16000`, 8 patched/12 abstract) and J0 remain evaluation-only.
- **2026-07-20 — 1.0.0:** Added V0-032 and profile `phase3e_accounted_dynamic_routing_v0`. Froze native-versus-comparison accounting, the eight shared resource axes, marginal strict-dominance routing, full domain-separated content IDs, typed upper/cap/cardinality/attestation chains, finite trusted budgets, negative-causal fallback, exact actual projection, explicit attempt/campaign terminal semantics, `acfqp_counter_registry_v1`, removal of operational host full replay, and estimate-before-execute access order. No scalar or official execution is opened; economics and counter-completeness remain `NOT_RUN` pending implementation and independent verification.
- **2026-07-21 — 1.0.1:** Added V0-033 without changing the contract-`1.0.0` route semantics: sealed-core/frozen-obligation two-stage operational accounting with exact manifests and receipts; invocation-typed standalone terminal/aggregate evaluation; runner-owned prior-WorkVector continuation authority; content-addressed runtime-tree CAS and single-use post-freeze executor factories; and denominator-preserving occurrence-level typed closure of selected-route exceptions with uniquely replayable native ownership. The four former scoped P0 implementation gaps are closed, while official execution remains false, scalar/break-even remain null, and both Phase 3E Gates remain `NOT_RUN` pending the remaining authorities, all-path instrumentation, rebuild/campaign replay and independent verification.
- **2026-07-21 — 1.0.2:** Added V0-034 and corrected Phase 3E's upstream query-time order to `verified manifest -> model-only RAPM contingent plan -> rectangular exact-sound audit -> PASS without ground / FAIL may authorize later ground binding`. Froze the H1 `PASS` and H2 `FAIL` goldens, implemented strict model-only `ABSTRACT_AUDIT` replay and the deliberately narrower plan-frozen retained-runtime exact-cache authority, and registered every new source/plan/policy/proof/audit/cache/orchestration/result domain centrally. This is a reusable-model-first control boundary, not evidence of automatic RAPM synthesis or generalization; isolated/native accounting, the PASS terminal, FAIL-to-run handoff, durable planner-free cache, real transaction 2, rebuild/retry, all-path hashes and independent bundle replay remain incomplete, so official/scalar/Gate locks do not move.
- **2026-07-21 — 1.0.3:** Added V0-035. Required retained `ABSTRACT_AUDIT=FAIL` authority before an opaque ground handoff and connected its frozen H2 plan/proof to Phase 3D causal estimation without replanning, reaudit, kernel transitions or execution, reproducing `16/8/24` frontier/ancestor/allowed pairs. Added strict retained-authority/native-work H1 `ABSTRACT_CERTIFIED` closure and a fresh `python -I` native producer whose exact partial-coverage blockers remain embedded and non-official. Added a proof-derived synthetic dependent-transaction benchmark that exercises the real two-transaction state machine and occurrence aggregation while explicitly retaining its test-only semantic-authority limitation. Automatic RAPM synthesis/generalization, production FAIL-to-route integration, production ground-derived transaction 2, sealed all-path accounting, rebuild/retry, durable preflight cache and independent bundle verification remain open; all official/scalar/Gate locks are unchanged.
- **2026-07-21 — 1.0.4:** Added V0-036. Registered the honest `ABSTRACT_FAILED_PREFIX`, connected the retained H2 failure through no-replanning ground handoff, production route authorities, strict marginal selection and one selected sealed factory, and embedded the still-unresolved preparation/accounting blockers so the bridge cannot self-promote to official. Added an independently source-replayed, TOCTOU-checked failed-prefix bundle and an eight-coordinate planner-free exact-cache preflight that deliberately cannot authorize infeasibility without a durable proof payload. Replaced copied module-token authority across the execution chain with exact internally minted live-instance/fingerprint checks, including full prepared-estimate member binding and a distinct post-freeze kernel derivative. Ground-derived transaction two, rebuild/retry, complete native hash/I/O/runtime accounting, durable exact proof, selected-route complete-bundle verification, automatic RAPM synthesis/generalization, scalar economics and both Gates remain open.
- **2026-07-21 — 1.0.5:** Added V0-037 without changing contract-`1.0.0` route semantics. Froze the canonical H2 preparation trace at 4 causal, 18 protocol, 3 integrity and 5 cap events while keeping hash/I/O/materialization exclusions and `RETAINED_POST_CORE_NOT_YET_OCCURRENCE_CHARGED`; closed the scoped successful LOCAL terminal/occurrence path; and added a fixed 54-role selected-route bundle whose highest claim is only `VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY`, never a transport-minted semantic certificate. Recorded bounded rebuild/retry as control-plane mechanics and established that the repaired canonical H2 transaction 1 certifies, making transaction 2 unreachable on that fixture and requiring a new dependent-horizon benchmark. Official execution remains false, scalar/break-even remain null and both Gates remain `NOT_RUN`; automatic RAPM synthesis/generalization is still the research objective, not a result of this infrastructure.
- **2026-07-21 — 1.1.0:** Added V0-038 and profile `lmb_feature_realized_reusable_rapm_v1`. Froze the query/J0/value/policy/held-out-free LMB construction API, the eleven-feature current-state registry, exhaustive 2048-subset enumeration, adjacent-value rational-midpoint `<=` atoms, exact ground-behavioural-oracle realization obligation, deterministic minimal selector, `action_count`/`(3/2,5/2)` and 25-state `25->5`/active-`18->3` goldens, locked registry/spec/certificate constants, strict content-addressed artifacts, bidirectional typed mismatch witnesses, the distinct 36-state target-11/action-count-7 negative control, full target/adapter/model/portable-registry independent rebuild attacks, and unchanged portable-RAPM reuse by two fresh-process in-coverage QuerySpecs. The new claim is automatic selection inside a preregistered human grammar under an exact behavioural target, not oracle-free unknown-quotient or feature invention, partial/learned dynamics, unknown-domain/scalable discovery, held-out or cross-domain generalization, or any aggregate/official/economics/counter Gate. All locks remain unchanged.
- **2026-07-21 — 1.2.0:** Hardened V0-038 by making its production API canonical and two-input only, separating restricted-grammar controls, freezing the feature implementation digest, enforcing exact JSON/runtime graph types and rejecting proxy substitution. Added V0-039/profile `lmb_direct_exact_homomorphism_v1`: full fixed 11-state/1-action grammar, 4096 direct candidates, exact label/action/dynamics homomorphism obligations, three typed witness families, `action_count + completes_match`, `(3/2,5/2)`, `25/18 -> 5/3`, four-entry singleton goldens, strict restricted/cap outcomes with role-separated production/control verifiers, poison-import target independence, independent rebuild and two-query portable reuse. V0-039 removes construction-time behavioural-target/signature dependence only for this exact finite fixed-grammar LMB slice; it is not feature invention, learning, scale/generalization or a Gate unlock. All official/scalar/Gate locks remain unchanged.
- **2026-07-22 — 1.3.0:** Added V0-040 and the non-blocking sample-efficiency authority sidecar. Production prior `source_unanimous_exact_v1` is derived only from unanimous exact mask-11/mask-13 source evidence and proposes one existing fixed-grammar hypothesis to a coverage-ID-held-out mask-7 target; target exact audit is sole authority. Froze source `14/14/14`, target `21/7/7`, zero-interaction and one-candidate telemetry, global-minimality false, two-query target reuse, broad-support-metadata-only semantics, and the role-separated empty-hypothesis `3/3/7` mismatch/fallback control. `SAMPLE_EFFICIENCY_GATE_NOT_RUN` does not block the mainline; no ranking, executed tail, sample saving or transfer claim is opened.
- **2026-07-22 — 1.4.0:** Added V0-041/profile `lmb_structural_typed_expression_dsl_v1`. From raw LMB primitives and fixed typed production templates it generates eight state/four action ASTs without V0-039 named-feature inputs, exhausts 4096 direct exact candidates, selects `cardinality(legal_actions)` plus `buffer_at_type(buffer_counts,selected_tile_type)`, and reproduces `(3/2,5/2)`, `25/18 -> 5/3`, four singleton entries and an independently rebuilt portable RAPM. Cap/state-only and AST/type/trace/digest attacks fail closed. This is fixed-DSL program generation, not unknown-semantic invention, partial/learned dynamics, generalization or sample efficiency; every official/scalar/Gate lock remains.
- **2026-07-22 — 1.5.0:** Added V0-042/profile `lmb_deterministic_observation_partial_rapm_v0`. A four-input, kernel/query-blind constructor and verifier consume only a pre-query allowlisted observation-authority graph, fixed manual coordinate ASTs and deterministic semantics. The literal eight-state/eleven-row fixture records seven offline-source observations and four explicit missing rows; Portable-model closure reconstructs all state/action/concretizer/realization relations and weighted ambiguities. Joint simplex atoms, horizon cap 6, external-boundary semantics, exact nested/name types, evidence native zeros and coherent re-sign attacks are frozen. Authority remains conditional, in-memory and non-transport; no automatic coordinates, plan/certificate, exact quotient, observer-truth, generalization or sample-efficiency claim is opened, and all Gates remain locked with sample efficiency non-blocking.
- **2026-07-22 — 1.6.0:** Added V0-043/profile `partial_fixed_plan_robust_audit_v0` with implementation schema `1.1.0`. The downstream auditor replays the hardened V0-042 source before reading registered query thresholds or one supplied deterministic plan, uses a canonical identity-bound `R_max=4` proof, charges joint unknown mass once, requires pointwise support regret plus distributional risk and external-coverage obligations, and emits only a robust fixed-plan certificate or earliest nonauthorizing proof hint. Froze the H3 certified and H1 missing-state negative-regression goldens, low-mass pointwise/external/known-threshold regressions, exact replay and invariant-violation attacks. This is not a planner, optimality/infeasibility proof, causal/local-recovery authority or Gate unlock; all locks remain unchanged.
- **2026-07-22 — 1.7.0:** Added V0-044/profile `partial_model_contingent_plan_proposal_v0` with implementation schema `1.0.0`. The source-first six-input producer exhausts all within-cap deterministic global abstract plans, audits each internally with V0-043, and selects by the frozen certified/risk-feasible/minimum-risk hierarchy. Froze production cap 65536 and its profile ID, typed zero-work cap exhaustion, finite reconstruction/audit telemetry, H3 certified selection, H1 nonauthorizing fallback proposal, cap-4 and two-query controls, independent full replay and authority/ordering/content attacks. The proposal is never certificate, feasibility/infeasibility, J0/ground-optimality, local-recovery, scale, sample-saving/economics or Gate authority; all locks remain unchanged.
- **2026-07-22 — 1.8.0:** Added V0-045/profile `lmb_query_free_observed_typed_coordinate_synthesis_v0` and the typed V0-044/V0-043 consumer boundary. Froze the exact 8-state/11-row/7-observed/4-missing source, 8+4 fixed DSL, complete 4096-candidate observation-only selection, boolean midpoint action compilation with unchanged V1 schema, six-cell/five-entry partial model, full retained synthesis authority, one-replay fixed-model planning and independent typed fixed-plan certification. H3 certifies reward/failure `4/0`; all-missing H1 remains a nonauthorizing unresolved frontier. No raw symbolization, learned/statistical latent dynamics, generalization, sample saving or official Gate is claimed; the next Gate is query-local evidence/overlay/refinement and promotion.
- **2026-07-22 — 1.9.0:** Added V0-046/profile `lmb_h1_query_local_exact_row_refinement_v0`. Replayed the complete V0-045/typed-plan/failed-audit chain, proved all four uniform H1 missing rows individually necessary under the fixed zero-risk row-completion scope, charged exactly four authorized exact-kernel calls, preserved the reusable base, constructed an `11/0` query-owned V2 overlay, replanned two abstract policies and independently certified reward/failure/regret zero. Promotion, general causal/multi-step claims, sample saving and every aggregate Gate remain locked.
- **2026-07-22 — 1.10.0:** Added V0-047/profile `lmb_h2_multistep_query_local_exact_refinement_v0`. Froze two full-chain evidence rounds: four time-zero transitions expose three evidence-derived active boundary states; three direct boundary catalogue calls register nine rows; the exact V0-045 coordinates reuse signature `(3,)`; an `11/9` V3 epoch moves the failed frontier to time one; and the `3 risk / 9 value / 9 distinct` second scope uses nine further transitions to build a `20/0` V3 epoch. Model-only replanning and independent audit certify reward/failure/regret `1/0/0` with 13 charged transition and 3 direct boundary catalogue calls, no ground optimizer, immutable base, no promotion and no sample-saving claim. Cross-query/held-out reuse, learned dynamics, sample intervention and every aggregate Gate remain open.
- **2026-07-22 — 1.11.0:** Added V0-048/profile `lmb_preregistered_h1_cross_query_promotion_v0`. Froze a target-blind source API and pre-source H1 target absent from V0-045; independently replayed and promoted the complete V0-047 `20/0` final model into scope-limited V4 without mutating the base or claiming neutral acquisition; and certified the held-out target at reward/failure/regret `1/0/0` with zero warm target ground calls. Recorded separate source `13+3`, promotion-replay `13+3`, warm `0+0`, and evaluation-only cold `3+1` lanes. Source amortization, a cold end-to-end planner, unrestricted promotion, statistical generalization, sample saving and every aggregate Gate remain open.
- **2026-07-22 — 1.12.0:** Added V0-049/profile `lmb_preregistered_h1_heldout_family_amortization_v0`. Froze three pre-source H1 targets and a ten-occurrence workload, promoted the complete V0-047 model into a separate three-state V5 scope, and paired ten zero-ground warm `1/0/0` certificates with ten source-blind complete cold H1 optimizers. Recorded exact source `(13,3)`, promotion-evaluation `(13,3)`, warm `20 candidates/30 audits`, cold `(30,10)` and componentwise prefix relations with diagnostic warm-dominance prefixes 5 and 9. Scalar/break-even, statistical generalization, sample efficiency and tax-operator claims remain locked; the next experiment is identity-bound certificate reuse/incremental proof.
- **2026-07-22 — 1.13.0:** Added V0-050/profile `lmb_identity_bound_certificate_memoization_v0`. Retained the unchanged V0-049 no-reuse workload, role-separated candidate and independent-selected proof requests, a complete semantic identity key with occurrence-bound receipts, owner-bound append-only runtime authority and independent replay. Nine trusted misses plus 21 exact hits preserve 20 candidates and ten certificates while reducing complete audit executions from 30 to nine. Cross-identity incremental proof, persistent cache authority, sample-tax/sample-efficiency, total-work/economics, scalar/break-even and all aggregate Gates remain locked; the next proof-reuse Gate requires an explicit proof-dependency DAG and affected-descendant re-derivation.
- **2026-07-22 — 1.14.0:** Added V0-051/profile `lmb_identity_bound_incremental_proof_dag_v0`. Factored the registered H1 audit into explicit `U/P/C/D/E/F/G/R` dependencies, kept all legacy threshold-bound rows at the freshly rebuilt role-bound root, and froze seven single-field-changed contexts with request/occurrence/global reset controls. The global DAG executes 62 node constructions and 106 hits versus occurrence-local `112/56`; only the resulting 50 avoided constructions are attributed to cross-context reuse. All 21 roots match unchanged V0-043 audits. H>1, persistence, sample-tax/sample-efficiency, total-work/economics, scalar/break-even and all aggregate Gates remain locked.
- **2026-07-23 — 1.15.0:** Added V0-052/profile `lmb_h2_stage_local_bellman_proof_dag_v0`. Over the unchanged V0-047 final query-local H2 V3 model, factored five Gray-order candidate/selected requests into eleven stage-local temporal slots. Request-reset, plan-partitioned and global arms compute/hit `55/0`, `45/10`, and `35/20`; only the ten global-versus-plan-partitioned avoided constructions are attributed to cross-plan reuse. The sole new claim is registered H2 stage-local Bellman recurrence. Generic H>1, changed query/model/reward, persistence, closed-loop overlay invalidation, sample efficiency, economics and official execution remain locked; six canonical V0-052 IDs are frozen in the normative spec.
