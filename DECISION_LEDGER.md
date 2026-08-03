# V0 Decision Ledger

**Status:** normative source of truth

**Ledger version:** 2.0.3
**Last updated:** 2026-08-03

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
| V0-053 | 2026-07-23 | Live H2 query-local epoch invalidation | FROZEN | Contract `1.16.0` registers schema `1.0.0`, profile `lmb_h2_live_query_local_epoch_invalidation_v0`, and status `CERTIFIED_REGISTERED_H2_LIVE_QUERY_LOCAL_EPOCH_INVALIDATION_CONTROL`. Its production runner consumes exactly the same eight upstream authorities as V0-047 and may not consume a completed V0-047 result or caller-supplied models, rows, plans, closure, cache, controls, or expected outcomes. It must freeze the first `11/9` V3 candidate DAG, DAG-derived proposal, and independent selected `t=1,h=1` failed root before deriving and executing the second request's exact nine authorized rows; only then may it freeze the immutable successor `20/0` V3, derive the row delta and affected proof closure, replan, and independently certify reward/failure/regret `1/0/0`. The exact delta changes nine time-one boundary rows from missing to observed. Because the model rows are stationary, both `U1/U0` scan them and both `P1/P0` consume the changed coord-3 realizations: the direct consumed-facet changes are therefore `U1/U0/P1/P0/C1`, while `D/E/F/G/R` are rebuilt as descendants and only the two distinct stage-0 `C0` constructions remain extensionally reusable across epochs. Request-reset, epoch-reset-global and continuous facet-DAG controls freeze `110/0`, `70/40`, and `68/42`; only `70-68=2` avoided constructions are cross-epoch reuse, never five C0 hits, transition samples, total work, bytes, or wall time. First and final planners both select the same semantic Gray `A0A0` schedule `(0,1,0,1,0,1,0,1)`; model-bound plan/proposal/root identities change, but V0-053 makes no semantic-policy-change claim. | Closes the live ordering and exact model-facet invalidation Gate left by V0-052 without retroactively changing V0-047 or using its completed result as post-hoc production authority. It remains a single registered H2 query-local correctness control, not generic changed-model proof, persistent cache, sample reduction/efficiency, economics, learned dynamics, coordinate invention, semantic policy change or official execution. | Eight-authority live runner and nine-input verifier; source-order protocol; immutable epoch/delta/invalidation manifests; facet-keyed temporal DAG; three matched controls; ten legacy-equivalent roots; operational/evaluation ground-access separation; stale-node, under/over-key, evidence-order, cache/owner, role and canonical-ID attacks. |
| V0-054A | 2026-07-26 | Same-query durable H2 proof state | FROZEN | Contract `1.17.0` registers schema `1.0.0`, profile `lmb_h2_same_query_durable_proof_state_v0`, and status `CERTIFIED_REGISTERED_H2_SAME_QUERY_DURABLE_PROOF_STATE_CONTROL`. The producer accepts only the owner-bound V0-053 result, freezes its exact final source chain, reconstructs and commits 30 lower H2 proof entries with zero `R`, and exposes no mutable `HEAD`. Two fresh isolated processes load the externally selected commit, semantically replay four candidates as `34/10`, require an exact model-derived payload, and run request-reset/occurrence-reset/durable arms totaling `110/0`, `70/40`, and `10/100`. Every durable `R` is fresh. Child output is untrusted: before success the parent exactly re-derives both complete occurrences from its verified lease, reporting separate `34/10` checkpoint and `190/140` worker-output validation telemetry. Evaluation rebuilds a fresh store/two processes and rechecks the original byte snapshot. | Closes only exact same-query/final-epoch cross-process lower-proof persistence. The 60 avoided worker-local constructions are not sample or total-work savings; the verifier is same-implementation deterministic replay, not an independent algorithm. Generic persistence, changed-query/model proof, semantic policy change, complete WorkVector/economics and official execution remain locked. V0-054B is a separate action-local strict-policy-switch Gate. | `h2_durable_transport_v1.py`; `h2_durable_proof_state_v1.py`; canonical payload/manifest/commit/load/occurrence/result schemas; exact source pins; fresh-process and untrusted-output binding; re-signed semantic/source attacks; byte-snapshot mutation and ground-guard tests; `specs/H2_DURABLE_PROOF_STATE.md`. |
| V0-054B | 2026-07-26 | One-row action-local H2 semantic switch | FROZEN | Contract `1.18.0` registers schema `1.0.0`, profile `lmb_h2_action_local_semantic_switch_v0`, model-only subprofile `lmb_h2_action_indexed_semantic_switch_v0`, and status `CERTIFIED_REGISTERED_H2_ACTION_LOCAL_SEMANTIC_SWITCH_CONTROL`. The literal seed-4 six-tile LMB first epoch is built with zero transition calls and contains exact `S+3N` rows with unique missing challenger `M` (`4/1`). Model-only H2 planning selects reachable `A0A0/N`, risk 0, but fails normalized regret `3/4`. The selected-support frontier excludes `M` and cannot authorize it. A non-authorizing unrestricted-challenger circuit identifies exactly `ROW_M`; a separate necessity proof and request activate a non-copyable, owner-bound, single-use authority behind a source-pinned process-local kernel gate. Exactly one `(x1,tile0)` transition is recorded. The immutable `5/0` epoch adds only `M`. Before final replanning, the live first-epoch cache independently verifies and freezes the complete 14-edge reverse-closure authority; final execution is impossible without it. The 18-node lower DAG changes from `18/0` to `10/8`, rebuilds three roots each epoch, and every submitted epoch graph is independently replayed from its exact model/query before the strict reward-0 `A0A0/N` to reward-1 `A0A1/M` switch is certified. | Closes the registered “certificate failure → one off-policy ground row → immutable epoch → exact action-indexed invalidation → strict policy change → recertification” loop. It does not prove generic causal minimality/H>1, durable or cross-query reuse, coordinate invention, partial/learned dynamics, sample/byte/CPU/wall-clock/total-work savings, economics, or official execution. Evaluation is same-implementation replay and is labelled accordingly. | `h2_action_indexed_proof_dag_v1.py`; `h2_action_local_semantic_switch_v1.py`; owner-bound source-pinned gate/authority/receipt/result; model/query semantic replay; pre-execution invalidation authority; fully re-signed graph, replaced-gate, incomplete-closure, early/no/duplicate-ground-call, copied-authority, overlay/policy and verifier-bypass attacks; `specs/H2_ACTION_LOCAL_SEMANTIC_SWITCH.md`. |
| V0-055 | 2026-07-26 | Two-generation durable action-local H2 recovery | FROZEN | Contract `1.19.0` registers schema `1.0.0`, profile `lmb_h2_two_generation_durable_action_local_recovery_v0`, transport subprofile `lmb_h2_durable_action_switch_transport_v0`, and status `CERTIFIED_REGISTERED_H2_TWO_GENERATION_DURABLE_ACTION_LOCAL_RECOVERY_CONTROL`. Before ground evidence, root-free C1 commits the exact first `4/1` model/query and 18 strict typed lower nodes. Fresh model-only P1 parses and semantically validates the checkpoint, operationally records `0 recomputed/18 loaded-reused + 3 fresh roots`, and reproduces the failed `A0A0/N` proof. Only after host verification may a V0-055 authorization invoke the source-pinned V0-054B runner, whose owner-bound `(x1,M)` call is the sole operational ground transition. Its immutable overlay projection is detached provenance, never transported ground authority. Fresh model-only P2 restores/reuses the first 18 lower nodes, performs the exact successor continuation as `10 recomputed/8 reused + 3 fresh roots`, and reproduces the strict reward-0 `N` to reward-1 certified `M` switch. Root-free C2 then commits the 28-lower-node union with 18 active and ten historical nodes; fresh model-only P3 records `0/18 + 3 fresh roots` and reproduces the final certificate. P1/P2/P3 are exactly three fresh processes with zero worker ground transitions. The 18 checkpoint semantic-validation obligations are not relabelled as native physical computations. Evaluation is separate same-implementation replay with one evaluation ground call and three evaluation launches, not an independent algorithm. | Closes only the registered durable composition of “failed proof -> one owner-bound ground row -> immutable overlay -> exact invalidation/replanning -> recertification” across two root-free lower-proof generations. It does not prove generic/crash-safe persistence, hostile-worker security, cross-query reuse, generic H>1 or H>2, generic action-local minimality, coordinate invention, partial/learned dynamics, sample/byte/CPU/wall/total-work savings, native-compute completeness, economics, or official execution. The next Gate is a preregistered matched multi-occurrence/multi-query workload; any Laplace/KG-OP sample-tax operator follows measured workload traces. | `h2_action_indexed_proof_dag_v1.py`; `h2_durable_action_switch_transport_v1.py`; `h2_durable_action_local_recovery_v1.py`; canonical root-free C1/C2 stores and typed node parsers; P1/P2/P3 fresh workers; host failed-proof verification and ground authorization; detached overlay provenance; source/hash/process/ground/store/owner attacks; full same-implementation replay; `specs/H2_DURABLE_ACTION_LOCAL_RECOVERY.md`. |
| V0-056 | 2026-07-26 | Preregistered durable H2 multi-query workload | FROZEN | Contract `1.20.0` registers schema `1.0.0`, profile `lmb_h2_preregistered_durable_multiquery_workload_v0`, and status `CERTIFIED_REGISTERED_H2_PREREGISTERED_DURABLE_MULTIQUERY_WORKLOAD_CONTROL`. Before its target-blind V0-055 source runs, it freezes threshold-only `Q1=(epsilon_regret=0,delta=0)`, `Q2=(3/4,0)`, `Q3=(0,1)` and order `1,2,3,1,2,3,1,2,3,1`. The exact Q1 source first fails on C1 (`4/1`, selected `N`, regret `3/4`), then and only then acquires one authorized `M` row and publishes certified C2 (`5/0`, selected `M`, reward/failure/regret `1/0/0`). W0 contains the full canonical 18-document active-C2 semantic projection (`21983` bytes; SHA-256 `b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55`), not only IDs. Fresh model-only targets derive regret/risk gates, selection, audits and three occurrence-bound roots from those semantic fields and exact parent topology; lower keys bind only the consumed threshold facet and ordered parent-node IDs. The append-only arm records `6 lower builders / 174 exact hits / 30 fresh roots` with W0/W1/W2 logical lower counts `18/21/24`; the matched C2-reset arm records `18/162/30`, retains ten typed W0 initializations, and records their scoped initializer/worker-observed store bytes with `query_store_io_complete=false`; both make zero target ground calls. A source-blind literal direct control, pinned to the source-independent four-row C1 projection and protected by a dynamic single-use `(x1,M)` guard, records exactly `10` ground calls, `10` complete catalogues, `40` policy evaluations and `10` optimizer calls, with paired action/value/risk/regret `M,1/0/0`. The implementation Gate, 21 registered attack cases and fresh-store evaluation replay pass; pins include campaign `8edf8a660fe3...`, evaluation `48e8919a0899...`, protocol `928b8233021b...`, semantics `5880e0a9a4d7...`, preregistration `2cde4f37b9e7...`, W0/W1/W2 `4e9deaec2baf.../8d15aae30b49.../8e33d23a1369...`, matched vector `f8fe8f4dd584...`, and reset-initialization vector `20339c4e312e...`. | Closes only the registered threshold-only source-before-target workload. The trace units are operation-family calls, not samples or complete CounterRegistry/WorkVector cost. The `18/162/30` tuple does not include or cancel reset-initialization I/O, while host lease/snapshot and verification rereads remain outside complete query-store I/O accounting. It does not authorize reward/horizon/action/dynamics/initial-support/structural changes, generic cross-query/H>2 reuse, generalization, coordinate invention, partial/learned dynamics, sample efficiency, byte/CPU/wall/total-work superiority, economics or official execution. | `h2_query_family_model_v1.py`; `h2_conditional_direct_ground_v1.py`; `h2_durable_multiquery_workload_v1.py`; `h2_durable_multiquery_workload_pins_v1.py`; full typed C2 semantic projection; consumed-facet proof keys; topological lookup-before-builder runtime; global/reset/direct controls; source-blindness, over/under-key, semantic-poison, selection-parent, roots/certificate, process/store, reset-initialization-I/O and scope-escalation attacks; `specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md`. |
| V0-057 | 2026-07-26 | Interleaved certificate-triggered durable H2 query-local epoch | FROZEN | Contract `1.21.0` freezes schema `1.0.0`, profile `lmb_h2_interleaved_certificate_triggered_durable_epoch_v0`, passing status `CERTIFIED_REGISTERED_H2_INTERLEAVED_CERTIFICATE_TRIGGERED_DURABLE_EPOCH_CONTROL`, and logical order `Q_R,Q_S,Q_R,Q_S,Q_R`, where new epoch-bound typed `Q_R=(3/4,1)` leaves the historical threshold registry unchanged and `Q_S=(0,0)` preserves strict V0-047 semantics. The pre-source scope binds all eight authorities and complete H2 semantics without future-derived IDs. Production constructs the authentic first `11/9` epoch; only the selected Q_S value/risk failure authorizes exact `3/9/9` rows with `3 safe / 6 failure`, producing final `20/0`. C1/C2 preserve the real strict core, C2 independently verifies complete C1 history, query facets and proof requests bind their exact roles/parents, and the exact update is `28/2`, C2 `58/30/28`. Native main/reset are `16/284` and `24/276`, projections `16/234` and `24/226`, operational total `40/560`, 12 launches, 60 roots and 23 events; host verification is `23/9/36/12/64/32/12`. All 85 registered tests pass. The comparison contains exactly one operational producer and one fresh same-implementation replay under the same frozen source pins; there is no third campaign or independent algorithm. Principal canonical IDs are frozen in the detailed V0-057 rule and normative specification (result `092c92708f67...`, verification `6330a3a6be2b...`, snapshot `4add6d49870f...`). | Advances V0-056 into one authentic certificate-gated query-local model-epoch change without promoting either V3 epoch. It does not prove generic changed-model/query reuse, H>2, automatic coordinates, partial/learned dynamics, generalization, sample reduction/efficiency, complete accounting, byte/CPU/wall/total-work superiority, economics or official execution. | `specs/H2_INTERLEAVED_DURABLE_EPOCH.md`; process-local claimed authority plus durable replay; positive, attack, deterministic-replay and same-implementation fresh-store suite passed. |
| V0-058 | 2026-07-26 | Observation-driven program closure and held-out H2 recovery | FROZEN | Contract `1.22.0` freezes schema `1.0.0`, profiles `lmb_observed_program_closure_partial_rapm_v0` and `lmb_observed_program_closure_heldout_h2_v0`, and passing statuses `OBSERVATION_CONSISTENT_PROGRAM_CLOSURE_PARTIAL_RAPM` and `CERTIFIED_OBSERVED_PROGRAM_CLOSURE_HELDOUT_H2_RECOVERY`. From only the preregistered `8/11/7` symbolic source graph, production closes the frozen human typed vocabulary to depth two, retains `215` semantic representatives (`174` state, `37` state-action), exhausts all `6650` optional-single-coordinate candidates, finds `1384` admissible candidates, and selects candidate `4013`: `cardinality(legal_actions)` plus `buffer_at_type(buffer_counts,selected_tile_type)<=3/2`. Its partial RAPM is `7 observed / 4 missing`. A source-log-held-out H2 target is frozen before synthesis; after full source replay, its one catalogue is registered but all three target rows remain vacuous. The selected audit fails at reward `[0,4]`, failure `[0,1]`; only then does the `1 risk / 3 value / 3 distinct` authorization permit exactly three target transitions. The safe row reaches an existing source state and reuses its observed second-stage dynamics without successor access. The immutable final epoch is `10/4` and independently certifies reward/failure/regret `1/0/0`. All 19 registered tests pass and the principal IDs are frozen below. The complete staged Python package is now approximately 6.5 MiB, so the content-addressed isolated-fallback runtime-source ceiling migrates from 6 MiB to the independently frozen 8 MiB sealed-manifest ceiling; the profile-ID change invalidates old route uppers, exact actual bytes remain charged, and no official Gate is unlocked. | Advances automatic world-model construction beyond a handwritten coordinate catalogue, but only inside one frozen human primitive/operator vocabulary and one finite deterministic symbolic log. It does not prove primitive/operator invention, raw symbolization, statistical/learned dynamics, generic H>2 recovery, broad held-out/cross-domain generalization, sample reduction/efficiency, complete accounting, economics or official execution. | `observed_program_closure_synthesis_v1.py`; `observed_program_closure_heldout_h2_v1.py`; complete 6650-candidate trace; preregistration/chronology/three-row/epoch/replay/overclaim attacks; isolated-fallback runtime-cap migration/replay; `specs/OBSERVATION_DRIVEN_PROGRAM_CLOSURE_HELDOUT_H2.md`. |
| V0-059 | 2026-07-26 | Multi-domain observed/statistical held-out campaign | FROZEN | Contract `1.23.0` freezes schema `1.0.0`, profiles `multidomain_observed_statistical_heldout_campaign_v0` and `g2048_d4_empirical_hoeffding_partial_rapm_v0`, and status `CERTIFIED_REGISTERED_MULTIDOMAIN_OBSERVED_STATISTICAL_HELDOUT_CAMPAIGN`. Before prospective model/plan identities it registers two distinct human schemas and twelve LMB/G2048 occurrences. LMB automatically composes/selects inside the V0-058 typed vocabulary, performs exactly three certificate-authorized target transitions on its first strict H2 occurrence, then executes two fresh model-only reuses. G2048 uses known D4 structure rather than discovering it; a probability-free seven-cell/six-row catalogue plus a trusted frozen aggregate ledger of `6*65536=393216` offline observations yields six nonzero-width statistical rows. Exact-rational Hoeffding/Taylor/union calibration freezes radius `1/128`, family tail `3/350` and confidence lower `347/350`. Robust enumeration selects `TOWARD,AWAY,AWAY`, reward `[3/64,3/64]`, failure `[9277983,75716127]/2147483648 < 1/20`, regret zero. Nine D4 point/uniform occurrences use zero online samples. Production accepts no G2048 kernel; standalone exact D4 replay contains value `3/64` and failure `99/5000` without promoting statistical evidence. All 15 focused tests and all 1242 repository tests pass. | Closes only the first registered two-domain exact/statistical evidence-composition campaign. It does not prove automatic D4/primitive discovery, shared cross-domain coordinates, raw symbolization, exact-sound statistical dynamics, broad structural/H>2 generalization, sample saving, complete accounting, economics or official execution. The 393,216 observations are an exposed sample tax, not a benefit claim. | `multidomain_statistical_campaign_v1.py`; typed schema/catalogue/ledger/calibration/model/preregistration/occurrence/work/result/verifier artifacts; count/order/evidence/runtime/kernel/implementation attacks; `specs/MULTIDOMAIN_STATISTICAL_HELDOUT_CAMPAIGN.md`. |
| V0-060 | 2026-07-27 | Raw replayable multi-context stochastic acquisition control | FROZEN | Contract `1.24.0` freezes schema `1.0.0`, profiles `g2048_raw_replayable_multicontext_partial_statistical_v0` and `g2048_certificate_directed_vs_uniform_acquisition_v0`, and status `CERTIFIED_REGISTERED_RAW_REPLAYABLE_MULTICONTEXT_ACQUISITION_CONTROL`. Without changing the canonical `99/100` safe-chain fixture, it preregisters three separately keyed spawn-law contexts `p=199/200,249/250,999/1000` and a point/uniform H2 query pair per context before any log/model/plan ID exists. An all-missing model-only proof selects `TOWARD,AWAY,AWAY` and authorizes exactly `ROOT_TOWARD,CHAIN_A_AWAY,CHAIN_B_AWAY`. The adaptive lane records 16,384 individual counter-based outcome draws for each of those three rows and keeps the other three legal rows explicitly vacuous; an independent control records all six rows. Exact-rational calibration freezes radius `1/64`, 54 obligations, family tail `27/700`, and confidence lower `673/700`. Both lanes certify reward `3/64`, risk `<1/20`, regret zero; each second context query reuses its immutable model with zero new draws. Production model/planner interfaces have no kernel and no exact probabilities. Standalone evaluation replays all `442368` individual nibbles and exact J0 risks `199/20000,249/31250,999/500000` over `3*5440` candidates. All 14 focused tests and all 1,256 repository tests pass. | Closes V0-059's aggregate-only evidence limitation only for this finite known-D4 simulation family. The all-six-row arm is a statistical control, not a matched direct-ground planner, so the adaptive/direct difference `147456` is not a sample-efficiency or tax-operator result. Automatic coordinates/symmetry, unknown support, broad structural generalization, exact-sound statistical promotion, complete accounting, economics and official execution remain locked. | `raw_multicontext_acquisition_v1.py`; packed individual draw/codebook/hash-chain, partial-model, authorization, occurrence, work, exact-comparator and verifier artifacts; kernel/API/context/aggregate/tamper/identity attacks; `specs/RAW_MULTICONTEXT_ACQUISITION_CONTROL.md`. |
| V0-061 | 2026-07-27 | Matched end-to-end adaptive versus cold direct-ground acquisition workload | FROZEN | Contract `1.25.0` freezes schema `1.0.0`, profile `g2048_matched_adaptive_vs_cold_direct_ground_v0`, and status `CERTIFIED_REGISTERED_MATCHED_END_TO_END_ACQUISITION_WORKLOAD_CONTROL`. It retains V0-060's three contexts and six point/uniform H2 occurrences but replaces the all-six-row abstract control with an occurrence-cold ground planner. The adaptive arm freezes three failed proofs, samples nine authorized abstract rows (`147456` individual draws), builds three `3/3` partial RAPMs, and reuses each context model once. The direct arm independently enumerates `78` ground state/action catalogues and `198` transition rows, records `4866048` individual draws, estimates `144` H1 and `54` root actions, evaluates `774` root assignments, certifies six deterministic ground plans, and performs zero cross-occurrence reuse. Both use radius `1/64`; exact-rational family accounting binds 18 adaptive plus 252 direct obligations, tail `783/43750`, and confidence lower `42967/43750`. Production planners receive no kernel/probabilities. Standalone evaluation replays all `5013504` observations, all 198 ground rows, both lifted/adaptive and direct plans, and six exact J0 problems. All 15 focused tests and all 1,273 repository tests pass. | Closes V0-060's unmatched-control limitation and licenses only the registered-workload observation `direct/adaptive raw draws = 33`. The adaptive arm uses a known human D4 prior and the direct arm uses known finite symbolic support. The result is not automatic hidden-space discovery, unknown-support RL, broad sample efficiency/generalization, or a Laplace/KG-OP sample-tax operator. Native fallback/noncertificate counts are zero; official execution, scalar/break-even and economics remain locked. | `matched_end_to_end_workload_v1.py`; preregistration, raw adaptive/direct evidence, cold ground plan/proof, work, comparator and verifier artifacts; kernel/API/row/reuse/tamper/identity attacks; `specs/MATCHED_END_TO_END_ACQUISITION_WORKLOAD.md`; `specs/TEST_EXECUTION.md`. |
| V0-062 | 2026-07-27 | Source-frozen, certificate-guarded sample-tax intervention | FROZEN | Contract `1.26.0` freezes schema `1.0.0`, profile `g2048_source_frozen_boundary_capability_operator_v0`, and status `CERTIFIED_REGISTERED_HELDOUT_SAMPLE_TAX_INTERVENTION`. Three source-only safe-chain contexts (`497/500`, `399/400`, `1999/2000`) contribute nine exact-kernel row enumerations and `147456` offline-source generative-oracle samples. Before any target evidence, the source builder evaluates all two-row subsets of the V0-061 failed-proof frontier and uniquely/unanimously proposes `ROOT_TOWARD + CHAIN_A_AWAY`, retaining `CHAIN_B_AWAY` as broad tail. The unchanged three V0-061 contexts and six occurrences are held out. Target-only intervals over six row enumerations/`98304` generative-oracle samples certify every occurrence with family confidence `347/350`; unchanged no-operator and cold-direct controls remain `147456` and `4866048` samples. A wrong proposal `ROOT_TOWARD + CHAIN_B_AWAY` fails in all three contexts, triggers exactly three tail acquisitions, and emits zero false certificates. The five evidence-event classes are explicit, with interaction/logged/synthetic native zeros for source/operator lanes. Standalone evaluation independently replays source evidence, the complete V0-061 control, both operator paths, and six exact J0 comparators. | Licenses only the registered held-out target-online reduction `49152` generative-oracle samples, exactly `1/3`, and the narrow claim that a source-frozen proposal plus target certificate is a sample-tax operator on this workload. Offline-plus-target work is `245760`, so offline-inclusive saving, broad sample efficiency, automatic coordinate/support discovery, official execution, scalar/break-even and all aggregate Gates remain false/null/`NOT_RUN`. The diagnostic source amortization is nine context-level savings and is not official `N_break_even`. | `sample_tax_operator_v1.py`; source/target preregistration, raw source blocks, five-class evidence counters, source subset assessments/prior, restricted target logs, target-only model/proof, wrong-prior fallback, work/campaign/comparator/verifier artifacts; 13 focused tests including leakage/tamper/kernel/identity attacks; `specs/SAMPLE_TAX_INTERVENTION.md`. |
| V0-063 | 2026-07-27 | Preregistered sequential source stopping | FROZEN | Contract `1.27.0` freezes schema `1.0.0`, profile `g2048_preregistered_sequential_source_stopping_v0`, and status `CERTIFIED_REGISTERED_OFFLINE_INCLUSIVE_SAMPLE_TAX_REDUCTION`. The complete V0-062/V0-061 target, no-operator, cold-direct and wrong-prior authorities remain unchanged. Before evidence, three ordered target-disjoint source contexts, one 4096-draw block per frontier row/context, minimum two/maximum three contexts, guard radius `1/64`, all two-row candidates and unique-unanimous stopping are frozen. Checkpoint one identifies the same prefix but must continue; checkpoint two freezes `ROOT_TOWARD + CHAIN_A_AWAY`; the third source context is not enumerated. Source work is exactly six row enumerations/`24576` generative samples. Target-only planning remains six rows/`98304` draws with confidence `347/350`; the no-operator and cold-direct controls remain `147456` and `4866048`, and the wrong prefix still yields three failures, three tail fallbacks and zero false certificates. Independent replay regenerates all acquired source draws, the complete matched baseline and six exact J0 comparators. All 13 standard/fresh-ID focused tests and all 1,300 repository tests pass. | Licenses only the registered-family offline-plus-online observation `24576+98304=122880 < 147456`, a saving of `24576` or `1/6`, and source reduction `5/6` relative to V0-062. The source guard is proposal-only, not a confidence certificate. The diagnostic context crossing is two and is not official `N_break_even`. Broad sample efficiency/generalization, automatic coordinate/support discovery, official execution, scalar/economics and aggregate Gates remain false/null/`NOT_RUN`. The next construction Gate returns to observation-driven coordinate/support proposals over a larger held-out structural family. | `sequential_source_stopping_v1.py`; ordered source logs, assessments/checkpoints, stopped evidence/prior, restricted target evidence, unchanged controls, work/campaign/comparator/verifier artifacts; 13 focused tests including post-stop access, draw/checkpoint/chronology/identity/implementation attacks; `specs/SEQUENTIAL_SOURCE_STOPPING.md`. |
| V0-064 | 2026-07-28 | Observation-driven relational coordinate/support synthesis | FROZEN | Contract `1.28.0` freezes schema `1.0.0`, profile `g2048_observation_driven_relational_support_v0`, and status `CERTIFIED_REGISTERED_OBSERVATION_DRIVEN_RELATIONAL_SUPPORT_FAMILY`. Before evidence it registers three complete H2 source structures, three structurally identity-disjoint held-out target structures, six target point occurrences, one depth-two relational grammar, and a complete optional-single coordinate search. From 144 anonymous source rows, with no query/target/kernel/group/frontier input to the producer, semantic closure is `7/19/56`; all 432 candidates are evaluated, 13 are admissible, and the selected coordinates are `cardinality_actions(legal_actions)` plus `cardinality_cells(adjacent_filter(survivor_cell,occupied_cells))`. They yield six anonymous supports and decisions `(1,2)->1`, `(1,4)->1`, `(2,2)->2`. Each target starts all-missing, authorizes eight root rows after the first failed proof and sixteen continuation rows after the second, then certifies two occurrence-bound queries from one immutable context model. The 24 rows are charged to context construction, not the first occurrence; both queries add zero rows after construction. Target probabilities come only from 16,384 replayable draws per row over registered symbolic outcome support. Exact-rational calibration gives radius `1/60`, 176 coordinate obligations, family tail `11/250`, and confidence `239/250`. A wrong proposal acquires 16 rows, fails risk with upper one, requires fallback, and emits no false certificate. Six occurrence-cold exact controls enumerate 108 rows and reproduce J0. | Licenses automatic coordinate selection and anonymous abstract-support proposal only inside the fixed human relational vocabulary, fixed 2x2 incidence graph, and registered rank-relative family, followed by target-only statistical certification and post-context-build query reuse. No D4 or named frontier enters construction. It does not license primitive invention, unknown outcome support, unseen graph geometry, cross-structural RAPM reuse, broad generalization, independent-algorithm verification, sample efficiency, official execution, scalar/break-even economics, or an aggregate Gate. | `relational_support_synthesis_v1.py`; source-completeness, full-search, generative-acquisition, typed evidence, occurrence-scope, fixed-concretizer, two-round recovery, wrong-proposal, exact-control, interval/identity/implementation and same-implementation replay tests; `specs/OBSERVATION_DRIVEN_RELATIONAL_SUPPORT.md`. |
| V0-065 | 2026-07-28 | Observation-driven cross-geometry relational RAPM | FROZEN | Contract `1.29.0` freezes schema `1.0.0`, profile `observation_driven_cross_geometry_relational_rapm_v0`, and status `CERTIFIED_REGISTERED_CROSS_GEOMETRY_RELATIONAL_RAPM_FAMILY`. Three pairwise non-isomorphic source graphs (`P4`, `K1,3`, paw) contribute 120 complete H2 rows over 51 states. A kernel/target/query-free producer closes 262 syntactic programs to 42 semantic representatives, exhausts 25 integer state/action pairs, finds two admissible pairs, and selects `cardinality_actions(legal_actions)` plus `cardinality_cells(adjacent_filter(survivor_cell,occupied_cells))`; its honest source sound-alias width is `99/100`. The proposal contains only ASTs and an anonymous support-key schema, never source dynamics or decisions. Non-isomorphic held-out `C4`, diamond and `K4` instantiate target-local supports and independently acquire `16+32`, `20+40`, and `24+48` rows, respectively, at 65,536 replayable draws per row. Base target audits are `CERTIFIED/FAILED_RISK_OR_REGRET/CERTIFIED`; only the failed diamond proof may search the source-frozen optional registry, whose four candidates select `rank_degree_signature` plus survivor degree, after which all `3/3` target contexts certify and six occurrences reuse only their context-local models. | Licenses only bounded held-out non-isomorphic graph transfer of a source-observed relational coordinate/support schema, target-local statistical dynamics and replanning, and one certificate-triggered source-registry refinement. It does not license source/cross-target dynamics transfer, cross-structural RAPM reuse, target-time primitive/program invention, broad graph generalization, a second domain, unknown outcome support, independent-algorithm verification, sample efficiency, official execution, scalar/break-even economics, or an aggregate Gate. | `relational_graph_core_v1.py`; `cross_graph_relational_support_v1.py`; `cross_geometry_rapm_v1.py`; complete closure/search, two-round target evidence, local refinement, no-transfer, legacy, semantic/unregistered OOD, permutation, identity/transplant, cold-control, raw-draw and same-implementation replay tests; `specs/CROSS_GEOMETRY_RELATIONAL_RAPM.md`. |
| V0-066 | 2026-07-28 | Variable-cardinality two-domain relational RAPM | FROZEN | Contract `1.30.0` freezes schema `1.0.0`, profile `variable_cardinality_two_domain_relational_rapm_v0`, and status `CONDITIONAL_TWO_DOMAIN_VARIABLE_CARDINALITY_RAPM_CLOSED`. One independently replayed 120-row anonymous graph source synthesizes a dynamics-free portable skeleton with exact programs `cardinality_actions(legal_actions)` and `cardinality_resources(linked_filter(action_anchor,active_resources))`. The graph consumer holds out vertex counts 5 and 6: W5 and K6 produce complete conditionally certified H2 contingent plans from 22 and 60 target-local rows, while K6-minus-edge exhausts nine fresh target candidates without a sound cover and invokes a charged 60-row exact fallback. A second-domain LMB consumer binds the same action AST through a query-neutral seven-row bridge and builds three separate two-support statistical models from 98,304 target draws, with zero operational exact ground rows. Source registry/dynamics and cross-target row imports are all zero; six wrong-arm transplants fail closed. A Boole union bound combines arm tails `287/250000` and `2/125` without a cross-arm-independence assumption, giving conditional confidence `245713/250000`. All 62 focused and 1,412 repository tests pass. | Licenses only this registered proof that one source-observed portable relational skeleton can be instantiated across vertex counts and in a second domain while target contexts, bindings, evidence, models and dynamics remain isolated. Automatic synthesis is confined to a human relational-role ontology and frozen grammar. Graph probabilities are conditional on the registered SplitMix64/IID simulator assumption; LMB probabilities are conditional on the registered SHA-256 random-oracle/IID assumption. LMB planning is domain-specific. Independent verification covers source synthesis only; target verification is same-implementation. It does not license primitive/ontology invention, generic model-selected planning, observational OOD generalization, changed-query reuse, sample efficiency, official execution, scalar/break-even economics or an aggregate Gate. | `portable_relational_skeleton_v1.py`; `portable_relational_independent_verifier_v1.py`; `variable_order_graph_rapm_v1.py`; `cross_domain_lmb_rapm_v1.py`; `variable_cardinality_multidomain_campaign_v1.py`; source-boundary, fresh target-closure, raw/rejection replay, full-policy, fallback, wrong-binding, no-transfer/OOD, permutation, identity/transplant, union-calibration and claim-lock tests; `specs/VARIABLE_CARDINALITY_TWO_DOMAIN_RELATIONAL_RAPM.md`. |
| V0-067 | 2026-07-28 | Target-local sequential sample-efficiency control | FROZEN | Contract `1.31.0` freezes profile `v0067_real_factorial_campaign_v0`, Gate profile `v0067_v0066_graph_factorial_sample_efficiency_v0`, and the four checkpoints `2048/4096/8192/16384`. Uniform-Beta likelihood-mixture confidence sequences are exact-rational and time-uniform at those checkpoints. Fixed and sequential streams are seed-paired and raw-prefix verified; the sequential implementation generates only the consumed prefix. On registered W5 and K6 positives, quotient sequential planning consumes `425984` target draws versus `737280` for the matched cold direct-ground route, saving `311296 = 19/45` draws, while the fixed routes consume `10747904` and `11796480`. K6-minus-edge remains a no-cover control with a charged 60-row exact feasible fallback. Eight deduplicated physical confidence authorities form four Boole-combined families with joint tail `97/25000` and confidence `24903/25000`. The source-only meta-prior changes proposals but not target prefixes, so its target main effect and offline-inclusive amortization are both zero. | Licenses only the registered positive-endpoint target-draw reduction caused by sequential stopping. It does not license broad sample efficiency, unknown-support learning, total-work or wall-clock savings, a meta-prior advantage, official execution, scalar break-even, workload economics or counter completeness. Exact support descriptors and exact fallback/evaluation remain separate lanes. Same-implementation replay is not an independent planning algorithm. | `sequential_bernoulli_acquisition_v1.py`; `variable_graph_direct_sequential_v1.py`; `factorial_sample_efficiency_gate_v1.py`; `v0067_factorial_campaign_v1.py`; raw-prefix, checkpoint, fixed/sequential pairing, family-confidence, no-cover fallback, identity/tamper and claim-lock tests; `specs/TARGET_LOCAL_SEQUENTIAL_SAMPLE_EFFICIENCY.md`. |
| V0-068 | 2026-07-28 | Observation-discovered partial-support H2 planning | FROZEN | Contract `1.32.0` freezes schema `1.0.0` and profile `observation_discovered_partial_support_campaign_v0`. The operational planner receives replayable realized transition tuples but no exact atom ordinal/count, support list, spawn law or probability. Each row uses 64 discovery tuples to freeze observed joint support and fresh validation at `2048/4096/8192/16384` over that support plus one adversarial `OTHER`; exact-rational uniform-Beta likelihood-mixture confidence uses row-epoch tail `1/64000`, at most 16 discovered atoms and a preregistered 512-authority family cap, giving conditional confidence `124/125`. W5 direct/quotient first certify at `4096`. K6 direct first certifies at `8192`; its base quotient and coordinate candidates fail, and the sole causally authorized support transaction charges `249728` new observations but still fails risk (`1321268563/17179869184 > 1/20`), so quotient first certifies at `16384`. K6 direct/quotient unique raw totals are `165120/578688`; construction passes but matched observation advantage is false. K6-minus-edge freezes `delta=2847/20000` between exact-ground `2277/16000` and base-lift `11393/80000`, so both lanes use the same complete-search exact feasible fallback. | Licenses only the registered finite H2 construction result that discovery-frozen support plus adversarial `OTHER` can drive robust direct/quotient planning, one immutable fail-closed support epoch and matched fallback without an operational exact support oracle. The SplitMix64 implementation is deterministic replay, not an IID proof: `exact_iid_implementation_claimed=false`, `formal_exact_iid_plan_certificate=false`, and every positive is conditional on the idealized target-local uint64 IID authority. It does not license exact-support recovery, raw symbolization, primitive/legal-action/ontology invention, broad generalization, H>2, sample efficiency, total-work economics, independent-planner verification or project completion. No second support promotion is authorized. All official/economics/counter locks remain. | `transition_tuple_observer_v1.py`; `partial_support_confidence_v1.py`; `observation_support_graph_acquisition_v1.py`; `observation_support_h2_closure_v1.py`; `observation_support_relational_adapter_v1.py`; `observation_support_graph_model_v1.py`; `partial_support_robust_planner_v1.py`; `observation_support_coordinate_refinement_v1.py`; `partial_support_expansion_authority_v1.py`; `observation_support_promoted_h2_consumer_v1.py`; `partial_support_family_confidence_v1.py`; `observation_support_exact_evaluation_v1.py`; `observation_support_campaign_v1.py`; complete row/family/role replay and support/stream/simplex/`OTHER`/epoch/fallback/access-order attacks; `specs/OBSERVATION_DISCOVERED_PARTIAL_SUPPORT.md`. |
| V0-069 | 2026-07-29 | Bounded second distinct-row support transaction | FROZEN | Contract `1.33.0` freezes schema `1.0.0` and profile `k6_two_distinct_row_support_transactions_v0`. Starting from the immutable failed K6 transaction-1 epoch at checkpoint `8192`, the probe recomputes all eligible different-row, selected-policy `OTHER -> 0` counterfactuals against that mixed model. It finds 49 fresh candidates and no individually causal row, then closes as `NO_SOUND_DIFFERENT_ROW_COVER` before authorization: transaction-2 observations, global-`16384` access, transaction 3 and exact evaluation are all zero/absent. | Rules out only one additional individually causal row under the registered transaction-1 model and plan. It does not rule out joint row interactions, alternative coordinates or policies, and it opens no sample-efficiency, generality, economics, official-execution or project-completion claim. | `observation_support_second_transaction_v1.py`; complete candidate, identity, history, cap, zero-access, schedule and replay tests; `specs/K6_TWO_DISTINCT_ROW_SUPPORT_TRANSACTIONS.md`. |
| V0-070 | 2026-07-29 | Model-only minimal-pair support-recovery screen | FROZEN | Contract `1.34.0` freezes schema `1.0.0` and profile `k6_model_only_minimal_pair_support_recovery_v0`. A fresh candidate registry reconstructs the same 49 K6 rows without treating V0-069 evidence as authority, replays all 49 singleton overlays and then all `C(49,2)=1176` canonical pairs through complete selected-policy H1-to-H2 recurrence, and independently verifies all 1225 obligations. Every singleton and pair remains failed, so the registered result is `NO_SOUND_FIXED_PLAN_PAIR_COVER` with zero observer draws, promotions, operational full replans, exact calls and global-`16384` access. A separate finite positive control proves the recurrence detects genuine pair-only interactions. | Closes only the cardinality-at-most-two, current-selected-policy frontier hypothesis. It does not authorize brute-force `k=3`, claim that the dormant materialization branch was exercised, or establish sample efficiency, automatic hidden-space discovery, generality, economics, official execution or the overall objective. The next intervention must rank or reject acquisition from source-frozen, target-evidence-gated proof information while leaving the target-local certificate unchanged. | `observation_support_joint_pair_recovery_v1.py`; full topology, independent recurrence, positive interaction, zero-access, cap, schedule, identity/transplant and exact 19-row sample-boundary tests; `specs/K6_MODEL_ONLY_MINIMAL_PAIR_SUPPORT_RECOVERY.md`. |
| V0-071 | 2026-07-29 | Source-guided certificate-sensitive acquisition audit | AUDITED / GATE NOT RUN | Ledger `1.34.1` freezes only the non-closure boundary for proposed target contract `1.35.0` and profile `source_frozen_certificate_sensitive_greedy_acquisition_v0`; it does not ratify either as the current completed construction contract. The checked-in mechanics compute exact per-context normalized midranks, `q=mean`, `worst=min`, disagreement `q-worst`, abstention above `1/4`, multiplier `1/2+(3/2)q`, and the same-prior wrong control `q -> 1-q`. Target-current-model one-row zero-`OTHER` slack gains are nonnegative ranking signals only; deterministic selection and authorization freeze before materialization, and synthetic receipts alone can exercise robust replanning. | The Gate is not run because source gains are still caller-supplied rather than semantically replayed from bound source models/audits/raw evidence; the v1 portable feature includes sample-dependent support documents and `OTHER` mass; no real authorization-bound target observer/materializer exists; round 2 does not implement the required independently fresh current-plan/frontier authority; and verification is same-implementation rather than an independent complete bundle replay. Real K6 can stop only at authorization, cap exhaustion or no positive gain. Positive controls are named `SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_*` and cannot support target acquisition, transfer, sample-efficiency, independent-verification, contract-`1.35.0`, Gate-pass or project-completion claims. Current completed contract remains `1.34.0`; all official/economics/counter/sample-efficiency locks remain unchanged. | `certificate_sensitive_greedy_acquisition_v1.py`; mechanics and attack tests only; `specs/SOURCE_FROZEN_CERTIFICATE_SENSITIVE_ACQUISITION.md`; a future revision must add verified source replay, a sample-invariant portable feature, real target materialization, fresh round-2 frontier reconstruction and an independent complete-bundle verifier before proposing Gate closure. |

| V0-072 | 2026-07-29 | Transfer-guided adaptive observation acquisition draft | NONAUTHORIZING DRAFT / TARGET LOCKED / GATE NOT RUN | Ledger `1.34.6` extends the audit-corrected prerequisites for proposed contract `1.36.0`, schema `2.0.0`, and profile `transfer_guided_adaptive_observation_acquisition_v1`; completed construction contract remains `1.34.0`. The draft freezes the clean-generation K7/W7/K7-minus-two family, five arms/15 occurrences, cold `64+2048` row schedule, two-round cumulative cap, direct checkpoints, and `beta=1/300000` confidence allocation. A physical row may carry its initial confidence epoch plus at most two promotions (three epochs total); the global schedule still permits at most two promotion authorities per context and conservatively caps each arm at 480 authorities. Implemented prerequisites now include exact lazy planning/independent proof replay; the seven-roll-forward source archive plus a separately implemented archive-transform verifier; exact split-support confidence and campaign allocation; evidence-first public novel-child cardinality/selection plus independent row/count replay; immutable row transcripts and discovery-only cold-H2 closure plus independent verifiers; the anchor-locked observer/full epoch-chain; a disjoint synthetic K4 control; and nonauthorizing manifest readiness. | Audit corrections supersede nonauthorizing drafts `8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29` and `e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4` with nonauthorizing draft `7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2`; all have null execution manifests and none is an anchor. The latest correction adds `DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE`, which is distinct from adaptive incremental/two-round exhaustion and from infeasibility. Eight earlier development identities remain retired; no tape, artifact, endpoint, or campaign output persisted. The real V0-068 campaign → production archive → independent archive-transform lane passes, but the independent verifier expressly consumes the same-implementation V0-068 campaign authority. Only the first `origin/main` commit containing a final non-null execution manifest and the final preregistration ID that binds it, whose parent lacks that final ID, can become the anchor. Registered row/model integration, relational/ground model construction, materialization, direct baseline, fresh round 2, campaign and standalone bundle verification remain incomplete; no sample-efficiency, held-out, transfer, official-execution, economics or completion claim opens. | `partial_support_confidence_v2.py`; `verified_source_acquisition_archive_independent_verifier_v2.py`; `public_novel_child_cardinality_authority_v2.py`; `public_novel_child_cardinality_independent_verifier_v2.py`; `row_bound_observation_core_v2.py`; `row_bound_observation_independent_verifier_v2.py`; `v072_synthetic_row_observation_adapter_v1.py`; `v072_cold_h2_closure_v1.py`; `v072_cold_h2_closure_independent_verifier_v1.py`; `v072_confirmatory_execution_manifest_v1.py`; prior V0-072 components; focused, real-source-integration, lock and attack tests; `specs/TRANSFER_GUIDED_ADAPTIVE_OBSERVATION_ACQUISITION.md`. |
| V0-074 | 2026-07-29 | Partial-support total lift and lossless execution acceleration | NONAUTHORIZING REPAIR CONSTRUCTION / FRESH SCIENTIFIC GATE NOT RUN | The V0-072 attempt-2 journal is frozen as a second historical `PROTOCOL_FAILURE`, not a campaign result.  The exhausted chain cannot run again.  Proposed contract `1.39.0` repairs the already-registered `OTHER -> ABSORBING_POLICY_ABORT_FAILURE` exact-lift rule: modeled selected children require their bound decisions, while every exact positive-probability child outside the frozen modeled support contributes failure one and zero continuation reward with a branch witness.  The repaired exact path independently replays the operational authority, exact row/atom partition, and reward/failure/regret envelope containment.  It additionally specifies a content-addressed frozen-source envelope and occurrence-level isolated process mechanics whose canonical merged output must be byte-identical to sequential execution.  The current archive/parallel worker registry is synthetic transport only and is not integrated with the production V0-072 proposal or campaign runner. | Supersedes only the pending-repair wording of ledger `1.34.7`; it does not rewrite either anchored attempt, reuse K7 evidence, change V0-072 scientific parameters, or open a third attempt.  K7 is retrospective regression only.  Any new sample-efficiency result requires a new preregistration, manifest and anchor plus fresh target identities/tapes and genuinely fresh held-out occurrences.  Applying the containment mechanism to a new scientific bundle remains `NOT_RUN`; V0-073 contracts `1.37.0` and `1.38.0` remain the earlier development-only VOI constructions and are not overwritten. | `specs/V072_ANCHORED_ATTEMPT_2_FAILURE.json`; `specs/PARTIAL_SUPPORT_TOTAL_LIFT_AND_PARALLEL_EXECUTION.md`; typed failure/journal verifier; partial-policy exact-lift witness and attacks; independent authority/partition/envelope replay; synthetic frozen-source transport verifier; sequential/parallel equivalence and child-failure tests. |
| V0-075 | 2026-07-29 | Fresh total-lift parallel confirmatory campaign | PRE-ANCHOR CONSTRUCTION / SOURCE FROZEN / TARGET LOCKED / GATE NOT RUN | Proposed contract `1.40.0` and profile `v075_fresh_total_lift_parallel_confirmatory_campaign_v0` define a new authority family rather than a V0-072 retry.  Three replicate contexts retain the public K7/W7/K7-minus-two structures.  The exact laws proposed during construction were publicly exposed and are now permanently `CONSTRUCTION_FIXTURE_ONLY`; production uses a law-free public dependency graph and may bind a separately held private environment only through a high-entropy salted opaque commitment.  The one-way authority chain is historical-exclusion registry plus public target-family generation plus a semantically verified compact source-proposal archive plus that opaque commitment, then a new execution manifest, final preregistration, first qualifying `origin/main` anchor, anchor-derived tape namespace and immutable 3×5 occurrence plan.  V0-075 now has a profile-neutral exact H2 core, law-free signed batch observation graph, parent-owned multistage lifecycle, observation-driven partial-support model/planner, row-specific total lift, private in-memory reveal/observer boundary, exact frozen source replay, strict manifest/preregistration and independent Git-anchor verifier, plus canonical process/CAS foundations. | Both V0-072 failure records and all historical target observations, models, plans, certificates, journals, results, caches and retry authority are forbidden scientific inputs.  The exact source replay has completed with `1,006,720` charged offline draws and zero target access; eight public artifacts and their tracked-source semantic replay are frozen.  A real construction positive control now traverses signed discovery, support freeze, validation, partial model, exact H2 planning and row-specific total lift without relaxing caps or thresholds.  This is not production evidence: the integrated adaptive occurrence worker, production total-lift terminal, reconciliation, endpoint, complete semantic role chain and first qualifying remote anchor remain incomplete.  Until those pass, target execution remains forbidden and sample-efficiency, official, scalar, economics and counter-completeness Gates remain false/null/`NOT_RUN`. | `specs/FRESH_TOTAL_LIFT_PARALLEL_CONFIRMATORY_CAMPAIGN.md`; eight `specs/V075_*SOURCE*` artifacts; tracked-source authority; batch observer and multistage lifecycle; partial-support backend/planner; adaptive proposal/round authorities; batch-native row-specific total lift; construction E2E/attack tests; private observer boundary; CAS/journal transport; manifest/preregistration and independent remote-anchor verifier. |
| V0-076 | 2026-07-30 | V0-075 portable semantic and private-replay authority closure | CONSTRUCTION / TARGET LOCKED / PRODUCTION REGISTRY INCOMPLETE | Contracts `1.60.0` through `1.68.0` replace the earlier assumption that a hash-complete portable occurrence bundle is itself semantic evidence.  The canonical bundle currently declares 67 roles.  Raw replay must cross the sealed `python -I -S` source/runtime boundary, reconstruct each producer-typed public object, bind every record to an iterative dependency proof, and keep unresolved private or downstream semantic claims explicit.  Contracts `1.64.0`–`1.66.0` reconstruct the raw public context, eleven-role M0 graph and observer-open binding.  Contract `1.67.0` reconstructs six signed-batch roles and uses an `O(V+E)` direct-edge dependency DAG; `SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` remains `UNRESOLVED_PRIVATE_REPLAY_CLAIM`.  Contract `1.68.0` adds a new observer-signed atomic private-replay attestation that performs private replay before signing within one trusted construction call; it is not a public proof of execution order and is not retroactively attached to old bundles. | Supersedes any interpretation that issuer tokens, same-implementation typed replay, hash-chain validity, an exact-shaped closure-verification object, or a generic observer signature proves private-law replay or all-role semantic closure.  A caller holding the generic signer can still sign a public claim; therefore production requires a signer-owning sealed observer service that owns the session from open through close and emits a new non-retroactive portable role.  M1B control roles, child/promotion authorities, source/code provenance, all-path native accounting, terminal/campaign closure and the full independent bundle verifier remain incomplete.  No fresh held-out identity, tape, law, observation or endpoint may be accessed before those prerequisites and a new final preregistration/manifest/anchor are frozen. | `specs/PORTABLE_PRODUCTION_SEMANTIC_CLOSURE.md`; `v075_portable_public_context_closure_v2.py`; `v075_portable_public_semantic_replay_v2.py`; `v075_portable_observer_open_binding_authority_v2.py`; `v075_portable_signed_batch_graph_authority_v2.py`; `v075_observer_signed_private_replay_attestation_v2.py`; raw replay, duplicate-outcome, mutation/transplant, 4096-node DAG, private-channel and residual signer-risk tests. |
| V0-077 | 2026-07-30 | Signer-owning sealed observer Stage A | CONSTRUCTION / NONCERTIFICATE / SESSION OWNERSHIP INCOMPLETE | Contract `1.69.0` starts a fresh sealed `python -I -S` child from a deterministic read-only source archive, passes private session material only through a separately sealed descriptor, and loads the registry-bound production observer signer only inside that child.  Its public request has no signer, private material, verification, old closure, B3 or result input channel.  Nonce, source/runtime/program, process, supervisor, journal and native work identities are strictly bound; every post-nonce staging, launch, capture, protocol or child-validation failure closes as a typed noncertificate.  Invalid child bytes are not serialized, but their domain-separated digest and byte count remain in the journal/work chain. | This is only the fail-closed transport and signer-ownership precursor.  The child deliberately does not own an observer session from open, performs zero private replay and zero B3 signatures, and returns `SESSION_OWNERSHIP_NOT_YET_COMPLETE` after a valid signer load.  It cannot upgrade an old closure or B3.  Process evidence remains a local attestation rather than cryptographic OS provenance, and all production, scientific, certificate, source/code, registry and held-out locks remain false. | `v075_signer_owning_sealed_observer_ipc_v1.py`; strict request/result replay, nonce, sealed-FD, crash/timeout, native-work, hidden-field, identity-transplant, invalid-child journal and no-post-hoc-upgrade tests. |
| V0-078 | 2026-07-30 | Portable M1B signed control graph | CONSTRUCTION / TARGET LOCKED / DYNAMIC SEMANTICS OPEN | Contract `1.70.0` reconstructs the 16 registered signed-control roles from the raw portable bundle and raw public-context authority after hardened M1A replay.  It verifies signed heads, semantic bindings, head-bound intents, receipts, appends, support freezes, open prefixes, control closure and reconciliation through an iterative direct-edge DAG.  Every executable ROOT authority is bound in journal order to the exact M0 root row, stage, lane, observer epoch and draw start/count/cap; template-only or wrong-row substitution fails.  Role states are exactly `FULL_PUBLIC`, `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` and `NOT_PRESENT_IN_OCCURRENCE`; absence is neither completion nor native zero. | Root-only registered K7 closes the generic and ROOT control roles publicly.  Present CHILD/PROMOTION authorities remain structural-only until their dynamic semantic producers are reconstructed, while absent roles remain explicitly absent.  The unresolved M1A private closure-verification role is never consumed.  Same-implementation replay, cached IDs, signer signatures and issuer tokens do not establish independent verification, source/code provenance, the complete 67-role registry, production, held-out access or certificates. | `v075_portable_signed_control_graph_authority_v2.py`; exact M0 root binding, 16-role tri-state/opaque propagation, private-verifier exclusion, signature/recurrence, wrong-row/template, dependency-role recomputation, stale-ID, raw-mutation and 4096-node iterative-DAG tests. |
| V0-079 | 2026-07-30 | Signer-owning complete observer lifecycle | CONSTRUCTION / SYNTHETIC POSITIVE CONTROL / NONCERTIFICATE | Contract `1.71.0` runs signer load, private reveal, observer open, the fixed two-batch root plan, journal close, exact private replay and B3 signing inside one fresh sealed-source child for `SYNTHETIC_REGISTERED_ROOT_ONLY_K7_V1`.  The caller supplies only public intent/registry/commitment/occurrence/session identities and a nonce; private seed and salt use a separately sealed descriptor, and no signer, private verification, old closure, old B3, observation result or caller session is accepted.  Exact fixture, arm/start/count/cap, failure-prefix, journal and work bindings are replayed. | Success is `ATTEMPT_CLOSURE_NONCERTIFICATE.COMPLETE_LIFECYCLE_CONSTRUCTION_NONCERTIFICATE`.  B3 is an observer-signed private-replay construction claim; the public verifier neither reruns the private law nor cryptographically proves process/order provenance.  This contract adds no portable role, does not upgrade the historical closure-verification record, accesses no held-out input and opens no production/scientific/certificate/source/code/registry lock. | `v075_signer_owning_complete_observer_lifecycle_ipc_v1.py`; request-channel, secret/signer/nonce, exact batch-plan, same-child, crash/timeout, typed failure, fixture/session/closure/B3 transplant, journal/work and private-serialization regressions. |
| V0-080 | 2026-07-30 | Portable M2 root boundary | CONSTRUCTION / TARGET LOCKED / TWO ROLES FULL PUBLIC | Contract `1.72.0` accepts only repository root plus raw bundle/context bytes, first invokes hardened M1B replay, and reconstructs `OCCURRENCE_IDENTITY` and `ROOT_EXECUTION` as `FULL_PUBLIC`.  Root execution is checked field-by-field against exact M0 occurrence/schedule/intents and M1B discovery/validation receipts, support freezes, semantic-authority bindings, resulting head and open-prefix chain.  The aggregate rederives the resolved-upstream registry, exact M1A private-verification registry and complete ordered M1B record/index/role/direct-edge spine. | The producer view is same-implementation reconstruction, not an independent execution algorithm.  The unresolved M1A private claim is not read or consumed.  Real root-only K7 replay, mutation/transplant and 4096-node regressions pass, but the remaining roles, source/code provenance, accounting, campaign closure, held-out access, production and certificates remain locked. | `v075_portable_root_boundary_authority_v2.py`; exact occurrence/root relations, registry/spine replacement, stale identity, wrong support/head/prefix and iterative-DAG tests. |
| V0-081 | 2026-07-30 | Portable M2 public lineage | CONSTRUCTION / TARGET LOCKED / PRIVATE FRONTIER EXPLICIT | Contract `1.73.0` starts from hardened M2 root replay and reconstructs `BATCH_PUBLIC_VERIFICATION` and `BATCH_SEQUENCE_VERIFICATION` as `FULL_PUBLIC`.  It rebuilds the `CONSTRUCTION_LINEAGE` public payload exactly, including occurrence, namespace, context, arm, signed batches, ordered public/sequence verifications, closure bytes and public context commitments. | `CONSTRUCTION_LINEAGE` remains `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` because its direct dependency on `SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` is the exact unresolved private frontier.  No private verifier/material is called or read, and no public projection, cached ID or self-reported DAG can upgrade that status.  Production, held-out, scientific, source/code, registry and certificate locks remain false. | `v075_portable_public_lineage_authority_v2.py`; producer-equivalent context/arm checks, raw-only entry, exact M2 spine, tri-state closures, stale/transplant and 4096-node iterative-DAG tests. |
| V0-082 | 2026-07-30 | Portable M2 construction lifecycle | CONSTRUCTION / TARGET LOCKED / PUBLIC LIFECYCLE SOURCES EXPLICIT | Contract `1.74.0` starts from hardened `1.73.0` raw replay and reconstructs lifecycle support evidence, support freezes and lifecycle events as `FULL_PUBLIC`.  It verifies the complete construction-lifecycle public bytes and verification projection, while adding content-addressed authority-local support-source edges separately from portable-declared edges and preserving both in the effective dependency DAG. | `CONSTRUCTION_LIFECYCLE` and `CONSTRUCTION_LIFECYCLE_VERIFICATION` remain `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` on the exact M1A private closure-verification frontier.  The cut calls neither private replay nor B3 and cannot convert public lifecycle bytes into a private-law claim.  Production, held-out, scientific, source/code, registry and certificate locks remain false. | `v075_portable_construction_lifecycle_authority_v2.py`; raw-order, exact support-source, three-edge-view, lifecycle mutation/transplant, tri-state and 4096-node iterative-DAG tests. |
| V0-083 | 2026-07-30 | Portable M2 live model epoch | CONSTRUCTION / TARGET LOCKED / ROW SOURCES PUBLIC / NUMERICAL FRONTIER EXPLICIT | Contract `1.75.0` starts from hardened `1.74.0` raw replay.  It reconstructs every live epoch only through `_build_epoch(replay_parent=False, register_operational=False, portable_prefix_replay=True)` using the current occurrence, route, open prefixes, controlled appends, support freezes and already reconstructed parent epochs.  It compares complete epoch canonical bytes and IDs, and requires the distinct-`binding_id` union of embedded row sources to equal the portable `LIVE_ROW_SOURCE_BINDING` registry exactly.  The three inherited dependency views—portable-declared, authority-local semantic and effective—remain distinct and byte-bound. | `LIVE_ROW_SOURCE_BINDING` is `FULL_PUBLIC`; `LIVE_MODEL_EPOCH` is only `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` on the exact `NUMERICAL_MODEL` plus `NUMERICAL_PLANNING_PROOF` frontier.  Operational epoch registration/parent validation, claimed typed epochs, private/B3/signer input, kernel/J0/K7/held-out access and certificates are forbidden.  Root/final identity deduplication and 4096-depth replay pass, but no numerical semantics or production authority is claimed. | `v075_portable_live_epoch_authority_v2.py`; raw-order, portable-build flags, operational-path exclusion, full-byte epoch/row union, parent/prefix/route/model/proof attacks, dependency-lane/frontier, root dedup and 4096-node tests. |
| V0-084 | 2026-07-30 | Portable M2 dynamic-child proposal | CONSTRUCTION / TARGET LOCKED / FOUR STRUCTURAL / TWO ABSENT | Contract `1.76.0` starts from hardened `1.75.0` raw replay and invokes only the current dynamic-child producer byte verifier with the exact reconstructed source epoch and namespace.  It requires byte-exact registries for causal edges, child states, discovery intents, validation templates, the singleton closure and singleton verification, including exact empty registries.  Every present proposal record receives a content-addressed authority-local binding to the exact source live epoch, numerical model and numerical planning proof; causal edges and child states additionally bind their numerical row, support descriptor, row source, observation row and support freeze scalar identities.  Forward authority-local dependencies use an iterative Kahn DAG while preserving portable-declared, authority-local and effective views separately. | The registered root-only cap-exceeded cut has exactly four `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` roles—causal edge, state, closure and closure verification—and exactly two `NOT_PRESENT_IN_OCCURRENCE` roles—discovery intent and validation template.  Every present frontier is exactly `NUMERICAL_MODEL` plus `NUMERICAL_PLANNING_PROOF`; no role becomes `FULL_PUBLIC`.  Operational freeze/epoch registry, legacy contract-1.51 authority, observer/worker/private/B3/kernel/J0/K7/held-out input, production and certificates remain forbidden. | `v075_portable_dynamic_child_proposal_authority_v2.py`; raw order, six-role equality, empty roles, source/scalar binding attacks, old-schema/operational/legacy exclusion, forward-edge/cycle/frontier, tri-state and 4096-depth tests. |
| V0-085 | 2026-07-30 | Portable M2 numerical planning | CONSTRUCTION / TARGET LOCKED / MODEL AND PROOF FULL / INPUT UNRESOLVED | Contract `1.77.0` starts from hardened `1.76.0` raw replay, enumerates the exact union of numerical models and proofs across every reconstructed live epoch, and reruns `plan_v075_construction_numerical_model_v2` for every epoch/route.  Standalone model and proof records must match those replays byte-for-byte.  Each model receives content-addressed authority-local edges to the exact occurrence, open-prefix verification and complete row-source records; each proof receives exact occurrence/model edges.  Live-epoch, reconciliation and result records are forbidden as reverse model dependencies.  The full three-lane graph is recomputed by bounded Kahn replay, closing the live epochs and four present dynamic-child roles transitively. | `NUMERICAL_MODEL` and `NUMERICAL_PLANNING_PROOF` are `FULL_PUBLIC`.  `CONSTRUCTION_PLANNING_INPUT` remains `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` with itself as the exact frontier: contract `1.73.0` exposes no legitimate issuer-owned typed private lineage, so this cut neither calls the construction-input compiler nor fabricates a private issuer object.  Its aggregate binds the typed graph and dependency DAG to the identical hardened upstream and exact source-binding set.  Private replay/input, operational epoch paths, observer/worker/B3/kernel/J0/K7/held-out access, production and certificates remain forbidden.  The fixed old raw-chain diagnostic exceeded its five-minute diagnostic timeout and is not counted as passing evidence; no fresh identity or scientific endpoint was accessed. | `v075_portable_planning_authority_v2.py`; all-epoch planner replay/mismatch, exact target/source registry, row-source identity, reverse-edge, source/DAG transplant, exact-type/currentness, three-lane propagation, cycle/4097/depth, determinism, pickle/gate and static forbidden-call tests. |
| V0-086 | 2026-07-30 | Portable construction-private replay | CONSTRUCTION / TARGET LOCKED / PRIVATE REPLAY LOCAL / INPUT UNRESOLVED | Contract `1.78.0` starts by completing hardened `1.77.0` raw replay before inspecting either ephemeral secret input.  It then reconstructs the exact public-context dependency chain, freezes the public private-environment generation profile, regenerates the private environment from a bounded in-memory seed, reseals it with a bounded in-memory salt, and requires the resulting commitment to equal the commitment already bound by the anchor, namespace, authorization and observer-open graph.  Only the registered construction lineage and lifecycle producer APIs may consume those ephemeral values.  The resulting closure verification, construction lineage, lifecycle and lifecycle verification must each match the singleton portable record byte-for-byte and by semantic ID. | `SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` closes only as `FULL_CONSTRUCTION_PRIVATE_REPLAY`; `CONSTRUCTION_LINEAGE`, `CONSTRUCTION_LIFECYCLE` and `CONSTRUCTION_LIFECYCLE_VERIFICATION` close as `FULL_CONSTRUCTION_TRANSITIVE`, never `FULL_PUBLIC`.  The three dependency lanes and authority scope are recomputed by a bounded iterative Kahn walk.  `CONSTRUCTION_PLANNING_INPUT` remains its own unresolved frontier and the compiler is forbidden in this cut.  Seed, salt, generated environment and private laws are not retained, serialized, directly hashed by this authority or emitted as secret digests; explicit currentness requires all five raw inputs and reruns the full chain.  This same-process construction replay is not a sealed production secret channel or process-provenance proof.  Source/code provenance, operational accounting, fresh held-out access, production, science and certificate Gates remain locked. | `v075_portable_construction_private_replay_authority_v2.py`; 1.77-first ordering, secret cap/uniform-error, exact producer type/byte/ID, commitment/context, source/transplant/currentness, three-lane scope, cycle/4097 and forbidden-API/secret-retention/lock tests. |
| V0-087 | 2026-07-31 | Portable construction planning-input replay | CONSTRUCTION / TARGET LOCKED / COMPILER REPLAY LOCAL / RECONCILIATION UNRESOLVED | Contract `1.79.0` starts by completing raw `1.78.0` before inspecting any typed object or secret input.  It extracts the exact M0 acquisition schedule and fresh construction lineage/lifecycle, calls only `compile_v075_construction_planning_input_v2`, and requires the singleton `CONSTRUCTION_PLANNING_INPUT` portable record to equal the compiler output by full canonical bytes and semantic ID.  The nested model must equal the unique standalone `NUMERICAL_MODEL` record selected by `(role, model_id)`, never by registry position.  Occurrence, namespace, repository/source binding, arm/route, lineage, lifecycle, lifecycle verification and every ordered row/batch/support-freeze evidence relation are rebound to the fresh producer graph. | `CONSTRUCTION_PLANNING_INPUT` closes only as `FULL_CONSTRUCTION_COMPILER_REPLAY`, never `FULL_PUBLIC`.  Its six authority-local producer edges are the exact occurrence, schedule, numerical model, construction lineage, lifecycle and lifecycle-verification records.  Source metadata is recomputed from the producer graph; target/model bindings require exact type, registry identity and currentness.  The inherited portable/local/effective lanes are checked before a bounded iterative Kahn recomputation.  `CLOSED_RECONCILIATION` and `MULTIROUND_RESULT` remain their own unresolved producer frontiers.  Ephemeral secrets are consumed only by the upstream raw replay and are not retained, serialized, directly hashed here or emitted as digests.  Source/code provenance, operational accounting, fresh held-out access, production, science and certificate Gates remain locked. | `v075_portable_construction_planning_input_authority_v2.py`; raw-1.78-first, compiler bytes/ID, exact schedule/model/source registry, row-evidence, same-role/duck/transplant/currentness, three-lane/cycle/4097, secret-surface and lock tests. |
| V0-088 | 2026-07-31 | Portable construction closed-reconciliation replay | CONSTRUCTION / TARGET LOCKED / OWNER REPLAY LOCAL / RESULT UNRESOLVED | Contract `1.80.0` starts with the five-input raw 1.79 replay.  The multiround-runner owner exposes one construction-only producer that accepts only schedule, final epoch, controlled closure, lineage and lifecycle—not a claimed input, proof or reconciliation.  It publicly replays the complete final epoch chain, control graph, signed lineage and lifecycle bytes; requires the final epoch to equal the complete closed heads/appends/freezes prefix and all occurrence/namespace/context/arm/route identities; recompiles the planning input and replans the proof; and only then uses the private reconciliation issuer inside its owning module.  The external authority requires the singleton `CLOSED_RECONCILIATION` record to equal this result by full canonical bytes and semantic ID. | Final epoch, model and proof are selected by the IDs named in the reconciliation record and must be unique; the epoch must also be the unique maximum epoch.  Schedule, controlled wrapper, signed control/batch closures, lineage, lifecycle, 1.79 input, epoch, model and proof each bind to exact portable records and form the local source edge set; `MULTIROUND_RESULT` is forbidden as a reverse source.  `CLOSED_RECONCILIATION` closes only as `FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY`; the planning-input scope is preserved and `MULTIROUND_RESULT` remains its own unresolved frontier.  Three dependency lanes, 4096-node Kahn replay, explicit five-input currentness and all production/science/accounting/certificate locks remain in force. | Owner construction producer in `v075_observer_signed_multiround_occurrence_runner_v2.py`; `v075_portable_construction_closed_reconciliation_authority_v2.py`; exact epoch/control/lineage/lifecycle/prefix, owner-only issuer, multi-record selection, target/source/transplant/reverse-edge, lane/cycle/4097, currentness/secret/pickle/lock tests. |
| V0-089 | 2026-07-31 | Portable construction multiround-result replay | CONSTRUCTION / ROOT-ONLY CAP PROFILE / TERMINAL PRODUCER REPLAYED / ALL GATES LOCKED | Contract `1.81.0` adds owner-public construction producers for the issuer-backed root execution and final multiround result.  Root execution is reconstructed from the exact replayed acquisition schedule, schedule verification and controlled open-prefix graph, including discovery/validation semantic bindings, receipts, same-row support freezes, head and order, then compared with the registered canonical bytes.  The result producer accepts no caller status or claimed result: it replays the root/final epoch chain, dynamic-child closure, any conditionally required child/promotion parents and the 1.80 reconciliation, derives the terminal state from verifier outputs, and contains the sole result-issuer call. | The external five-input authority must complete raw 1.80 first and is deliberately limited to the registered root-only `CHILD_ACTION_ROW_CAP_EXCEEDED` profile.  It proves all child-execution/promotion roles absent from the fresh bundle, takes the namespace from the fresh public-context resolution and cross-checks the controlled graph, reconstructs every parent before reading the singleton `MULTIROUND_RESULT` target, and compares final bytes and semantic ID only afterward.  Portable-declared, authority-local and effective dependency lanes remain distinct; bounded Kahn replay closes `MULTIROUND_RESULT` only as `FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY` and requires the aggregate frontier to be empty.  This does not cover authorized-child or promotion profiles and does not complete source/code provenance, the portable semantic registry, native accounting, campaign closure, production, fresh held-out science or certificates.  Five-input currentness, secret nonretention and every official/scientific/accounting Gate remain locked. | Owner APIs in `v075_observer_signed_multiround_occurrence_runner_v2.py`; `v075_portable_construction_multiround_result_authority_v2.py`; owner root/result, raw-first, target-after-producer, fresh empty-role, namespace/source, three-lane/cycle/4097/frontier, currentness/secret/pickle/lock tests. |
| V0-090 | 2026-07-31 | Portable construction semantic terminal closure | CONSTRUCTION / EXACT OCCURRENCE REGISTRY CLOSED / PRODUCTION LOCKED | Contract `1.82.0` starts with the exact five-input raw 1.81 replay and then joins its fully resolved typed dependency DAG to the unchanged contract-1.63 67-role declaration registry and a freshly regenerated legacy shape/content-ID attestation set.  Every one of the 49 records present in the registered root-only occurrence is covered exactly once by a new `FULL_TYPED_REPLAY` overlay binding its declaration, legacy attestation, record bytes/semantic ID, dependency node, source binding, resolver, all three dependency lanes, depth and unflattened authority scope.  The legacy two-role `COMPLETE`/65-role `INCOMPLETE` labels remain unchanged and are recorded as a separate historical lane rather than relabelled. | The remaining 18 declarations close only as `NOT_PRESENT_IN_VERIFIED_OCCURRENCE`, with exact zero-count evidence from the fresh 1.81 root-only empty-role registry; arbitrary missing roles cannot be promoted to verified absence.  Bundle records, legacy attestations and 1.81 DAG nodes must form the same ordered `(record_id,index,role)` bijection.  An independent bounded Kahn walk rejects cycles and foreign edges, all present frontiers must be empty, and the aggregate records a native-zero-inclusive authority-scope histogram whose counts equal the record count.  Only construction-qualified registry/typed-object/full-occurrence completion flags become true.  Unqualified registry completion, source/code provenance, accounting, production, fresh held-out science, official execution and certificate issuance remain false. | `v075_portable_semantic_terminal_closure_v2.py`; raw-first entry/byte verifier, exact 49/18 partition, fresh absence registry, legacy-status preservation, declaration/attestation/DAG bijection, three-lane/scope/histogram, cycle/4097, currentness/secret/pickle and lock tests. |
| V0-091 | 2026-07-31 | Construction source/archive/compile provenance | CONSTRUCTION / LOCAL COMMITTED SNAPSHOT / PRODUCTION LOCKED | Contract `1.83.0` starts with exact raw 1.82 replay and then includes every tracked `src/acfqp/**/*.py` file as a source-closure root, eliminating dependence on an incomplete static- or dynamic-import guess.  Every entry must be a regular nonsymlink file whose live worktree bytes, index stage-zero blob and local `HEAD` blob agree.  The historical 64-entry occurrence source manifest remains an exact subset lane; all additional ACFQP entries form a distinct semantic-code lane in a content-addressed DAG.  Git is fixed to a digest-bound `/usr/bin/git` under a replacement clean environment, and the complete repository/configuration identity is rechecked after the child operation. | All ACFQP sources are packed in a deterministic `ZIP_STORED` archive and bound to the tracked dependency lock, `pyproject.toml` and `/usr/bin/python3`.  A sealed `-I -S` child verifies and compiles every exact archive member without adding the archive to `sys.path`, importing a tested module or executing tested code.  The loaded-source claim is explicitly false: an adversarial source can forge an in-process import observer, so a real target-worker loaded-code receipt remains a later production obligation.  A separate verifier reconstructs Git, the two lanes, archive, runtime/compile evidence, DAG and all content IDs without importing or calling the producer/freezer/issuer.  Only construction-qualified all-tracked-source, archive, sealed-compile and two-lane claims become true.  Unqualified source/code authority, accounting, production, fresh science, official execution and certificates remain false; this is not a final manifest, remote-main anchor, OS attestation or third-party source-tree proof. | `_v075_construction_source_runtime_v2.py`; `v075_construction_source_code_provenance_v2.py`; `v075_construction_source_code_provenance_independent_verifier_v2.py`; raw-first, complete tracked-set, live worktree/index/HEAD, symlink, Git environment/executable, exact 64-entry subset, lane/DAG, deterministic archive, runtime lock, sealed no-execute compile, malicious-source forgery, final-currentness, independent-reconstruction and lock tests. |
| V0-092 | 2026-07-31 | Construction native-accounting boundary | CONSTRUCTION / REGISTRY-AND-GAP FOUNDATION / ALL-PATH LOCKED | Contract `1.84.0` accepts the contract-1.83 provenance bytes plus the original five raw inputs and first completes independent raw-1.83 verification.  It freezes the exact Phase-3E v1 registry/comparison/projection identities (`49` leaves, `34` operational), forbids mutation of that registry, reserves 13 BUILD/ACQUISITION path names distinct from REBUILD, and inventories all five historical V0-075 custom counter catalogues.  The reserved names intersect neither the 49 v1 paths nor the 87 distinct legacy custom paths; legacy custom paths also have zero intersection with v1.  Custom documents/totals are not `CounterRecord` evidence, and the registered root-only portable bundle contains no native WorkVector from which missing records or native zeroes may be inferred.  Path reservation does not freeze v2 unit/lane/scope/reducer/axis semantics or materialize `acfqp_counter_registry_v2`. | The unchanged 67-role semantic registry gains no accounting roles; a separate companion registry marks only the boundary, coverage matrix, terminal-derivation registry, role registry and readiness attestation present, while registry-v2 materialization, live WorkVectors/projections, loaded-source receipt, typed terminal/occurrence/campaign closure and independent complete-bundle verification remain required and absent.  The root-only `CHILD_ACTION_ROW_CAP_EXCEEDED` cause is registered to derive only `ROUTE_ATTEMPT / ATTEMPT_CLOSURE_NONCERTIFICATE / ATTEMPT_BUDGET_EXHAUSTED` while retaining the specific cause; it is never infeasibility.  Logical-occurrence closure remains deferred until a typed rebuild/retry policy and exhaustion proof are bound, and no terminal is materialized by this foundation.  Raw-1.83 Git/subprocess/I/O/hash/peak work was not recorded from its execution start and is explicitly a provenance/evaluation prefix excluded from actual route work, so no retrospective wrapper may claim all-path accounting.  All counter/economics/production/fresh/scientific/certificate Gates remain locked. | `v075_construction_native_accounting_foundation_v2.py`; `v075_construction_native_accounting_foundation_independent_verifier_v2.py`; raw-first, exact v1 identities, five-catalogue inventory, zero-intersection, path/stage reservation, 67-role nonmutation, companion absence, terminal derivation, custom-summary substitution, missing/native-zero, stale identity, self-reference and overclaim tests. |
| V0-093 | 2026-07-31 | Construction accounting-v2 schema | CONSTRUCTION / SCHEMA MATERIALIZED / LIVE WORK LOCKED | Contract `1.85.0` consumes only an exact issuer-backed independent verification of contract 1.84 and materializes `acfqp_counter_registry_v2` without changing the 49-leaf v1 prefix.  The scoped registry has 69 leaves, 53 operational leaves and 62 required leaves: the 13 previously reserved initial BUILD/ACQUISITION paths receive exact owner/unit/lane/scope/reducer/axis semantics, and seven separate `closure.reconciliation_*` operational leaves charge the real repeated compile/plan/replay work during closed reconciliation and terminalization rather than reusing `initial.*` or hiding it in protocol/hash work.  Accepted observer draws project one-for-one to `kernel_transition_calls`; random-word calls project to nonkernel work; rejection count is a required diagnostic subset and is not projected a second time. | Eight construction stage kinds are frozen separately from v1 route kinds, with exact nonzero-family exclusivity.  The unchanged eight shared axes receive exactly one coefficient-one term for each operational leaf, and a distinct actual-projection profile is content-addressed.  Counter records bind subject, stage instance and stage kind; WorkVector/projection schemas and an explicit-zero recorder mechanism exist, but no live record or vector is issued by this contract because stage-start/completion semantic authority and the 11 currently identified hash/integrity/protocol/I/O/process/peak recorder gaps are not yet closed.  That 11-path list is explicitly non-exhaustive: all 87 distinct historical custom paths still require operation-site mapping or a later registry revision.  Legacy custom documents and caller totals remain inadmissible.  Scalar cost/break-even, all-path accounting, typed attempt/occurrence/campaign closure, complete-bundle verification, production, fresh science and certificates remain false or `NOT_RUN`. | `construction_accounting_v2.py`; `v075_construction_accounting_schema_closure_v2.py`; `v075_construction_accounting_schema_independent_verifier_v2.py`; exact v1-prefix and 69/53/62 cardinality, metadata, diagnostic no-double-charge, eight-stage exclusivity, 53-term projection, content-ID/domain, missing/native-zero, cross-stage splice, reconciliation, sum/max, tamper, independent reconstruction and lock tests. |
| V0-094 | 2026-07-31 | Construction accounting successor registry | CONSTRUCTION / COVERAGE REPAIRED / LIVE WORK LOCKED | Contract `1.86.0` consumes only the exact independent contract-1.85 verification and freezes `acfqp_counter_registry_v3` as an additive successor; the 69 v2 leaves and metadata remain unchanged.  A source/operation audit proves the five historical catalogues contain 95 entries and 87 distinct paths, partitioned exactly as `7` re-instrument-at-existing-family, `18` decompose at native protocol/integrity/I/O sites, `51` derived-or-diagnostic views, and `11` genuinely missing operational families.  Those eleven families are registered stage-locally for confidence events, exact likelihood comparisons, interval-LP allocations, dominance comparisons, deterministic tie breaks, outcome projections, proposal-entry bindings, child-catalogue builds, quotient cells, semantic actions and concretizer ground actions.  The failed child-catalogue audit receives its own `audit.failed_*` leaf.  The resulting successor has 116 leaves, 99 operational leaves and 109 required leaves. | The stage taxonomy gains `OPEN_INCREMENTAL_ACQUISITION` and `OPEN_CHECKPOINT_REPLANNING`, so validation sampling and checkpoint replanning while an observer remains open cannot be relabelled as initial or closed work.  Initial root-epoch compile/plan belongs to `INITIAL_MODEL_BUILD`; `FAILED_ABSTRACT_PREFIX` owns only the verified child audit; the v2 interval-row compatibility path is governed by its registered `row_behavior_evaluations` unit.  All 99 operational leaves project exactly once with coefficient one onto the unchanged eight axes.  Historical custom summaries remain inadmissible, operation-site instrumentation and derived formulas remain incomplete, and hash/check/I/O/peak granularity plus stage lifecycle authority are still open.  No live record, vector, terminal or occurrence/campaign closure is issued; production, fresh science, scalar/economics and certificate Gates remain false or `NOT_RUN`. | `construction_accounting_registry_v3.py`; `v075_construction_accounting_registry_successor_v3.py`; independent successor verifier; exact v2 preservation, 116/99/109 cardinality, 10-stage exclusivity, 99-term projection, exhaustive 87-path partition, duplicate-summary, wrong-stage, failed-audit, tamper, independent reconstruction and lock tests. |

| V0-095 | 2026-08-01 | Construction accounting operation ownership | CONSTRUCTION / OPERATION OWNERSHIP CORRECTED / LIVE WORK LOCKED | Contract `1.87.0` independently replays contract 1.86 and freezes `acfqp_counter_registry_v4` as a second immutable additive successor. All 116 v3 leaf documents and their metadata remain unchanged. Eight newly audited required leaves place outcome projection and proposal binding at the actual initial-build/open-checkpoint stages and separately charge closed private-replay ground steps, random-word calls, rejections and aggregate rows. The result has 124 leaves, 106 operational leaves, 117 required leaves and 106 coefficient-one shared-axis projection terms. Registered v3 acquisition paths remain valid for architectures that truly execute those operations during acquisition; this owner-run path must record native zero there rather than move work between stages. | The K7 audit established that scientific acquisition is 4,224 accepted draws while the current closed private verification executes another 4,224 deterministic ground replay steps; the latter is operational work but not a second scientific observation set. A dormant, context-gated owned same-process no-full-replay hook is registered for the failed-child/result audit; it is not yet wired to an operational runner or live-evidenced, and legacy V2 portable replay remains the unchanged default. The nonfresh K7 root-cap manifest freezes the exact five-stage path, 13 audited direct-native hook sites and 10 explicitly pending common/hash/I/O/process/peak sites, but installs none of them. Trusted v3 lifecycle/start/event/completion, explicit-zero WorkVector and exact projection mechanics are implemented and structurally accept v4, but this revision issues no live event or vector. Operation-site hooks, 51-view formula closure, hash/check/I/O/process/peak completeness, typed attempt/occurrence/campaign closure, loaded-source receipt, production, fresh science, scalar/economics and certificates remain false or `NOT_RUN`. | `construction_accounting_registry_v4.py`; `construction_accounting_live_v3.py`; `construction_operational_context_v3.py`; `v075_k7_root_cap_operation_site_manifest_v1.py`; `v075_construction_accounting_operation_ownership_successor_v4.py`; independent v4 verifier; v3-leaf preservation, 124/106/117 cardinality, exact eight-addition ownership, 106-term projection, five-stage/23-site manifest, lifecycle/event replay, native-zero, reducer/reconciliation, context rejection, no-full-replay, tamper and lock tests. |
| V0-096 | 2026-08-01 | K7 source-owner operation-site correction | CONSTRUCTION / V1 HOOK CLAIM SUPERSEDED / AUDIT ONLY | Contract `1.88.0` preserves the immutable v4 registry and binds the exact contract-1.87 K7 manifest ID, but freezes `v1_direct_native_semantic_audit_passed=false` and forbids importing or reusing its sink. A strict source-owner audit classifies 43 v2 audit entries as `9` owner-matched v4 targets, `13` required native-zero families that are not executed on this path, `10` unresolved common/hash/I/O/process/peak sites, `1` derived-only route reconciliation view and `10` leafless batch-v2 counter-family gaps. Learned-support quotient/LP/dominance/tie/action counters, semantic-replay counters and abstract-planner counters cannot be charged for batch-v2 or dynamic-child work merely because their units look similar. The closure private replay operation is bound to `verify_loaded_private_observer_batch_closure_v2`, not the higher runner wrapper. | This correction supersedes only V0-095's K7 v1 direct-hook admissibility subclaim; it does not invalidate the generic v4 registry, lifecycle or projection mechanics. The audit manifest deliberately exposes no sink or emitter and issues zero live events, CounterRecords, WorkVectors, ComparisonVectors or projection proofs. The deterministic K7 trace has `4,224` acquisition draws and `4,224` closure replay steps; its aggregate-row count is `41`, not the previously considered `42`. An additive registry revision must first give the actual batch-v2 compiler/planner and dynamic-child operations their own owner-specific leaves. Common/hash/I/O/process/peak, formulas, typed closures, loaded-source receipt, production, fresh science, scalar/economics and certificate Gates remain false or `NOT_RUN`. | `v075_k7_root_cap_operation_site_manifest_v2.py`; exact v1 identity binding, owner/lane/stage classification, emitter absence, closure-source correction, derived-route exclusion, mutation/cross-owner attacks and lock tests. |
| V0-097 | 2026-08-01 | Batch-v2 known-owner accounting successor | CONSTRUCTION / ADDITIVE V5 FROZEN / LIVE WORK LOCKED | Contract `1.89.0` consumes the exact independent contract-1.87 verification plus canonical bytes for the strict-owner contract-1.88 manifest, preserves all 124 v4 leaf documents exactly and freezes 27 new required operational `SUM -> nonkernel_compute_events` leaves at their schema-assigned owners. Initial build gains eight batch-v2 compiler/planner families plus live-model outcome projection and support-descriptor construction; failed-prefix audit gains six dynamic-child scan/build/cap/attestation families; closed reconciliation gains nine batch-v2 compiler/planner families plus model-row and row-evidence-binding construction. The resulting v5 registry has `151` total, `133` operational and `144` required leaves, ten unchanged stages and `133` coefficient-one projection terms. Greedy interval semantics is one event per executed allocation step, not per outer extreme call. An implementation-independent verifier rehashes all 43 strict-owner site audits and reconstructs all additions, stage assignments, identities and projections from canonical manifest and verified v4 bytes without importing the v5 registry or producer. | This closes only the counter families currently proven missing by the strict K7 owner audit. Runtime owner match, runtime stage attribution and the complete event-boundary profile remain explicitly false; no source hook is installed and zero events, records, vectors or projection proofs are emitted. Hash/check/I/O/process/peak, derived formulas, typed terminal/occurrence/campaign closure and all-path coverage remain incomplete. Contract-1.88's `41` aggregate-row audit is one non-live fixture fact, not a K7-wide invariant: a live expected vector must bind the exact private commitment, namespace, occurrence and schedule. No value is backfilled from returned artifacts or historical summaries. Loaded-source receipt, production, fresh science, official execution, scalar/economics and certificate Gates remain false or `NOT_RUN`. | `construction_accounting_registry_v5.py`; `v075_construction_accounting_known_owner_gap_successor_v5.py`; independent verifier; strict-owner canonical-byte binding, exact v4 preservation, 27-addition ownership, 151/133/144 cardinality, ten-stage deltas, 133-term projection, greedy-step semantics, mutation/transplant/unknown-field and locked-Gate tests. |
| V0-098 | 2026-08-01 | Owner-bound partial-native K7 operation evidence | CONSTRUCTION / `PARTIAL_NATIVE_ONLY` / ALL-SITE LOCKED | Contract `1.90.0` preserves the complete v5 prefix and freezes `acfqp_counter_registry_v6` with 58 additions: `209` total, `182` operational and `202` required leaves, plus `182` coefficient-one projection terms over the unchanged eight shared axes and ten construction stages.  The K7 root-cap operation-boundary v3 catalogue contains exactly `150` entries and resolves each emittable event only from the trusted active stage plus a stage-neutral dispatch key; the runtime additionally binds the direct caller to the registered module's exact code object.  Owner-local hooks now cover the registered engine, observer, confidence/cache, live-model, dynamic-child and batch-planner primitives.  An owned-wrapper-exclusive, registered-cache-user-isolated cold epoch brackets the exact five-stage root-cap path and emits an immutable positive-event transcript whose coverage state is `PARTIAL_NATIVE_ONLY`, while preserving the underlying V2 result bytes.  The V0-075 execution-identity overlay reuses only boundary semantics, rejects the historical V0-072 execution identity and binds the exact public V0-075 K7 context, `NO_PRIOR` arm, adaptive route and root-cap terminal.  A producer-independent verifier reconstructs V6, all 150 boundary identities and the partial transcript hash chain from canonical bytes. | This is deliberately not complete accounting.  Unobserved work remains unknown and is never inferred as native zero.  The seven common additive paths `common.hash_invocations`, `common.integrity_checks`, `common.protocol_checks`, `io.output_bytes`, `io.read_bytes`, `io.staged_bytes`, `process.launches` and the two capacity paths `io.mounted_bytes_peak`, `memory.working_bytes_peak` still lack complete owner-native hooks.  The wrapper lock excludes only other owned-wrapper runs, and its cache lock excludes registered Bernoulli cache users; neither is a whole-process sandbox.  Same-process evidence callbacks are cooperative, deferred until authority closure and never receive accounting authority.  No `CounterRecord`, `WorkVector`, `ComparisonVector` or actual-projection proof is issued; no full live K7 owned-partial artifact has been frozen.  All-site accounting, typed terminal/occurrence/campaign closure, loaded-source receipt, production, official execution, official scalar/break-even, workload economics, fresh scientific endpoint credit and plan/infeasibility certificate issuance remain false, null or `NOT_RUN`. | `construction_accounting_registry_v6.py`; `v075_k7_root_cap_operation_boundary_manifest_v3.py`; `construction_accounting_partial_native_v1.py`; `construction_accounting_owned_runtime_v1.py`; `v075_k7_root_cap_execution_identity_overlay_v1.py`; `v075_k7_root_cap_owned_partial_runner_v1.py`; independent V6 verifier; exact-prefix/cardinality/projection, stage/owner/code-object dispatch, cold-cache, identity-transplant, unknown-versus-zero, abort-chain, source-hook and independent-replay attack tests. |
| V0-099 | 2026-08-01 | K7 accounting evidence-completion prerequisite | CONSTRUCTION / STRUCTURAL COVERAGE ONLY / FORMAL VECTORS LOCKED | Contract `1.91.0` freezes the exact disjoint disposition of all 202 required V6 leaves as `9 shared-resource + 8 derived reconciliation + 114 profile-static-zero + 71 owner-emittable`, with 89 concrete emittable boundary sites. Every closure starts with 202 `UNRESOLVED` rows and permits one immutable structural reference per row; syntactic coverage is named `STRUCTURAL_COVERAGE_COMPLETE_UNVERIFIED`, never complete evidence. The nine shared-resource receipt schemas distinguish recorded-but-unverified claims from typed unknown/unavailable values, bind SUM/MAX method, monitor, occurrence/window and content-derived charge keys, and always deny numeric projection. The 114 path-specific zero rules require stage, branch, loaded-code, execution-identity and semantic-verifier evidence; the 71/89 owner catalogue freezes coverage obligations without asserting runtime completion. A structural occurrence identity join binds owned result, transcript terminal, closure and receipt identities, while an ordered cutoff schema permits explicit terminalization work before the operational cutoff, forbids business work after that cutoff and then permits only explicit accounting/provenance tails. A composite prerequisite manifest content-binds every upstream authority and the exact six typed missing-evidence sets. | This revision closes the schema and fail-closed readiness boundary only. Bare hashes, caller-signed zero receipts, positive streams without owner-complete windows, unreplayed formulas and structural cutoff markers have no semantic authority. The current same-process K7 path deterministically remains not ready: all nine live shared-resource receipts, both peak measurements, route-context authority, 71 owner-complete windows, 114 zero obligations and eight reconciliation obligations are unsatisfied. No CounterRecord, WorkVector, ComparisonVector or projection proof may be emitted. Official execution, scalar/break-even, workload economics, counter completeness, fresh science and plan/infeasibility certificates remain false, null or `NOT_RUN`. | `specs/CONSTRUCTION_NATIVE_ACCOUNTING_COMPLETION.md`; evidence-closure, shared-resource receipt, exact readiness, profile-zero/owner-boundary, occurrence identity/cutoff and composite-prerequisite schemas; central domain registration; exact 202-partition, no-inferred-zero, structural-overclaim, identity/cutoff and mutation attack tests. |
| V0-100 | 2026-08-01 | K7 shared-resource live-supervision boundary | CONSTRUCTION / LIVE PRIMITIVES STRUCTURAL ONLY / SEMANTIC CLOSURE AND FORMAL VECTORS LOCKED | Contract `1.92.0` implements the first executable primitives for the nine shared-resource leaves. A single-owner live meter records typed exact-integer hash, named-obligation, byte-transfer, successful-launch and capacity claims in one identity-bound window; SUM and MAX reducers are disjoint, missing never means zero, and accounting/provenance hashes remain explicit excluded events. A capped in-memory renderer solves an eight-role-labelled canonical-JSON output candidate fixed point from zero, with identical double renders per iteration and two post-convergence replays, but verifies neither role semantics nor a write. A strict K7 request/route/two-child-frame schema rejects crossed or incomplete identity graphs, duplicate/reordered/extra frames, noncanonical/nonfinite JSON and `bool`-for-integer substitution. A structural post-cutoff envelope/finalization join rejects pre-cutoff peak substitution, requires the final peak to dominate the live prefix and orders `cutoff < reap < descendant scan < final peak < terminal`. The sealed source archive remains ZIP/entry/hash validated, and freshness rechecks exact immutable bytes plus SHA-256. | None of these mechanisms closes a shared-resource leaf semantically. The structural envelope accepts opaque source IDs and ordered integers; it does not prove supervisor provenance, the typed K7 route graph or a global event journal. The eight-role byte total excludes its own fixed-point trace/result and later outer-finalization wrappers, commits nothing and authorizes no write. The existing Stage-A one-frame transport, real K7 child body, exact schedule admission, mount/cgroup provenance, atomic wrapper-complete output writer and independent source-byte verifier remain unconnected. Live `io.output_bytes` stays typed unavailable. No CounterRecord, WorkVector, ComparisonVector, projection proof, official execution, economics/science Gate or certificate is authorized. | `specs/K7_SHARED_RESOURCE_LIVE_SUPERVISION.md`; live-meter, output-fixed-point and structural outer-finalization modules; accounted K7 IPC skeleton; central domain registry; SUM/MAX, zero/unavailable, recursion, fixed-point determinism/cap, post-cutoff sequence, pre-cutoff-peak substitution, identity, canonical-JSON, bool/int, frame-order, archive-replacement and locked-authority tests. |
| V0-101 | 2026-08-01 | Typed K7 structural-supervision admission | CONSTRUCTION / STRUCTURAL IDENTITY AND JOURNAL ORDER ONLY / OS AND FORMAL AUTHORITY LOCKED | Contract `1.93.0` derives all seven shared-resource binding fields from the exact replayed accounted K7 route graph and permits no field override. An issuer-owned journal accepts exactly six typed source-document roles and assigns the only accepted contiguous structural order: `WINDOW_START -> BUSINESS_CUTOFF -> PROCESS_REAP -> DESCENDANT_SCAN -> FINAL_CGROUP_PEAK -> PARENT_TERMINAL`; caller sequence fields do not exist. A structural bridge joins that route-derived binding to one closed live snapshot, journal scope and output fixed point, internally derives every outer-finalizer source role, post-cutoff sequence, lifecycle boolean and final peak, and calls the existing V0-100 outer finalizer. The signer runtime also exposes an additive K7-only loader that validates the registered ordinary `.git`-directory checkout and a disjoint external private-key root using no-follow POSIX reads without invoking Git or another subprocess. | These additions remove caller-selectable structural arguments only. Journal source documents remain caller claims; journal order is not mapped to OS time; structural launch/mount/reap/scan/peak roles carry no OS provenance; and deterministic sequence rebasing is not a global observation clock. The subprocess-free signer loader is not wired into any real K7 child or runner. There is no real child body, `Popen`/pidfd/cgroup-v2/one-child authority, supervisor-native evidence, atomic wrapper-complete write or independent source-byte semantic verification. No CounterRecord, WorkVector, ComparisonVector, projection proof, terminal/certificate or official result is issued. Every official/formal flag remains false, scalar/break-even stays null, and counter-completeness/economics/science/certificate Gates remain locked or `NOT_RUN`. | Exact typed route-to-shared-resource derivation; six-event global-supervisor structural journal; supervised-finalization bridge; K7-only subprocess-free signer-loader path; central content domains; identity-crossing, caller-sequence, order, mutation, rebasing, source-role and subprocess-invocation attacks. |
| V0-102 | 2026-08-01 | K7 OS-supervisor prelaunch admission | CONSTRUCTION / REAL READ-ONLY HOST PROBE / EXECUTION LOCKED | Contract `1.94.0` adds bounded no-follow host reads for POSIX/Linux, pidfd primitives, unified-cgroup membership and mount data, delegatable controllers, required leaf stat/access facts and descriptor identity facts. Raw read bytes remain only on the probe stack; artifacts retain bounded path, byte count and SHA-256. A caller-preopened delegated-parent directory FD is mandatory for the future lease, but this revision validates no lease or cgroup filesystem, so absence or presence both produce typed `NOT_AVAILABLE`. The admission result issues no attempt terminal or noncertificate closure. | The probe is diagnosis, not OS provenance. It never launches a process, creates or writes a cgroup, validates delegation, sets `pids.max`, places a child atomically, opens a pidfd lifecycle, proves no descendants or reads a formal final peak. The current WSL2 context has pidfd primitives and cgroup v2 but no supplied usable delegated parent, so it deterministically fails closed. All nine-path semantic, CounterRecord, WorkVector, ComparisonVector, projection, official, economics, science and certificate locks remain false, null or `NOT_RUN`. | `specs/K7_OS_SUPERVISOR_ADMISSION.md`; read-evidence, profile, probe and result domains; read-cap, mount-root, descriptor-transplant, no-launch/no-write, caller-mint, mutation, replacement and unknown-blocker tests. |
| V0-103 | 2026-08-01 | K7 parent-owned successor IPC admission | CONSTRUCTION / COMPLETE PRELAUNCH IDENTITY GRAPH / EXECUTOR ABSENT | Contract `1.95.0` freezes a successor profile over the exact accounted-sealed K7 profile, the V0-102 admission profile and exactly one bootstrap entry derived from the sealed source snapshot. Its request binds the complete route identity graph, full signer registry document, opaque-environment and sealed-secret commitments, session identity, single request nonce, scientific occurrence and schedule, plus a one-request mapping to the Phase-3E logical occurrence. A future launched exchange is frozen as exactly two ordered roles: child-owned K7 business followed by a parent-owned accounting suffix. On the current `NOT_AVAILABLE` host result, the constructor emits only a route-bound structural prelaunch blocked result with zero successor launches/frames and explicitly no attempt-terminal or noncertificate-closure authority. | The bootstrap is identified but not executed; the nonce is bound but no consumption/replay store exists. No delegated cgroup lease, atomic cgroup child placement, pidfd lifecycle, child body, parent suffix, wrapper-complete atomic output, source-semantic replay or formal 202-leaf materialization is implemented. Therefore the blocked result is not a terminal artifact, the two future frame roles are not issued, and no CounterRecord, WorkVector, ComparisonVector or projection proof exists. All official, economics, counter, science and certificate locks remain false, null or `NOT_RUN`. | `specs/K7_PARENT_OWNED_SUCCESSOR_IPC.md`; exact predecessor/bootstrap derivation, scientific-to-Phase-3E mapping, request and blocked-result content domains; canonical replay, identity-crossing, caller-mint, bootstrap-substitution, bool/int, zero-frame and no-terminal-authority tests. |
| V0-104 | 2026-08-01 | K7 delegated cgroup-v2 attempt lease | CONSTRUCTION / REAL LEAF LEASE / CHILD AND FORMAL AUTHORITY LOCKED | Contract `1.96.0` adds a real cgroup-v2 attempt-leaf lease behind the exact V0-103 request and V0-102 admission graph. A process-local issuer records and consumes one exact request nonce before acquisition can inspect or mutate the cgroup; the token binds the live request/admission objects, FD number, stat identity and `/proc/self/fd` target digest. Acquisition accepts no pathname authority, duplicates the caller-opened directory FD, verifies cgroup2 and delegated `memory`/`pids`, creates one exclusive request-labelled leaf with `dir_fd`, verifies the required files, empty/domain state and exact initial `memory.peak=0`, writes and reads back `pids.max=1`, `cgroup.max.depth=0` and `cgroup.max.descendants=0`, and returns a process-local unpickleable lease. Every failed setup removes its owned leaf or raises a typed cleanup failure; close rechecks identity/emptiness and always closes owned FDs. The positive syscall path was exercised in a temporary real systemd-delegated scope and removed the leaf after exact readback. | The nonce guard is deliberately process-local and does not prove durable or cross-process replay exclusion. The lease does not launch or attach a child, does not implement `clone3(CLONE_INTO_CGROUP|CLONE_PIDFD)`, pidfd timeout/signal/reap, descendant exclusion after child exit, final peak capture, parent accounting suffix, atomic wrapper-complete output, independent semantic replay or formal 202-leaf materialization. A normal non-delegated workspace shell remains fail-closed. No CounterRecord, WorkVector, ComparisonVector, projection proof, terminal/certificate or official result is issued; every Gate remains locked. | `specs/K7_DELEGATED_CGROUP_LEASE.md`; cgroup-lease module and central domains; exact nonce/FD/target binding, single-use, cgroup2/delegation, domain/zero-peak, control-readback, cleanup, transplant, unpickleable and no-formal-authority tests; real temporary delegated-scope positive integration. |
| V0-105 | 2026-08-01 | K7 fresh-exec successor authority replay | CONSTRUCTION / PORTABLE AUTHORITY CLOSED / LAUNCH AND FORMAL AUTHORITY LOCKED | Contract `1.97.0` preserves the retained-runtime V0-103 verifier and adds a separate fresh-exec reconstruction path. It accepts only the exact sealed source archive plus canonical sealed-transport, lifecycle and successor-profile documents; reconstructs the transport from archive entries/runtime facts; freshly reissues the lifecycle, complete V6 accounted profile and successor profile; and requires all profile documents to match byte for byte. It then reconstructs the complete accounted route and public signer registry, freshly freezes the successor request, and requires exact canonical-byte equality without accepting a live parent request object. Both reconstructed authorities are process-local and unpickleable. | This removes only the live-object transport blocker. It does not verify loaded child code, enter the isolated runtime, acquire/consume a cgroup lease, launch or supervise a child, execute business work, emit a frame, close the parent suffix, verify any of the nine shared-resource paths or materialize the 202 formal leaves. No CounterRecord, WorkVector, ComparisonVector, projection proof, terminal/certificate, scientific result or official authority is issued; every Gate remains locked. | `specs/K7_SUCCESSOR_PORTABLE_REPLAY.md`; portable replay module and central domains; exact archive/profile/request reconstruction, no-live-parent API, mutation/type/cross-identity rejection and process-local tests. |
| V0-106 | 2026-08-01 | K7 typed child business frame | CONSTRUCTION / CHILD FRAME CLOSED / PARENT SUFFIX AND FORMAL AUTHORITY LOCKED | Contract `1.98.0` implements the first V0-103 frame from the exact V0-105 replay. It verifies sealed runtime/secret descriptors, derives signer and request-bound private-taint authority from one secure key read, reconstructs the registered `NO_PRIOR` schedule, invokes the owned partial runner once and embeds the existing strict portable evidence bundle plus its owned wrapper/transcript/cache documents. Raw replay verifies the true portable schema/topology/semantics, every redundant request coordinate and known document cross-binding; no generic caller-selected document table or naked taint-pattern API exists. A real owned-runner/portable/request-replay integration test passes and rejects a rehashed nested semantic mutation. | This closes the typed child business body only. Complete loaded-module and OS-spawn exclusion are not claimed; parent cgroup/pidfd supervision is still required. The frame has no parent accounting suffix, complete raw partial-transcript semantic replay, atomic two-frame output, nine-path semantic closure or formal 202-leaf reduction. It issues no CounterRecord, WorkVector, ComparisonVector, terminal/certificate, scientific result or official authority; every Gate remains locked. | `specs/K7_CHILD_BUSINESS_BUNDLE.md`; child-business module and central domain; request/taint binding, single-read, real portable integration, nested mutation, absent-root, secret, identity, subprocess-guard and nonformal-lock tests. |
| V0-107 | 2026-08-01 | K7 atomic clone3/pidfd runtime | CONSTRUCTION / REAL ATOMIC CHILD RUNTIME / BUSINESS JOIN AND FORMAL AUTHORITY LOCKED | Contract `1.99.0` consumes one real V0-104 cgroup lease and one opaque sealed-bootstrap authority, then uses an audited x86-64 native trampoline for exactly one `clone3(CLONE_INTO_CGROUP|CLONE_PIDFD|CLONE_CLEAR_SIGHAND)`. The GIL is retained across the final signal-blocked single-thread check and clone; descriptor roles are revalidated inside that critical section, cleanup identities are saved before the parent unmasks, and the child never returns into Python. Admission requires non-root identities/groups and zero inherited/permitted/effective/ambient capabilities. Before sealed-memfd `execveat` the child installs parent-death SIGKILL, no-new-privileges, a Landlock write-denial ruleset and seccomp denial of x32, spawn, broker/IPC, metadata, namespace/mount and parent-control syscalls. A CLOEXEC setup channel distinguishes sandbox/exec failure from program exit codes. The parent enforces exact memory/swap caps, bounded pidfd signal/wait/reap, truthful deadline/output outcomes, EOF, final peak, empty leaf, zero descendants, `cgroup.kill` cleanup and authority closure. The sealed bootstrap copies bytes to runtime-private fixed-mode inodes and has no caller-mutable state. A real delegated-systemd integration executes `/bin/true`, proves fork/file/metadata/cgroup/socket/parent-limit denial and reports typed `ENOEXEC`. | This is a nonformal low-level runtime, not yet the complete V0-103 successor. It does not bind and execute the V0-106 business entry, prove the complete loaded-module graph, produce the parent suffix or atomically publish two frames. Its raw observations are not CounterRecords and do not close the nine shared-resource paths or 202-leaf reduction. No WorkVector, ComparisonVector, projection proof, terminal/certificate, scientific result or official authority is issued; every Gate remains locked. | `specs/K7_ATOMIC_PIDFD_RUNTIME.md`; runtime module, audited assembly and tests for native byte identity, sealed bootstrap immutability, capability blockers, memory/swap/cgroup-kill controls, status/output truth, cleanup, preflight ownership and real seccomp/Landlock denial. |
| V0-108 | 2026-08-01 | K7 parent-owned atomic executor | CONSTRUCTION / REAL V0-105 -> V0-106 -> V0-107 JOIN / STRICT TWO-FRAME REPLAY / FORMAL AUTHORITY LOCKED | Contract `2.0.0` consumes one request-bound nonce and V0-104 lease, freezes the interpreter plus six exactly ordered sealed source/profile/request/secret inputs, and enters the archive-loaded child through V0-107. The child reconstructs the V0-105 authority chain without a live parent request, executes the registered V0-106 owned K7 business exactly once and self-checks all loaded `acfqp` modules against the sealed archive. The parent accepts only zero exit, untruncated EOF-before-reap, final peak, empty cgroup and no descendants, then publicly replays the frozen child frame and derives the suffix. The immutable in-memory output has exactly `CHILD_OWNED_K7_BUSINESS` followed by `PARENT_OWNED_ACCOUNTING_SUFFIX`; a bounded fixed point binds the exact wrapper-complete byte count, and strict replay rejects malformed, reversed, crossed, extra or trailing bytes. A real delegated-systemd integration executes and replays this authentic two-frame route. | This closes the parent executor integration only. The module-graph check is child-self authority rather than independent complete stdlib/native provenance, and no durable atomic artifact writer is claimed. The suffix exposes three raw nonformal facts and six unavailable shared-resource paths; none of the nine is a semantic receipt. No CounterRecord, WorkVector, ComparisonVector, projection proof, 202-leaf reduction, terminal/certificate, scientific result or official authority is issued; all Gates remain locked. | `specs/K7_PARENT_ATOMIC_EXECUTOR.md`; atomic child-entry and parent-executor modules; unit framing/identity/failure/cleanup attacks; opt-in real delegated-systemd business integration. |
| V0-109 | 2026-08-01 | K7 atomic shared-resource authority | CONSTRUCTION / TWO WINDOW-LOCAL OBSERVATIONS / ZERO ATTEMPT-SCOPE RESOLUTIONS / FORMAL AUTHORITY LOCKED | Contract `2.0.1` adds runtime-issuer-owned lifecycle evidence for the exact launch, EOF, reap, empty-cgroup, descendant-scan, final-peak and memory-control-verification order. A production nine-row registry is derived without caller path/value inputs from the V0-108 request/spec/result, verified route/shared-resource identity, V6 registry/stage/execution profiles, sealed parent/runtime sources and native trampoline. Strict V0-108 replay rederives `memory.working_bytes_peak` from final cgroup `memory.peak`, but freezes it as `VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE`: the child cgroup omits parent bootstrap, prelaunch, replay, publication and close work. It also rederives `process.launches=1` as `VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE`. Both are ineligible as attempt-scope resolutions; the remaining seven paths are exactly `NOT_CONNECTED`. The authentic delegated-systemd path produces and verifies this partition. | This is not nine-path semantic closure. Same-process runtime issuer evidence exists, but standalone bytes-only OS replay does not. Hash, integrity, protocol, mounted bytes and all three additive I/O paths remain unconnected; the V0-108 output-byte fact is not upgraded. No receipt set, CounterRecord, WorkVector, ComparisonVector, projection proof, 202-leaf reduction, terminal/certificate, scientific result or official authority is issued; every Gate remains locked. | `specs/K7_ATOMIC_SHARED_RESOURCE_AUTHORITY.md`; runtime lifecycle evidence; production registry/resolution/verifier module; window-local peak, incomplete launch scope, canonical-snapshot mutation, source/request/lifecycle crossing and caller-mint attacks; real parent-executor integration. |
| V0-110A | 2026-08-01 | K7 attempt-wide raw process supervisor | CONSTRUCTION / PRE-BIND-THROUGH-PARENT-PAYLOAD RAW PREFIX / OS-SEMANTIC AND FORMAL AUTHORITY LOCKED | Contract `2.0.2` opens one issuer-owned session and activates its sink before successor-request binding/replay. The sink remains active through the V0-108 parent executor, typed parent-result payload freezing and raw-journal closure; the later envelope is only a post-cutoff no-launch canonical wrapper and proves neither complete publication nor post-cutoff helper coverage. After positive `clone3`, the receiver advances a volatile write-ahead edge lower bound before provenance/event materialization and pidfd validation. Materialization failure becomes a nonformal protocol prefix; covered finalization failure retains a closed journal, canonical emergency prefix or, after dual encoding failure, a noncanonical raw-field snapshot. | The strongest status is only `VERIFIED_ATTEMPT_WINDOW_RAW_SCOPE_INCOMPLETE`. Import-time executor/runtime pins resist ordinary public-symbol rebinding only; arbitrary same-process underscore/global/object mutation, including `object.__setattr__`, is outside the raw threat model. Canonical raw bytes are not independent OS proof, the raw-field fallback is not canonical/replayable, and sink/interpreter crash, no-loss capture, exhaustive failure/cleanup paths and post-cutoff helpers remain unproved. `CONNECTED_EXACT` requires external isolation and supervisor/kernel attestation spanning the intended publication/cleanup scope. No eligible receipt, CounterRecord, WorkVector, ComparisonVector, projection proof, terminal/certificate, scientific result or official authority is issued; all nine-path and formal/official Gates remain locked. | `specs/K7_ATTEMPT_PROCESS_SUPERVISOR.md`; attempt-process sink/supervisor/executor; pre-bind sink, write-ahead lower-bound, zero/pre/postlaunch protocol prefixes, payload-before-close, finalization fallback, public-symbol rebinding and locked-authority tests. |
| V0-110B-1 | 2026-08-01 | K7 outer attempt cgroup hierarchy | CONSTRUCTION / REAL ANCESTOR+WORKER PREPARATION / RUNTIME CONSUMPTION LOCKED | Contract `2.0.3` creates a fresh empty cgroup-v2 attempt ancestor and one empty worker leaf from a request/admission/descriptor-bound single-use nonce. Before descendant creation, the ancestor is empty/domain with `memory.peak=0`; it then enables `memory+pids`, freezes a 4-GiB/zero-swap/two-process cap and depth/descendant bounds, creates the one-process worker leaf and revalidates the complete empty one-descendant topology. The writable `cgroup.kill` interface is opened. Cleanup start permanently revokes consumer access; partial deletion retries without request/admission currentness, post-identity setup failure transfers remaining FDs to a process-local guard, and the pre-identity create gap explicitly requires an external parent guardian. Cap mismatch cannot block safe deletion and instead raises a typed cleanup-complete protocol error. A real delegated-systemd path passes. | This is `PREP_ONLY`. Descendant metadata can raise the ancestor peak, so no launch baseline or numeric memory evidence exists until a future runtime resets and verifies the peak immediately before launch. Parent exclusivity, atomic name-to-inode deletion and a crash-surviving cleanup guardian are unproved, so `safe_for_exact_runtime_consumption=false`. A future external supervisor must broker both worker and business launches; neither process receives writable ancestor authority or may spawn, and existing V0-107/V0-108 semantics cannot be silently relabelled. The unified window must extend through final publication/output and cleanup. `pids.max` is not cumulative launch evidence. No receipt, CounterRecord, WorkVector, ComparisonVector, terminal/certificate or official authority is issued; all Gates remain locked. | `specs/K7_OUTER_ATTEMPT_CGROUP.md`; outer cgroup module; domain/profile, nonce/descriptor, typed blocker, complete-snapshot, name-swap, retryable lease/setup cleanup, pre-identity gap, stale-authority/cap mutation, no-premature-evidence and real delegated-scope tests. |
| V0-110B-2A | 2026-08-01 | K7 outer-attempt broker protocol | CONSTRUCTION / STRUCTURAL IPC CLOSED / BROKER EXECUTION LOCKED | Contract `2.0.4` freezes exactly five canonical length-prefixed roles—`WORKER_READY -> BUSINESS_REQUEST -> BUSINESS_RESULT -> PARENT_OUTPUT -> WORKER_EOF`—under one request/route/broker-spec/session binding. Role-derived indices, exact role payload fields, payload byte/digest commitments, frame IDs and the final transcript ID are strictly replayed. The sole business request is ordinal zero and cannot carry an FD, executable, argv, environment, cgroup or unknown launch authority. | This is caller-constructible offline byte-protocol structure only. Same-binding byte replay is allowed; live peer ownership, broker-spec authority and one-time nonce/request consumption remain false, and the transcript has no launch authority. The required attempt-preexisting broker, two sibling from-birth launches, role-specific write-ahead edges, kernel no-spawn, two pidfd lifecycles, same-open-description peak reset/read, operational output window and crash-surviving cleanup guardian do not exist yet. Existing V0-107/V0-108 outputs are not relabelled. No shared-resource value, CounterRecord, WorkVector, ComparisonVector, terminal/certificate or official authority is issued; all Gates remain locked. | `specs/K7_OUTER_ATTEMPT_BROKER_PROTOCOL.md`; broker IPC module; profile/frame/transcript domains; canonical framing, immutability, order/cardinality, binding transplant, role-payload authority, bool/int, cap, unknown-field and caller-mint tests. |
| V0-110B-2B | 2026-08-02 | K7 prepared live broker session | CONSTRUCTION / LIVE PROCESS-LOCAL PREPARATION / LAUNCH AND FORMAL AUTHORITY LOCKED | Contract `2.0.5` transfers one active V0-110B-1 lease into an issuer-owned process-local guardian only after that cleanup capability has been constructed under the lease lifecycle lock. The same commit binds an object-identity token to the exact guardian; failure resolution and context exit use that lock/token, preventing an interrupted stale handoff from closing another service's committed session. Transfer revokes old descriptor/cleanup access. The guardian creates the fixed `business` sibling, retains every hierarchy/kill/peak/socket descriptor, mints the execution spec and nonce, and rejects process-local request reuse. Real delegated-cgroup evidence supersedes the proposed immediate-prelaunch zero reset: the unique `A/memory.peak` OFD is reset while `A` is descendant-free and peak/current are exactly zero, then retained while topology and session preparation are charged inside the window. Prelaunch peak may be nonzero, and baseline subtraction is forbidden. | Serialized device/inode bytes do not prove OFD continuity; that authority exists only in the live transferred descriptor. Cleanup is monotonic and retryable, persists observed control violations across retries and reports them after safe empty-tree deletion. The business pre-identity gap still requires the parent guard; crash persistence, exclusive parent-writer ownership and atomic name deletion remain unproved. No process, live peer, frame, final peak, shared-resource value, CounterRecord, WorkVector, ComparisonVector, terminal/certificate or official authority exists; all Gates remain locked. | `specs/K7_OUTER_ATTEMPT_BROKER_PREPARATION.md`; preparation and outer-cgroup modules; preparation-profile/execution-spec/session domains; real delegated-scope reset/OFD path; issuer/mutation/replay/concurrency, token-bound transfer/context-exit, constructor-failure, persistent-violation, retry, identity/control and no-authority tests. |
| V0-110B-2C | 2026-08-02 | K7 two-role native broker probe | CONSTRUCTION / REAL TWO-ROLE PROBE / LIVE PROTOCOL AND FORMAL AUTHORITY LOCKED | Contract `2.0.6` consumes one admitted prepared session and two caller-supplied sealed probe bootstraps before the first clone; no production role manifest is claimed. Exact `PREPARED` state plus frozen descriptor, name, cgroup-v2, control, topology, target-emptiness and endpoint bindings are replayed before consumption and each clone. Under the guardian lock, blocked signals and a final single-thread audit, the sole broker performs the fixed `worker -> business` sequence with `CLONE_INTO_CGROUP | CLONE_PIDFD | CLONE_CLEAR_SIGHAND`. The checked-in x86-64 parent branch writes each role-specific edge and returned PID into outer-frame native cells before Python return; a guardian-bound cleanup authority already exists, and receives those facts before signal unmasking or failure hashing. The child reuses parent-death containment, no-new-privileges, Landlock, no-spawn seccomp and descriptor-only `execveat`. Success requires PID-bound distinct pidfds, two direct reaps, same-retained-OFD peak read and empty identity-bound cleanup. Real delegated execution launches and reaps two sibling-cgroup `/bin/true` images. | Only `(0,0)`, `(1,0)` and `(1,1)` failure prefixes are legal. Post-clone failures cannot roll back an edge; invalid pidfds fall back to direct-child reap, while unresolved reaps retain pidfds and guardian in the preinstalled unpickleable retry authority before tree deletion. Reaped pidfds are monotonically retired, ancestor kill runs for tree-only contamination and its OFD survives partial emptiness failure. The cells remain volatile and are not crash/no-loss evidence. `clone3` temporarily copies CLOEXEC broker FDs into the trusted native pre-exec child; the claim is only that they do not enter the untrusted exec image. The direct peer socketpair proves no five-frame sender provenance, no real K7 output is committed and the peak window is not yet the complete production occurrence. Consequently no exact process launch, shared-resource receipt, CounterRecord, WorkVector, ComparisonVector, terminal/certificate or official authority is issued; all Gates remain locked. | `specs/K7_TWO_ROLE_BROKER_PROBE.md`; two-role probe module and audited successor assembly; central domains; profile/edge/result-cell/role-order/preflight/capability, pre-helper FD exception, signal/prefix failure, mismatched/stale-pidfd direct-reap, tree-only retry-authority and real delegated-scope tests. |
| V0-110B-2D-1 | 2026-08-02 | K7 production role and durable-output core | CONSTRUCTION / STATIC ROLE TEMPLATE + ROLE-LOCAL PROTOCOL CORES / LIVE BROKER AND FORMAL AUTHORITY LOCKED | Contract `2.0.7` derives an issuer-owned worker/business template from the exact successor request, live-replayed prepared session, sealed source/runtime and interpreter. Public callers cannot select role order, cgroups, dispatch/argv/environment or FD roles; every bind replays live PID/state/descriptors/names/controls/empty topology/socket queues/peak under the guardian lock. Dispatch digests are separate from absent entry-member digests, so this template is explicitly non-launchable. Business snapshots the full binding, checks kernel socket state, uses owned FD duplicates, rolls back pre-seal failure and retains typed post-seal/send evidence. Worker accepts a bounded delayed half-close, rejects extra packets, seals exact output via no-replace/fsync/readback, never unlinks a foreign raced temp inode, binds recovery to the original directory/file, and retains output+receipt preimages. | 2D-2 must issue a new archive/request/manifest with present wrapper members and a real archive-loading bootstrap; this template cannot be relabelled. A bare output-directory FD is not exclusive-writer authority, Python-private sentinels are not same-address-space capabilities, and no live SCM/PID/pidfd sender join, Landlock role split, complete transcript, reaps/final peak/cleanup envelope, crash journal or nine-path receipt exists. No formal accounting/vector/terminal/certificate/scientific/official authority is issued; all Gates remain locked. | `specs/K7_PRODUCTION_ROLE_AND_OUTPUT_CORE.md`; manifest/business/worker/IPC modules; stale-session, kernel socket, binding mutation, partial-write rollback, typed irreversible stage, delayed half-close/extra packet, sealed-empty, temp/name race, directory-bound recovery, retained preimage and caller-mint tests. |

## V0-076 current production-boundary state

The current V0-075 evidence path has three distinct meanings that must not be
collapsed:

```text
portable byte/topology validity
!= producer-semantic reconstruction
!= private-law replay or production authorization
```

The highest completed public cut is:

```text
raw bundle + raw public context
-> M0: 11 public roles reconstructed for the NO_PRIOR arm
-> B1: observer-open binding reconstructed
-> M1A: 6 signed-batch roles reconstructed
-> M1B: 16 signed-control roles reconstructed with exact ROOT/M0 binding
-> M2 root: OCCURRENCE_IDENTITY and ROOT_EXECUTION are FULL_PUBLIC
-> M2 lineage: batch public/sequence verification are FULL_PUBLIC
-> CONSTRUCTION_LINEAGE public projection reconstructed
-> closure-verification public projection checked
-> private native replay claim remains unresolved
```

M1A record identities commit the record index, role, producer semantic ID,
direct dependency IDs, canonical-byte digest and byte count.  Its dependency
proof is an iterative topological direct-edge DAG; it does not materialize a
quadratic transitive closure.  `4096` chained entries are a mandatory
non-recursive regression.  Repeated `outcome_id` values are not record keys:
distinct nested canonical outcome bytes remain distinct records.

The contract-`1.68.0` attestation is a new construction artifact.  Its trusted
freeze accepts private salt/environment, performs the exact private verifier
inside that call, then signs the resulting public projection.  Neither private
material is serialized.  The public verifier recomputes the public
closure/stream graph and verifies the signature, while retaining:

```text
private_replay_claim_observer_signed = true
private_replay_independently_recomputed = false
public_verifier_proves_private_replay_execution_order = false
execution_order_is_trusted_api_discipline_not_cryptographic_proof = true
production_requires_signer_owning_sealed_observer_boundary = true
```

An old or public-reconstructed
`SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` has no input path to this freeze
and cannot be upgraded through it.  The new artifact is not yet a portable
bundle role.  Contract `1.71.0` now proves the required same-child custody
shape for one registered synthetic K7 positive control, but its public output
remains an observer-signed construction claim rather than independent private
replay or process-order proof.  It does not retroactively alter the portable
bundle, and production still requires a new role/bundle integration plus the
remaining semantic, source/code, accounting and campaign authorities.

The following locks are normative until the 67-role semantic chain,
production lifecycle integration, source/code authority, all-path accounting, campaign closure and
independent bundle verifier are complete:

```text
official_execution_allowed = false
fresh_heldout_access_allowed = false
scientific_endpoint_credit_allowed = false
plan_certificate_issuance_allowed = false
infeasibility_certificate_issuance_allowed = false
portable_semantic_registry_complete = false
source_authority_complete = false
code_provenance_complete = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

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

## V0-072 nonauthorizing draft and target-lock rule

Ledger `1.34.5` retains the `1.34.3` audit correction, fixes the confidence
epoch/schedule-cap distinction, and records additional
nonauthorizing construction prerequisites for proposed contract `1.36.0`,
schema `2.0.0`, and profile
`transfer_guided_adaptive_observation_acquisition_v1`. This is a
`NONAUTHORIZING DRAFT`; it is not a completed construction contract or an
executable preregistration. Current completed construction contract
`1.34.0` remains unchanged.

The clean-generation draft freezes:

1. K7, W7 and K7-minus-two public H2 contexts with common root
   `(1,1,2,0,0,0,0)`, risk/regret tolerance `1/20`, rank cap 6 and reward
   ceiling `3/64`;
2. separate environment-only hidden-law commitments that do not appear in
   public context documents;
3. SOURCE, NO_PRIOR, WRONG, OOD and MATCHED_DIRECT_GROUND arms, ordered
   context-major into exactly 15 logical occurrences;
4. a cold initial schedule of 64 discovery plus 2,048 validation draws for
   every physical row in the complete registered H2 closure, with
   conservative per-arm initial cap 506,880;
5. at most two authorization-bound rounds, at most 19 distinct new child
   action rows, and cumulative incremental cap
   `C_R=2048*R+8256*|union(new child rows through R)| <= 160960`;
6. direct-ground validation checkpoints `2048/4096/8192/16384` and adaptive
   audits only after the complete cold model and complete round-1/round-2
   materializations;
7. row-epoch `beta=1/300000`, at most 480 authorities per arm and 2,400
   across the campaign, giving family tail at most `1/125` and confidence at
   least `124/125` by a union bound with no independence assumption; a
   physical row may have one initial plus two promotion epochs, while the
   two-round protocol permits at most two promotion authorities per context;
8. seven V0-068 adjacent raw-prefix roll-forwards and sample/probability/
   identity-free portable feature keys; and
9. primary SOURCE-versus-NO_PRIOR and matched SOURCE-versus-direct
   online-target-draw endpoints.

The following construction prerequisites are implemented and tested:

- exact-`Fraction` lazy H2 branch-and-bound with typed resource exhaustion
  and a separately implemented verifier that replays interval-simplex
  Bellman values, relevant decisions, prefix cover, prunes, counters, and
  legacy audit equality;
- a verified V2 source archive that mechanically derives the seven adjacent
  raw prefixes, separates portable features from identity-bound snapshots,
  and abstains per feature, plus a separately implemented transform verifier
  that recomputes prefix, fixed-policy, rank, consensus, and content
  identities while explicitly consuming the same-implementation V0-068
  campaign authority;
- exact V2 split-support confidence, one `OTHER` event, all-novel fresh
  promotion, and the finite-union `2400/300000=1/125` campaign allocation;
- evidence-first public novel-child cardinality and selector authorities:
  complete absent-row lists and exact draw uppers freeze before gain/ranking,
  postselection requires positive gain bound to that evidence, and an
  independent verifier rebuilds the public row/count/cap chain;
- immutable chunked row transcripts with incremental prefix work,
  arm-free random-word semantics, arm-bound evidence, and fresh promotion,
  together with a separately implemented development-control verifier;
- a generic discovery-only cold-H2 closure with complete root/child public
  row obligations, validation novelty excluded from expansion, exact native
  work, exact context-total `96/48/96` root-plus-child caps, one physical
  charge across its arm-registered consumer routes, and independent closure
  replay;
- a public-only adapter for the three clean registered graph contexts whose
  legal catalogues and total-cap bindings replay independently without
  calling hidden-law, kernel, observer-outcome, or tape APIs;
- an exact development-only confidence-to-interval-simplex projection that
  preserves support-event bounds, keeps validation novelty aggregated in
  one row-bound adversarial `OTHER` until promotion, and leaves the
  registered cap-6 entry locked;
- an evaluation-only exact H2 ground enumerator independent of the
  production model/planner implementation, with separate K4/K5 brute-force
  controls and a registered entry locked on the absent future semantic
  anchor and occurrence terminal authority;
- a registered target observer with raw commitments and full support-epoch
  chain verification, whose registered open/replay/evaluation APIs fail
  closed until a future semantic remote-`main` anchor authority exists; and
- a domain-separated synthetic K4 control with no registered context, law,
  stream, observation, model, endpoint, or claim identity; and
- a read-only, content-addressed execution-manifest readiness authority that
  derives actual repository bytes and reports missing roles/identities but
  cannot finalize, mint an anchor, access a remote, or authorize target
  observations.

### Development-identity retirement

An earlier fake-placeholder unit-test path generated only in-memory
registered tuples under these eight development identities:

```text
0f8061ac58630cced8f01bce01191ab0d02aff5cf64b4cc106f579ad53d02312
1f240bb0305012a9144b4039d9f2f9b13a0be18b23c0cc7c70dc2909f09ccc29
a5775190ea336702a7f4e1f06bdd93ec0bd0609f03f69ad7a72c2262e6645976
ad7dca2b9db96d98d0c8bd6608315264995d3dcb0b6457a4b2b5d073db494ab0
571d4cb2a7b2b55fc85012b2b417f397b57226df7ae4b00c47d0bb5f35639441
e8cb7a070c7d6bbdb93683367a8026f422a8ef397877b87d07a3c6c549820cde
f0d8db6165c3d0a125945b43b4b0d8e221b13ea7870021e96f18b91e218ed00e
495927b2c72c847086008b2b2c6e8f65ea4a2b5a45ce409c8c7ec3d4be915500
```

No observation tape, artifact, endpoint, or campaign output was persisted,
but the zero-draw premise is not assigned to those identities. They are
permanently retired with disposition
`DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE` and are invalid in
every confirmatory role.

The replacement clean-generation identities are:

```text
K7 public context       5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a
W7 public context       48a6f36af9ef5ff1ba9920d783d2435cedd9458c8383f48ccf40412ff55f0dda
K7-minus-two context    52363b3d6e6508e6734418103be98da18cd7aafe6657d24de16c2547c630ba7a
K7 hidden law           434f67074a8be498fd8cc532fe780f4227f6f8233bc90a62fab6e8cb595a5f71
W7 hidden law           801683343ef1973337e534f2d36ac6c8493717d240ef05677abd3a2abb72559c
K7-minus-two law        b0803f306f3d5ac79abd6e87fc713caedcceae3411f3172f88d103cb7b540347
environment manifest    f1b158319b5c059786829fc6b5ca4cda60e0b49e9e173a3c70daa4c8a04100da
```

They have zero registered draws. Current audit-corrected draft
preregistration
`7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2`
has `confirmatory_execution_manifest_id=null`,
`confirmatory_profile_finalized=false`, `anchor_commit_id=null`, and
`target_execution_allowed=false`. Superseded nonauthorizing drafts
`8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29`
and
`e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4`
are retained only as audit provenance.

### Anchor and remaining work

The draft ID cannot be an anchor. The first possible anchor is the first
`origin/main` commit that contains both a final non-null execution manifest
with every component digest/semantic ID and the final preregistration ID that
content-binds that manifest, and whose parent does not contain that final
preregistration ID. The parent therefore necessarily lacks the final ID.
Merely pushing the current draft, specification, implementation
prerequisites, or null manifest does not open the target tape.

Before a positive Gate may be read, the following remain incomplete:

```text
final non-null execution manifest and final preregistration
semantic origin/main anchor verifier and attestation
registered-row/confidence/model/closure integration
relational and ground robust-model construction
authorization-bound incremental materializer
matched direct-ground baseline
real dependent fresh round-2 execution
five-arm held-out campaign
standalone raw-evidence/model/plan/certificate bundle verifier
```

After those are implemented, a valid campaign must additionally preserve
noninferior certificate coverage, issue zero false certificates, satisfy
`SOURCE draws < NO_PRIOR draws`, and satisfy
`SOURCE draws <= matched direct-ground draws`. No held-out target tape may
open earlier, and no graph, law, threshold, root, arm, schedule, cap,
checkpoint, terminal rule, endpoint, or component digest may be rerolled
after the anchor.

Locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-071 audited mechanics and non-closure rule

Ledger `1.34.1` records an audit note, not a construction-contract
promotion. Contract `1.34.0` and profile
`k6_model_only_minimal_pair_support_recovery_v0` remain the current completed
construction contract and profile. The `1.35.0` constant and
`source_frozen_certificate_sensitive_greedy_acquisition_v0` profile in the
V0-071 draft identify a proposed target contract only.

The checked-in mechanics establish:

1. exact rational source aggregation by normalized within-context midranks,
   with `q=mean`, `worst=min`, `disagreement=q-worst`, abstention above
   `1/4`, and multiplier `1/2+(3/2)q`;
2. `WRONG_CONSENSUS_PRIOR` reverses `q -> 1-q` on the same frozen prior;
3. exact target-current-model one-row zero-`OTHER` counterfactual gains are
   clipped at zero and may rank proposals only;
4. the complete score table, deterministic top admissible selection, cap,
   authorization identity and access order are frozen before target
   materialization;
5. ranking counterfactuals cannot become evidence, model epochs or
   certificates; and
6. only a typed synthetic exact-support materializer reaches a complete
   robust replan and the explicitly synthetic positive endpoints
   `SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_1/2`.

Those mechanics do not close the proposed Gate. The following obligations are
missing:

1. `SourceLocalTrialV1.source_gain_per_draw` is accepted as caller input; no
   semantic authority reconstructs it from the referenced source model,
   failed audit and raw roll-forward evidence;
2. `PortableCandidateFeatureV1` still includes sample-dependent support
   documents and `other_mass_upper`, so its v1 key is not a valid
   sample-invariant cross-context transfer key;
3. there is no real authorization-bound target observation materializer;
4. the second round does not yet establish the required independently fresh
   current-model/current-plan/failed-frontier candidate authority; and
5. `verify_certificate_sensitive_greedy_run_v1` reruns the production
   implementation and explicitly records `independent_verifier=false`; it is
   not the required independent source/raw-evidence/model/certificate bundle
   verifier.

Accordingly, real K6 may emit only `AUTHORIZATION_READY`,
`DRAW_CAP_EXHAUSTED`, or `NO_POSITIVE_GAIN`. A synthetic fixture can test
control flow but cannot establish real target acquisition, a plan
certificate for K6, source-to-target transfer, sample saving, sample
efficiency, independent verification, contract `1.35.0`, a V0-071 Gate pass,
or completion of the reusable hidden-world-model objective. The run-level
claims remain frozen false:

```text
retrospective_mechanics_only       = true
confirmatory_result                = false
sample_efficiency_claimed          = false
source_semantic_replay_claimed     = false
fresh_round2_frontier_claimed      = false
independent_verifier_claimed       = false
```

The aggregate locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## V0-070 model-only minimal-pair support-recovery rule

Contract `1.34.0` freezes schema `1.0.0` and profile
`k6_model_only_minimal_pair_support_recovery_v0`. It reconstructs a fresh
49-row selected-policy registry from the immutable K6 transaction-1 model,
evaluates all singleton overlays, then all 1,176 canonical unordered pairs.
Every overlay sets only the selected `OTHER` intervals to zero and recomputes
complete H1-to-H2 fixed-policy recurrence.

The registered result is:

```text
singleton evaluations / covers = 49 / 0
pair evaluations / covers      = 1176 / 0
outcome                         = NO_SOUND_FIXED_PLAN_PAIR_COVER
observer / full-replan / exact  = 0 / 0 / 0
global-16384 accesses           = 0
```

An independent recurrence replays all 1,225 subset obligations, while a
finite positive control demonstrates pair-only interaction. This closes only
the current-selected-policy frontier through cardinality two. It neither
licenses brute-force cardinality three nor claims the dormant
materialization path was exercised.

## V0-069 bounded second distinct-row support-transaction rule

Contract `1.33.0` freezes schema `1.0.0` and profile
`k6_two_distinct_row_support_transactions_v0`. It recomputes eligible
different-row selected-policy counterfactuals against the immutable failed
transaction-1 K6 model. All 49 registered candidates remain failed under an
individual `OTHER -> 0` overlay, so the result is
`NO_SOUND_DIFFERENT_ROW_COVER` with zero transaction-2 observations, exact
calls, global-16384 access or transaction 3. Stream/closure/materialization
requirements are conditional obligations and are not claimed exercised by
this negative terminal.

## V0-068 observation-discovered partial-support H2 rule

Contract `1.32.0` freezes schema `1.0.0` and executable profile
`observation_discovered_partial_support_campaign_v0`.

The operational target interface is tuple-only. It exposes symbolic
next-state, reward, failure/terminal flags and replay identities, but not an
atom ordinal/count, exact support, spawn law or transition probability. Each
authorized row takes 64 discovery tuples, freezes the distinct observed joint
outcomes and uses a separate validation stream at checkpoints
`2048/4096/8192/16384`. Validation is permanently interpreted as the frozen
outcomes plus exactly one `OTHER` category.

The row-epoch tail is `1/64000`; at most 16 discovered atoms are allowed and
event alpha is divided uniformly across the support-plus-`OTHER` partition.
At most 512 physical row-epoch authorities may be considered, yielding
family tail `1/125` and confidence `124/125` by Boole's inequality. The
manifest includes failed checkpoints, rejected coordinate candidates and
promoted epochs. Logical direct/quotient consumers share a physical
statistical authority only when every identity matches.

Robust planning operates on the joint interval simplex and charges `OTHER`
once as absorbing policy-abort failure, zero lower reward and zero lower
continuation. It requires complete deterministic H2 policies, a fixed uniform
distinct-action concretizer, `failure_upper <= delta` and the registered
normalized-regret threshold. Exact lift and complete-search/post-hoc-cap
fallback are separate lanes and may run only after a typed operational route
freeze.

The registered results are:

```text
W5 direct / quotient first certificate      4096 / 4096
K6 direct / quotient first certificate      8192 / 16384
K6-minus-edge direct / quotient closure      exact feasible fallback / same
```

At K6/8192 the base quotient and all registered coordinate candidates fail.
The one permitted missing-mass transaction authorizes the deterministic
earliest individually causal row, uses fresh promoted-row validation 2048,
constructs seven new child catalogues and 30 child rows at 8192, and charges
249,728 incremental observer draws. Its immutable mixed-epoch result remains:

```text
failure upper           = 1321268563 / 17179869184
normalized regret upper = 1300423631 / 38654705664
status                  = FAILED_PROOF_FRONTIER
```

Because the failure upper exceeds `1/20`, the transaction does not certify.
The runner retains it and continues; V0-068 authorizes no second promotion.
K6 direct/quotient unique raw totals are `165120/578688`, so
`construction_gate_passed=true` but
`matched_observation_advantage=false`.

K6-minus-edge binds `delta=2847/20000`, strictly between exact ground failure
`2277/16000` and base quotient-lift failure `11393/80000`. Both comparison
lanes therefore emit no false partial certificate and invoke the same exact
feasible fallback. Fallback cap exhaustion remains a noncertificate, never
an infeasibility proof.

The checked-in SplitMix64 stream is deterministic counter replay. It supports
raw-prefix and tamper verification but does not prove IID, so all statistical
terminals retain:

```text
exact_iid_implementation_claimed = false
formal_exact_iid_plan_certificate = false
statistical_claim_scope =
  CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_
  NOT_PROVEN_BY_DETERMINISTIC_REPLAY_IMPLEMENTATION
```

Only complete same-implementation campaign replay has Gate authority. It
must reconstruct all considered/promoted rows, the confidence family,
bridge/audit/freeze identities, exact lift/fallback roles and terminal
conclusions. Bare model, interval, audit or confidence artifacts are
insufficient.

This rule licenses neither exact support recovery nor primitive/ontology
invention, raw perception, broad graph/domain generalization, H>2 planning,
changed-query reuse, sample efficiency, total-work/wall-clock economics,
independent-planner verification or completion of the general reusable
hidden-world-model objective. A distinct second-row support transaction
requires a later contract.

The official locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## V0-066 variable-cardinality two-domain relational RAPM rule

Contract `1.30.0` freezes schema `1.0.0`, profile
`variable_cardinality_two_domain_relational_rapm_v0`, and passing status
`CONDITIONAL_TWO_DOMAIN_VARIABLE_CARDINALITY_RAPM_CLOSED`.

The only portable construction input is one complete, anonymous 120-row
four-vertex graph source log. A source-only constructor with no target, query,
kernel, policy, dynamics, graph-name or domain input closes the frozen human
depth-two relational grammar to 86 syntactic programs and 23
source-semantic representatives. It evaluates all 10 integer state/action
pairs and emits only these two ASTs and their anonymous support schema:

```text
state  = cardinality_actions(legal_actions)
action = cardinality_resources(
           linked_filter(action_anchor, active_resources)
         )
```

The selected program IDs are
`051e6331bd01c4df41a889d0cc248d7ad48c3cc0815a4b91d2597f36ceae2fa1`
and
`59ae6240e21b48097e94f3259e024aeb0341d21128bff5604c1c2ea3cf7e80e7`.
The portable skeleton ID is
`77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322`.
Its separate verifier reconstructs source completeness, semantic closure,
candidate selection and content identities without importing the producer or
either target domain. This independence applies only to source synthesis.

The graph target arm freezes source vertex count 4 and target counts 5 and 6.
It receives the portable ASTs but no source registry, transition row,
probability, reward or policy. Each target root row is selected from observed
legal actions; exact local symbolic outcome support is registered, while
probabilities are estimated from replayable target draws. Failed proof may
generate a fresh target-local program closure from the target slice; no
source-frozen refinement registry is available.

The graph results are:

```text
W5                  22 rows   2,883,584 draws   conditional H2 certificate
K6                  60 rows   7,864,320 draws   conditional H2 certificate
K6 minus one edge   60 rows   7,864,320 draws   no sound cover; exact fallback
```

W5 evaluates 11 fresh target candidates and selects
`active_attribute_degree_signature`; K6 needs no refinement. K6-minus-edge
evaluates all nine registered target candidates, finds no sound cover, emits
no false certificate and invokes an independently accounted 60-row exact
fallback with failure `2277/16000` and normalized reward `3/64`. Positive
certificates contain every reachable H2 abstract state-time assignment and a
uniform concretizer over distinct inverse ground actions. The operational
construction uses 142 local rows, 18,612,224 draws and zero complete target
closure calls. Its family tail is `287/250000`, conditional on the registered
SplitMix64-IID simulator semantics. W5 is strictly sparse relative to its cold
closure; the K6 cones happen to equal their matched closures extensionally,
so V0-066 makes no blanket strict-compression claim.

The LMB target arm uses a query-neutral exact seven-row bridge in a separately
registered human LMB ontology. It automatically selects the unique binding
`same_type_buffer_tokens`, preserving the same two portable program IDs while
giving every LMB context, binding, evidence row, model and dynamics object a
domain-local identity. Each of three contexts performs two
certificate-triggered acquisitions at 16,384 draws per support, for six
supports and 98,304 operational draws. Operational exact ground-row count is
zero. All three domain-specific symbolic H2 plans certify reward interval
`[59/60,61/60]`, failure upper `119/3600`, and normalized-regret upper `1/60`.
The 13 exact H2 rows belong only to standalone cold controls. The LMB family
tail is `2/125`, conditional on its registered SHA-256
random-oracle/IID-simulator assumption.

Only source log, skeleton and exact program identities may be shared between
arms. Graph and LMB context, binding, evidence, model and dynamics identity
sets must be disjoint. Source-registry rows, source-dynamics rows and
cross-target transition rows imported into either arm are exactly zero. Six
executed wrong-arm campaign/evidence/model/source transplants fail closed.
The union calibration uses Boole's inequality, requires no cross-arm
independence, and freezes:

```text
graph tail             287/250000
LMB tail               2/125
union tail             4287/250000
conditional confidence 245713/250000
```

Principal IDs are:

```text
independent source verification c1383c8d2a37bc44270347f4dcf4159a8415d97744b7217dd5c99735b896e4e0
graph campaign                 8e839923dd2d965f6180fbff8abaebfbd6c5e9d6546cb60cb12666182bf7a77a
graph verification             ad4a502c71eb1c3f3a55c1a1c468be06b529d2e1ba0cc62cbd149ba9dbae3bd1
LMB campaign                   baa37d57d60fb67c513e5655734e98d211e82ef278c1c0347bed864cf8a9f1d6
LMB verification               be94dbe27e83eadc72282cf4d45f035857d230c97441837fcdbba72e09be344e
union calibration              de5441cbc0ed337aa1468eaf3717d90be2066c4b38d31a91f37e350d646cb83f
combined campaign              f71c28b83cff8854c406da85a97408d62480548568e15ca488e75bbfaca93c20
combined verification          f8e39e7822dc88477b246037eafd2ca6a2f48ff6c1e0af73580bb37c7affba41
```

The licensed claim is narrow: within these preregistered finite H2 families,
one source-observed portable relational skeleton is instantiated across
vertex counts and in a second domain, planning occurs in target-local partial
statistical RAPMs, failed proof restores only local distinctions, and a
no-cover case falls back exactly. The role ontology and grammar remain human
supplied; LMB uses a domain-specific symbolic selector. Target verification is
same-implementation, and the no-transfer/OOD controls cover registered
identity, transplant and permutation attacks rather than observational OOD
generalization. Repeated occurrences have identical query parameters and do
not establish changed-query reuse. Primitive/ontology invention, generic
model-selected planning, unconditional statistical validity and sample
efficiency remain unclaimed.

All 62 V0-066 focused tests pass in one fresh process. The 115-module
parallel repository regression passes all 1,412 tests with no failed module.

All official execution, scalar, break-even, workload-economics,
counter-completeness and sample-efficiency locks remain false, null or
`NOT_RUN`. The next Gate may use the now-observed acquisition costs to test a
Laplace-style heuristic operator or KG-OP-style meta-prior against a matched
no-operator route, but must not weaken target-local certification.

## V0-065 observation-driven cross-geometry relational RAPM rule

Contract `1.29.0` freezes schema `1.0.0`, profile
`observation_driven_cross_geometry_relational_rapm_v0`, and passing status
`CERTIFIED_REGISTERED_CROSS_GEOMETRY_RELATIONAL_RAPM_FAMILY`. Before source
observations, target draws, programs, supports, models, plans or certificates, it
registers source graphs `P4`, `K1,3` and paw; held-out target graphs `C4`, diamond
`K4-e` and `K4`; graph-isomorphism and structural-ID disjointness; H2 semantics;
two occurrences per target; the bounded grammar and candidate order; target
acquisition rounds; symbolic outcome support; calibration; controls; and all
claim locks. No source graph is isomorphic to a target graph.

The source fixture contains 120 complete state/action rows over 51 H2 states.
Its public producer receives only the anonymous source log. It has no kernel,
target, query, plan, value, group, graph-name feature or prospective evidence
input. Complete depth-two closure produces 262 syntactic programs and 42
source-semantic representatives. The scalar base search evaluates all 25
integer state/action pairs, admits two and deterministically selects:

```text
state  = cardinality_actions(legal_actions)
action = cardinality_cells(
           adjacent_filter(survivor_cell, occupied_cells)
         )
```

The selected source summary has 51 ground states, 120 ground rows, four
abstract state keys, seven abstract support keys and honest maximum sound-alias
width `99/100`. This width is deliberately not relabelled as exact
homomorphism, probability transfer or certificate evidence. The emitted
proposal contains only the two ASTs, content-addressed source/registry
provenance and a topology-independent anonymous support-key schema; it contains
no source transition row, probability, reward, decision or policy.

Every target instantiates its own support catalogue, begins with an all-missing
target-local statistical RAPM and performs two proof-authorized acquisition
rounds. `C4`, diamond and `K4` acquire root/continuation rows `16+32`, `20+40`
and `24+48`, respectively, for 180 positive rows total. Every row records
65,536 individual replayable draws, so positive target construction uses
11,796,480 generative samples. Source rows and probabilities never narrow a
target interval, and the three final RAPMs have distinct context/model
identities. Two occurrences per target then run model-only against that
context's immutable final RAPM and add zero ground rows.

The base-coordinate final audits are, in target order:

```text
C4       CERTIFIED
diamond  FAILED_RISK_OR_REGRET
K4       CERTIFIED
```

Only diamond's frozen failed proof may search optional programs already present
in the source-frozen 42-program registry. All four registered combinations are
evaluated; target program and primitive generation counts remain zero. The
smallest certifying profile appends state program
`rank_degree_signature` and action program
`cardinality_cells(adjacent_filter(survivor_cell,all_cells))`, i.e. survivor
degree, creates a new immutable diamond epoch, replans and certifies. The final
target result is therefore `3/3` certified contexts with normalized-regret
upper zero and failure uppers:

```text
C4       230656215 / 5905580032
diamond  516701257 / 10737418240
K4       839745981 / 21474836480
```

Each bound is strictly below `1/20`. Six occurrence-cold exact controls perform
no RAPM reuse and reproduce optimal failure `99/5000`.

Statistical calibration is frozen before draws over every possible positive
and semantic-OOD atom obligation, including failed paths: 65,536 draws per
row, radius `1/110`, 912 obligations, per-atom tail upper `1/25000`, family
tail `114/3125`, and confidence lower `3011/3125 > 19/20`. Exact probabilities
and J0 controls remain evaluation-only; target interval centers come only from
raw target draws over the registered symbolic support.

The mandatory controls are authoritative:

- three no-transfer arms forbid target transition-driven abstraction search,
  emit no abstract certificate, use direct fallback and match the cold result;
- the V0-064 legacy fixed schedule certifies only one of three target contexts,
  rejects two and emits zero false certificates;
- a 48-row/3,145,728-draw hidden-colour semantic-OOD mechanism fails mechanism verification,
  forbids model construction, emits zero abstract/false certificates and
  requires fallback;
- an unregistered topology is rejected before any ground access;
- permutation `(2,0,3,1)` preserves the selected ASTs, semantic-support
  multiset and mapped value/risk certificate without using a graph-identity
  feature;
- stale, source, cross-target and cross-epoch evidence/model/authorization
  transplants fail closed.

Campaign ID
`2399c56dd7378429cc08dabb52d7bb76c61bc26f7541dccb535badfe193a7d7a`
and verification ID
`ea29a7e0c885166c1b321df24a53edc37975fe680f9bc97f4fa38288830ea329`
are frozen. The verifier replays the same implementation, all raw draws,
epochs, occurrence audits, controls and cold comparators; it is not an
independent algorithm. All 33 V0-065 focused tests and all 1,350 repository
tests pass on a stable source/spec snapshot.

The licensed claim is restricted to this preregistered finite graph-merge
family: a source-observed relational coordinate/support schema transfers to
non-isomorphic held-out graph geometries; target-local observations build
separate statistical RAPMs; planning occurs in those RAPMs; and one
source-registry distinction is restored only after certificate failure. It is
not broad graph generalization, a second-domain result, primitive invention,
raw perception, unknown support, source/cross-target dynamics transfer,
cross-structural RAPM reuse, independent verification, sample efficiency or
official economics. All official, scalar, break-even, workload-economics,
counter-completeness and sample-efficiency locks remain false, null or
`NOT_RUN`.

## V0-064 observation-driven relational coordinate/support rule

V0-064 freezes the source/target structural split, grammar, candidate shape,
occurrences, kernel and implementation digests before evidence. Source and target
structural IDs are disjoint. The source producer accepts only a semantically complete
144-row anonymous log and cannot receive target/query inputs, a transition interface,
a group canonicalizer, named frontier rows, Q/value signatures, or a plan.

The complete depth-two closure and search must reproduce `7 -> 19 -> 56` semantic
programs, `432/432` evaluated candidates, 13 admissible candidates, six anonymous
supports, and the state/action coordinates and three semantic decisions frozen in
`specs/OBSERVATION_DRIVEN_RELATIONAL_SUPPORT.md`. The abstract selector is
deterministic; its concretizer is uniform over distinct matching ground actions.

Each target context begins with six missing rows. Only the current failed model-only
audit may authorize acquisition. The required trace is one missing root support,
eight ground rows, two missing continuation supports, sixteen ground rows, then a
certificate. Source probabilities never narrow target intervals. Target acquisition
uses a generative atom API and records individual draws; the symbolic outcome support
is registered, so unknown-support discovery remains explicitly false.

The 24 target rows are context-build work before either registered point occurrence.
Both occurrence certificates bind their own occurrence and initial-catalogue IDs and
then add zero query-local rows. Calling this sequential first-to-second occurrence
acquisition is forbidden. Cross-structural RAPM reuse is also forbidden.

Every target evidence artifact requires semantic replay of its failed audit, model,
authorization, legal catalogue, seed, symbolic support and raw draws before model
construction. Every audit binds model epoch, exact evaluation scope, occurrence when
applicable, and calibration. The exact family calibration is radius `1/60`, exponent
`2048/225`, degree-13 Taylor lower greater than 8000, per-coordinate tail `1/4000`,
176 obligations, family tail `11/250`, and confidence `239/250`.

The campaign verifier is a same-implementation full semantic replay, not an
independent algorithm. The principal IDs, target risk bounds, exact controls, claim
locks and next Gate are frozen in the normative specification. Official execution,
scalar/break-even, workload economics, counter completeness, sample efficiency,
primitive invention, unknown support, unseen graph geometry and broad generalization
remain false, null, or `NOT_RUN`.

## V0-063 preregistered sequential source-stopping rule

Contract `1.27.0` freezes schema `1.0.0`, profile
`g2048_preregistered_sequential_source_stopping_v0`, and passing status
`CERTIFIED_REGISTERED_OFFLINE_INCLUSIVE_SAMPLE_TAX_REDUCTION`.

The complete V0-062/V0-061 target workload and controls remain unchanged.
Before evidence, V0-063 freezes three ordered target-disjoint source contexts,
all three two-row candidates, one 4096-draw block per row/context checkpoint,
minimum two and maximum three contexts, proposal guard radius `1/64`, delta
`1/20`, unique-unanimous stopping, source seed/counter protocol, and the
implementation digest. Prospective evidence, prior, plan and result IDs are
absent.

The source guard is proposal-only and has no confidence-certificate
authority. A checkpoint is allowed only after all three frontier rows in the
current context have one complete block. Before two contexts, stopping is
forbidden. At or after two contexts, exactly one subset must pass in every
acquired context; otherwise acquisition continues or abstains at the maximum.

The registered trace is:

```text
checkpoint 1 = CONTINUE_MIN_CONTEXTS
checkpoint 2 = STOP_UNIQUE_UNANIMOUS
frozen prefix = ROOT_TOWARD + CHAIN_A_AWAY
unused source contexts = 1
source rows/draws = 6 / 24576
```

No row from the third source context may be enumerated. The stopped prior sees
no target context/evidence and cannot narrow target envelopes or certify
plans.

The target-only route remains six rows/`98304` draws and certifies all six
occurrences at confidence `347/350`, with three model reuses. The unchanged
no-operator and cold-direct controls remain `147456/9` and `4866048/198`
draws/rows. The wrong prefix still fails in all three contexts before three
tail acquisitions; false certificates remain zero.

The only new positive claim is:

```text
V0-062 fixed source draws             = 147456
V0-063 stopped source draws           =  24576
source draw reduction                 = 122880 = 5/6
source + operator target              = 122880
unchanged no-operator target          = 147456
registered offline-inclusive saving   =  24576 = 1/6
```

The two-context crossing is a single-unit diagnostic, not
`official_N_break_even`. The following locks remain:

```text
broad_sample_efficiency_claimed = false
automatic_coordinate_discovery_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

Normative semantics and principal IDs are in
`specs/SEQUENTIAL_SOURCE_STOPPING.md`.

## V0-062 source-frozen sample-tax intervention rule

Contract `1.26.0` freezes schema `1.0.0`, profile
`g2048_source_frozen_boundary_capability_operator_v0`, and passing status
`CERTIFIED_REGISTERED_HELDOUT_SAMPLE_TAX_INTERVENTION`.

Three source-only safe-chain contexts with rank-one probabilities
`497/500`, `399/400`, and `1999/2000` are disjoint from the three V0-061
target context identities. The source/target split, all six target
occurrences, the unchanged V0-061 baseline preregistration, sampling profile,
and implementation digest are frozen before any source evidence, target
evidence, prior, plan, or result ID exists.

The offline lane samples exactly the three V0-061 failed-proof rows in every
source context, for nine row enumerations and `147456` generative-oracle samples. From source logs
only, it evaluates all three two-row subsets with honest `[0,1]` missing
rows. The unique subset that robustly certifies in every source context is:

```text
ROOT_TOWARD + CHAIN_A_AWAY
```

It is frozen as the proposal prefix; `CHAIN_B_AWAY` is the broad tail. The
prior records empty target context/evidence references and zero target-kernel
access. It may rank/propose only and may not narrow a target interval or
certify a target plan.

On the unchanged V0-061 held-out targets, production sees only the two-row
prefix, constructs an honest `2 observed / 4 missing` partial RAPM, enumerates
all eight deterministic H2 schedules, and certifies from target observations
only. Six target row enumerations/`98304` generative-oracle samples replace the no-operator control's
nine rows/`147456` observations. The 12 target coordinate obligations give
family tail `3/350` and confidence lower `347/350`. All six point/uniform
occurrences certify and three second occurrences reuse their context model.

The unchanged V0-061 adaptive and cold-direct arms remain the required
controls. A registered wrong-prior prefix
`ROOT_TOWARD + CHAIN_B_AWAY` must fail in all three targets, authorize only
`CHAIN_A_AWAY`, then certify after exactly three fallback rows. False
certificates remain zero. This proves that source information can change
work, but not target certificate authority.

The only new positive sample claim is:

```text
registered target-online saving = 147456 - 98304 = 49152
registered target-online reduction = 1/3
```

Offline source draws are separately charged. Offline plus registered target
work is `245760`, so offline-inclusive saving is false. The ratio of source
draws to one-context target saving is nine; this is a diagnostic in one
native unit, not official scalar economics or `N_break_even`.

Production prior fitting accepts no target input. Production target
builder/planner accepts no exact kernel. Standalone evaluation regenerates
all source draws, reruns the complete V0-061 verifier, reconstructs positive
and wrong-prior paths, evaluates all six target plans exactly, and rejects
draw, leakage, identity, context, kernel-interface and implementation
attacks.

The global locks remain:

```text
offline_inclusive_sample_reduction_claimed = false
broad_sample_efficiency_claimed = false
automatic_coordinate_discovery_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

Complete semantics and identities are normative in
`specs/SAMPLE_TAX_INTERVENTION.md`.

## V0-061 matched end-to-end acquisition workload rule

Contract `1.25.0` freezes schema `1.0.0`, profile
`g2048_matched_adaptive_vs_cold_direct_ground_v0`, and status
`CERTIFIED_REGISTERED_MATCHED_END_TO_END_ACQUISITION_WORKLOAD_CONTROL`.
The same three V0-060 contexts and six point/uniform H2 QuerySpecs are bound
before evidence. Both routes must consume identical context/query identities.

The adaptive route starts from six explicit missing abstract rows per context.
Its failed risk proof authorizes only `ROOT_TOWARD`, `CHAIN_A_AWAY`, and
`CHAIN_B_AWAY`. It samples nine total rows at 16,384 draws per row, builds
three honest `3 observed / 3 missing` partial RAPMs, evaluates eight semantic
policies per occurrence, and reuses each immutable context model for the
second query. Its totals are three initial failed proofs, 24 failed-proof
candidate evaluations, nine kernel-row enumerations, 147,456 individual
draws, three model builds, 48 occurrence candidate evaluations, six
certificates, and three within-context zero-draw reuses.

The direct route starts cold for every occurrence and receives no D4 quotient.
It independently enumerates the complete any-policy reachable ground
state-time/action support, records a probability-free codebook and 24,576
individual draws for every row, constructs an occurrence-local ground model,
selects deterministic H1 actions, enumerates every root action assignment,
certifies the complete deterministic ground policy, then discards the model.
A point query has `6/18/16/2/2` state-time/action/H1/root/candidate counts; a
uniform query has `20/48/32/16/256`. Campaign totals are 78 catalogue calls,
198 transition rows, 4,866,048 draws, 144 H1 estimates, 54 root estimates,
252 statistical obligations, 774 root candidate evaluations, six
certificates, and zero model reuse.

Both routes use radius `1/64`. Adaptive obligations retain per-coordinate
tail `1/1400`; direct scalar obligations use exact-rational exponent 12 and
tail `1/50000`. The frozen union calculation is
`18/1400 + 252/50000 = 783/43750`, giving simultaneous confidence lower
`42967/43750`. The direct arm's larger per-row sample count is explicit
family-multiplicity compensation, not hidden post-run tuning.

Every raw outcome index is stored in a content-addressed packed trace.
Codebooks contain concrete transition semantics but no probability.
Production model builders and planners accept no exact kernel. The
standalone verifier independently replays 147,456 adaptive plus 4,866,048
direct observations, re-enumerates all 198 direct rows, evaluates both
selected routes exactly, and runs six unrestricted J0 controls. Adaptive
exact value equals J0. Direct plans match J0 reward `3/64`, remain below risk
`1/20`, and expose any finite-sample risk gap from J0 rather than requiring
or pretending exact risk-optimal tie breaking.

The native draw ratio is:

```text
4866048 / 147456 = 33
```

This licenses only
`registered_workload_draw_advantage_observed=true`. It is conditional on the
registered known-D4 prior, known finite symbolic support, six occurrences,
and frozen confidence profile. `broad_sample_efficiency_claimed`,
`sample_tax_operator_claimed`, automatic coordinate/symmetry/support
discovery, and broad generalization remain false. Both route fallback counts
and noncertificate occurrence closures are explicit native zeros. Official
execution remains false; official scalar and break-even remain null; all
economics Gates remain `NOT_RUN`.

The next Gate may introduce a separately preregistered Laplace-style
acquisition operator or KG-OP-style offline/online meta-prior only with an
unmodified no-operator control, held-out contexts, separate offline-prior
cost, and complete evidence replay. V0-061's ratio is its baseline, not its
promised outcome. Full semantics are in
`specs/MATCHED_END_TO_END_ACQUISITION_WORKLOAD.md`.

## V0-060 raw replayable multi-context acquisition rule

Contract `1.24.0` freezes schema `1.0.0`, profiles
`g2048_raw_replayable_multicontext_partial_statistical_v0` and
`g2048_certificate_directed_vs_uniform_acquisition_v0`, and status
`CERTIFIED_REGISTERED_RAW_REPLAYABLE_MULTICONTEXT_ACQUISITION_CONTROL`.
The original safe-chain fixture and its `99/100` spawn law remain unchanged.
Three new, noninterchangeable simulation contexts freeze rank-one
probabilities `199/200`, `249/250`, and `999/1000` over the same explicitly
known `D4` structural/action catalogue. A point query and a uniform-orbit
query per context are registered before any raw-log, model, or plan identity.
Evidence and models may be reused only inside an identical context.

Every initial context model has six explicit missing `[0,1]` binary-simplex
rows. Model-only enumeration first selects `TOWARD,AWAY,AWAY` but fails its
risk proof; that frozen proof authorizes only `ROOT_TOWARD`,
`CHAIN_A_AWAY`, and `CHAIN_B_AWAY`. The adaptive lane samples exactly those
three rows and leaves the other three rows vacuous. The independent direct
control samples all six registered rows under a different seed. Every
observed row contains 16,384 counter-based draws in four 4,096-draw
content-addressed blocks. One exact ground-outcome index per draw is embedded
as a hexadecimal nibble. Codebooks retain concrete next state, status,
normalized reward, failure/terminal flag, and structural destination but no
transition probability. Aggregate-only evidence is invalid.

Exact-rational Hoeffding calibration uses radius `1/64`,
`2*n*radius^2=8`, per-coordinate tail `1/1400`, and exactly
`2*3*(3+6)=54` obligations, giving family tail `27/700` and simultaneous
confidence lower `673/700`. Production model construction decodes every
nibble, imports no probability, and accepts no exact kernel. Missing rows
remain native uncertainty. Both lanes enumerate eight deterministic
policies per occurrence and certify reward `3/64`, regret zero, and robust
risk below `1/20`. Adaptive failure uppers are
`11153865/268435456`, `2575781/67108864`, and `34527/1048576`;
direct-control uppers are `1382201/33554432`,
`10511905/268435456`, and `8871139/268435456`. The second query in each
context reuses the same immutable model with zero new draws.

Native totals freeze `9` adaptive observed rows, `9` adaptive explicit
missing rows, `18` direct observed rows, `147456` adaptive draws, `294912`
direct draws, `27` acquisition kernel-row enumerations, three within-context
zero-draw reuses, and zero cross-context model reuse. The standalone
evaluation verifier independently recomputes and checks all `442368`
individual draws, reconstructs the codebooks from three exact context
kernels, and executes unrestricted J0. Exact reward is `3/64`; exact risks
are `199/20000`, `249/31250`, and `999/500000`, with `5440` composed
candidates per context. Each exact optimum lies inside both statistical
certificates, but evaluation cannot promote statistical evidence to
`exact_sound`.

The all-six-row arm is normatively an
`independent_uniform_all_six_row_statistical_control`, not a matched
direct-ground planner. Therefore `294912-147456=147456` is recorded only as
a draw-count difference. `matched_direct_ground_planning_claimed`,
`sample_efficiency_claimed`, and `sample_tax_operator_claimed` remain false;
official scalar cost and `N_break_even` remain null. Automatic `D4`,
coordinate, primitive or support discovery, raw symbolization, broad
cross-geometry/domain generalization, learned dynamics, complete accounting,
economics and official execution remain locked.

Principal frozen identities are preregistration
`6117c8d72ee25afe393145db726bfa7a6edafde8d4439a83963b7d1bf8a41b3e`,
evidence bundle
`547cee4144499e9de4753f910f0571f64c58c3266c50744cce967f8482aca7c0`,
campaign
`6c5e95ac16d157ff28f103fbb6fb9782846d1b8407aa5a2808bfc744e91ad1f0`,
verification
`fa055f4525189d6e1dcbc4a1e849ca4b475018e2cc74e4e3885c9367cd562269`,
and implementation
`364696557d33f67a5ff96a97684917a822f49beb62ad95d25c4447fbe81544b6`.
The complete normative protocol and next Gate are in
`specs/RAW_MULTICONTEXT_ACQUISITION_CONTROL.md`.

## V0-059 multi-domain observed/statistical held-out campaign rule

Contract `1.23.0` freezes schema `1.0.0`, profiles
`multidomain_observed_statistical_heldout_campaign_v0` and
`g2048_d4_empirical_hoeffding_partial_rapm_v0`, and passing status
`CERTIFIED_REGISTERED_MULTIDOMAIN_OBSERVED_STATISTICAL_HELDOUT_CAMPAIGN`.

The preregistration must exist before prospective models or plans. It binds:

- the V0-058 LMB observation log, semantics and observation authority;
- a probability-free G2048 D4 structural catalogue;
- a trusted content-addressed aggregate sample ledger;
- two distinct primitive-schema registrations; and
- the exact twelve-occurrence LMB/G2048 order and domain-specific thresholds.

LMB retains automatic complete depth-two composition and selection only
inside its frozen human primitive/operator vocabulary. G2048 explicitly
retains `known_exact_d4_automorphism_not_automatically_discovered`; its D4
state-time cells and relative-survivor semantic actions are a human
structural prior. No shared cross-domain coordinate or automatic G2048
symmetry-discovery claim is permitted.

The G2048 catalogue contains seven cells and six binary action rows with
known rewards, destination identities and failure/terminal semantics, but no
transition probabilities or held-out queries. The offline ledger provides
65,536 trusted aggregate observations per row and 393,216 total. It is frozen
before query release and explicitly does not embed individual draws.
Statistical validity is conditional on this sufficient-statistic authority.

Each destination coordinate uses empirical probability plus/minus `1/128`,
intersected with the binary simplex. The exact-rational proof freezes
`2*n*epsilon^2=8`, the degree-13 positive Taylor lower
`exp(8)>2800`, per-coordinate tail less than `1/1400`, twelve-coordinate
family tail at most `3/350 < 1/100`, and confidence lower `347/350`.
Every G2048 probability row and plan certificate must remain
`statistical_high_probability`; exact-sound promotion is forbidden.
This is a profile-specific research/evaluation extension to the evidence
classes listed in V0-011, not a relaxation of V0-004/V0-011 for official
execution: any Gate requiring `exact_sound` still rejects this statistical
certificate.

The robust H2 planner enumerates the complete eight deterministic
relative-survivor schedules and selects:

```text
schedule                  = TOWARD,AWAY,AWAY
reward                    = [3/64,3/64]
failure lower             = 9277983/2147483648
failure upper             = 75716127/2147483648
risk threshold            = 1/20
normalized regret upper   = 0
```

The campaign order contains three strict LMB H2 occurrences (`delta=0`),
eight G2048 D4 point occurrences and one D4-uniform occurrence
(`delta=1/20`). The first LMB occurrence performs exactly three
certificate-triggered target transition calls; two later occurrences perform
fresh model-only proposal/audit and no target calls. The first G2048
occurrence uses the newly built statistical model and the next eight reuse
it; all nine enumerate eight policies and use zero online samples. The G2048
family is one quotient-equivalent D4 control, not broad changed-query
generalization.

Production receives no exact G2048 kernel. The standalone evaluation verifier
alone rebuilds the exact D4 quotient, checks exact row probabilities lie in
the intervals, and confirms exact optimal value `3/64` and failure `99/5000`
are contained by the selected statistical certificate. Evaluation cannot
change the production evidence class.

Canonical work is:

```text
logical occurrences                         = 12
LMB program candidates                      = 6650
LMB plan candidates                         = 16
LMB exact target transition calls           = 3
G2048 offline logged samples                = 393216
G2048 statistical policy candidates         = 72
G2048 online samples                        = 0
exact-sound certificates                    = 3
statistical high-probability certificates   = 9
```

All 15 focused tests and all 1242 repository tests pass. Principal IDs are frozen in
`specs/MULTIDOMAIN_STATISTICAL_HELDOUT_CAMPAIGN.md`. V0-059 leaves
sample-efficiency, complete CounterRegistry accounting, scalar economics and
official execution locked. The 393,216 logged observations expose the
current sample tax; they do not establish necessity, optimality or savings.
The next construction Gate requires raw or independently replayable
stochastic logs across multiple structural contexts and matched adaptive
acquisition/direct-planning traces before any Laplace-style heuristic
operator or KG-OP meta-prior claim.

## V0-058 observation-driven program-closure and held-out H2 rule

Contract `1.22.0` freezes schema `1.0.0`, profiles
`lmb_observed_program_closure_partial_rapm_v0` and
`lmb_observed_program_closure_heldout_h2_v0`, and statuses
`OBSERVATION_CONSISTENT_PROGRAM_CLOSURE_PARTIAL_RAPM` and
`CERTIFIED_OBSERVED_PROGRAM_CLOSURE_HELDOUT_H2_RECOVERY`.

The coordinate producer accepts exactly the observation log, deterministic
semantics profile and preregistered observation authority. It receives no
query, kernel, target, candidate subset/cap, caller value table, policy,
frontier, value/Q/J0 object or transition callback. Within the frozen human
primitive/operator vocabulary it generates every type-correct expression of
depth at most two, semantically deduplicates by exact type/context/full-source
covariate signature, and retains the least AST. The frozen closure is
`8 -> 21 -> 215` cumulative representatives; scalar catalogues are `174`
state and `37` state-action programs. Production exhausts
`(174+1)*(37+1)=6650` optional-single-coordinate candidates, of which `1384`
are admissible, and selects candidate `4013`:

```text
state  = cardinality(legal_actions)
action = buffer_at_type(buffer_counts, selected_tile_type)
atom   = action <= 3/2
```

The selected source audit is `7` point rows, `3` equal observed alias pairs,
`0` partial rows, `5` entries, `4/6` active/total cells, `18` separated null
conflicts and `3` nontrivial point entries, with no availability violation or
observed contradiction. The resulting source partial RAPM preserves
`7 observed / 4 missing`; missing rows remain vacuous.

The held-out query is preregistered before synthesis at
`removed_mask=35, buffer=(2,1), H=2`, exact regret/risk tolerance zero. The
target is absent from all source states/rows. After one complete source
synthesis replay, exactly one target catalogue is read. The automatic program
maps it to state coordinate `(3,)` and labels tile 2 false, tiles 3/4 true.
All three target dynamics remain missing in the initial `7/7` query epoch.
Four H2 contingent plans and a role-distinct selected audit reproduce
`FAILED_PROOF_FRONTIER/EXTERNAL_COVERAGE_ESCAPE`, reward `[0,4]`, failure
`[0,1]`, unrestricted upper `4` and normalized regret `1`.

Only this selected failure creates the `1 selected-risk / 3 unrestricted-value
/ 3 distinct` single-use authorization. Exactly three target transition rows
are queried. Tile 2 yields match reward one and an already-registered source
successor; tiles 3 and 4 fail. No successor catalogue or successor transition
is queried. The immutable final epoch is `10 observed / 4 missing`; all
source rows are byte-identical between initial and final query epochs and the
four original missing rows remain missing. Four new model-only plan audits
plus a separate selected audit certify reward/failure/regret `1/0/0`.

The chronology-sensitive implementation digests are:

```text
program closure = c17ee3b4501beb859b2fca1a9b07968f32e7f653c6897679581766cca91d1e8f
candidate audit = 7a011aa2c35910196e277f281c2d2063ef60c4cb7e067e1b66b9493bd68ccf39
held-out H2     = 9bda243287c2bea3db70d822cd027451e7b6f2e34dffd99beb5a7a726e6c1c94
```

Principal canonical IDs are:

```text
program_registry_id       = 1331c29c9f23390b296d3be3777b99cda7eba915755bbd7d92808b411df1a9b0
candidate_trace_id        = a2addf7fc8a78889793d0fa381041e9e12f41e010d51f21580040108e938281a
selected_candidate_id     = aa9c34b68073c1869f8103183fb00df5a792b4c75c56d106088bf65e2abb7356
coordinate_proposal_id    = 1afa79feca7d6ea93f687f5fe9386427b1d79bce7848f19fad98ddcccc3669b1
source_partial_model_id   = a3a03c8c31adc8236c549fd311ace906e3af5331937d0f8537ff220d75785f4f
synthesis_result_id       = f4b4904a5d1944e97dcf4dfc8e2fd7620b74dedf32f60ee2dd94e41f7b22666f
preregistration_id        = 3389cec70655a35e69a606c2ef72daca00c5c6362f780fe78bb4218911d3dcd5
initial_epoch_id          = 027abab818aae2bd0469f5ab4f45197457bcc08a66700c434a87799a708f40f1
authorization_id         = b30d795691a056c08ead4a003e187d7b57ed8ad2829f73c5a4a2c190065614aa
evidence_bundle_id        = 5269dd0c8675201b637cf274d570225463885a9ffc0ce9336f53e9d4345eb5a3
final_epoch_id            = b835afe210574787aa668640d12500d7829268c1d041e521defdaaa687792efe
final_selected_audit_id   = d09b1882d41234bd930ea6702d1ca620b6f7c7afec6967a83e34578005a93d96
coordinate_transfer_id    = fe3656299154cd6b79fd3e2ba102fa997bfc1857ec15eebf086261a631e32f8b
heldout_result_id         = f70cbc1c48645c071ab842c0ec328d22157a61458b72a17933daf82e9ae7efdd
```

All 19 registered tests pass. V0-058 does not open primitive/operator
invention, raw symbolization, statistical/learned dynamics, general H>2,
broad held-out/cross-domain generalization, sample-efficiency, economics,
counter-completeness or official-execution claims. Full rules and attacks are
normative in
`specs/OBSERVATION_DRIVEN_PROGRAM_CLOSURE_HELDOUT_H2.md`.

## V0-057 interleaved certificate-triggered durable H2 epoch rule

Contract `1.21.0` freezes schema `1.0.0`, profile
`lmb_h2_interleaved_certificate_triggered_durable_epoch_v0`, and passing
status
`CERTIFIED_REGISTERED_H2_INTERLEAVED_CERTIFICATE_TRIGGERED_DURABLE_EPOCH_CONTROL`.
The complete registered suite passes all 85 positive, attack,
deterministic-replay and fresh-store evaluation tests. The Gate passes and
its canonical principal identities are:

```text
orchestrator_sha256      = 9808009f3e9aa2c444466799679e80772a444e69f49ede632f09a0153f8ea419
result_id                = 092c92708f67a2b0044abce792a96e9afed5cda56a017d1b99063433861ce01c
verification_id          = 6330a3a6be2b4a3e1365f8cf62cc8c4dec6ad02b80c7aba5fd65e64c4f28e9d9
campaign_snapshot_id     = 4add6d49870f37692622db051b56b830158e30ab9cf0dbe65140c44718e02553
preregistration_id       = 530e7c76f29c7590826abacb44e13cf3559481ae7f21b54c68a166a24fb57435
source_chain_id          = a070baa803adf19a435fbcc558016b2a729313b5cfd06776c309f5e35a5b8f45
authorization_id         = 09aecbb5df77b7d102928f0f1a3c4bd1ced8bf33f9218ed4a58ed336eed998ef
accounting_id            = dce0c871d4f2ebecfba185e39d8097737cd850541f6bcbbfa38f28c355981a5a
event_log_id             = 6b0de30820c6460a783e558ed514b37499087c14d7d73505e76cb4b9d231a21d
C1_payload_id            = 2fb3897106fff1387ebe6f3edb5618c88fe597e0e952b1531805da3db359fc3e
C1_commit_id             = 0272231a20d8162882fdf309c008c19fb3e3265f4d10bc2df918c9ec11430737
C2_payload_id            = d81d33a52705488ab9944c2911222f54b2a773f26ba2decf5bb4ad53eb4b2a49
C2_commit_id             = 2164daa10ae031ab4b36e0f3602c0d015430befca256ee13c8bde2899b066e29
first_facet_tip_id       = adea7a973cfaa2bc3a5e671b82417c04dcaed942a521dd97b8d6e9aa830aad66
final_facet_tip_id       = 1c135cd185268051e992191628a7f9788079c01ebb5169db43ad96f3d5d919cf
```

Before any source construction or query result, the protocol freezes the
threshold-only family and order:

```text
Q_R = normalized-regret tolerance 3/4, risk tolerance 1
Q_S = normalized-regret tolerance 0,   risk tolerance 0
order = Q_R,Q_S,Q_R,Q_S,Q_R
```

The same pre-source artifact binds the exact eight input-authority identities
(`observation_log`, semantics profile, observation authority, observed
synthesis, source thresholds, base proposal, failed audit and kernel digest),
plus goal, H2 initial/reward/return/unrestricted formulas, base
structural/environment/model/coordinate scope, complete semantics
profile/state/action/realization/concretizer scope, policy class, candidate
order and proof registry. It freezes
`derived_source_artifact_ids_absent=true`: prospective first/final V3 model,
checkpoint, source-chain and result IDs are forbidden from the
preregistration.

Q_R is a new epoch-bound typed query/eligibility object. The historical
`FrozenPartialAuditThresholdsV1` does not admit `(3/4,1)` and must not be
edited, monkeypatched or duck-typed. Q_S retains the exact original strict
V0-047/V0-053 semantics. Both queries bind the same H2 structure, initial
distribution, reward basis, return proof, state/action semantics,
concretizer, candidate order and V3 model lineage; only the two threshold
facets differ.

Production starts from the original eight V0-047/V0-053 upstream authorities,
not a completed result or caller-supplied model, row set, proof graph or
expected outcome. It must derive the authentic first V3 epoch live as
`11 observed / 9 missing`, charging the four round-one transitions and three
direct boundary catalogues. Once that epoch and root-free C1 are frozen:

1. occurrence 1 independently certifies Q_R at regret/risk `3/4 / 1` with
   zero additional query-triggered transition, catalogue or optimizer calls;
2. occurrence 2 applies strict Q_S and freezes the selected
   `t=1,h=1` value/risk failed root with
   `external_coverage_failed=false` and
   `external_coverage_certified=true` before any further ground access;
3. only that selected Q_S failure may derive the exact registered nine-row
   request;
4. exactly nine owner-bound transitions freeze the immutable `20/0` V3
   successor;
5. strict Q_S replans and certifies exact reward/failure/regret `1/0/0`; and
6. later Q_R/Q_S/Q_R occurrences use the final epoch with zero target ground
   calls and the same exact final values.

C1/C2 persist the authentic 30-node strict-Q_S lower core. Its E/F entries
are real strict threshold gates, not threshold-neutral placeholders. Q_S
roots must bind and semantically replay those actual entries. Only Q_R uses
a disjoint epoch-bound overlay containing four relaxed-regret E and four
relaxed-risk F variants. First-epoch Q_R facets are ineligible after the model
change; final-epoch Q_R derives eight new variants. Query facets never enter
C1/C2 strict-core cardinalities and cannot overwrite strict E/F. Every Q_R
facet binds preregistration, eligibility, query, epoch/model, metric and exact
source-D parent. Every root carries a separate proof request bound to
candidate-versus-independent-selected role, occurrence, model, epoch,
evidence request, metric, schedule and selected proposal where applicable.

The exact strict-core epoch delta is:

```text
C1 union/active/historical = 30/30/0
new final lower nodes       = 28
reused lower nodes          = 2, exactly the two extensional C0 entries
C2 union/active/historical = 58/30/28
persisted roots             = 0
```

Five logical occurrences resolve five proof blocks times ten lower slots.
Their append-only Q_R-facet builder/hit traces are:

```text
8/42, 0/50, 8/42, 0/50, 0/50
global total = 16 builders / 234 exact hits
```

Those five-occurrence figures are projections, not native worker totals.
Occurrence 2 has a sixth fresh model-only proof process for final
recertification. The main arm's six worker records are `16/284`; the matched
overlay-reset arm's six are `24/276`. Each arm builds 30 fresh roots. The
complete operational campaign therefore has 12 launches, 60 roots and
`40/560`; its logical projections remain `16/234` and `24/226`. Neither O2
worker nor the `28/2` strict-core epoch update may be discarded. The logical
projection uses `O2_RECERTIFIED_FINAL` as occurrence 2's closure;
`O2_FAILED_FIRST` remains native certificate-triggering attempt work. The
reset arm does not reset C1/C2 or replay ground acquisition.

C1 and C2 are separate immutable checkpoint stores. C2's predecessor is a
cross-store pointer whose C1 target must be independently loaded and
externally verified; it is not directory-local history. C2's complete
retained C1 records and historical set must equal the independently loaded C1
active set minus the two shared C0 identities. Final workers snapshot C1, C2
and their facet store. `facets-c1` and `facets-c2` likewise form two
epoch-local append-only chains, each with its own W0/genesis. The campaign
freezes exactly 23 owner-bound, sequence- and context-bound live events.
Literal `EXPECTED_*_SHA256` values in a separate V0-057 pins module bind the
complete orchestrator and registered upstream module/callable sources before
host root/ground access and before worker checkpoint/query reads. The pins
module cannot self-hash or derive those values at runtime.

Both model epochs select semantic schedule `A0A0`. Model, plan, proposal and
root identities change, but V0-057 makes no semantic-policy-switch claim.
Both V3 epochs remain query-owned, non-query-neutral, nonpromotable,
non-exact and not globally transition-closed.

The operation traces above are not environment samples or a complete
`CounterRegistryV1`/`WorkVectorV1`. Byte telemetry covers only
query/occurrence input files, worker result files and serialized
checkpoint/facet footprint, not cumulative I/O traffic. A fresh-store
evaluation replay runs the
same implementation over both arms with another 12 evaluation-only worker
launches and must report `independent_algorithm=false`. Operational host
checkpoint/cross-store/facet counts are `23/9/36`; result
reconstruction/snapshot/immutability/assertion counts are `12/64/32/12`.
Evaluation reports the same vector with evaluation-prefixed fields, outside
operational work. The exact repair scope is `3 selected-risk / 9
unrestricted-value / 9 distinct requested` rows with `3 safe / 6 terminal
failure` outcomes.

The positive result is a process-local runtime-minted claimed handle plus
durable campaign bytes. A copied or deserialized wrapper does not mint final
semantic authority. The verifier validates the live claimed handle and
durable snapshot, then performs the second clean producer execution in a
fresh store under the identical frozen literal source-pin set. Production is
one operational producer execution and fresh evaluation is one
same-implementation replay: these are the only two clean producer executions
used for exact comparison. No third campaign or independent algorithm is
required. This is not a generic cross-process final-wrapper parser.

The complete suite has passed every registered positive, ordering, identity,
semantic, store, authority, invalidation, process-isolation, attack and
deterministic fresh-store replay obligation in
`specs/H2_INTERLEAVED_DURABLE_EPOCH.md`; the status and principal IDs above
are therefore frozen.

The result artifact carries only the implemented closed claim fields:
`query_local_model_only=true`, `promotion_authorized=false`,
`policy_switch_claimed=false`, `learned_dynamics_claimed=false`,
`coordinate_invention_claimed=false`, `sample_efficiency_claimed=false`,
`workload_economics_claimed=false`, and
`official_execution_allowed=false`, plus its status. Generic reuse/H>2,
independent-verifier, savings, scalar and Gate statements below are
ledger-level locks; they are not additional result fields.

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

This Gate does not claim generic changed-model/query reuse, H>2, reusable-base
promotion, automatic coordinates, partial/learned dynamics, statistical
generalization, independent-algorithm verification, sample
reduction/efficiency, byte/CPU/wall/total-work superiority or economics. A
Laplace-style heuristic operator or KG-OP-style meta-prior remains a later,
separately preregistered sample-tax intervention informed by completed
closed-loop traces.

## Historical V0-056 preregistered durable H2 multi-query workload rule

Contract `1.20.0` freezes schema `1.0.0`, profile
`lmb_h2_preregistered_durable_multiquery_workload_v0`, and passing status
`CERTIFIED_REGISTERED_H2_PREREGISTERED_DURABLE_MULTIQUERY_WORKLOAD_CONTROL`.
The implementation Gate, 21 registered attack cases and fresh-store
evaluation replay pass, and the status is emitted. Principal canonical pins
are:

```text
campaign result = 8edf8a660fe3ceca19543aeb41d9c2683b540f15956abf0fe898f41aeb376122
evaluation      = 48e8919a089986892a2141f0b06edced07f0ae86a623d68b75817f6b33400ce7
protocol        = 928b8233021b2f961a485c57709e43dc1b368f167b46ecf7e15d9f5bf61f7787
proof semantics = 5880e0a9a4d70efe5bfc387c3faf81fe1587f8e56c0130f10dc49fbe8c28c224
preregistration = 2cde4f37b9e7cfd3f89d87c3f2a29811060f5a481accda6351c432a4da6761fb
W0/W1/W2        = 4e9deaec2baf... / 8d15aae30b49... / 8e33d23a1369...
matched vector  = f8fe8f4dd584...
reset-init vec  = 20339c4e312e...
```

Full W0/W1/W2 IDs, the semantic-projection digest and literal code/source
hashes are frozen in `specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md` and the
data-only `src/acfqp/h2_durable_multiquery_workload_pins_v1.py`.

Before the source starts, the protocol freezes the threshold-only family
`Q1=(epsilon_regret=0,delta=0)`, `Q2=(3/4,0)`,
`Q3=(0,1)` and the ten-occurrence order
`Q1,Q2,Q3,Q1,Q2,Q3,Q1,Q2,Q3,Q1`. Reward basis, horizon two, action
semantics, dynamics, initial distribution, fixture and candidate order remain
the exact V0-055 values. The V0-055 source API receives Q1 and its own frozen
inputs, but no target order, Q2/Q3, target control, target result or
target-dependent selection instruction.

The exact Q1 source must first reproduce C1 as `4 observed / 1 missing`,
select `N`, and fail certification at normalized regret `3/4`. Only after
that failed proof is verified may the owner-bound source acquire the single
missing `M` row. C2 is then `5/0`, selects `M`, and certifies exact
reward/failure/regret `1/0/0`. No target occurrence begins before C2, its
source-before-target order and its complete V0-055 authority chain are
verified and all source ground authority has been closed.

W0 is a semantic world-model/proof-state projection, not an ID-only memo.
It contains all 18 active C2 typed lower-node documents, their kinds, input
slices, identity terms, result fields, ordered parent-node IDs and exact
source bindings. The canonical concatenated projection is exactly `21983`
bytes with SHA-256
`b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55`.
Fresh model-only workers must parse and verify those documents and derive
their results without importing the matching-buffer kernel or V0-055 recovery
implementation. The digest is only an integrity/source pin; it cannot replace
semantic replay.

Persistent lower identities bind their formula, semantic address/action,
ordered parent-node IDs and only the facet that the formula consumes.
`REGRET_N/M` consume `return_upper` and normalized-regret tolerance;
`RISK_N/M` consume risk tolerance; `SELECTION` consumes no threshold
directly and instead binds its eight ordered result-node parents. It is an
error to bind selection to parent key IDs, to over-key unchanged lower nodes
on the full query, or to omit a consumed threshold. Occurrence identity is
excluded from reusable lower keys but remains mandatory in receipts, roots
and final occurrence artifacts.

Regret and risk are recomputed from the verified C2 semantic fields:

```text
regret(a) =
  max(0, (U0.reward_upper - PLAN_a.reward_lower) / return_upper)
REGRET_a.passes iff regret(a) <= epsilon_regret
RISK_a.failure_upper = PLAN_a.failure_upper
RISK_a.passes iff PLAN_a.failure_upper <= delta
```

Selection is then derived from the two regret, risk and coverage results.
It maximizes plan reward lower among certified actions; the registered
fallback/tie rules are used only when needed. Candidate audits, proposal,
two candidate roots, independent selected root and certificate must all be
derived from the resolved semantic fields and current occurrence identity.
A query-index/address answer table, hard-coded result, IDs-only projection or
fully re-hashed semantically false graph cannot authorize a result.

Lookup precedes the registered lower builder for every obligation. Q2/Q3
gate entries are resolved before the selection key is derived from their
result-node IDs. A hit performs zero builder calls and a miss exactly one;
monotone access records and host replay establish the order. This freezes the
following target-arm traces:

```text
global append-only arm:
  occurrence 1 Q1 = 0 builders / 18 hits
  first Q2      = 3 / 15
  first Q3      = 3 / 15
  later seven   = 0 / 18 each
  total         = 6 / 174 / 30 fresh roots
  W0/W1/W2 logical lower counts = 18/21/24

C2 base-reset arm:
  total         = 18 builders / 162 hits / 30 fresh roots
  typed W0 initializations retained = 10
  scoped initializer + worker-observed read/output I/O retained
  query_store_io_complete = false

both model-only arms:
  target ground/catalogue/policy-evaluation/optimizer calls = 0
```

The reset arm rebuilds W0 once per occurrence. Its ten typed initialization
records, initializer-observed projection/checkpoint read and W0 output bytes,
and worker-reported store bytes must be preserved in the reset operational
lane. Host before/after/final lease and snapshot reads plus verification
rereads remain incompletely instrumented, so
`query_store_io_complete=false`. The `18/162/30` tuple is only lower
builder/hit/root telemetry; it neither includes nor cancels reset
initialization I/O and cannot support a byte- or total-work-saving claim.

The matched direct arm starts every occurrence in a fresh process from the
same exact, source-independent four-row offline C1 semantic projection. It
cannot read C2, the source M row/receipt, a target facet store, or any earlier
direct result. Its source-pinned trusted literal comparator has an internal
dynamic recorder and a single-use exact `(x1,M)` guard. It completes that row,
constructs one catalogue, evaluates four policies and runs one optimizer per
occurrence, for totals `10 ground calls / 10 catalogues / 40 policy
evaluations / 10 optimizer calls`. This is a registered conditional-online
control, not hostile-worker security or a transferable owner-bound
capability. Every paired route must select `M` and reproduce
reward/failure/regret `1/0/0`.

The exact `6/174/30`, `18/162/30` and `10/10/40/10` values are
operation-family telemetry. They are not samples, native-compute-complete
WorkVectors, total work, byte/CPU/wall-clock rankings, a scalar cost or a
break-even result. The semantic projection is sufficient only for these
threshold-only Q1/Q2/Q3 variants because its source input-slice documents
remain opaque. Reward, horizon, action, dynamics, initial-support or
structural changes require a separately compiled semantic projection and
Gate.

Passing opens only finite source-before-target reuse of the actual C2
semantic state, exact consumed-facet changed-query derivation,
cross-process lookup-before-builder avoidance and the matched registered
direct control. Generic cross-query/H2+ reuse, H above two, statistical
generalization, coordinate invention, partial/learned dynamics, independent
algorithm verification, sample efficiency, economics and official execution
remain locked. The next construction Gate must connect a real query-local
model-epoch change to durable proof dependencies, exact invalidation,
replanning/recertification and reuse by later queries. The sample-tax
operator/meta-prior remains a later, separately preregistered intervention
informed by the deeper closed-loop traces, not the immediate next mainline
step.

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

Complete topology, formulas, process boundaries, acceptance values and attack
requirements are frozen in `specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md`.

## Historical V0-055 two-generation durable action-local H2 recovery rule

Contract `1.19.0` freezes schema `1.0.0`, profile
`lmb_h2_two_generation_durable_action_local_recovery_v0`, transport subprofile
`lmb_h2_durable_action_switch_transport_v0`, and success status
`CERTIFIED_REGISTERED_H2_TWO_GENERATION_DURABLE_ACTION_LOCAL_RECOVERY_CONTROL`.

The purpose of this rule is not proof-DAG construction for its own sake. It
composes durable proof state with the existing model-first local-recovery path
so that the registered multi-step failed proof, successor planning and final
certification are performed primarily in the reusable abstract world model,
while exactly one ground distinction is opened only after certification
failure has been verified.

Before ground evidence exists, C1 commits the exact first V0-054B `4/1`
model/query plus 18 canonical lower proof nodes and zero complete roots. Every
node is stored as a strict typed document and parsed/replayed against the exact
model/query on load; an opaque, self-consistent or differently typed payload
cannot substitute for the registered graph. The store has no mutable `HEAD`
and is selected by an external commit ID.

Fresh model-only P1 consumes C1, operationally loads/reuses all 18 lower nodes
without recomputing a lower node, builds three complete roots fresh and
reproduces the failed `A0A0/N` proof. The host must exact-verify that result
before freezing a distinct V0-055 ground authorization bound to C1, P1, the
target row and source hashes. C1 bytes, P1 output and the original V0-054B
request do not by themselves embed or mint that authorization.

Only then may the exact source-pinned V0-054B runner execute. Its live
owner-bound `(x1,M)` transition is the sole operational ground call. The
resulting immutable overlay projection binds the exact row, predecessor,
source result, evidence bundle and overlay build as detached provenance, but
transported bytes never become a reusable ground capability.

Fresh model-only P2 verifies C1 and the overlay, operationally restores/reuses
the first 18 lower nodes, then performs the exact final continuation as ten
lower recomputations, eight lower reuses and three fresh roots. Its row delta,
pre-execution invalidation, complete execution and selected certificate must
equal the owner-bound V0-054B source. Thus the strict reward-0 failed
`A0A0/N` plan changes to the reward-1, risk/regret-zero certified `A0A1/M`
plan.

C2 is another immutable root-free checkpoint. It stores the canonical
28-lower-node union with exactly 18 active final nodes and ten historical
first-only nodes. It may not persist final roots or an opaque P2 continuation
as substitutes for typed lower proof. Fresh model-only P3 loads/reuses the 18
active nodes, recomputes zero lower nodes, creates three roots fresh and
reproduces the final certificate.

The operational trace contains exactly three fresh model-only launches, one
source-owned ground transition, zero pre-ground transitions and zero worker
ground transitions. The 18 semantic validation obligations used to establish
that C1 or C2 represents the exact graph are not labelled as 18 native
physical computations. Complete CounterRegistry/native-compute accounting is
not claimed.

The verifier rebuilds the whole chain in a separate evaluation store and
requires exact result equality and unchanged original C1/overlay/C2 bytes.
Its one ground call and three launches are evaluation-lane work. This is
same-implementation deterministic replay, not an independently implemented
proof algorithm.

Passing sets only the registered two-generation/root-free/model-only
continuation/strict-switch claims. Generic durable or crash-safe persistence,
hostile-worker security, cross-query reuse, generic `H>1`, horizons above two,
generic action-local minimality, automatic coordinate invention,
partial/learned dynamics, sample efficiency, byte/CPU/wall-clock/total-work
savings, native-compute completeness and independent-algorithm verification
remain false. Official execution stays false, official scalar and break-even
stay null, and workload-economics, counter-completeness and sample-efficiency
Gates remain `NOT_RUN`.

V0-056 now consumes this historical control as the source for a
preregistered matched multi-occurrence/multi-query workload with strict
base-reset and direct controls. Only measured workload traces may justify a
later Laplace-style heuristic operator or KG-OP-style meta-prior sample-tax
intervention.
Canonical identities and mandatory attacks are frozen in
`specs/H2_DURABLE_ACTION_LOCAL_RECOVERY.md`.

## V0-054B one-row action-local H2 semantic-switch rule

Contract `1.18.0` freezes schema `1.0.0`, profile
`lmb_h2_action_local_semantic_switch_v0`, model-only proof subprofile
`lmb_h2_action_indexed_semantic_switch_v0`, and success status
`CERTIFIED_REGISTERED_H2_ACTION_LOCAL_SEMANTIC_SWITCH_CONTROL`.

The control uses the literal six-tile LMB instance generated by the canonical
generator at seed 4, while production instantiates the literal rather than
depending on the generator. Its initial state is mask 32, buffer `(0,1)`,
remaining horizon 2. At stage zero only `S=tile4` is legal and it reaches the
downstream state mask 48, buffer `(0,2)`. The trusted complete downstream
catalogue contains `M=tile0` and `N={tile1,tile2,tile3}`.

The first query-local model is built with no transition call. It contains the
registered exact `S` and three `N` rows and marks only `M` missing. Model-only
planning selects `A0A0/N`, with reward/risk `0/0`; the unrestricted H2 reward
upper is 3, so normalized regret is `3/4` and certification fails. The
selected-policy support frontier contains only `S+3N`, explicitly excludes
`M`, and is non-authorizing.

The unrestricted-challenger frontier follows the failed `REGRET_N` circuit
through `U0`, `U1`, `Q_M`, and `ROW_M`. It is diagnostic and non-authorizing.
A separate exact-one-row necessity proof and content-addressed request bind
the target state, action, row, query, first model and proof circuit. The
transition capability is owner-bound, non-copyable and single-use. During the
registered run a process-local, non-reentrant step gate source-pins both the
canonical LMB step and its own execution entry, rejects every LMB transition
before request activation, every non-target call, and every second call. Its
guard closes directly over the canonical step. Receipt, protocol trace and
result are live-owner-bound, so constructing golden receipt bytes without the
monitored call cannot mint a passing result.

The single exact call observes deterministic reward 1, risk 0 for `M`. The
successor model is immutable/query-local/non-promotable, preserves all four
base rows exactly and appends only `M`, changing coverage from `4/1` to `5/0`.

The proof subprofile contains exactly 18 lower nodes and three fresh,
noncacheable roots per epoch. Before final replanning, production derives the
one-row model delta and complete 14-edge reverse closure from the live first
execution, then binds that pre-execution invalidation authority to the live
runtime. A missing, copied, incomplete or stale closure cannot authorize the
final epoch. The exact work is:

```text
first: 18 lower computes / 0 hits + 3 roots
final: 10 lower computes / 8 hits + 3 roots
```

The ten affected addresses are:

```text
ROW_M,Q_M,U1,U0,PLAN_M,REGRET_N,REGRET_M,
RISK_M,COVERAGE_M,SELECTION
```

The eight unaffected addresses are:

```text
ROW_S,ROW_N1,ROW_N2,ROW_N3,Q_N,PLAN_N,RISK_N,COVERAGE_N
```

All candidate audits, roots, proposals, selection values and ordered lower
node IDs are cross-bound. In addition, a pure model-only semantic replay
rebuilds all 18 lower nodes, both audits, both candidate roots, the proposal
and selected root from the exact model/query and requires document equality.
A copied or fully re-signed but semantically false graph cannot pass. Final
replanning selects `A0A1/M`, reward/risk/regret
`1/0/0`, and certifies. The `0 -> 1` reachable value improvement proves a
strict semantic switch rather than a tie-break-only label change.

Passing sets only the registered one-row/frontier/invalidation/strict-switch
claims. Generic action-local minimality, generic `H>1`, durable/cross-query
reuse, automatic coordinate invention, partial/learned dynamics, sample
efficiency, byte/CPU/wall-clock/total-work savings and official execution
remain false. `official_scalar_cost` and `official_N_break_even` remain null;
the economics and counter Gates remain `NOT_RUN`. The verifier performs fresh
same-implementation deterministic replay and does not claim a separately
implemented proof algorithm.

V0-055 now composes this semantic switch with two root-free durable
lower-proof generations. Sample-tax mitigation remains a measured downstream
design problem rather than a retroactive V0-054B claim. Canonical V0-054B
fixture identities and mandatory attacks remain frozen in
`specs/H2_ACTION_LOCAL_SEMANTIC_SWITCH.md`.

## Historical V0-054A same-query durable H2 proof-state rule

Contract `1.17.0` freezes schema `1.0.0`, profile
`lmb_h2_same_query_durable_proof_state_v0`, and success status
`CERTIFIED_REGISTERED_H2_SAME_QUERY_DURABLE_PROOF_STATE_CONTROL`.

The source is the exact owner-bound V0-053 result. Its final model, thresholds,
build/rebase, evidence request/bundle, four Gray candidate requests and inner
audits, proposal, selected plan/request/receipt/inner and wrapper audits, final
execution, proof semantics and source implementation digests are all frozen.
A copied or merely hash-matching source is not sufficient.

The producer reconstructs exactly 30 lower H2 entries in topological order and
persists no `R`. It writes canonical payload and manifest blobs before the
single commit. There is no mutable `HEAD`; consumers require an externally
supplied expected commit ID. The loader proves present-state completeness and
linkage, not historical filesystem immutability or write ordering. A
content-addressed snapshot must remain byte-identical across both occurrences.

Each fresh worker strictly loads the model and executes a four-candidate
semantic replay of 44 resolutions (`34/10`). The recomputed candidate audits
and complete lower payload must match the frozen manifest/payload before a
verified lease exists. This semantic replay rejects fully re-signed hidden
values and wrong parent graphs.

Two separately launched `python -I -s -B` workers each run three five-request
arms:

```text
REQUEST_RESET                         55 /  0 per occurrence
OCCURRENCE_RESET_GLOBAL_DAG           35 / 20 per occurrence
DURABLE_CROSS_PROCESS_CONTINUATION     5 / 50 per occurrence
```

The two-occurrence totals are `110/0`, `70/40`, and `10/100`. All durable lower
resolutions hit; every occurrence-/role-/proposal-bound `R` is recomputed.
Both select semantic `A0A0`. The process imports the ground module to install a
fail-closed guard but receives no target kernel instance and performs zero
transition, catalogue or ground-optimizer calls.

Worker documents are untrusted. The host replays the entire occurrence against
its own verified lease and requires exact equality before minting the result.
Host telemetry retains `34/10` checkpoint semantic replay plus `190/140` proof
work for validating the two worker outputs. Therefore `70-10=60` denotes only
worker-local avoided lower constructions; it is not net work, samples, bytes,
CPU or wall time.

The evaluation verifier strictly checks the original raw store, reruns the
private producer core into a fresh store with two fresh processes, requires
exact campaign equality, then checks the original snapshot again. This is
same-implementation deterministic evaluation replay, not a separate proof
algorithm or independent codebase. Occurrence artifacts carry resolution
documents and audit/root commitments; audit payloads are recomputed rather than
accepted as expected answers.

Passing sets only:

```text
registered_h2_same_query_durable_proof_state_claimed = true
```

Generic persistence, complete-certificate or `R` persistence, cross-query,
changed threshold/reward/model reuse, generic `H>1`, semantic policy change,
sample reduction/efficiency, total-work/economics, learned/partial dynamics,
coordinate invention and official execution remain false. Scalar cost and
break-even remain null; workload-economics, counter-completeness and
sample-efficiency Gates remain `NOT_RUN`. Complete source identities, canonical
V0-054A IDs and attack obligations are frozen in
`specs/H2_DURABLE_PROOF_STATE.md`.

V0-054B now separately supplies the six-tile seed-4 strict reachable
`A0A0 -> A0A1` switch. It does not overwrite or broaden V0-054A.

## Historical V0-053 live H2 query-local epoch-invalidation rule

Contract `1.16.0` freezes schema `1.0.0`, profile
`lmb_h2_live_query_local_epoch_invalidation_v0`, and success status
`CERTIFIED_REGISTERED_H2_LIVE_QUERY_LOCAL_EPOCH_INVALIDATION_CONTROL`. This is the
first Gate that interleaves the temporal proof DAG with the authentic V0-047
first-to-final model evolution. It is not satisfied by reading an already completed
V0-047 result and reconstructing a cache trace after the fact.

The live production runner accepts exactly the eight V0-047 upstream authorities, in
this order of meaning:

```text
observation_log
semantics_profile
observation_authority
observed_synthesis_result
thresholds
base_plan_proposal
failed_audit
kernel
```

It accepts no completed V0-047 result, first/final model, row or state list, plan,
closure, cache, control arm, expected outcome, legacy audit, ground optimizer or
promotion choice. The runner must execute the following monotonic authority order:

```text
verify the complete base failure chain
-> execute round one and evidence-derived boundary registration
-> freeze the first immutable V3 epoch
-> build four candidate DAG roots and the DAG-derived proposal
-> freeze a role-distinct independent selected failed root
-> derive and freeze the round-two request from that root/frontier
-> execute only its nine authorized ground rows
-> freeze the final immutable V3 successor epoch
-> derive the exact epoch delta and affected-descendant closure
-> rebuild the final four candidate roots and proposal
-> freeze the final independent selected certificate
```

No round-two transition may precede the first selected root. Production constructs
the stage-local roots directly; whole-horizon V0-043 replay is reserved for the
independent verifier. A consumer of an already completed V0-047 result may at most
emit a separately labelled post-hoc artifact-replay control and cannot return the
V0-053 success status or positive claim.

The first checkpoint remains exactly the V0-047 `11 observed / 9 missing` V3 model
`e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba`, with proposal
`b5db44c042eaa656980f942430c2fee6eda6fcf6ec8c0a1af1142b723ec006e4` and an
independently keyed selected `FAILED_PROOF_FRONTIER` at `time=1,h=1`, reason
`UNRESOLVED_POLICY_PATH_DISTINCTION`. The round-two request remains
`dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf`: it contains
exactly nine distinct rows with retained native roles `3 selected-plan risk / 9
unrestricted value / 9 distinct`. Its operational execution performs exactly nine
kernel steps and their nine step-internal legality checks, zero direct boundary
catalogue calls, zero extra-row access, zero search and zero ground optimization.
Step-internal legality checks are included in transition work and are not charged a
second time. The complete logical occurrence still reports the earlier four round-one
steps and three direct boundary catalogue calls separately.

The final immutable V3 is
`a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315`, has
`overlay_version=2`, binds the first model as `previous_model_id`, and changes coverage
to `20 observed / 0 missing`. The first V3 and reusable base remain byte-identical.
The exact delta is derived from the two model documents and must equal precisely the
nine requested/evidenced rows changing from `MISSING_VACUOUS` to
`OBSERVED_SINGLETON`. State/action catalogues, cells, semantic actions, concretizers,
query, thresholds, reward, horizon and every non-delta row remain unchanged. A
caller-supplied delta, same-ID/different-byte object, wrong predecessor, omitted or
extra row, or bundle/request substitution fails closed.

Every epoch executes the unchanged five-request workload: four Gray candidate roots
`A0A0,A0A1,A1A1,A1A0`, followed by a proposal-bound independent selected root. The
eleven-slot graph remains:

```text
U1 -> U0
P1 -> P0
C0 -> C1
D  <- U0,P0,C0,C1
E,F <- D
G  <- C0,C1
R  <- all ten lower nodes
```

V0-052's full-model identity cannot simply be copied into every lower cross-epoch
key. Each lower key binds an allowlisted, content-addressed extensional stage facet
and exact ordered parents; each `R` still binds the complete current model epoch,
plan, query, thresholds, request, role and selected proposal. Although acquired from
the time-one frontier, these are stationary model rows: `U1` and `U0` both scan them,
while `P1` and `P0` both directly consume the changed coord-3 realizations. The direct
consumed-facet changes are therefore `U1`, `U0`, `P1`, `P0` and `C1`; `D`, `E`, `F`,
`G` and `R` are rebuilt as affected descendants. Only `C0` is unchanged. Numeric
equality of a result or verdict never permits reuse of an invalidated node.

All three controls resolve ten requests and 110 logical slots:

```text
REQUEST_RESET                 110 computes /  0 hits
EPOCH_RESET_GLOBAL_DAG         70 computes / 40 hits
GLOBAL_CROSS_EPOCH_FACET_DAG   68 computes / 42 hits
```

The continuous arm's cumulative compute/hit prefixes are:

```text
computes: 11,19,27,34,35,45,53,60,67,68
hits:      0, 3, 6,10,20,21,24,28,32,42
```

At the final epoch all five `C0` resolutions hit the two distinct `A0`/`A1` entries
constructed in the first epoch. Consequently `70-68=2`, not five, is the exact count
of avoided cross-epoch constructions. Every proof-control arm consumes the same
frozen evidence transaction and performs no additional operational sampling.
Independent replay ground work is evaluation-only. These counts are neither sample
reduction nor total-work, byte, wall-clock or economics evidence.

Both epochs replan from the four candidate roots using the unchanged
numeric-then-semantic rule. Both select the same semantic Gray schedule `A0A0`, whose
key is `(0,1,0,1,0,1,0,1)`. Model-bound plan, proposal and root IDs must change across
epochs, but that re-binding is not a semantic action/policy change. A test that checks
only unequal plan IDs is noninformative and cannot pass. All ten `R` roots must be
byte-identical to the corresponding unchanged V0-043 audits; candidate roots never
authorize selected roots. The first selected root fails, while the final selected
root is `CERTIFIED_FIXED_PLAN` with reward interval `1/1`, failure interval `0/0`,
normalized regret zero and certified external coverage.

The nine-input independent verifier adds only the claimed result to the eight
production authorities. It reconstructs the full 13-transition/three-catalogue
V0-047 source chain, both epochs, exact delta and closure, all ten legacy matches,
all three controls and every append-only cache pre/post state from a canonical empty
cache, then requires byte-identical documents. Mandatory failures include evidence
before the first root, post-hoc-as-live substitution, missing/extra rows, final
evidence leaking into the first DAG, stale `U1/U0/P1/P0/C1` or descendants, a
full-model-ID `C0` false miss, under-keyed false hit, relevant-row mutation with a hit, edge/order/
cycle attacks, prewarm/import/overwrite/rollback/owner-copy, candidate-as-selected,
operational/evaluation work mixing, and mutation of the V0-047/V0-052 pinned sources.

The source goldens above, final audit
`81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529`, and complete
V0-047 result `9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42`
remain fixed. The source-order protocol, epoch delta, invalidation manifest,
cross-epoch cache, execution and result each require distinct domain-separated
canonical IDs. The deterministic V0-053 replay freezes:

```text
semantics ID = 17a7fb36b05d6dcf9ed319cae706a5a5b0fd496359b66348cc444ea16955f264
ordering ID = e7e0a08ecf6cf5ef04fd990f73065955e6d4412aec5fb474aff1e4660f391da2
delta ID = 40e6447cfff4526e4b17f4e381bf8067f6dec946a1d3e655a3380c780de053fa
invalidation ID = a9657e12ebd46cee061263205d103ff4b82dfd557b3923a843ef00c1b841668c
request-reset arm ID = e91726ac2b17bf42b2890bf456118de04ec9c09bfd07d29830e2239e558340d6
epoch-reset arm ID = a51f8e3682aac5d932bb68cfd54193be7bd19f1b302865a2f8ca467438cc69d9
cross-epoch arm ID = 5e8c2d23cfcf96c9d810fac1af3069b83eea2caa1a191c6b02e546a29bf21b56
first-epoch execution ID = 4818bcaa0a2217bb720b02879869062e58efb4dd0e05a5555c57c0e22ff81572
final-epoch execution ID = 3cbe43d106be12824e8d15a27a8fc0e82d37cf37a8c772a191eacd2b5fb77279
final cross-epoch cache ID = 270b5b126953dfbe9ab1e33e3f99505f5e0b95f8a5929b1f581b78165706185f
result ID = 5e46f0eda3f6d9c96e955315034829913dc248d09ed1a73ca8384d4cbcd65d44
```

Every role uses its own registered content domain and schema; cross-role ID reuse is
invalid. No placeholder, empty or `TO_BE_FROZEN` value can pass independent replay.
Canonical IDs prove byte identity and binding, never live ordering, delta correctness,
proof soundness or semantic certification by themselves.

Passing permits exactly the registered-scope positive claim:

```text
registered_h2_live_query_local_epoch_invalidation_claimed = true
```

Generic changed-model or H>2 incremental proof, semantic policy change, cross-query
reuse, persistent cache, sample reduction/efficiency, total-work/wall-clock,
economics, learned/partial dynamics, coordinate invention and official execution
remain false, null or `NOT_RUN`. This is a live correctness Gate on one canonical H2
query-local evolution, not a performance or generality Gate.

The next construction Gate must move beyond this broad nine-row future-stage update.
It should preregister a repeated H2 occurrence family with durable epoch/proof state
and at least one action-local sparse delta that causes a genuine semantic policy
change, while retaining matched no-reuse/cold-direct traces. Only after those traces
identify acquisition or proof work as the actual sample-tax bottleneck may a
Laplace-style heuristic operator or KG-OP-style offline/online meta-prior enter the
mainline.

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


## V0-072 anchored-attempt-1 protocol failure and one-time repair

The first final V0-072 identity chain was anchored at remote-main commit
`b711cc52001419cfb0962e2a94af91cc03c5ffc2`. Its source recipe, manifest,
final preregistration and remote-main anchor IDs were respectively
`d836f0b0c7f3b302541ce81dc5372c077d336add5f28a973ebd6ae611ccbd8b9`,
`acbec3e259e9df0e5b56c172ae2261f6d072f29b3a669b1eaafbcbdcae28b1c6`,
`b6a543a0e30214338214bf025bbf543994f6afc3251608f522d11f5c20e236f2`
and
`157f6c512b912d4e100e76a30fdb4ae43c051cef6ac073778a303dd523e6d88e`.
The authority-only replay passed with zero source reconstruction and zero
target access.

The subsequent registered campaign attempt completed its source
reconstruction, began target execution, and reached the first K7
`MATCHED_DIRECT_GROUND` 2,048-validation checkpoint. It then failed closed
with `KeyError(MATCHED_DIRECT_CHECKPOINT)` in
`v072_cold_h2_closure_independent_verifier_v1._work_payload`: production
native work already supported this registered purpose, but the independent
verifier's purpose-to-draw-schedule mapping omitted it. No campaign result,
typed campaign terminal or scientific endpoint was written. The canonical
historical record is
`specs/V072_ANCHORED_ATTEMPT_1_FAILURE.json`, ID
`ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f`.

This attempt is `PROTOCOL_FAILURE / INCOMPLETE_CAMPAIGN_ARTIFACT`, not a plan
or infeasibility result. Its denominator remains 15. Because no durable
partial ledger existed, its exact completed-occurrence count, target draws,
native work and wall time are `UNKNOWN_NOT_DURABLY_PERSISTED` and must never
be interpreted as zero. The old attempt may not be resumed at occurrence
five, omitted from future accounting, or combined with a replacement
attempt.

One replacement attempt is authorized solely as a protocol repair. The
allowed changes are:

1. exhaustively replay every registered matched-direct checkpoint purpose;
2. fail closed on unexpected selector-terminal and route-kind enum values;
3. persist atomic, non-overwriting attempt progress and failure records.

No context, law, seed semantics, arm, schedule, threshold, confidence
allocation, cap, endpoint or scientific comparison may change. The old
target tape, observations, occurrence identities and work may not be reused.
The replacement is attempt ordinal 2 and is bound to predecessor failure
record
`ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f`.
Its new authority chain and execution plan own exactly one fresh-only attempt
slot. The only authorized output transport is
`artifacts/v072_registered_campaign_result_v1.json`; changing the output path
must not create another attempt identity or permit another target execution.
No random nonce, resume, retry, journal-derived seed, or journal evidence
reuse is allowed.
The repair must pass the exact fresh-ID Gate, freeze a new source recipe,
manifest and final preregistration, obtain a new remote-main anchor, and
restart all 15 occurrences from the beginning. The old authority remains
historical failed-attempt provenance.

Until a complete replacement result and its independent endpoint replay
exist, all locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-072 anchored-attempt-2 failure and exhausted chain

The one authorized replacement was anchored at remote-main commit
`63cc0f5f78f64b7845319d1c1a5856212e3b8097`.  Its source recipe, manifest,
final preregistration, anchor claim, anchor and independent attestation IDs
are respectively:

```text
7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1
2af044753017e6aeb1295408db23a2f8e923fbd7acdd207029e21371e7f09865
966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26
022ced158d19aea8293a8c8c75e70aa93f93e1913380a76ad11f729f54057076
1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474
408e76d3350bc4fc7a6e2a625d7a42b7949672e98615d51870b156aafc8924c0
```

The exact fresh-ID Gate passed before execution.  Attempt
`a925bb7104727ccce81b4da5361fab9610638f5e6a35e46177faa3dfced4174a`
then reconstructed the source authority and durably completed four of the
15 registered occurrences.  In the fifth occurrence, K7
`MATCHED_DIRECT_GROUND` reached route-native `CERTIFIED` at checkpoint
`16384`.  The standalone exact evaluator subsequently failed closed because
it required the fixed-κ policy to contain actions for every exact reachable
child, including children represented operationally by the frozen row
`OTHER` escape.

The attempt closed as:

```text
ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE
completed_occurrences = 4 / 15
campaign_result_written = false
scientific_endpoint_read_allowed = false
```

Its hash chain contains 16 events and 21 referenced objects and verifies
against an externally supplied identity.  The canonical tracked record is
`specs/V072_ANCHORED_ATTEMPT_2_FAILURE.json`, ID
`cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e`.
Unknown work after the last durable boundary is explicitly not zero.

The V0-072 authority chain is exhausted.  It has no resume, reuse, retry or
third-attempt authority.  Durable K7 prefix records are diagnostic regression
evidence only and cannot be read as a sample-efficiency endpoint or used to
make K7 held out again.

Proposed V0-074 contract `1.39.0` repairs the implementation under the
already-frozen `ABSORBING_POLICY_ABORT_FAILURE` semantics.  A modeled selected
child still requires its bound decision; an exact child outside frozen
modeled support is charged exactly once as failure one with zero continuation
reward.  The same revision freezes a pre-target source proposal archive and
occurrence-level process isolation/canonical merge.  Those changes are
construction and wall-clock mechanics only.  A scientific rerun requires
new preregistration, manifest and anchor plus fresh target identities, tapes
and genuinely fresh held-out occurrences.  The checked-in archive/parallel
worker registry is synthetic transport only; production proposal/campaign
integration and operational-envelope containment remain `NOT_RUN`.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-110B-2E-16..22 complete K7 occurrence-accounting chain

Contracts `2.0.26`--`2.0.32` freeze one non-retroactive successor chain over
the genuine production K7 occurrence:

1. complete all eight derived reconciliation proofs using the semantically
   bound route result `1/0/1`;
2. prove all 114 profile-native zeros from closed owner/source obligations;
3. resolve the exact `9 + 71 + 114 + 8 = 202` V6 path partition;
4. atomically materialize 202 CounterRecords, one failed-prefix WorkVector,
   the 182-term V6 projection proof and eight-axis ComparisonVector;
5. derive the root-cap attempt terminal as
   `ATTEMPT_CLOSURE_NONCERTIFICATE.ATTEMPT_BUDGET_EXHAUSTED`; and
6. independently reconstruct that complete bundle in the evaluation lane
   without invoking the production materializer or terminal producer; and
7. retain the unchanged complete work and close the non-retryable logical
   occurrence in every denominator with certificate coverage false.

Missing events are never interpreted as zero. Status strings, ID-only
artifacts, hash-only integrity, worker budget claims and cap exhaustion cannot
mint semantic evidence, infeasibility or a certificate. Operational and
evaluation work remain separate. The terminal authority closes one route
attempt; the successor occurrence authority closes only this registered
non-retryable occurrence, not a campaign. Therefore these contracts do not yet
establish all-path campaign Counter Completeness and do not unlock official
execution, scalar/break-even economics, fresh science or sample efficiency.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-110B-2E-23 all-path profile and durable exact infeasibility

Contracts `2.0.33`--`2.0.34` freeze two prerequisites for the remaining
all-path campaign accounting:

1. an exhaustive profile over the ten FQ9 terminal codes, five route kinds,
   ten stages and seven accounting families, together with an AST-replayed
   inventory of all 47 current V075 terminal/status enum classes and 164
   members; and
2. a self-contained exact-infeasibility proof for the unchanged canonical
   G2048 regression, independently reconstructed as 46 states, 16
   state-action rows, 96 positive outcomes and 256 deterministic H1 policies,
   with minimum failure probability `383/410 > 1/20`.

The source inventory has no default mapping: 22 members map to FQ9, 128 are
explicitly nonterminal and 14 remain typed `PROFILE_EXTENSION_REQUIRED`
blockers. The durable proof separates `IDENTICAL_MATCH`, `NO_MATCH` and
`INVALID`; a cap, status string or opaque live search seal cannot mint
infeasibility. Neither contract supplies the still-missing route executions,
formal vectors, operation-boundary instrumentation or campaign aggregation.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-110B-2E-24 integrity-failure accounting

Contract `2.0.35` replaces the generic `WORK_VECTOR=INVALID` shortcut with a
non-retroactive integrity-failure authority. It proves an externally anchored
expected-artifact identity differs from the actual canonical bytes, retains
all work through the detection cutoff, materializes all 202 observed V6
CounterRecords and derives a valid WorkVector and eight-axis ComparisonVector.
Read and hash work are charged once; diagnostic hashed volume is retained but
not double charged.

The exact terminal is
`ROUTE_ATTEMPT / ATTEMPT_CLOSURE_NONCERTIFICATE / INTEGRITY_FAILURE`.
Protocol sequence, route-family, counter and reconciliation violations cannot
be relabelled as integrity failures. The independent verifier reconstructs the
identity violation and complete accounting from bytes without invoking the
producer. This closes one attempt path, not logical-occurrence/campaign
coverage or all-path Counter Completeness.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-110B-2E-25 all-path operation-boundary manifest

Contract `2.0.36` binds ten existing production call sites across the six
PREOPEN/common, ABSTRACT, LOCAL, FALLBACK, REBUILD and
VERIFICATION/terminal families. Complete source bytes, symbol and call ASTs,
locations, cardinalities, stages, route/terminal applicability and
counter/evidence families are content-addressed and independently replayed.
Any source or manifest change yields a typed blocker.

The manifest is intentionally non-executing: it emits no event, zero,
CounterRecord, WorkVector, ComparisonVector or terminal. It closes the exact
hook-placement prerequisite only; the route-native instrumentation and all
formal campaign paths remain open.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-110B-2E-26 protocol-failure accounting negative control

Contract `2.0.37` uses the production FQ13 access profile and semantic replay
to reject a canonical pre-freeze `KERNEL_STEP`. It retains all 202 observed
records and the valid failed-prefix WorkVector/eight-axis projection, then
derives exactly
`ROUTE_ATTEMPT / ATTEMPT_CLOSURE_NONCERTIFICATE / PROTOCOL_FAILURE`.
The rejected access is not charged as a kernel call.

The registered production runner currently has no such violation. A typed
`NO_PRODUCTION_PREDECISION_VIOLATION_OBSERVED` blocker and
`production_violation_claimed=false` prevent this negative control from being
used as production evidence. Thus the protocol-failure state machine and
accounting are regression-closed, while genuine all-path production coverage
remains open.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-110B-2E-27..28 abstract and exact-fallback readiness blockers

Contracts `2.0.38`--`2.0.39` replace two possible false promotions with exact
source- and identity-bound blocker artifacts.

For the live model-only H1 PASS, all 202 required V6 paths partition as
`160` without a V1 leaf/hook, `15` with positive V1 records but no V6
occurrence/stage/cutoff evidence, and `27` with V1 zeros but no V6 native-zero
proof. Nine shared receipts and eight derived proofs are also absent.

For the canonical exact-infeasible H1 query, direct fallback genuinely returns
`INFEASIBLE_CERTIFIED` with the same query identity as the durable proof, but
retains only a 42-leaf V1 WorkVector. It lacks the formal 202-record/shared
receipt/route decision/materializer/verifier/terminal/occurrence chain. The
durable proof remains evaluation-only and cannot replace operational work.

Both artifacts are centrally domain-separated and independently replayable,
but issue zero formal vectors or terminals. They freeze the next concrete
instrumentation work; they do not close either route.

All locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## V0-110B-2E-29 conditional terminal normalization

Contract `2.0.40` replaces the 14 unresolved V075 status interpretations with
one exact source-bound conditional profile. Two successful-total-lift rows
require route provenance; seven risk/regret/statistical/no-frontier,
policy-abort or construction-control rows remain route-continuation
nonterminals; two process failures require retained process and protocol
evidence; two timeouts require preregistered cap plus trusted replay before a
cap code can be selected; and the generic noncertificate requires typed cause
evidence.

The profile selects only a candidate FQ9 target. It never creates a live
terminal, certificate, vector or occurrence closure, and unknown/new members
receive no default. Independent replay binds all 14 source rows and five
centrally registered role-separated domains. All official, Counter
Completeness, economics, scalar/break-even, sample-efficiency and scientific
Gates remain locked or `NOT_RUN`.

## V0-110B-2E-30 ABSTRACT_CERTIFIED zero-value closure

Contract `2.0.41` consumes the exact Contract-2.0.38 live PASS blocker and
closes only values supported by its retained process, event and source window.
Twenty-three inactive LOCAL/FALLBACK/REBUILD paths receive forbidden-route-stage
native-zero value proofs, not the formal profile-native-zero authority. The
zero-valued process, route and solver failure rows receive three
separately typed derived-complement value proofs; those are not native-zero
attestations and do not complete the eight-path derived reconciliation.

The unmeasured `io.mounted_bytes_peak` zero is rejected. The revised exact
partition is `23 native zero + 3 derived value + 176 residual gaps = 202`;
the residuals are `100` required-stage owner gaps, `60` optional-stage
reachability/transitive-source gaps, `15` positive V1 records without V6
occurrence/stage/cutoff binding, and one mounted-peak gap. No V1 record is
relabelled as V6 and no missing event becomes zero.

Five central domains separate the execution window, zero-value proof,
residual gap, closure and replay roles. The contract issues no V6
CounterRecord, vector, terminal, certificate or occurrence closure. Nine
shared receipts, all formal derived reconciliations and every official,
Counter Completeness, economics, scalar/break-even, sample-efficiency and
scientific Gate remain locked or `NOT_RUN`.

## V0-110B-2E-31 canonical exact-infeasible fallback raw acquisition

Contract `2.0.42` binds the canonical G2048 H1 exact-infeasibility proof to an
issuer-owned current identity reconstructed separately from the claimant using
the current source, live kernel/query law and explicit build, threshold,
reward, policy-class and complete-search identities. The marginal fallback
decision freezes before ground access; claimant self-match, stale identity and
solver/kernel substitution fail closed.

The historical raw in-process solver retains seven native-operation values and
six route/solver reconciliation values. They remain V1 source candidates. The
exact V6 partition is `178 stage-zero candidates + 7 legacy native values + 6
legacy reconciliation values + 9 missing shared receipts + 2 missing process
proofs = 202 formally blocked paths`. Stage-forbidden does not prove native
zero, and null trusted provenance plus the missing occurrence stages prevent
production use. Cap exhaustion remains noncertificate.

Seven content domains are central and role-separated. Production V6 recorders,
CounterRecords, vectors, terminal/occurrence authority and all Gates remain
absent or locked.

## V0-110B-2E-32 abstract PASS retained-V1 evidence inventory

Contract `2.0.43` inventories only what the real historical model-only PASS
retained: eight shared aggregate claims, one unmeasured mounted-payload result,
two owner-event candidates and eight internal reconciliation claims. None has
the prospective V6 stage/window/cutoff or dependency authority required for
formal accounting.

Independent replay proves the pairwise-disjoint blocker partition `160 no V1
event + 23 value-only proofs + 8 shared aggregates + 1 unmeasured mounted peak
+ 2 owner candidates + 8 reconciliation claims = 202`. No V1 row is promoted,
no missing event becomes zero and no vector, terminal or certificate is
issued. Seven content domains are central and role-separated; all official,
Counter Completeness, economics, scalar/break-even, sample-efficiency and
scientific Gates remain locked or `NOT_RUN`.

## V0-110B-2E-34 production-owned DIRECT_FALLBACK primitives

Contract `2.0.45` replaces the additive construction shim with seven literal
unit-event sites in an independent real fallback implementation. One exact
V3 source/runtime manifest binds the complete owner source, method and call
ASTs, class/method/gateway/validator identities, one ledger instance and one
frozen search invocation. Every event must be durably acknowledged before its
native counter changes; search finish and segment completion independently
reconcile the ledger and immutable event chain.

The canonical H1 exact-infeasible route yields
`states/actions/steps/outcomes/backups/checks/rejections =
8/16/16/96/16/56/0`, exactly 208 positive events, and exact parity with the
historical ground search. Direct ledger driving, readable private bind/finish
issuers, transient gateway or search-authorizer replacement, and live-code
replacement fail closed. This remains a Python construction control and does
not issue shared receipts, formal V6 accounting, a semantic terminal or an
occurrence closure. All official, scalar/break-even, Counter Completeness,
economics and sample-efficiency states remain locked or `NOT_RUN`.

## V0-110B-2E-35 V6 finite direct-fallback admission candidate

Contract `2.0.46` requires durable-proof/current-identity replay to reissue the
canonical H1 pre-execution source and exact typed access-log replay before any
candidate decision. It freezes the exact operational partition
`166 stage zeros + 7 typed owner cardinalities + 9 finite shared admission
caps = 182` and requires exactly the eight official comparison axes.

Because the current runner does not enforce all nine shared caps at their
owners, this object is only a `FINITE_ADMISSION_CAP_CANDIDATE`:
formal actual-compliance, route-selection authority and execution permission
are false. It creates no CounterRecord, vector, terminal, occurrence or Gate
result. Caller actual hints, V1 upper relabelling, stale access logs and
self-consistent but non-authoritative source objects are rejected.

## V0-110B-2E-37 exact nine-path successor-source schema

Contract `2.0.48` freezes one exact successor owner-site definition for each
of the nine shared-resource paths, including its V6 reducer/unit, intended
admission primitive, downstream side-effect boundary, ordered local protocol
and the cross-site happens-before edges required by the two-role broker. Four
central domains separate site, manifest, aggregate-formula schema and
manifest-bound cap-profile join identities.

The aggregate layer is deliberately nonnumeric. It specifies typed
`count x extent`, distinct-payload interval, eight-role output fixed-point,
two-role hierarchy-cap/same-OFD peak and positive launch-cardinality evidence,
but accepts no operands and issues no upper. Cross-path evidence reuse,
shared-admission reuse and zero placeholders are forbidden. The former stream,
worker-output and `memory.max` values cannot be relabelled as route aggregates
or actual peak evidence.

The public join factory accepts exact canonical manifest bytes and derives all
nine site IDs internally; it accepts neither a manifest ID nor caller-provided
site IDs. A profile produced directly by the historical generic factory is not
join evidence. Issuer-retained byte seals and independent exact-byte replay
reject object forgery, mutation, recomputed IDs and manifest/site identity
splicing. Live owner wiring, semantic cardinalities, a numeric V7 upper,
production execution, formal vectors, FQ9 closure and every Gate remain
blocked.

## V0-110B-2E-38 production shared-cap V2 pending boundary

Contract `2.0.49` creates a production-only successor namespace without
promoting the construction V1 cap session. The only issuable activation and
engine state is `V7_AUTHORITY_PENDING`. The engine is an issuer-retained exact
nested-tuple capability containing nine fixed owner-name/pending-sentinel
pairs; it has no callback, transaction, receipt, semantic-event or lifecycle
surface. Caller tuples and tuple subclasses are not authorities, and the
reachable runtime object graph has no mutable backing.

Activation, profile and engine identity candidates use three distinct local
domains. Receipt, semantic-event and atomic-pair domains remain unregistered
non-mintable candidates; the local identity helper rejects them and rejects
non-exact string domains. Exact-type, mutation, class/subclass, object-new,
GC-referent, malicious-string and private-mint attacks fail closed. A future
V7 adapter must supply a formal fallback decision, exact aggregate caps,
atomic receipt/event authority and all output, launch, mount and same-OFD peak
semantics before any owner operation can exist. No execution, vector,
terminal or Gate is authorized.

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
- **2026-07-23 — 1.16.0:** Added V0-053/profile `lmb_h2_live_query_local_epoch_invalidation_v0`. The eight-authority runner must freeze the first V3 DAG failure before the exact nine-row round-two acquisition, then derive the immutable final epoch, exact row delta, facet invalidation closure, replanning and final certificate live rather than from a completed V0-047 result. Request-reset, epoch-reset-global and continuous cross-epoch controls compute/hit `110/0`, `70/40`, and `68/42`; exactly two distinct `C0` constructions are reused across epochs. Both epochs retain the same semantic `A0A0` policy, so only model-bound plan/proposal/root re-binding is claimed. Eleven domain-separated V0-053 canonical IDs are frozen, while their hashes remain integrity/binding anchors rather than semantic proof. Generic model change, semantic policy change, persistence, sample efficiency, economics and official execution remain locked.
- **2026-07-26 — 1.17.0:** Added V0-054A/profile `lmb_h2_same_query_durable_proof_state_v0`. The owner-bound V0-053 final epoch is serialized as a canonical externally selected 30-lower-node/no-`R` checkpoint and consumed by two fresh processes. Strict loaders perform exact `34/10` model-derived candidate replay; matched two-occurrence arms freeze `110/0`, `70/40`, and `10/100`. The parent treats child output as untrusted and re-derives both complete documents (`190/140`), while evaluation rebuilds a new store/process pair and protects the original snapshot. This proves only registered same-query lower-proof persistence: no independent-algorithm, sample/total-work, generic persistence, semantic-policy-change, economics or official claim is opened. V0-054B remains the separate strict action-local policy-switch Gate.
- **2026-07-26 — 1.18.0:** Added V0-054B/profile `lmb_h2_action_local_semantic_switch_v0` and pure proof subprofile `lmb_h2_action_indexed_semantic_switch_v0`. A literal seed-4 LMB first epoch is constructed at `4 observed / 1 missing` with zero transition calls; its `A0A0/N` plan fails regret `3/4`. A non-authorizing unrestricted-challenger circuit and separate necessity/request chain open one owner-bound, non-copyable transition capability behind a process-local non-reentrant step gate. The monitored `M` row is the only acquisition and immutable addition. Before final replanning, the live 18-node cache verifies and binds the complete 14-edge pre-execution reverse closure. Final proof work is `10 computes / 8 hits` plus three fresh roots, and the reachable action changes strictly to reward-1 `A0A1/M`, risk/regret zero, certified. Candidate/audit/root/proposal identities and live receipt/result ownership are cross-checked against fully re-signed, no-step, early/duplicate-step, incomplete-closure and copied-authority attacks. Only this registered one-row semantic closed loop is claimed; generic H>1/minimality, persistence/reuse, coordinate invention, learned dynamics, sample/total-work savings, economics and official execution remain locked.
- **2026-07-26 — 1.19.0:** Added V0-055/profile `lmb_h2_two_generation_durable_action_local_recovery_v0` and transport subprofile `lmb_h2_durable_action_switch_transport_v0`. Root-free C1 persists 18 strict typed first-model lower nodes; fresh P1 loads/reuses all 18, recomputes none, builds three fresh roots and reproduces the failed `N` proof before ground authorization exists. Only after host verification does the exact source-pinned V0-054B runner execute the sole operational `M` transition. A detached immutable overlay preserves provenance without transporting live ground authority. Fresh P2 restores the 18 first nodes, performs the final `10/8 + 3 fresh roots` continuation and reproduces the strict `N -> M` certificate. Root-free C2 persists the 28-node lower union with 18 active and ten historical nodes; fresh P3 loads/reuses the active 18, recomputes none and builds three fresh roots. All three workers are model-only. The 18 checkpoint semantic obligations are not native physical compute counts; same-implementation evaluation replay is separate and no generic persistence, cross-query/H>2, independent-verifier, sample/byte/CPU/wall/total-work, economics or official claim opens. The next Gate is a preregistered matched multi-occurrence/multi-query workload, after which a measured sample-tax operator/meta-prior may be designed.
- **2026-07-26 — 1.20.0:** Added V0-056/profile `lmb_h2_preregistered_durable_multiquery_workload_v0`. Before the target-blind V0-055 Q1 source runs, it freezes threshold-only Q1/Q2/Q3 and ten-occurrence order `1,2,3,1,2,3,1,2,3,1`. The target projection contains the complete canonical 18-document active-C2 semantics (`21983` bytes; SHA-256 `b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55`), and fresh workers formula-derive all changed gates, selection, audits, roots and certificates from exact semantic fields and ordered parent-node IDs. Consumed-facet keys and lookup-before-builder execution freeze global `6/174/30`, matched C2-reset `18/162/30`, and source-blind conditional-online direct `10 ground / 10 catalogue / 40 policy-evaluation / 10 optimizer` traces. The reset arm additionally retains ten typed W0 initializations and records every initializer plus worker-observed store byte count, while `query_store_io_complete=false` because host lease/snapshot and verification rereads remain incomplete. The implementation, registered attack cases and fresh-store evaluation replay emit status `CERTIFIED_REGISTERED_H2_PREREGISTERED_DURABLE_MULTIQUERY_WORKLOAD_CONTROL`; final campaign/evaluation IDs are `8edf8a660fe3...`/`48e8919a0899...`, with matched/reset-initialization vectors `f8fe8f4dd584...`/`20339c4e312e...`. This remains a threshold-only operation-specific workload control, not sample, byte/total-work, economics, generic reuse/generalization or official-execution evidence.
- **2026-07-26 — 1.21.0:** Added and verified the V0-057 construction contract/profile `lmb_h2_interleaved_certificate_triggered_durable_epoch_v0`. It freezes the new typed relaxed Q_R `(3/4,1)`, original strict Q_S `(0,0)` and order `Q_R,Q_S,Q_R,Q_S,Q_R` before the authentic V0-047 source is constructed. The pre-source record binds all eight input-authority identities and complete H2 semantic/query scope while forbidding prospective derived epoch IDs. Q_R certifies the first live `11/9` epoch with zero additional query ground; only the next selected Q_S value/risk failure may authorize the exact `3/9/9` row scope and `3 safe / 6 failure` nine-row acquisition that produces the final `20/0` epoch. C1/C2 retain the real 30-node strict-Q_S core; Q_R facets bind preregistration/eligibility/query/source-D and roots bind typed proof requests. C2 independently loads C1 and proves exact retained history; facet stores remain distinct epoch-local W0/genesis chains. The exact core update is `28 new / 2 C0 reused`, yielding C2 `58/30/28`. Native main/reset traces are `16/284` and `24/276`; projections are `16/234` and `24/226`; the operational campaign is 12 launches, 60 roots and `40/560`, with host verification `23/9/36/12/64/32/12`. A 23-record event ledger is mandatory. All 85 registered tests pass. One operational producer and one fresh same-implementation evaluation replay use the identical frozen source-pin set; evaluation work is separate, no third campaign or independent algorithm is claimed, and the final authority boundary is a process-local claimed handle plus durable bytes/fresh replay rather than a generic cross-process wrapper parser. The passing status and canonical principal IDs are frozen in the detailed rule and normative specification. No generic reuse/H>2, promotion, generalization, sample/total-work/economics or official claim opens.
- **2026-07-26 — 1.22.0:** Added and verified V0-058 profiles `lmb_observed_program_closure_partial_rapm_v0` and `lmb_observed_program_closure_heldout_h2_v0`. The source-only producer closes the frozen typed vocabulary to depth two, retains 215 semantic representatives, exhausts all 6650 bounded optional-single-coordinate candidates, and selects `cardinality(legal_actions)` with `buffer_at_type(buffer_counts,selected_tile_type)<=3/2`, yielding an honest `7/4` partial RAPM. A pre-synthesis source-log-held-out H2 target first fails model-only audit at reward `[0,4]`, failure `[0,1]`; only that failure authorizes its exact `1/3/3` three-row scope. The safe row reaches an existing source successor, so no successor ground access is needed. The immutable `10/4` epoch replans and independently certifies reward/failure/regret `1/0/0`. All 19 registered tests and deterministic replay pass; implementation digests and principal IDs are frozen. This advances automatic program composition/selection only within one human-specified vocabulary and finite deterministic symbolic log; unknown-semantic invention, learned/statistical dynamics, broad generalization, sample savings/economics and official execution remain locked.
- **2026-07-26 — 1.23.0:** Added and verified V0-059 profiles `multidomain_observed_statistical_heldout_campaign_v0` and `g2048_d4_empirical_hoeffding_partial_rapm_v0`. A pre-model twelve-occurrence campaign composes the V0-058 LMB exact partial/recovery path with a G2048 probability model learned from six trusted aggregate rows of 65,536 offline observations each. The known D4 structural quotient remains an explicit human prior. Exact-rational Hoeffding/Taylor/union calibration freezes radius `1/128`, family tail `3/350` and confidence lower `347/350`; robust H2 enumeration selects `TOWARD,AWAY,AWAY` with reward `3/64`, failure upper `75716127/2147483648 < 1/20` and regret zero. The first LMB occurrence acquires exactly three rows and two later occurrences reuse its final model; all nine G2048 occurrences use zero online samples. Production has no G2048 kernel, while standalone exact D4 evaluation contains value `3/64` and risk `99/5000` without promoting statistical evidence. All 15 focused tests and all 1242 repository tests pass. Automatic symmetry/primitive invention, shared cross-domain coordinates, raw symbolization, broad generalization, sample savings/economics and official execution remain locked; 393,216 is an exposed sample tax, not a benefit claim.
- **2026-07-27 — 1.24.0:** Added and verified V0-060 profiles `g2048_raw_replayable_multicontext_partial_statistical_v0` and `g2048_certificate_directed_vs_uniform_acquisition_v0`. Three separately keyed spawn-law contexts and two queries per context are frozen before raw evidence. A model-only failed risk proof authorizes exactly three of six rows; the adaptive lane stores 147,456 individual packed draws and retains nine explicit missing context-rows, while the independent all-six-row statistical control stores 294,912 draws. Exact-rational calibration freezes radius `1/64`, 54 obligations and confidence `673/700`. Both lanes certify `TOWARD,AWAY,AWAY`, reward `3/64`, risk below `1/20` and regret zero; each second query reuses its context model with no new draws. Production has no kernel/probability input. Standalone evaluation replays all 442,368 nibbles and three exact J0 risks without promoting evidence. All 14 focused tests and all 1,256 repository tests pass. The 147,456 draw difference is not a sample-efficiency claim because the control is statistical all-row acquisition, not a matched direct-ground planning system. Automatic coordinates/symmetry, unknown support, broad generalization, sample-tax operators, complete accounting, economics and official execution remain locked.
- **2026-07-27 — 1.25.0:** Added V0-061/profile `g2048_matched_adaptive_vs_cold_direct_ground_v0`. It preserves V0-060's three contexts/six queries but replaces the unmatched all-six-row control with six cold complete ground statistical planners. The adaptive route records 147,456 draws and three within-context model reuses; direct records 4,866,048 draws across 198 occurrence-local ground rows with zero reuse. Exact-rational joint confidence is `42967/43750`; production has no kernel, and standalone evaluation replays 5,013,504 observations plus six exact J0 controls. The registered draw ratio is exactly 33 and may be reported only as a finite known-D4 workload observation. All 15 focused tests and all 1,273 repository tests pass. Exact test-only immutable-ID memoization and six-node module sharding reduce the compatible full-suite critical path to 208.1 seconds while retaining a fresh-ID release lane; this is execution acceleration, not research evidence. Broad sample efficiency, automatic hidden-coordinate/support discovery, sample-tax operators, official execution, scalar/break-even, complete economics and generalization remain locked.
- **2026-07-27 — 1.26.0:** Added V0-062/profile `g2048_source_frozen_boundary_capability_operator_v0`. Three disjoint source contexts contribute nine exact row enumerations/147,456 offline-source generative-oracle samples; source-only exhaustive two-row capability evaluation uniquely proposes `ROOT_TOWARD + CHAIN_A_AWAY` and retains `CHAIN_B_AWAY` as broad tail. On the unchanged V0-061 held-out targets, six rows/98,304 target generative-oracle samples certify all six occurrences at confidence `347/350`, saving 49,152 online samples, exactly one third, against the unchanged nine-row control. The five evidence-event classes are explicit. A wrong-prior prefix fails three times, invokes three tail rows, and emits zero false certificates. Standalone verification replays source evidence, the complete V0-061 baseline, both operator paths, and six exact J0 values. All 13 focused and fresh-ID tests pass; the compatible full-suite union covers 1,287 cases in 105 modules. Live interpreter caches are excluded only while selecting the immutable source payload, making concurrent snapshots deterministic; the resulting CAS tree and every private lease retain exact-file-set verification. Offline-plus-target samples are 245,760, so offline-inclusive and broad sample efficiency remain unclaimed; the nine-context source-amortization value is diagnostic, not official break-even. Automatic coordinate/support discovery, official execution, scalar/economics and all aggregate Gates remain locked.
- **2026-07-27 — 1.27.0:** Added V0-063/profile `g2048_preregistered_sequential_source_stopping_v0`. Ordered complete-context checkpoints stop the V0-062 source acquisition after two contexts and six 4,096-draw rows; checkpoint one is forbidden to stop, checkpoint two uniquely/unanimously freezes `ROOT_TOWARD + CHAIN_A_AWAY`, and the third source context remains unqueried. The proposal guard is explicitly nonauthoritative. The unchanged target route certifies all six occurrences from 98,304 target draws, while the no-operator and cold-direct controls remain 147,456 and 4,866,048. Source plus target is 122,880, yielding a registered-family offline-inclusive saving of 24,576 (`1/6`); the wrong prior still fails three times, invokes three fallbacks and emits zero false certificates. Independent replay covers all source draws, the complete V0-061 baseline and six exact J0 comparators. All 13 standard/fresh-ID focused tests and all 1,300 repository tests pass. Broad sample efficiency/generalization, automatic coordinate/support discovery, official execution, scalar/economics and aggregate Gates remain locked; the next construction Gate returns to observation-driven coordinate/support proposals over a larger held-out structural family.
- **2026-07-28 — 1.28.0:** Added V0-064/profile `g2048_observation_driven_relational_support_v0`. A source-only bounded relational closure selects state/action coordinates and six anonymous support templates from 144 complete rows after evaluating all 432 candidates, without D4 or named frontier inputs. Three identity-disjoint target structures each execute an all-missing, `8+16` row, two-failed-proof partial/statistical construction and then certify two occurrence-bound queries from their context-local model. Target probabilities are draw-only over registered symbolic support; exact calibration gives simultaneous confidence `239/250`. Context-build versus occurrence work is explicitly separated. A wrong proposal fails closed; six cold exact controls reproduce J0. Typed evidence replay, fixed concretizer, occurrence scopes, horizon/simplex checks, kernel/implementation pins, and chain-splice attacks are mandatory. Verification is same-implementation semantic replay, not independent-algorithm evidence. All 17 focused and all 1,317 repository tests pass. Primitive invention, unknown support, unseen graph geometry, cross-structural reuse, broad generalization, sample efficiency, official execution and economics remain locked.
- **2026-07-28 — 1.29.0:** Added V0-065/profile `observation_driven_cross_geometry_relational_rapm_v0`. Three non-isomorphic source graphs contribute 120 complete H2 rows/51 states to a target/query/kernel-free depth-two relational synthesis; 262 syntactic programs reduce to 42 semantic representatives, and complete 25-pair search selects legal-action count plus survivor occupied-neighbor count with honest alias width `99/100`. Held-out non-isomorphic `C4`, diamond and `K4` build separate target-only statistical RAPMs from `48/60/72` rows and 11,796,480 total raw draws. C4/K4 certify under the base schema; diamond's failed certificate searches four source-frozen refinement candidates and selects rank-degree signature plus survivor degree, after which all three contexts and six occurrences certify, with cold exact risk `99/5000`. Exact calibration covers 912 positive/OOD obligations at confidence `3011/3125`. No-transfer, one-of-three legacy, semantic/unregistered OOD, permutation, identity-isolation and cold-ground controls fail closed where required. Campaign/verification IDs are frozen; verification is same-implementation, not independent. All 33 focused tests and all 1,350 repository tests pass. Broad graph/second-domain generalization, primitive invention, unknown support, dynamics transfer, cross-structural reuse, sample efficiency, official execution and economics remain locked.
- **2026-07-28 — 1.30.0:** Added V0-066/profile `variable_cardinality_two_domain_relational_rapm_v0`. An independently replayed source-only constructor selects a dynamics-free portable relational state/action skeleton from a complete 120-row anonymous log. The graph arm crosses from four to five/six vertices, conditionally certifies W5/K6 complete H2 plans from target-local observations, and sends a registered K6-minus-edge no-cover case to a charged exact fallback. The second-domain LMB arm binds the same program identities through a query-neutral bridge and certifies three separate two-support target models from 98,304 operational draws and zero operational exact rows. Target identities and dynamics remain disjoint; six wrong-arm transplants fail closed. Arm-wise conditional tails combine by Boole's inequality to confidence `245713/250000` without assuming cross-arm independence. Independent verification is source-only, LMB planning is domain-specific, and ontology invention, generic planning, observational OOD, changed-query reuse, sample efficiency, official execution and economics remain locked. All 62 focused and 1,412 repository tests pass.
- **2026-07-28 — 1.31.0:** Added V0-067 profiles `v0067_real_factorial_campaign_v0` and `v0067_v0066_graph_factorial_sample_efficiency_v0`. Target-local uniform-Beta likelihood-mixture stopping reduces registered positive quotient acquisition to `425984` draws versus `737280` for matched sequential direct planning, while the tested source-only meta-prior changes no target prefix and has no incremental target effect. K6-minus-edge remains a charged exact-fallback control; eight physical authorities combine to confidence `24903/25000`. Unknown-support learning, total-work economics, official execution and broad sample efficiency remain locked.
- **2026-07-28 — 1.32.0:** Added V0-068/profile `observation_discovered_partial_support_campaign_v0`. Operational direct/quotient planners receive only realized transition tuples; discovery freezes observed support, fresh validation estimates it plus one adversarial `OTHER`, and exact-rational row/family authorities drive robust H2 planning. W5 certifies at 4096 in both lanes. K6 direct certifies at 8192; one 249,728-draw support promotion still fails risk and quotient certifies at 16384, yielding `matched_observation_advantage=false`. K6-minus-edge invokes matched exact feasible fallback. Every statistical positive is conditional on an idealized uint64 IID authority not proven by deterministic SplitMix64 replay. No exact-support, broad generalization, total-work/economics, independent-planner or project-completion claim opens, and all official locks remain.
- **2026-07-29 — 1.33.0:** Added V0-069/profile `k6_two_distinct_row_support_transactions_v0`. The immutable K6 transaction-1 model yields 49 fresh different-row selected-policy counterfactuals and zero individually causal rows. It closes `NO_SOUND_DIFFERENT_ROW_COVER` before sampling, exact evaluation, global-16384 access or transaction 3; its materialization branch remains unexercised.
- **2026-07-29 — 1.34.0:** Added V0-070/profile `k6_model_only_minimal_pair_support_recovery_v0`. A fresh authority evaluates 49 singleton and all 1,176 unordered pair overlays under complete fixed-policy H1-to-H2 recurrence; all fail, and an independent recurrence replays all 1,225 obligations. The negative terminal performs zero acquisition/full-replan/exact/16K work and closes only the selected-policy `k<=2` hypothesis.
- **2026-07-29 — ledger 1.34.1 (construction contract unchanged at 1.34.0):** Audited the proposed V0-071 `1.35.0` source-guided acquisition mechanics and froze their non-closure boundary. Exact midrank/source-multiplier, one-row sensitivity ranking, authorization ordering and synthetic two-round control mechanics exist, but caller-supplied source gains, a sample-dependent v1 feature key, the absence of a real target observer/materializer and fresh round-2 frontier authority, and same-implementation-only replay keep the Gate `NOT_RUN`. Synthetic endpoints authorize no target-acquisition, transfer, sample-efficiency, independent-verification or project-completion claim; every official/economics/counter/sample-efficiency lock remains unchanged.
- **2026-07-29 — ledger 1.34.2 (construction contract unchanged at 1.34.0):** Preregistered the V0-072 transfer-guided adaptive-acquisition experiment before any held-out target tape. Three seven-vertex contexts, environment-only laws, five arms, exact two-round draw caps, seven source raw-prefix roll-forwards and source/no-prior plus source/direct endpoints are frozen. Exact lazy planning and proposal-only source replay are prerequisites, not result evidence. Execution remains disabled pending a pushed-commit anchor; real materialization, fresh round 2, independent search/bundle verification and the confirmatory campaign remain `NOT_RUN`.
- **2026-07-29 — ledger 1.34.3 audit correction (construction contract unchanged at 1.34.0):** Corrected V0-072 from “preregistered” to `NONAUTHORIZING DRAFT / TARGET LOCKED / GATE NOT RUN`, schema `2.0.0`, profile `transfer_guided_adaptive_observation_acquisition_v1`. Retired eight development IDs after a fake-placeholder test path generated in-memory registered tuples; no tape/artifact/endpoint persisted, and clean-generation replacements start at zero draws. Draft preregistration `8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29` has a null execution manifest and cannot anchor. Exact lazy planning plus independent proof replay, verified source archive, selector, anchor-locked observer/full epoch-chain and disjoint synthetic K4 control are prerequisites only. The first possible anchor must be the first qualifying `origin/main` commit containing a final non-null execution manifest and its final binding preregistration ID, whose parent lacks that final ID; real model/materializer/direct/round-2/campaign/bundle verification remains incomplete.
- **2026-07-29 — ledger 1.34.4 prerequisite closure (construction contract unchanged at 1.34.0):** Added exact split-support confidence and campaign allocation, evidence-first public novel-child cardinality and selection, immutable row-bound observation/replay records, discovery-only cold-H2 closure, a separately implemented source-archive transform verifier, and nonauthorizing execution-manifest readiness. A real V0-068 campaign now traverses the production V0-072 archive and the independent archive-transform verifier, while the latter explicitly does not claim independence from the upstream same-implementation V0-068 campaign authority. Registered target access remains locked; relational/ground model construction, materialization, fresh round 2, direct baseline, campaign and standalone bundle verification remain incomplete, so no V0-072 result or aggregate Gate opens.
- **2026-07-29 — ledger 1.34.5 confidence-schedule audit correction (construction contract unchanged at 1.34.0):** Corrected the V0-072 per-row confidence limit from two to three epochs: one initial epoch plus at most two promotions. The distinct two-round execution bound still permits at most two promotion authorities per context, so the conservative total remains 480 authorities per arm and 2,400 per campaign; `beta=1/300000`, joint tail `1/125`, and confidence `124/125` are unchanged. Superseded nonauthorizing draft ID `8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29` is retained in audit provenance and replaced by nonauthorizing draft ID `e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4`; neither authorizes target access or changes any Gate.
- **2026-07-29 — ledger 1.34.6 direct-terminal audit correction (construction contract unchanged at 1.34.0):** Added `DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE` to the V0-072 terminal registry for the matched-direct arm reaching its complete 16,384-draw checkpoint without a sound certificate. It is distinct from adaptive incremental/two-round exhaustion, exact-DP resource exhaustion, fallback, and infeasibility. Superseded nonauthorizing draft ID `e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4` is retained in audit provenance and replaced by nonauthorizing draft ID `7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2`; both retain null manifests, keep target execution locked, and change no Gate.
- **2026-07-29 — ledger 1.34.7 anchored-attempt protocol repair (construction contract unchanged at 1.34.0):** Recorded anchored attempt 1 as `PROTOCOL_FAILURE / INCOMPLETE_CAMPAIGN_ARTIFACT` after the independently replayed matched-direct native-work purpose omitted `MATCHED_DIRECT_CHECKPOINT`. No result or endpoint was written; unknown paid work is explicitly not zero and all 15 occurrences remain in the failed-attempt denominator. Authorized one clean, full-restart replacement using only exhaustive enum handling and durable attempt journaling, with new target identities and a new recipe/manifest/preregistration/remote-main anchor. Scientific parameters and every aggregate Gate remain unchanged.
- **2026-07-29 — ledger 1.34.8 attempt-2 closure and V0-074 repair construction (completed construction contract unchanged at 1.34.0):** Recorded the sole V0-072 replacement as a hash-chain-valid `ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE` after four of 15 completed occurrences; no result or endpoint exists and the old chain has zero remaining attempt slots.  The tracked record ID is `cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e`.  Proposed contract `1.39.0` now makes the frozen partial-support escape semantics explicit in exact lift, with separate environment/abort risk and branch witnesses, and specifies pre-target frozen-source plus occurrence-parallel mechanics.  The current archive/worker implementation is synthetic transport only; production integration and operational-envelope containment remain `NOT_RUN`.  Existing V0-073 development contracts `1.37.0` and `1.38.0` remain unchanged.  V0-072 K7 evidence is retrospective only; fresh science requires a separate preregistration, manifest and anchor plus fresh target identities/tapes and genuinely fresh held-out occurrences.  All official, scalar, economics, counter and sample-efficiency locks remain unchanged.
- **2026-07-30 — contracts 1.37.0–1.39.0:** Preserved V0-073 certificate-boundary VOI as a development proposal, added fixed/target-only/source-weighted shared-prefix controls, and implemented the V0-074 `OTHER -> ABSORBING_POLICY_ABORT_FAILURE` total-lift repair plus frozen-source/occurrence-isolation mechanics.  None is a third V0-072 attempt or a fresh scientific endpoint.
- **2026-07-30 — contract 1.40.0:** Established the V0-075 authority family, source replay, law-free public target graph, private commitment/reveal boundary, construction observer, campaign identities and locked fresh-campaign plan.  This is the foundation contract, not target-execution authority.
- **2026-07-30 — contracts 1.41.0–1.42.0:** Added batch-native exact H2 total lift and a 15-occurrence plan/transport/reconciliation construction runner.  Process transport and canonical topology do not by themselves establish producer semantics or official execution.
- **2026-07-30 — contracts 1.43.0–1.44.0:** Froze exact V2 identity closure with no V1 projection, then bound the V2 reveal/preopen and observer-signed aggregate lineage.  Private material remains unexported and target execution remains locked.
- **2026-07-30 — contracts 1.45.0–1.50.0:** Added target-free production profiles, aggregate total lift, signed lifecycle/failure replay, five-arm pretarget schedules, initial acquisition/support bindings, exact-rational robust planning and schedule-to-numerical-planning construction.  `OTHER` remains distinct from modeled environment failure and is charged as policy-abort failure.
- **2026-07-30 — contracts 1.51.0–1.53.0:** Added complete child catalogues/all-or-none intents, open-session prefix checkpoints and an in-process support/validation controller.  These revisions explicitly provide no causal-before-draw proof, cryptographic process ownership or production authority.
- **2026-07-30 — contracts 1.54.0–1.59.0:** Unassigned.  No authority, compatibility or migration meaning may be inferred for these version numbers.
- **2026-07-30 — contract 1.60.0:** Added signed control heads/intents/appends, finite dynamic caps, at most two promotions, immutable model epochs/barriers and the multiround construction runner.  The implementation remains same-process and construction-only.
- **2026-07-30 — contracts 1.61.0–1.63.0:** Added portable occurrence bundle transport/topology, sealed `python -I -S` raw replay and the 67-role static semantic registry.  Bundle hash validity and static role declaration are not semantic completion; only the registry's self-contained roles were initially complete.
- **2026-07-30 — contracts 1.64.0–1.66.0:** Added raw public-context closure, raw eleven-role M0 reconstruction and raw observer-open binding replay.  Source manifests remain opaque construction inputs until source/code authority is separately closed; M0 currently supports only the registered `NO_PRIOR` arm.
- **2026-07-30 — contract 1.67.0:** Added raw M1A signed-batch reconstruction.  Six public producer roles are complete; repeated outcome IDs use nested canonical bytes rather than global-ID uniqueness; an iterative `O(V+E)` dependency DAG replaces recursive transitive expansion.  The closure-verification private replay claim remains unresolved.
- **2026-07-30 — contract 1.68.0:** Added an atomic construction freeze that performs exact private replay before observer signing and rejects caller-supplied or legacy verification objects.  The public result is an observer-signed claim, not an independent proof of execution order.  A generic signer can bypass the helper, so a signer-owning sealed service and a new non-retroactive portable role remain mandatory before production.
- **2026-07-30 — contract 1.69.0:** Added a fail-closed signer-owning sealed-child transport.  It loads the production signer behind a separate sealed descriptor and closes every post-nonce path with typed native accounting, but intentionally owns no observer session, performs no private replay and signs no B3.
- **2026-07-30 — contract 1.70.0:** Added raw M1B signed-control reconstruction for 16 roles.  ROOT authorities bind exactly to M0 row/stage/lane/epoch/draw witnesses; CHILD/PROMOTION semantics remain explicit structural-only or absent states, and the M1A private-verification claim remains unresolved.
- **2026-07-30 — contract 1.71.0:** Added a construction-only signer-owning complete lifecycle for the registered synthetic root K7 fixture.  One sealed child owns open through private replay/B3 signing; public replay remains noncertificate and does not upgrade the portable private-verification record.
- **2026-07-30 — contract 1.72.0:** Added the M2 root boundary.  `OCCURRENCE_IDENTITY` and `ROOT_EXECUTION` are reconstructed as `FULL_PUBLIC` with exact M0/M1B relationship and full dependency-spine replay.
- **2026-07-30 — contract 1.73.0:** Added M2 public lineage.  Batch public and sequence verification close as `FULL_PUBLIC`; construction lineage is reconstructed publicly but remains structural-only on the exact unresolved private closure-verification frontier.
- **2026-07-30 — contract 1.74.0:** Added M2 construction-lifecycle replay.  Support evidence, freezes and events close publicly with explicit authority-local source edges; lifecycle and lifecycle verification remain structural-only on the exact private closure-verification frontier.
- **2026-07-30 — contract 1.75.0:** Added M2 live-epoch replay.  Row-source bindings close publicly; complete epoch bytes are rebuilt through the portable non-operational producer path, while live epochs retain the exact numerical-model and numerical-planning-proof frontier.
- **2026-07-30 — contract 1.76.0:** Added M2 dynamic-child proposal replay.  The six-role registry is rebuilt exactly, including two absent roles; every present role receives exact epoch/model/proof source edges and remains structural-only on the numerical model/proof frontier.
- **2026-07-30 — contract 1.77.0:** Added M2 numerical planning replay.  Every live-epoch model/proof is checked through the public exact planner; standalone model/proof registries close as `FULL_PUBLIC`, which transitively closes live epochs and the four present dynamic-child roles.  Construction planning input remains self-frontier unresolved because no legitimate portable typed-private-lineage authority exists.  No private issuer/compiler, operational path, K7/held-out access or Gate unlock is introduced.
- **2026-07-30 — contract 1.78.0:** Added raw construction-private producer replay after hardened 1.77.  A bounded ephemeral seed/salt regenerates and commitment-checks the private environment, then only the registered construction lineage/lifecycle APIs may close the exact private verification and its three transitive consumers.  These roles are explicitly construction-private/transitive rather than public.  The planning input compiler, production secret channel, fresh target access and every official/scientific/certificate Gate remain locked.
- **2026-07-31 — contract 1.79.0:** Added raw construction planning-input compiler replay after hardened 1.78.  The exact M0 schedule and fresh private-replayed lineage/lifecycle rebuild the complete input, model and row-evidence graph byte-for-byte.  The input closes only as construction-compiler authority; closed reconciliation and final result remain self-frontier unresolved, and all production/science/certificate locks remain closed.
- **2026-07-31 — contract 1.80.0:** Added an owner-bound construction closed-reconciliation producer and raw portable replay.  Exact final epoch/control/lineage/lifecycle replay precedes compiler/planner replay and owner-only issuance; the closed reconciliation now has construction authority while the final multiround result remains self-frontier unresolved.
- **2026-07-31 — contract 1.81.0:** Added owner-public root-execution and multiround-result construction replay plus a raw portable root-only cap-profile authority.  Terminal status is derived from exact parents, the result target cannot select its producer inputs, and the final construction frontier is empty; source/code provenance, registry aggregation, accounting, production and scientific Gates remain locked.
- **2026-07-31 — contract 1.82.0:** Added a raw-1.81-first construction semantic terminal overlay.  It preserves the unchanged legacy declaration/shape labels, binds all 49 present records one-to-one across bundle, old attestation and typed DAG, proves the exact 18-role absence set from the fresh root-only registry, and closes all 67 declarations with per-record authority scopes and an exact scope histogram.  Only construction-qualified semantic completion is established; source/code provenance, accounting, production, official, scientific and certificate Gates remain locked.
- **2026-07-31 — contract 1.83.0:** Added raw-1.82-first local construction source/archive/compile provenance.  All tracked ACFQP Python files are bound to clean-environment Git evidence, split into the exact historical 64-entry occurrence lane and an additional semantic-code lane, packed into a deterministic sealed archive and compiled without executing tested code.  The loaded-source claim was deliberately kept false after an adversarial child-forgery regression; final manifest, remote anchor, real target-worker receipt and all unqualified production/science/accounting/certificate Gates remain locked.
- **2026-07-31 — contract 1.84.0:** Added the raw-1.83-first construction native-accounting foundation.  It freezes the immutable Phase-3E v1 registry/profile identities, separates initial BUILD/ACQUISITION from REBUILD, inventories all five incompatible historical V0-075 custom catalogues, reserves 13 disjoint v2 path names without claiming their counter semantics are complete, keeps the 67-role portable registry unchanged, and registers only the route-attempt-level cap-exceeded noncertificate derivation.  No historical summary is promoted to a CounterRecord, no WorkVector/terminal/occurrence/campaign closure is materialized, and all all-path, production, fresh, scientific, economics and certificate Gates remain locked pending live-from-start instrumentation.
- **2026-07-31 — contract 1.85.0:** Materialized the scoped construction accounting-v2 registry and stage/comparison/projection profiles after exact independent 1.84 verification.  The immutable 49-leaf v1 prefix plus 13 initial and seven closed-reconciliation leaves gives 69/53/62 total/operational/required cardinalities.  Accepted draws are charged on the kernel axis, rejection count is diagnostic rather than double-charged, and repeated closure computation has its own paths.  No live record, vector, terminal or occurrence/campaign closure is issued; the 11 currently identified recorder gaps are explicitly non-exhaustive, all 87 legacy custom paths still need operation-site mapping or a registry revision, and every production/fresh/scientific/economics/certificate lock remains open or `NOT_RUN`.
- **2026-07-31 — contract 1.86.0:** Added the immutable accounting-v3 successor after an operation-site audit proved v2 incomplete.  It partitions all 95 legacy entries/87 distinct paths as 7/18/51/11 migration dispositions, registers the eleven missing operational families plus the failed child-catalogue audit at truthful stage-local paths, adds open incremental-acquisition and checkpoint-replanning stages, and freezes 116/99/109 leaf cardinalities with 99 exact projection terms.  No legacy summary is promoted and no live work evidence is issued; operation-site hooks, derived formulas, hash/check/I/O/peak granularity, lifecycle/terminal/campaign closure, production, fresh science, scalar/economics and certificates remain locked.
- **2026-08-01 — contract 1.87.0:** Added the immutable accounting-v4 operation-ownership successor after the live K7 call graph exposed build-stage projection and closed private-replay coverage holes. The unchanged 116 v3 leaf documents plus eight additions give 124/106/117 total/operational/required leaves and 106 projection terms. Trusted lifecycle/event/vector/projection mechanics, a context-gated same-process no-full-replay audit hook and an exact five-stage/23-site K7 hook manifest now exist; the hook remains unwired and no live evidence is issued, so every all-path, formula, hash/I/O/peak, terminal/campaign, production, fresh-science, economics and certificate Gate remains locked.
- **2026-08-01 — contract 1.88.0:** Superseded only the K7 v1 hook-admissibility claim after strict source-owner replay. The audit-only v2 manifest binds v1 as a negative predecessor and partitions 43 entries into 9 owner-matched, 13 native-zero, 10 pending common-resource, one derived-only and 10 missing-family entries; it corrects private-replay ownership and freezes the deterministic aggregate-row count at 41. No sink, emitter or live evidence is authorized, and every Gate remains locked pending owner-specific batch-v2 leaves and operation-site hooks.
- **2026-08-01 — contract 1.89.0:** Added the immutable accounting-v5 known-owner-gap successor: canonical strict-owner-manifest bytes plus independently verified v4 bytes bind 27 schema-assigned operational leaves, producing 151/133/144 total/operational/required cardinalities and 133 exact projection terms while preserving all v4 leaf documents. An independent implementation rehashes the manifest and reconstructs the schema. Runtime attribution, hooks and evidence remain false, fixture-dependent row counts require full identity binding, and every production, fresh-science, accounting, economics and certificate Gate remains locked.
- **2026-08-01 — contract 1.90.0:** Added the additive V6 registry (`209/182/202` total/operational/required leaves and 182 projection terms), the 150-entry K7 operation-boundary catalogue, owner/code-object-bound five-stage positive-event instrumentation, the exact V0-075 K7 execution-identity overlay, an owned-wrapper-exclusive and registered-cache-user-isolated cold `PARTIAL_NATIVE_ONLY` path, and independent canonical-byte/schema/boundary/hash-chain replay.  No whole-process or adversarial callback isolation, full live K7 artifact, CounterRecord, WorkVector, ComparisonVector or projection proof is claimed; nine common shared-resource paths remain uninstrumented, so official/scalar/economics/scientific/certificate locks do not move.
- **2026-08-01 — contract 1.91.0:** Added the fail-closed K7 accounting completion prerequisite. It partitions all 202 V6 required paths exactly as `9+8+114+71`, freezes 89 owner-emittable sites, starts every closure unresolved, distinguishes structural source claims from semantic evidence, registers path-specific zero obligations, and binds occurrence/transcript/receipt identities plus an ordered operational cutoff. The current same-process path remains deterministically blocked and no formal CounterRecord, WorkVector, ComparisonVector or projection proof is issued; all official, economics, counter, science and certificate locks remain unchanged pending live supervisor evidence and independent semantic replay.
- **2026-08-01 — contract 1.92.0:** Added the structural K7 shared-resource execution boundary: a nine-path live event meter with exact SUM/MAX separation and explicit unavailable/zero semantics, a deterministic capped eight-role-labelled output-byte candidate fixed point, a canonical identity-bound K7 child-frame protocol, and a structural post-cutoff envelope/finalization join. Full source archive validation remains exact and freshness rechecks SHA-256. The envelope proves only local type/order constraints, its wrappers are outside the uncommitted eight-role total, and real supervisor provenance, typed K7 route/global-event joins, atomic output, source-semantic replay and formal 202-path consumption remain locked; no Gate state changes.
- **2026-08-01 — contract 1.93.0:** Added exact accounted-K7-route derivation of the seven shared-resource identity fields, a caller-sequence-free six-event structural supervisor journal, and an internally derived structural finalization bridge. Added a K7-only subprocess-free signer loader for the registered ordinary checkout/external-key shape, but did not wire it to a child. Journal source documents remain caller claims and its sequence is not OS order; no real child, `Popen`/pidfd/cgroup/one-child provenance, atomic output, semantic verifier, CounterRecord, WorkVector or ComparisonVector exists. Every official/formal/economics/science/certificate lock remains unchanged.
- **2026-08-01 — contract 1.94.0:** Added a real bounded read-only K7 OS-supervisor host probe and a mandatory preopened delegated-parent-FD admission boundary. Raw source bytes are not retained, cgroup mount roots and stat/access facts are explicit, and descriptor identities are transplant-resistant. The current host returns nonauthoritative `NOT_AVAILABLE`; a supplied directory FD also remains unavailable until a real exclusive cgroup lease, atomic child placement, pidfd lifecycle and post-reap peak verifier exist. No attempt terminal, nine-path semantic or formal-vector lock is issued.
- **2026-08-01 — contract 1.95.0:** Added the parent-owned successor IPC prelaunch identity graph. It derives its bootstrap digest and size from the exact sealed source snapshot; binds the accounted route, signer registry, commitments, session/nonce, scientific occurrence/schedule and Phase-3E occurrence mapping; and reserves child-business then parent-accounting-suffix roles for a future launched path. The current unavailable admission yields only a zero-launch/zero-frame structural blocked result, not an attempt terminal. No runtime or formal-vector lock moves.
- **2026-08-01 — contract 1.96.0:** Added the real process-local cgroup-v2 attempt-leaf lease. It consumes the exact request nonce before cgroup access, binds the delegated FD by stat and target digest, creates an exclusive empty domain leaf, verifies zero initial peak, freezes/readbacks one-child/depth/descendant caps and removes only its owned leaf. A temporary systemd-delegated scope passed the real positive syscall path. Child placement, pidfd supervision, durable replay, parent suffix, semantic nine-path closure and formal vectors remain locked.
- **2026-08-01 — contract 1.97.0:** Added fresh-exec reconstruction of the complete V0-103 authority chain from the sealed source archive and canonical profile/request bytes. The child no longer needs the live parent request object, while exact byte equality and process-local reconstructed issuers preserve fail-closed identity binding. Loaded-code/runtime proof, child launch, business output, parent suffix, semantic nine-path closure and formal vectors remain locked.
- **2026-08-01 — contract 1.98.0:** Added the typed child-owned K7 business frame. It runs the existing owned partial path once from the exact portable request replay, embeds and strictly replays the real portable evidence authority, and binds a single-read private signer/taint scan to the sealed request. Parent atomic supervision, accounting suffix, complete partial-transcript semantics and formal vectors remain locked.
- **2026-08-01 — contract 1.99.0:** Added the real x86-64 atomic `clone3(CLONE_INTO_CGROUP|CLONE_PIDFD)` runtime with native child-only setup, sealed memfd execution, parent-death/Landlock/seccomp containment, memory/swap/output/deadline limits, bounded pidfd supervision and cgroup-kill cleanup. Real delegated execution and fork/file/cgroup-write denial pass; the business join, parent suffix, atomic two-frame result and formal nine-path/202-leaf accounting remain locked.
- **2026-08-01 — contract 2.0.0:** Added the real parent-owned atomic successor executor. The exact V0-105 portable replay now enters the V0-106 owned K7 business once through the V0-107 cgroup/pidfd runtime; the parent validates EOF-frozen child bytes, derives the accounting suffix after runtime finalization and strictly replays exactly two ordered frames with a wrapper-complete byte fixed point. The nine shared-resource paths still have no semantic receipts, and no CounterRecord, WorkVector, ComparisonVector, terminal, certificate, scientific result or official authority is issued.
- **2026-08-01 — contract 2.0.1:** Added runtime-issuer-owned atomic lifecycle evidence and a production nine-row shared-resource registry. Final cgroup `memory.peak` is `VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE`; the native launch count is `VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE`; both are ineligible at attempt scope and the other seven paths are `NOT_CONNECTED`. Canonical snapshots prevent shallow cached IDs from mixing with later live mutations. No complete receipt set, CounterRecord, WorkVector, ComparisonVector, terminal, certificate, scientific result or official authority is issued.
- **2026-08-01 — contract 2.0.2:** Added the V0-110A in-process raw-prefix supervisor. Its session and sink start before request binding/replay and close after the typed parent-result payload freezes; the envelope is a post-cutoff no-launch wrapper, not proof of complete publication or later helpers. A positive `clone3` advances a volatile write-ahead edge lower bound before provenance/event materialization and pidfd validation; covered failures retain a closed journal, nonformal canonical emergency prefix or noncanonical raw-field fallback. Import pins cover ordinary public-symbol rebinding only, not arbitrary same-process mutation such as `object.__setattr__`, crash or no-loss capture. Status remains `VERIFIED_ATTEMPT_WINDOW_RAW_SCOPE_INCOMPLETE`; external isolation/OS attestation is still required, and no nine-path receipt, CounterRecord, WorkVector, ComparisonVector, terminal, certificate, scientific result or official authority is issued.
- **2026-08-01 — contract 2.0.3:** Added the V0-110B-1 outer cgroup `PREP_ONLY` hierarchy. A request/admission/descriptor-bound nonce creates a fresh empty ancestor, delegates `memory+pids`, freezes finite controls, opens writable `cgroup.kill`, creates a one-process worker leaf and revalidates the complete empty topology. Cleanup is an explicit `ACTIVE -> CLEANUP_PARTIAL -> CLOSED` state machine: consumer access is revoked at cleanup start, partial removal retries without request/admission authority and post-identity setup failures retain FDs in an exception-carried process-local guard. The pre-identity create gap explicitly requires an external parent guardian; cap mismatch deletes safely and raises a typed cleanup-complete protocol error. The pre-descendant zero peak is not a launch baseline; parent-writer exclusivity, atomic descriptor deletion, crash-surviving guardianship, reset-at-launch and safe runtime consumption remain false. Exact execution requires an external two-launch/no-spawn broker and a window through final output/cleanup, so all receipt/vector/terminal/certificate/official Gates remain locked.
- **2026-08-01 — contract 2.0.4:** Added the V0-110B-2A structural external-broker IPC. Exactly five canonical length-prefixed frames bind one request/route/broker-spec/session and close as one immutable transcript; exact role schemas prevent the sole business request from selecting launch authority, while order, counts, digests, IDs, unknown fields, noncanonical encodings and transplant attacks fail closed. The binding/stream remain caller-constructible offline values, same-binding replay is allowed, and no live peer, nonce-consumption, broker-spec or launch authority is claimed. The future two-sibling, broker-only `clone3`, kernel no-spawn, pidfd, same-OFD peak, operational output and cleanup-guardian contract is frozen but not executed. No shared-resource value or formal vector/Gate authority moves.
- **2026-08-02 — contract 2.0.5:** Added V0-110B-2B live process-local broker preparation. Cleanup capability is constructed under the lease lifecycle lock before irreversible transfer; transferred context exit defers to the guardian, and control violations survive partial cleanup retries. The fixed `business` sibling, kill/peak/socket descriptors, issuer-owned spec and nonce are prepared without launch. Real cgroup evidence moves the exact zero reset to the descendant-free start of the retained memory window and charges all later preparation without subtraction; serialized file identity is not treated as OFD proof. No live peer, process/frame/final peak/shared-resource value or formal vector/Gate authority moves.
- **2026-08-02 — contract 2.0.6:** Added V0-110B-2C real two-role native broker probe. Exact prepared-state/topology/control identities are replayed before consumption and each fixed worker/business clone. Outer-frame native cells retain each positive edge and PID before Python return; a pre-clone guardian-bound guard receives them before signal unmasking or fallible prefix hashing. Matching pidfds, direct-reap fallback, monotonic pidfd retirement, tree-only ancestor kill with retained OFD and retry-held unresolved cleanup prevent prefix rollback or lost containment authority. Two real sibling-cgroup processes launch and reap under a delegated scope. Bootstraps remain caller-supplied probe inputs, FD exclusion is claimed only at the untrusted exec boundary, cells remain crash-volatile, and no live five-frame/output/shared-resource/formal-vector Gate moves.
- **2026-08-02 — contract 2.0.7:** Added V0-110B-2D-1 non-launchable production-role template and role-local protocol cores. Live session replay fixes all public launch fields while explicitly separating dispatch digests from absent wrapper members; the successor must issue a new archive/request/manifest. Business adds owned-FD publication and typed irreversible stages; worker adds race-free bounded half-close, inode-safe commit/recovery and retained output/receipt preimages. No live sender, exclusive output directory, nine-path receipt or formal-vector Gate moves.
- **2026-08-02 — contract 2.0.8 / V0-110B-2D-2A:** Issued a fresh source archive/request/manifest containing the fixed production process wrappers and strict archive-only bootstraps. The bootstraps bind isolated interpreter flags, exact environment/FD namespace, immutable public inputs, separate nonsealed capability lanes, interpreter/archive digests and ZIP module origin; all inherited role FDs become CLOEXEC before project import. Runtime source provenance now supports exact ZIP-member bytes, and the private lifecycle secret is metadata-checked without a pre-business read. This closes executable source provenance only: no native production launch, sandbox, sender-credential join, final output/peak/reap envelope, shared-resource resolution or formal accounting vector is authorized.
- **2026-08-02 — contract 2.0.9 / V0-110B-2D-2B:** Added the issuer-owned broker resource session joining the executable manifest and exact two role contexts to two broker-mediated SEQPACKET pairs, broker-only `SO_PASSCRED`, one empty result memfd with separate business-RW and worker/broker-RO descriptions, and a worker-only fresh output directory. Role and broker FD lanes are pairwise disjoint, content IDs omit raw descriptor numbers/paths, and a process-local guardian detects binding, queue, option, memfd and directory changes before inode-safe cleanup. This remains no-launch preparation: sandbox, live protocol, post-reap envelope, nine semantic resolutions and formal vectors remain locked.
- **2026-08-02 — contract 2.0.10 / V0-110B-2E-0:** Froze the nine-path semantic resolution catalogue against the official V6 registry. Each shared path now has one distinct exact live source family, required V2 evidence schemas, provenance obligations and fixed verifier key. Typed envelopes carry raw canonical evidence only; V1 receipt/closure relabelling, mapping spoofing, explicit unverified bytes and numeric self-report are rejected. All nine results remain explicitly pending until their semantic replayers exist, and this slice exposes no CounterRecord or vector materializer.
- **2026-08-02 — contracts 2.0.11--2.0.13 / V0-110B-2E-1..3:** Added the two-stage production sandbox, one-shot manifest/input/capability launch records and per-packet SCM-credential/PID/pidfd authentication. The worker receives only its output subtree as a Landlock write root, business receives none, descendant creation is denied before the sole exact-FD exec edge, and postexec denies all later exec. These are partial construction authorities, not a complete launch/transcript/reap envelope.
- **2026-08-02 — contract 2.0.14 / V0-110B-2E-4:** Added raw replayable sources for read-byte SUM, staged-byte SUM and unique-visible-payload mounted-byte MAX. Purposes, transfers, intervals, automatic sequences, occurrence identities and inclusive cutoff are bound without caller totals. The component schemas match the nine-path catalogue but remain semantically unverified and cannot yet issue CounterRecords.
- **2026-08-02 — contracts 2.0.15--2.0.16 / V0-110B-2E-5..6:** Added atomic one-shot prepared-to-runtime descriptor transfer with monotone retirement/retry-safe empty cleanup, plus raw source-site/registry/event journals for hash, integrity and protocol work. Six of nine shared-resource source families now support independent internal arithmetic replay, but live completeness and every formal Gate remain locked.
- **2026-08-02 — contract 2.0.17 / V0-110B-2E-7:** Added the remaining raw output, working-peak and process source families. Output uses an eight-role durable byte fixed point with exclusive suffix writing and pinned `P == P'`; working memory uses one retained `memory.peak` OFD through descendant-free post-reap readback; launches require two positive native clone edges joined to PID/pidfd/SCM, postexec no-spawn and direct `P_PIDFD` reaps. Failure prefixes retain only launch lower bounds. All identities are centrally domain-separated, but the actual worker first-role join, complete live envelope, semantic replayers and formal vectors remain locked.
- **2026-08-02 — contract 2.0.18 / V0-110B-2E-8:** Closed the production-role bootstrap-to-entry exec gap. The exact archive-loaded sandbox now installs its TSYNC postexec filter once before role-entry import, live-probes both `execve` and `execveat` denial, and issues a process-local one-shot attestation bound to archive FD/OFD metadata, sandbox source, PID and role. Worker/business entries consume it before importing manifest/common/core modules; missing, duplicate, cross-role and rebound-FD attacks fail. This strengthens launch provenance only; it does not by itself create the live broker/output envelope or formal accounting authority.
- **2026-08-02 — contract 2.0.19 / V0-110B-2E-9:** Joined the prepared outer cgroup, resource session, archive-bound launch records and role sandboxes in one irreversible production-broker lifecycle. The broker executes two native sibling-cgroup launches, authenticates the exact five-frame stream by PID/pidfd/SCM credentials, publicly replays the business bundle, directly reaps both children, post-reap seals and no-replace-promotes the pinned worker output, reads final peak from the retained prepared OFD and retains retry-safe cleanup authority on failure. One absolute deadline now covers setup EOF and backpressured relay; pinned-FD ownership and post-rename provenance survive failure cleanup. Its centrally domain-separated envelope is explicitly nonformal: the operational wrapper is not yet the first registered eight-role output artifact and no receipt, CounterRecord, vector, terminal or certificate is issued.
- **2026-08-02 — contract 2.0.20 / V0-110B-2E-10:** Replaced the synthetic output-first-role gap with one-shot adoption of the actual worker `operational-output.json` inode under exact authenticated `PARENT_OUTPUT`, request/binding replay and worker-V1 byte verification. After direct reaps the broker seals the same inode `0600 -> 0400`, fsyncs and rereads it before writing the seven-role suffix; synthetic construction commits cannot become live evidence. Added fixed catalogue dispatch for all nine shared-resource semantic replayers with central component-ID/SHA, identity, source-local cutoff, provenance and official-reducer checks. These issuer-owned exact integers remain nonformal and cannot issue CounterRecords until joined to the V3 nine-source envelope and every other required V6 path.
- **2026-08-02 — contract 2.0.21 / V0-110B-2E-11:** Replaced the over-strong identical-sequence assumption at the complete nine-source join with an honest V3 envelope. Each SUM/MAX journal retains its own closed local interval and cutoff, while all nine exact path/component contracts are content-addressed under one runtime, occurrence, attempt, decision and measurement-window identity plus runtime-replay and terminal-closure observations. Padding, renumbering and missing-path substitution are forbidden. This is a nonnumeric join only; semantic replay and formal accounting remain separate Gates.
- **2026-08-02 — contract 2.0.22 / V0-110B-2E-12:** Replayed all nine exact source-local journals through their fixed semantic verifiers and froze path-specific materialization authorizations. No formal record is issued before the remaining 193 paths close.
- **2026-08-02 — contract 2.0.23 / V0-110B-2E-13:** Closed the production owner-event family by binding the actual child-business transcript and joined runtime to the exact source archive and loaded code. All 89 sites reduce to 71 ordered positive or complete-window-zero candidates; absence, abort and cross-site/stage substitution cannot mint zero or formal accounting. The atomic 202-path materializer remains locked.
- **2026-08-02 — contract 2.0.24 / V0-110B-2E-14:** Froze the exact eight-path reconciliation DAG. Direct-PIDfd replay closes process outcomes and the complete five-stage chain closes solver exclusion, while route outcomes retain a typed semantic-authority blocker; status, hashes and wrapper shape cannot substitute for a production business-bytes/transcript join. Incomplete readiness remains nonformal.
- **2026-08-02 — contract 2.0.25 / V0-110B-2E-15:** Added the positive occurrence/cutoff semantic prerequisite without relabelling the historical V1 structural objects. Issuance requires the exact current production role manifest and transport archive, broker runtime, raw operational output and embedded business result, complete owner transcript, production-rederived 71-path candidate set, verified nine-resource envelope and independently replayed output tails. It freezes `CHILD_ACTION_ROW_CAP_EXCEEDED -> FAILURE` with route counts `(1,0,1)` and centrally registers six role-separated domains. This is not the atomic 202-path materializer: no CounterRecord, WorkVector, ComparisonVector, projection, terminal certificate or official authority is issued, and every Counter Completeness, economics, scalar/break-even, fresh-science and certificate Gate remains locked or `NOT_RUN`.
- **2026-08-02 — contracts 2.0.26--2.0.32 / V0-110B-2E-16..22:** Closed the genuine K7 route-derived, 114 profile-zero and atomic 202-path semantic authorities; materialized the exact `CounterRecord -> WorkVector -> ComparisonVector` chain; derived the cap-exhausted noncertificate attempt terminal while retaining all work; added an independent evaluation-lane semantic reconstruction; and closed the canonical non-retryable logical occurrence in every denominator with certificate coverage false. Campaign all-path completeness, official execution, economics, scalar/break-even, sample efficiency and scientific claims remain locked or `NOT_RUN`.
- **2026-08-03 — contracts 2.0.33--2.0.34 / V0-110B-2E-23:** Froze the complete FQ9 route/stage/family accounting profile and fail-closed 47-class/164-member V075 terminal-status inventory, leaving 14 explicit extension blockers; added a self-contained independently replayable exact-infeasibility proof for the canonical G2048 fixture with `46/16/96/256` finite enumeration and minimum failure `383/410`. These are all-path prerequisites, not route execution, operation-boundary instrumentation, formal campaign accounting or any Gate unlock.
- **2026-08-03 — contract 2.0.35 / V0-110B-2E-24:** Replaced invalid-WorkVector integrity closure with externally anchored expected-versus-actual byte evidence and complete last-valid-prefix accounting: 202 observed records, a valid WorkVector and exact eight-axis projection. Integrity and protocol failures remain disjoint, fully re-signed attacks fail independent replay, and no certificate, occurrence closure or Gate is minted.
- **2026-08-03 — contract 2.0.36 / V0-110B-2E-25:** Froze an exact source/AST manifest of ten real production operation boundaries spanning all six required route/control families. Missing or changed source produces typed blockers; the catalogue performs no execution and emits no accounting or terminal authority.
- **2026-08-03 — contract 2.0.37 / V0-110B-2E-26:** Exercised the production FQ13 access semantics with a canonical pre-freeze forbidden-access negative control, preserving a complete 202-record failed-prefix vector and exact `PROTOCOL_FAILURE` terminal. A typed real-site blocker prevents the control from masquerading as a production violation, so all-path coverage remains open.
- **2026-08-03 — contracts 2.0.38--2.0.39 / V0-110B-2E-27..28:** Audited the live abstract PASS and genuine exact-infeasible direct fallback against the K7/V6 all-path contract. The former has an exact `160/15/27` required-path gap plus missing `9+8` shared/derived evidence; the latter matches the durable proof but retains only a 42-leaf V1 vector. Both produce centrally registered replayable blockers, never formal vectors or terminals.
- **2026-08-03 — contract 2.0.40 / V0-110B-2E-29:** Closed the 14 V075 extension-row interpretations with exact evidence-conditioned normalization. Candidate FQ9 targets still require downstream semantic terminal authorities; the profile issues no terminal or Gate claim.
- **2026-08-03 — contract 2.0.41 / V0-110B-2E-30:** Closed exactly 23 forbidden-route-stage native-zero values (without issuing the formal profile-native-zero authority) plus three separately typed derived-complement values for the live abstract PASS, rejected the unmeasured mounted-payload zero, and retained an exact 176-gap nonterminal partition. No formal V6 record, vector, terminal or Gate claim was issued.
- **2026-08-03 — contract 2.0.42 / V0-110B-2E-31:** Acquired 13 exact source values from the canonical raw infeasible fallback under an independently issued current source/kernel/query identity, while preserving the exact `178+7+6+9+2=202` all-formal-blocker partition. The raw marginal solver has null trusted provenance and no complete occurrence stage chain; no V6 record, vector, terminal or Gate claim was issued.
- **2026-08-03 — contract 2.0.43 / V0-110B-2E-32:** Inventoried the real abstract-PASS V1 evidence as an exact `160+23+8+1+2+8=202` formal-blocker partition. Shared aggregates, owner candidates, value-only proofs and reconciliations retain their source semantics and cannot become V6 records, native zeros, vectors or certificates.
- **2026-08-03 — contract 2.0.44 / V0-110B-2E-33:** Added an independently replayed, single-stage DIRECT_FALLBACK construction chain with seven exact owner-path shim sites and fail-closed Python-API spoof controls. The shim is not production fallback work and issues no formal accounting or terminal authority. A production successor must bind real fallback-ledger primitives under a new manifest version.
- **2026-08-03 — contract 2.0.45 / V0-110B-2E-34:** Replaced the seven-site shim with real exact-fallback ledger primitives, bound one issuer-created ledger to the frozen search invocation, required event acknowledgement before counter mutation, and independently reconciled the 208-event H1 transcript at search finish and completion. The slice remains construction-only and emits no shared-resource receipts, formal V6 vector or terminal.
- **2026-08-03 — contract 2.0.46 / V0-110B-2E-35:** Reissued the canonical H1 pre-execution authority from durable proof/current identity, replayed the typed preselection access log and froze an exact 182-leaf/eight-axis V6 finite admission candidate. All nine shared caps remain unenforced by the selected runner, so execution, formal actual-compliance and every Gate remain locked.
- **2026-08-03 — contract 2.0.47 / V0-110B-2E-36:** Added an issuer-owned one-shot construction admission authority for all nine V6 shared-resource paths. SUM work is reserved before side effects and conservatively settled on unverifiable failure; MAX working and distinct-payload mounted peaks are retained; staging is restricted to named sandbox COPY/BIND ingress; every admission adds one nonrecursive cap check. External issuer seals reject budget forks, object forgery, mutation, stale/foreign capabilities and callback attempts to erase work, while protocol failure still permits sealed mount cleanup. The source-site IDs remain construction-only and semantically unverified, no formal V7 route decision or production owner consumes the session, and no CounterRecord, vector, terminal or Gate is issued.
- **2026-08-03 — contract 2.0.48 / V0-110B-2E-37:** Froze the exact nine-path successor-source and typed aggregate-formula schema without issuing numeric operands or an upper. Added an independently replayed manifest-bound cap-profile join that derives all site IDs internally and rejects exact-manifest/fake-site splicing. Production wiring, semantic cardinality, formal V7 routing, vectors, terminal authority and every Gate remain blocked.
- **2026-08-03 — contract 2.0.49 / V0-110B-2E-38:** Added a production-only, permanently `V7_AUTHORITY_PENDING` shared-cap boundary. Its exact immutable tuple exposes nine non-callable pending sentinels and no private live kernel; receipt/event/pair domains are non-mintable. Production methods may appear only behind a later independently verified V7 adapter, so all execution and Gate locks remain unchanged.
