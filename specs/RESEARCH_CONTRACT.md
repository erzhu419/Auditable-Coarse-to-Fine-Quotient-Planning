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
- **V0-038 feature-realized LMB RAPM slice:** the query-free exhaustive selection of
  human-readable current-state feature coordinates and rational threshold atoms that
  exactly realizes the LMB behavioural quotient on one frozen training coverage and
  serves two in-coverage queries. It is not the aggregate Phase 3/human-grammar Gate.
- **V0-039 direct homomorphism synthesis slice:** the target-free direct verification
  of exact state-action homomorphism candidates drawn from fixed LMB state/action
  grammars over one exact finite coverage. It is not feature invention, learned
  dynamics or an aggregate Gate.
- **V0-040 prior-guided held-out exact-audit control:** a non-blocking control in
  which exact, distinct source coverages must unanimously support one existing
  fixed-grammar hypothesis before it can be proposed to a coverage-ID-held-out target.
  Target exact audit is the sole acceptance authority; this is not a sample-efficiency
  or transfer/generalization Gate.
- **V0-041 generated-coordinate exact synthesis slice:** exhaustive direct
  homomorphism synthesis over coordinate ASTs instantiated from a fixed typed LMB DSL.
  It removes V0-039 named-feature inputs, but not human production templates, full
  exact-kernel access, finite coverage, or the later partial/learned-dynamics problem.
- **V0-042 observation-log partial RAPM slice:** a four-input, kernel/query-blind
  construction from one externally allowlisted pre-query observation-authority graph,
  fixed manual coordinate ASTs and deterministic semantics. It retains every missing
  legal row as joint-simplex uncertainty and rebuilds every Portable-model relation;
  it is conditional in-memory authority, not automatic coordinates, observer-truth,
  public transport, a plan/certificate, exact quotient or aggregate Gate.
- **V0-043 robust fixed-plan audit slice:** a query-scoped, source-first exact replay of
  one supplied deterministic contingent plan against the conditional V0-042 partial
  RAPM. It may certify that fixed plan or emit a nonauthorizing failed-proof hint; it is
  not a planner, optimality/infeasibility proof, causal/local-recovery authority or
  aggregate Gate.
- **V0-044 bounded partial-model plan-proposal slice:** a query-scoped, source-first
  exhaustive producer over the finite V0-042 partial RAPM. It ranks internally audited
  deterministic plans under a fixed cap, but the selected plan still requires an
  independent V0-043 audit. It is not certificate, feasibility/infeasibility, J0,
  local-recovery, scale, sample-efficiency/economics or aggregate-Gate authority.
- **V0-045 observation-only typed-coordinate partial-RAPM slice:** a query-free,
  kernel-free exhaustive selection of coordinate programs from one fixed human typed
  DSL over an already-symbolized, externally allowlisted finite observation graph. It
  emits a reusable log-conditional partial RAPM and feeds typed V0-044/V0-043 consumers;
  it is not raw symbolization, unknown-DSL invention, learned/neural latent dynamics,
  statistical consistency, generalization, sample efficiency or an aggregate Gate.
- **V0-046 query-local evidence/refinement slice:** full-chain authorization of exactly
  four individually necessary exact rows for the canonical H1 failed certificate,
  followed by an immutable query-owned V2 model, abstract replanning, and independent
  certification. It is not general causal minimality, multi-step recovery, base
  promotion, learned acquisition/dynamics, sample efficiency or an aggregate Gate.
- **V0-047 multi-step query-local model-evolution slice:** two proof-authorized
  evidence rounds on the canonical H2 path, including evidence-derived boundary
  registration, reuse of the fixed V0-045 coordinates, immutable V3 epochs,
  model-only replanning, frontier movement, and independent final certification.
  It is not cross-query promotion, learned/statistical dynamics, general causal
  minimality, sample saving, or an aggregate Gate.
- **V0-048 preregistered cross-query promotion slice:** a target-blind V0-047
  source acquisition followed by complete-model promotion into a scope-limited V4
  reusable epoch and a distinct held-out H1 model-only certificate. A matched cold
  evidence trace remains evaluation-only. It is not unrestricted promotion,
  statistical generalization, learned dynamics, sample efficiency, or an aggregate
  Gate.
- **V0-049 preregistered held-out family amortization slice:** one complete V0-047
  promotion into a separate three-state V5 scope, followed by ten preregistered
  logical occurrences whose model-only certificates are paired with source-blind
  complete H1 ground planners. It freezes native vector prefix relations and source
  amortization mechanics, not a scalar break-even, statistical generalization,
  environment-sample reduction, tax operator, or aggregate Gate.
- **V0-050 exact identity-bound certificate memoization slice:** the unchanged
  V0-049 ten-occurrence workload executed with an initially empty, append-only,
  role-separated exact proof cache and a strict no-reuse control. It preserves all
  20 plan candidates and ten independent selected-plan certificates while reducing
  complete audit executions from 30 to nine through 21 exact-identity hits. It is not
  cross-identity incremental proof, persistent cache authority, sample reduction,
  total-work/economics evidence, or an aggregate Gate.
- **Phase 3C local-recovery slice:** the V0-029 certificate-triggered, isolated,
  query-owned overlay positive control over an immutable reusable RAPM; it is not the
  aggregate Phase 3 or economics Gate.
- **Phase 3D general local-recovery Gate:** the V0-030 finite, cap-aware positive
  control for slack-aware causal localization, sparse worker authority, and joint
  deterministic value/risk composition; it is not the aggregate Phase 3 or economics
  Gate.
- **Phase 3E accounted dynamic-routing profile:** the contract-`1.0.0` consumer of
  frozen RAPM, failed-certificate, causal, and route-cardinality evidence. It freezes
  a route decision before route-specific execution, preserves native work provenance,
  and remains nonofficial until every V0-032 counter, verifier, failure-path, and
  access-order acceptance test passes.

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

### Contract 0.9.0: Phase 3D general local recovery

Execution profile `phase3d_general_local_recovery` resolves `V0-RISK-004..006` in a
registered finite scope. Its operational input is a fully verified frozen Phase 3C
bundle supplied through `--phase3c-bundle`. The runner binds the source RAPM,
`BuildEpoch`, run, manifest, locality, authorization, and local pre-certificate without
calling the Phase 3C world constructor, `SuiteBuildCoverage.from_queries`/transition
closure, partition/quotient/RAPM builders, or ground `U_all`; every such counter, plus
binding and pre-authorization kernel steps, is zero. The binding pass captures the
complete registered 144-action catalogue. All causal/ancestor legality and capability-
cost lookups before authorization use this frozen catalogue rather than new ground
calls.
The source pre-certificate freezes the action-unrestricted reward upper bound. The
trusted authority then constructs the exact selected-policy
reward-min/risk-max Bellman circuit, retains every tied active extremizer, and searches
ambiguity-discharge sets under an explicit cap. One transaction can authorize only the
current earliest `DirectBad` antichain; a deeper causal layer requires a complete
post-audit and a new occurrence-bound transaction. On safe-chain this selects only the
common eight-state cell and reduces authorization from Phase 3C's `40/160` records to
`24/96`, with a `16/64` worker slice. The former is authorized capability scope, not a
claim that all 24 pairs/96 outcomes were executed.

Before isolation, a trusted compiler eliminates the four-node/twenty-realization
source boundary into a `SparseRobustAffineCapability` with one frontier input, zero
exit ports, one reward-min form, and one risk-max form. Minimality means minimum form/
port representation over the fully enumerated finite admissible domain in the frozen
sparse min/max-affine class. The source boundary and equivalence/necessity evidence are
available in the trusted bundle for audit, but the isolated worker receives exactly
three mounted inputs: sparse capability, sparse slice, and occurrence-bound request.

The standard-library worker jointly enumerates deterministic assignments across every
authorized cell/member, composes cell values as `(min reward,max risk)`, and Pareto
prunes only complete root points. It exhausts every lower-cardinality subset before
accepting a cardinality-minimal result; caps and cap-exhausted statuses are explicit.
Safe-chain exhausts 257 assignments and the operational sound post-audit reproduces
reward lower `3/64`, failure upper `397/20000`, regret upper zero, and the immutable
RAPM/BuildEpoch. Its exact-hybrid fields are `null` with status
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`; the operational runner cannot perform
an exact lift. The standalone verifier reconstructs and exact-lifts only in its
evaluation lane, obtaining exact failure `317/16000` from eight patched and twelve
retained abstract decisions before it opens J0. A separate two-cell/two-member control
exhausts 25 assignments and reaches `(1,1/25)` at thresholds `(3/4,1/20)`, while
independent minimum-risk selection returns value zero.
Passing returns `PHASE3D_GENERAL_LOCAL_RECOVERY_PASS`,
`GENERAL_LOCAL_RECOVERY_GATE_PASS`, `PHASE3_AGGREGATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

Ground dynamics enter the operational path only after the abstract full-plan proof
fails and only through the authorized occurrence-bound slice. Frontier materialization
steps exactly 16 pairs and observes 64 positive-probability outcomes. The final sound
post-audit receives `PatchedAuditKernelView`, may step exactly the eight overlay pairs,
and keeps unpatched behavior in the abstract envelope. Thus operational ground work is
exactly `16+8=24` step calls, with zero extra accounting calls and zero calls outside
authorized or patched pairs. The output embeds byte-identical source RAPM/epoch
documents plus the Phase 3C run, manifest, locality, authorization, and local pre-
certificate with content/hash links. The independent verifier's authoritative rebuild,
exact lift, and J0 checks are evaluation-only and cannot be counted as operational work.

This supports exact finite-domain causal authorization, sparse authority compilation,
and joint value-risk local repair under declared caps. It does not support automatic
predicate/quotient discovery, one-shot dependent-horizon repair, an information-
theoretically minimum encoding, uncapped scalability, economics, learning, or cross-
domain empirical generality. Workload economics/dynamic routing is the next Gate;
learned proposal/model synthesis follows it.

### Contract 1.0.0: accounted dynamic routing

Ledger V0-032 freezes profile `phase3e_accounted_dynamic_routing_v0`. The scientific
center remains an automatically synthesized reusable abstract world model in which
multi-step contingent planning occurs primarily. Ground distinctions may be reopened
only after that model cannot certify the current plan at the registered value/risk
thresholds. Phase 3E accounts and routes that recovery; it does not replace the
world-model objective with a local-repair or accounting objective.

`WorkVectorV1` is the complete native ledger. Operational, evaluation, provenance,
and diagnostic lanes remain distinct, and local, fallback, rebuild, failed-attempt,
verification, process, I/O, and peak-capacity leaves retain their source. The shared
comparison profile projects every operational charged leaf exactly once onto eight
axes: kernel transition calls, registered nonkernel compute events, process launches,
read bytes, staged bytes, output bytes, peak mounted bytes, and peak working bytes.
Additive traffic and peak capacity are never summed together. Evaluation-only replay
never enters an operational route vector.

At one decision point only marginal `U_local_attempt` and `U_direct_fallback` are
compared. Local is selected only under strict componentwise dominance; equality,
incomparability, missing/stale/invalid evidence, a profile mismatch, or any causal
outcome other than `FOUND` selects fallback. Common-prefix work is charged once outside
both marginal uppers. A failed local attempt closes its transaction with its actual
work intact; any fallback begins a new decision point.

Every upper, cap, cardinality proof, frontier, causal result, decision, transaction,
work vector, projection, attestation, and terminal artifact is typed and content
addressed by full SHA-256 over `domain-tag || 0x00 || canonical-json`. Route uppers bind
all query/build/plan/threshold/occurrence/attempt/decision/transaction/frontier/cap/
cardinality/formula/profile identities. A changed identity makes the upper stale even
when its numeric vector is unchanged. Typed `NOT_APPLICABLE` records are not missing
fields and cannot replace a required local identity.

The registered profile permits at most two continuous local transaction indices and
uses the exact V0-032 causal, materialization, compiler, solver, rational, and
post-audit caps. A trusted replay derives the budget outcome from unique native
records; worker budget labels are untrusted. Tight route uppers are computed from
frozen pre-execution cardinalities and exact formulas capped by the registered hard
limits, never by substituting a broad hard cap.

The operational protocol is estimate-before-execute. Before the content-addressed
route decision freezes, no ground transition enumeration, local materialization,
compiler, local/fallback worker, stitch, or post-audit is permitted. A fallback-selected
path has native-zero local execution leaves and no local execution artifacts. A local
path may materialize, compile and launch only after the decision; it either closes
after a negative worker result or, for a candidate, continues through exact-bound
stitch and sound post-audit artifacts. Preselection reads bind the exact failed-
certificate and action-catalogue identities alongside every other frozen input. The
charged semantic authority is the exact decision/causal/two-upper/two-cardinality
dependency closure, not an arbitrary set of attestations. Phase 3B/3C/3D full solver/J0/lift reconstruction belongs to standalone
evaluation verifiers; the 1.0.0 operational path cannot replay it on the host.

Terminal authority is the typed `(terminal_scope, terminal_class, terminal_code)`
triple. Feasible plan, exact infeasibility, and noncertificate attempt closures are
disjoint. `FALLBACK_CAP_EXHAUSTED`, protocol/integrity failure, rebuild required, and
attempt-budget exhaustion never become infeasibility certificates. Every registered
logical occurrence stays in the closure, certificate-coverage, and future economics
denominators, including all failed local, fallback, rebuild, and retry work.

Contract 1.0.0 freezes no scalar cost: `official_scalar_cost` and
`official_N_break_even` are null and the scalar Gate is `NOT_RUN`. Until the native
counter registry covers every operational and failure path, the no-full-replay
migration, typed attestations, exact projections, trusted cap replay, terminal closure,
access-order attacks, and independent verifier all pass, the only valid status is
`official_execution_allowed=false`, `COUNTER_COMPLETENESS_GATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

V0-033 closes the four former scoped P0 contract gaps with exact two-stage non-self-
referential accounting, runner-owned continuation `WORK_VECTOR` authority, a
content-addressed runtime tree and single-use post-freeze executor factory, and
whole-occurrence typed failure/aggregate-terminal replay. These are four scoped
interface closures, not completion of the Phase 3E Gate or of automatic reusable-world-
model synthesis. Their current strict evidence includes manifest-derived
`RuntimeFactoryCardinalityV1` in route uppers, a success receipt bound to the final
access log, `SealedExecutorFailureMergeProofV1` over exact factory/delegate/merged
partials, and rejection-only `PARTIAL_ACCOUNTED_COMMON` preservation of already
observed verifier work. The foregoing official status remains locked because exact
cached-infeasibility proof replay, complete all-path native hash/I/O/runtime
instrumentation, a registered dependent-horizon transaction-2 fixture, semantically
authorized rebuild/retry, integrated campaign/workload execution, and independent
semantic/campaign bundle verification remain absent. V0-034--V0-037 add the model-only
audit/handoff, scoped LOCAL occurrence closure, partial preparation accounting,
control-plane rebuild/retry mechanics and 54-role accounting/topology transport, but
none opens an official Gate.

### Contract 1.1.0: automatic feature-realized reusable LMB RAPM slice

Profile `lmb_feature_realized_reusable_rapm_v1` is an additive, single-domain
construction vertical slice. It advances the primary world-model objective by
automatically selecting a minimal feature/predicate realization from a fixed human-
readable grammar. It does not alter V0-028's two-domain Phase 3B campaign or any Phase
3E route/accounting contract.

The production synthesis inputs are exactly an exact `LMBKernel` and immutable
`SuiteBuildCoverage[LMBState]`. The complete canonical `FeatureRegistryV1` and its
coverage/structure/registry-bound `SynthesisSpecV1` are constructed internally; the
production API accepts no registry/spec argument, preventing a caller from encoding a
query bit by selecting a subset that changes exact versus nonexact outcome.
`QuerySpec`, J0, Q-values, value or Pareto frontiers, selected policies, and held-out
data are forbidden parameters and information channels. Restricted registries are
accepted only by the explicit non-production negative-control API and cannot mint a
production claim. Construction may inspect the exact one-step kernel, structural LMB
configuration, frozen training coverage and registered current-state features.
The implementation dependency audit excludes planning, J0/Q/value/policy,
held-out/evaluation-oracle and Phase-3A construction imports. It explicitly permits
`build_exact_behavioral_quotient`: that exact ground-model behavioural oracle is the
realization target, so this slice has not removed target/signature supervision.

The canonical exact-rational feature grammar contains eleven uniquely sorted names:
`action_count`, `branching_count`, `buffer_occupancy`, `capacity_slack`,
`capacity_slack_count`, `immediate_release_liquidity`, `match_debt_mean`,
`match_debt_min`, `match_debt_nonzero_types`, `max_match_debt`, and
`remaining_object_count`. Each definition binds its semantics ID/text, the current
adapter implementation SHA-256, and threshold generator
`adjacent_distinct_value_midpoints_v1`.

V1 starts from the three terminal-kind cells (`active`, `failure`, `success`) and
enumerates every feature subset by feature count and lexicographic names. With eleven
features the complete candidate trace contains `2^11=2048` candidates under cap 4096.
For each selected feature, all distinct exact values on active covered states are
sorted and every adjacent pair generates one reduced-rational midpoint atom with
operator `<=`. Atoms and splittable active cells are processed canonically; empty
branches are skipped.

The realization obligation is the query-neutral complete exact controlled one-step
behavioural quotient over that same frozen coverage. This target uses full exact ground
behaviour and is neither a partial nor learned dynamics model. A feature candidate is
successful only when its entire partition signature equals the target. The exact
selector minimizes `(feature_count, applied_split_count, selected_feature_names,
final_partition_id)`. The registered golden is:

```text
selected_features = (action_count,)
selected_thresholds = (3/2, 5/2)
applied_split_count = 2
ground_state_count / quotient_cell_count = 25 / 5
active_ground_state_count / active_quotient_cell_count = 18 / 3
target_partition_id = realized_partition_id
envelope_is_singleton = true
```

Feature registry, synthesis spec, predicate atoms/tree, candidates and mismatch
witnesses, complete candidate trace, and realization certificate are strict
domain-separated content-addressed documents. Their V1 schemas/domains and the frozen
registry semantics, information channels, target/generator/order/selector, certificate
claim and lock constants cannot be changed by coherent re-signing. The feature adapter
implementation digest is independently frozen and checked before registry creation.
Document parsers require exact canonical JSON field types, including list/string
distinctions, and result verification requires exact nested runtime graph types; proxy
objects with honest serialized bytes but altered behaviour are rejected. The portable
model retains its ordinary RAPM content ID. Independent verification reruns every
subset/atom/tree and rebuilds the exact behavioural target partition, refinement trace,
semantic adapter and quotient model; it also rebuilds the candidate trace,
certificate, realized partition/quotient, and portable model plus registry. Canonical
reordering is stable, and coherently re-signed semantics, trace, target/realized model,
portable registry, claim or Gate substitutions fail replay.

If no subset realizes the target, the only semantic outcome is
`NO_EXACT_FEATURE_REALIZATION`. The result carries a content-addressed mismatch
witness and publishes no predicate tree, realized partition, quotient models,
portable build or realization certificate. `TARGET_SEPARATED_FEATURE_ALIASED` records
two states merged by the candidate and separated by the target;
`TARGET_MERGED_FEATURE_SEPARATED` records two states separated by the candidate and
merged by the target. Oversplitting is a typed negative mismatch, not an invariant
failure and not a feature-realization success.

The 36-state seed-0 canonical-initial negative control is distinct from the 25-state
positive golden. Its exact behavioural target has 11 cells, its `action_count`-only
candidate has 7 cells, and its complete trace contains both mismatch-witness kinds;
the selected unresolved witness is `TARGET_MERGED_FEATURE_SEPARATED`.

The explicit negative-control API may also find an exact restricted subset, but that
control cannot alter the complete canonical production registry/trace or production
verifier expectation and cannot be cited as the production profile.

The positive model is serialized once and loaded unchanged by fresh Python planner
subprocesses for two distinct QuerySpecs inside the frozen coverage: one `H=3`,
match-plus-clear, `delta=1/20` query and one `H=2`, match-only, `delta=1/10` query. This
is two-query in-coverage portable reuse; it is not a sealed production runtime, a
preregistered held-out evaluation, or evidence of held-out generalization.

The allowed claim is precisely automatic selection of feature coordinates and rational
threshold atoms from this preregistered LMB grammar to exactly realize a reusable,
query-neutral world model on the frozen training coverage. It does not support feature
invention, incomplete/learned dynamics, oracle-free unknown-quotient discovery,
unknown-domain or scalable discovery, cross-domain/shared-coordinate conclusions,
held-out generalization, or any aggregate Phase 3, Phase 3E, counter-completeness,
workload-economics, transfer or learning Gate.
`official_execution_allowed=false`; official scalar cost and break-even remain null,
and both registered Gates remain `NOT_RUN`.

### Contract 1.2.0: direct exact homomorphism synthesis inside fixed LMB grammars

Profile `lmb_direct_exact_homomorphism_v1` is the additive V0-039 construction slice.
Its production entry point `synthesize_direct_lmb_homomorphism_v1(kernel, coverage)`
accepts only an exact `LMBKernel` and frozen `SuiteBuildCoverage`. It internally fixes
the complete state/action registries and `production_full_grammar_v1` spec. It imports
neither V0-038 feature realization nor the behavioural target builder and accepts no
`BehavioralActionSignature`, behavioural quotient target, query, J0, Q/value/frontier,
policy, planning or held-out channel. Internally computed exact raw one-step signatures
are proof records, not a preconstructed target or candidate label.

The state grammar contains V0-038's eleven exact-rational current-state coordinates.
The action grammar contains exactly `completes_match`: one iff the selected tile's type
currently has buffer count two. Both implementations are independently SHA-256-anchored
under a frozen implementation epoch. State subsets generate adjacent-value rational-
midpoint `<=` trees; action subsets generate state-dependent semantic labels and a
uniform concretizer over distinct matching ground actions. Production enumerates all
`2^11 * 2 = 4096` candidates under cap 4096.

A candidate is an exact homomorphism only if direct kernel replay proves all of the
following without reference to a target partition:

1. every member of each active state cell exposes the same semantic-label set;
2. all ground actions aliased to one label at one state have identical exact expected
   reward-feature, failure, termination and successor-cell distributions before any
   mixture; and
3. the same label has that identical exact one-step signature across all members of
   the cell.

Typed counterexamples are `LABEL_SET_MISMATCH`, `WITHIN_STATE_ACTION_ALIAS` and
`CROSS_STATE_LABEL_DYNAMICS_MISMATCH`. Exact candidates are selected by minimum state-
feature count, action-feature count, split count, state names, action names and
partition ID. The canonical golden is:

```text
status = EXACT_DIRECT_HOMOMORPHISM
required/evaluated candidates = 4096/4096
selected_state_features = (action_count,)
selected_action_features = (completes_match,)
state_thresholds = (3/2, 5/2)
ground/active state count = 25/18
quotient/active cell count = 5/3
abstract_entry_count = 4
envelope_is_singleton = true
action_alias_checked_before_mixture = true
```

Restricted grammars are available only through the non-production control API. No
exact candidate gives `NO_EXACT_DIRECT_HOMOMORPHISM`; insufficient cap gives
`CANDIDATE_CAP_EXHAUSTED` with zero evaluated candidates and one
`CANDIDATE_CAP_INSUFFICIENT` witness. A restricted control that finds an exact candidate
returns `RESTRICTED_CONTROL_EXACT_FOUND` and deliberately publishes no tree,
partition, semantic adapter, quotient, portable model or certificate. The production
verifier rejects it. A separate role-locked verifier is the only authority for
negative-control results. The production verifier also rejects restricted-control
provenance, incomplete canonical registries and duck-typed result objects, so a
control result cannot be re-signed into production evidence.

State/action registries, spec, predicate tree, semantic labels and exact signatures,
witnesses, candidates, full trace and certificate are domain-separated content-
addressed artifacts. Canonical JSON types, exact nested runtime types, state/action
implementation anchors and complete independent reconstruction reject coherent
re-signing, list/string malleability, nested proxies, trace deletion and source
substitution. A fresh process with the behavioural module poisoned still imports and
constructs the canonical result. Only after construction, evaluation-only comparison
may load the old behavioural oracle; it reproduces the same partition and quotient
model but supplies no construction/certificate authority. One unchanged portable model
also serves the registered `H=3` match-plus-clear and `H=2` match-only queries in fresh
planner processes.

V0-039 supports direct exact state-action homomorphism synthesis from fixed human-
readable grammars on one exact finite LMB coverage without construction-time
behavioural target/signature dependence. It still assumes a complete exact ground
kernel, exact finite coverage and preregistered feature semantics. It does not support
feature invention, partial/learned dynamics, unknown-domain or scalable discovery,
held-out/cross-domain generalization, or any aggregate Phase 3, Phase 3E, counter-
completeness, workload-economics, transfer or learning Gate. Official execution stays
false, scalar cost and break-even stay null, and both Phase 3E Gates stay `NOT_RUN`.

### Contract 1.3.0: source-unanimous proposal with held-out exact authority

V0-040 is an additive, non-blocking proposal/authority control. Production profile
`source_unanimous_exact_v1` consumes exact source-candidate evidence over the complete
V0-039 4096-hypothesis catalogue. `build_structural_hypothesis_prior_v1` has no
caller-selected preferred hypothesis: every source candidate must be exact and all
sources must name the identical hypothesis, otherwise production-prior construction
fails. The canonical source task/coverage pairs use masks 11 and 13; target task and
coverage use mask 7. Target task and coverage IDs must be absent from all source
records. The structural LMB kernel may be shared; held-out status is coverage-ID exact,
not a false claim of a distinct environment family.

The production prior proposes the unanimous
`(state=(action_count,), action=(completes_match,))` hypothesis. Its positive
`wide_tail_base_mass` gives every member of the catalogue nonzero recorded mass, but
the artifact explicitly fixes `broad_support_metadata_only=true` and
`executed_candidate_schedule=false`. V0-040 executes exactly one target proposal. It
does not implement a target candidate schedule, learned ranking, posterior update or
wide-tail enumeration, and broad-support metadata supplies no coverage or
sample-efficiency claim.

The proposal records `proposal_is_acceptance_authority=false`. Only
`exact_target_ground_homomorphism_audit_v1` can accept it. On success, exact target
replay builds the tree, partition, semantic adapter, quotient and portable RAPM. The
certificate fixes `global_minimality_verified=false` and also denies feature invention,
sampled dynamics, sample efficiency and official-Gate claims. QuerySpec, J0, Q/value,
policy, target behavioural signature and planning results are absent from construction.
The independent verifier rebuilds every source audit and the target audit/model from
the bound kernel and coverages, rejects duck types and content re-signing, and one
unchanged accepted target RAPM serves two distinct in-coverage queries.

The positive telemetry is exact and lane-separated:

```text
source tasks / target candidate evaluations = 2 / 1
source-offline exact-kernel calls / unique rows / eligible rows = 14 / 14 / 14
target exact-kernel calls / unique rows / eligible rows = 21 / 7 / 7
source and target interaction samples = 0
acquisition_kind = EXACT_KERNEL_QUERY
```

Exact-kernel calls are never relabelled as samples. Repeated calls and unique rows are
both retained. This is telemetry for later diagnosis, not evidence that the prior
saved interactions or total work. The separate profile
`nonproduction_external_control_v1` is built only through an explicit external-control
API and is accepted only by its role-locked control runner/verifier. The empty
hypothesis takes three exact-kernel calls over three observed of seven eligible rows,
returns `PRIOR_MISMATCH_FALLBACK_REQUIRED`, publishes no model/certificate, and never
claims infeasibility. Production runners/verifiers reject that profile.

The companion `SAMPLE_EFFICIENCY_PROTOCOL.md` freezes evidence terminology and prior
authority but deliberately does not block the construction line:

```text
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

No scalar, break-even or tax-reduction operator is frozen. Such an operator is deferred
until the real mainline access pattern identifies the dominant evidence cost.

### Contract 1.4.0: generated typed-coordinate programs

V0-041 registers production profile `lmb_structural_typed_expression_dsl_v1`. Its API
is exactly `synthesize_generated_lmb_homomorphism_v1(kernel, coverage)` and accepts only
exact `LMBKernel` and `SuiteBuildCoverage` instances. QuerySpec, reward weights, J0,
Q/value, policy, behavioural target/signature, held-out data and caller-selected
features are forbidden. The module and serialized DSL registry contain neither of the
V0-039 named feature strings `action_count` and `completes_match`.

A preregistered typed production-template instantiator starts from the raw primitives
`legal_actions`, `remaining_tiles`, `buffer_counts`, `buffer_capacity`,
`selected_tile_type`, and integer literals. With the frozen cardinality, vector,
arithmetic, indexed-buffer and equality templates it emits exactly eight canonical
state ASTs and four canonical state-action ASTs, under depth and registry caps. This is
typed program generation inside a fixed human DSL, not free synthesis of unknown
semantics.

Production exhausts every subset pair:

```text
state programs / action programs = 8 / 4
required / evaluated candidates = 4096 / 4096
selected state AST = cardinality(legal_actions)
selected action AST = buffer_at_type(buffer_counts, selected_tile_type)
thresholds = (3/2, 5/2)
ground/active states = 25/18
quotient/active cells = 5/3
abstract entries = 4
envelope_is_singleton = true
```

Each candidate is judged only by direct exact-kernel label-set, pre-mixture within-state
action-alias and cross-state same-label dynamics obligations. Selection minimizes
state-program count, action-program count, split count, then frozen AST size/depth/
operator order, IDs and partition ID. Expression ASTs, DSL registry, synthesis spec,
predicate tree, witnesses, complete trace and certificate are domain-separated content
objects. Frozen evaluator, enumerator, compiler and audit implementation digests prevent
source substitution. The independent verifier reconstructs the raw-program registry,
all 4096 candidates, selected quotient and portable RAPM.

The `candidate_cap_one` control requires 4096 candidates, evaluates zero and emits
`CANDIDATE_CAP_INSUFFICIENT`; the state-only DSL control evaluates 256 candidates,
returns `NO_EXACT_GENERATED_HOMOMORPHISM`, and publishes no model/certificate. AST type,
duck-result, trace, content and implementation-digest attacks fail closed.

V0-041 is the current mainline construction slice, but its evidence remains finite and
exact. It does not establish unknown-semantic invention, neural/partial/learned
dynamics, larger or unknown-domain scalability, held-out/cross-domain generalization,
sample efficiency, or an aggregate Phase 3/Phase 3E Gate. All prior locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```


### Contract 1.5.0: allowlisted observation-log partial dynamics

V0-042 registers profile `lmb_deterministic_observation_partial_rapm_v0`. Builder and
verifier accept exact `ObservationLogManifestV1`, `FrozenCoordinateProposalV1`,
`DeterministicObservationProfileV1`, and `PreregisteredObservationAuthorityV1` objects;
the verifier additionally accepts the claimed result. Kernel, QuerySpec, J0, Q/value,
policy, planner, target quotient/signature and held-out results are absent.

The external allowlist is the source-of-truth boundary. Canonical authority
`5aac3e8f1e7b8b2af4cafe50a8b54c25c21008d2b9fccd4aaaeebc3ab79df825` binds one
pre-query acquisition manifest, structural/environment/profile identities, eight
literal states, eleven complete legal state-action rows/catalogues, seven distinct
event receipts/observations, the log and complete evidence ledger. The row set is not
an initial-state transition closure. Acquisition and construction query-input counters
are independently zero. The evidence ledger has all twenty lane/class cells:

```text
offline_source / OFFLINE_LOGGED_OBSERVATION = 7
remaining 19 cells = observed native zero
```

Seven rows are deterministic observed singletons; four rows retain unit unknown mass.
Every ambiguity exposes a joint outcome atom set containing continuation to each active
cell and the external boundary, terminal success, and terminal failure. One simplex
couples those atoms: continuation plus terminal is one, failure implies terminal, and
unknown mass is allocated once. Marginal successor/failure/terminal intervals cannot
be summed or selected independently. An external successor is disjoint from all
registered states and is active, nonterminal and nonfailure only.

`PortablePartialRAPMV1` does not trust its own derived bytes. It reconstructs cells,
semantic actions, state/action-derived ground-row IDs, complete concretizer/realization
coverage, support rows, observed/missing status partitions, and exact weighted
ambiguities from ground rows. Distinct-action concretizers are uniform. Reward-cap,
known-reward, reward-interval, known-successor and successor-interval names are unique.
The model binds `semantics_horizon_cap=6`, registered-catalogue query support, no
transition closure, and no exact-quotient/plan/infeasibility claim. Outside support or
horizon requires rebuild or fallback.

The authority graph is retained in memory and exact-typed:
`in_memory_exact_graph_required=true`, `transport_authority_claimed=false`. Domain-
separated hashes protect bytes and bindings only. Observer honesty, catalogue truth,
deterministic stationarity and public authenticity remain external assumptions; a new
fixture needs an explicit authority-registry and contract revision. The fixed
`legal_action_count`/`completes_match` proposal is manual and preregistered, so V0-042
does not demonstrate coordinate synthesis, learned dynamics, statistical consistency,
generalization, planning, a plan certificate, infeasibility or sample reduction.

### Contract 1.6.0: conditional robust audit of a supplied partial-RAPM plan

V0-043 registers implementation schema `1.1.0` and profile
`partial_fixed_plan_robust_audit_v0`. The audit and verifier first invoke the complete
V0-042 source/model verifier on `ObservationLogManifestV1`,
`FrozenCoordinateProposalV1`, `DeterministicObservationProfileV1`,
`PreregisteredObservationAuthorityV1`, and `ObservationPartialRAPMBuildV1`. Only after
that source graph passes may they read `FrozenPartialAuditThresholdsV1` or one
`FrozenContingentAbstractPlanV1`; the verifier alone also receives the claimed result.
No kernel, transition interface, ground solver, planner, J0, optimality or feasibility
oracle is imported or callable.

The plan is a supplied deterministic selector, not an audit output. Its stages are
exactly `0..H-1`; each stage assigns one legal semantic action to every active cell;
randomization is false; and model, thresholds and plan bind the same `H<=6`. Threshold
initial support is a sorted unit-mass distribution over exact registered active ground-
state IDs. Reward weights are exactly `match=1` and `terminal_clear=1`; normalized-
regret tolerance is in `{0,1/20}` and risk tolerance in `{0,1/20,1/10}`. The threshold
payload and ID bind exact `goal_id="default"`. Foreign strings, non-string values and
string-like duck objects raise `PartialSoundAuditInvariantViolation`; they are not a
second QuerySpec or a supported goal extension.

The canonical return-scale authority has ID
`6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98`. It binds the
canonical LMB `N=6` structural/environment/log/semantics/observation-authority/
acquisition-manifest identities, at most two match events, terminal-clear bonus upper
two, nonnegative reward basis and deterministic `R_max=4`. It is independent of the
chosen model/partition but must match that model's source ancestry and reward caps.
Changing the reward basis, scale or any bound identity requires a new preregistered
proof and contract revision.

The proof pipeline is:

```text
reconstruct hardened V0-042 source graph and Portable partial RAPM
-> validate registered thresholds, return proof and supplied complete plan
-> upper-bound unrestricted control from every registered ground-action row
-> robust Bellman replay of only the supplied plan under the joint simplex
-> enumerate reachable state/action/time proof obligations
-> enforce pointwise support regret, distributional risk and external coverage
-> emit fixed-plan certificate or earliest nonauthorizing failed-proof hint
-> independently recompute the complete result and compare canonical documents
```

The unrestricted comparator is an upper bound, not an optimal ground value. For every
initial support state, `InitialSupportPointRegretRowV1` records unrestricted upper minus
plan lower divided by `R_max`; all rows must pass. Distribution regret is reported only
as a diagnostic. Risk lower/upper is aggregated under `rho0`. Joint unknown mass is
allocated once in Bellman arithmetic. Per-destination reachability uppers may reuse the
same unknown mass only to expose possible obligations; they are not a probability
distribution. Any unknown row or known external continuation reachable under the
supplied plan with remaining horizon above one separately fails selected-plan external
coverage.

The minimum artifact graph is:

```text
FrozenPartialAuditThresholdsV1 -> RegisteredReturnBoundProofV1
FrozenContingentAbstractPlanV1 -> ContingentPlanStageV1/AssignmentV1
PartialFixedPlanRobustBoundsV1
  -> UnrestrictedGroundUpperRowV1
  -> PartialPolicyBoundRowV1
  -> InitialSupportPointRegretRowV1
PartialSoundAuditResultV1
  -> StateActionTimeObligationV1
  -> exactly one of PartialFixedPlanCertificateV1 /
                    PartialFailedProofFrontierV1
```

`CERTIFIED_FIXED_PLAN` requires value, risk and external-coverage obligations to pass
and binds every model/threshold/plan/proof/bounds/obligation/support-row identity. It
sets planning, optimality and infeasibility claims false. `FAILED_PROOF_FRONTIER`
selects the earliest relevant stage with reason `EXTERNAL_COVERAGE_ESCAPE`,
`UNRESOLVED_POLICY_PATH_DISTINCTION`, or `KNOWN_FIXED_PLAN_THRESHOLD_FAILURE`. Its
`NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1` sets local authorization, causal necessity,
causal sufficiency and infeasibility false. `unresolved_exposure_sum` is a sum of
representative proof exposures, never a probability.

The positive H3 observed-path control has unrestricted upper 4, supplied-plan interval
`[4,4]`, zero distribution and maximum support regret, failure `[0,0]`, external-
coverage pass, 33 unrestricted rows and `CERTIFIED_FIXED_PLAN` despite unrelated
missing rows. The H1 missing-state negative regression has unrestricted upper 3, plan
lower 0, normalized regret `3/4`, failure upper 1 and earliest
`(0,1,UNRESOLVED_POLICY_PATH_DISTINCTION)` frontier. Mandatory negative regressions also
cover a low-mass support point hidden by distribution averaging, an H2 external escape,
and a known-threshold failure with no selected missing row.

A self-signed source edit, unregistered/altered return proof, changed weights or
threshold registry, cell-as-ground-state support, foreign model/plan, noncontiguous or
over-cap plan, altered bounds/frontier, erased unknown mass, mutable/duck nested object
or coherently re-signed result is an invariant violation, not a normal negative
regression. V0-043 does not search for policies, authorize local recovery, prove model
exactness/closure, learning/generalization or sample savings, or open any official,
scalar, economics, counter-completeness, Phase 3 or Phase 3E Gate.

### Contract 1.7.0: bounded partial-model contingent-plan proposal

V0-044 registers implementation schema `1.0.0` and profile
`partial_model_contingent_plan_proposal_v0`. The production API is exactly:

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

Both paths reconstruct the complete hardened V0-042 source/model before reading any
threshold field. Production exposes no kernel, transition callback/interface, `J0`,
ground solver, feasibility oracle, second QuerySpec or caller-selected cap. The sole
threshold input already content-binds exact `goal_id="default"`; a foreign or non-string
goal is rejected before enumeration and cannot create a second QuerySpec or goal
profile. The private `_propose_partial_model_plan_nonproduction_cap_control_v1` and its
caller cap are a named control surface only; the public verifier rejects its result.

For every active abstract cell, `PartialPlannerCellActionDomainV1` freezes the complete
semantic-action set. With

```text
S = product_z |Abar(z)|
candidate_count = S^H
```

each candidate assigns exactly one semantic action to every active cell at every stage
`0..H-1`. If within cap, construction enumerates the complete deterministic product and
invokes V0-043 once per candidate. `PartialPlannerCandidateSummaryV1` binds each plan,
audit result, reward/failure bounds, distribution and maximum-support regret, risk-
feasible flag and selected-plan external-coverage flag.

The canonical selector is hierarchical:

1. `INTERNAL_V0043_AUDIT_PASS_REWARD_MAX`: among internal
   `CERTIFIED_FIXED_PLAN` results, maximize reward lower, minimize failure upper, then
   minimize plan ID.
2. `RISK_FEASIBLE_REWARD_MAX`: only when tier 1 is empty, apply the same key among
   candidates with failure upper at most `delta`.
3. `MIN_FAILURE_RISK_FALLBACK`: only when both earlier tiers are empty, minimize
   failure upper, maximize reward lower, then minimize plan ID.

The internal audit is selection evidence, not proposal authority. The result fixes
`proposal_is_certificate_authority=false`,
`selected_plan_requires_independent_v0043_audit=true`, false feasible-plan,
infeasible-query and optimal-ground-policy claims, and claim kind
`MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL`.

Production freezes candidate cap `65536` and cap-profile ID
`9176c40aec0b6ecb3c7645a61363cefa32d9d13396ab33ee70fb0238f171932b`,
with `caller_cap_allowed=false` and `production_claimed=true`. When the exact count
exceeds cap, construction returns `CAP_EXHAUSTED` after trusted source/context replay
and counting but before any candidate audit: evaluated/audit counts are zero, summaries
are empty, selection is `NOT_APPLICABLE`, enumeration is incomplete and the selected
plan is null. A private cap must satisfy `1<=cap<65536`, sets
`caller_cap_allowed=true`/`production_claimed=false`, and cannot be promoted.

`PartialModelPlannerTraceV1` records:

```text
fixed_plan_audit_count = candidate_evaluated_count
source_graph_reconstruction_count = 1 + fixed_plan_audit_count
external_transition_authority_calls = 0
ground_search_calls = 0
work_economics_claimed = false
```

These are finite model-side enumeration, source-reconstruction and audit counters. They
are neither environment interactions/generative samples nor evidence of sample saving,
sample-complexity improvement, complete operational accounting or economics.

The canonical H3 row has `S=2`, eight required/evaluated candidates, eight audits and
nine source reconstructions. Tier 1 selects plan
`1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc`
with reward `[4,4]`, failure `[0,0]`, zero regret diagnostics and internal
`CERTIFIED_FIXED_PLAN`; independent V0-043 replay reproduces that result/certificate.
The H1 missing-state row reuses the same partial-model/build IDs with distinct
threshold/result IDs, evaluates two candidates, selects
`MIN_FAILURE_RISK_FALLBACK`, has reward `[0,3]`, failure upper one, is not risk feasible,
and binds `FAILED_PROOF_FRONTIER/UNRESOLVED_POLICY_PATH_DISTINCTION` with local authority
false. The named cap-4 H3 control predicts eight candidates but records zero candidate
evaluations/audits, one source reconstruction, no summaries/plan and public-verifier
rejection.

The independent verifier reconstructs source/model, enumerates and audits the complete
within-cap plan set, reapplies tier/tie-break selection and compares canonical bytes.
Candidate order/summary/plan-ID/selection tampering, source/model/threshold/result
substitution, nested duck types, coherent re-signing, early threshold access,
kernel/ground/caller-cap injection and control-role promotion fail closed.

Passing proves bounded exhaustive model-only plan proposal for the registered finite
control. It proves neither certificate/feasibility/infeasibility, `J0` or ground
optimality, exact quotient/transition closure, automatic/unknown coordinate invention,
causal frontier/local recovery/fallback authority, learned/statistical dynamics,
generalization/transfer/scale, sample savings/economics, official execution nor any
Phase 3/3E/aggregate Gate. Cap 65536 is not a scalability result; every Gate lock stays
unchanged.

### Contract 1.8.0: observation-only typed-coordinate partial RAPM

V0-045 registers implementation schema `1.0.0`, typed V0-042 extension schema `1.2.0`,
typed V0-044 planner schema `1.1.0`, typed V0-043 audit-wrapper schema `1.2.0`,
and profile `lmb_query_free_observed_typed_coordinate_synthesis_v0`. Its producer has
exactly three inputs `(observation_log, semantics_profile, observation_authority)`;
the verifier adds only `claimed_result`. Both require the exact allowlisted V0-042
in-memory graph before any coordinate evaluation. No query, kernel, behavioural
target/signature, V0-041 result, caller registry/subset/cap, planner, audit, policy,
value/risk object, J0, ground solver or callback is accepted.

The fixed human DSL contains eight state and four state-action ASTs under a V0-045-
specific registry authority. A separate observation-only evaluator materializes
`FrozenTypedCoordinateValueTableV2` for all eight registered states and eleven legal
rows. Construction exhausts all `4096` subset pairs. Only seven observed rows support
congruence; four missing rows are neither equality nor mismatch evidence and remain
explicitly unknown.

Production requires exact member label-set equality, observed pre-mixture congruence,
one nontrivial observed alias, separation of a null/coarser observed conflict, point
identification and strict compression. Its frozen selector chooses
`cardinality(legal_actions)` and
`buffer_at_type(buffer_counts,selected_tile_type)`. The raw integer action value is
compiled to exact boolean atom `<=3/2`. This preserves, rather than revises, the V1
schema:

```text
PartialSemanticActionV1.label_values = nonempty tuple[bool, ...]
```

Boolean raw coordinates use identity atoms; integer coordinates use adjacent-value
midpoint atoms; the empty action subset uses one `UNIVERSAL_TRUE` boolean sentinel.
The selected model contains six total/four active cells, five abstract entries/actions,
six realizations, seven point rows and one four-row `UNOBSERVED_UNKNOWN` entry. Its
seven observed rows are singletons, its four missing rows have unit unknown mass, its
horizon cap is six, and it claims neither exact quotient nor transition closure.

`FrozenTypedCoordinateProposalV2`, the typed table and
`build_observation_partial_rapm_from_typed_values_v2` are deterministic internal
derivation artifacts, not authority. In particular the pure builder cannot establish
that a caller-supplied table actually came from the source or that opaque candidate/
trace IDs represent the exhaustive selector. Only
`verify_observed_lmb_partial_rapm_v1` may accept the full
`ObservedTypedPartialRAPMResultV1`; it reconstructs source values, all candidates,
selection, proposal, build, model, telemetry and certificate.

The typed V0-044 producer surface is exactly:

```text
propose_partial_model_plan_from_observed_synthesis_v2(
  observation_log,
  semantics_profile,
  observation_authority,
  observed_synthesis_result,
  thresholds,
)
```

Its verifier adds only the claimed proposal result. The proposer fully replays V0-045
once, freezes the verified portable model, then enumerates plans and invokes the shared
verified-model V0-043 core once per candidate. `retained_v0045_full_replay_count=1`,
`internal_audit_source_replay_count=0`, and
`fixed_plan_audit_count=candidate_evaluated_count`. Internal audit outcomes are
ranking evidence only; `selected_plan_requires_independent_typed_v0043_audit=true`.

The typed V0-043 public auditor accepts the same source and full V0-045 result plus one
threshold object and frozen plan. It independently replays the complete V0-045 chain,
then invokes the same bound core. `TypedPartialSoundAuditResultV2` binds the synthesis
result and certificate, coordinate proposal, partial build, model, thresholds, plan and
unchanged inner V0-043 result. No bare portable model, proposal, value table, pure-build
result or caller verifier can substitute for this boundary.

Canonical downstream controls are:

```text
H3 observed: S=2; plans/audits=8/8; reward=4; failure=0;
             independent typed V0-043=CERTIFIED_FIXED_PLAN
H1 all-missing: plans/audits=2/2; reward=[0,3]; failure upper=1;
                independent typed V0-043=FAILED_PROOF_FRONTIER;
                reason=UNRESOLVED_POLICY_PATH_DISTINCTION;
                local recovery authorized=false
```

Historical manual V0-042--V0-044 APIs and artifacts remain byte-compatible. The frozen
V0-045 result/model IDs are
`4834efc30b9ae292e33f83932525195df1997ae31f7c7898b452b6175815ded2` and
`1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18`;
the complete typed identity table is normative in
`specs/OBSERVED_TYPED_COORDINATE_SYNTHESIS.md`.

Contract 1.8.0 proves fixed-DSL discovery over already-symbolized logged states/actions
only. It does not prove raw observation symbolization, neural/continuous latent-state
learning, unknown primitives/operators/DSL, an exact or true latent model, observer
truth, ground optimality/infeasibility, statistical consistency, held-out/cross-domain
generalization, scale or sample saving. V0-046, frozen below, implements the separate
evidence authority, immutable overlay and replan/re-audit loop for the canonical H1
row-completion control. V0-047 then extends that chain to a two-round H2 path with
evidence-derived active boundary states. Cross-query/held-out promotion remains the
next Gate. A V0-043 failed frontier remains nonauthorizing by itself.

Contract 1.8.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.9.0: certificate-triggered query-local exact-row refinement

V0-046 registers implementation schema `1.0.0` and profile
`lmb_h1_query_local_exact_row_refinement_v0`. It consumes the full V0-045 source/result,
the canonical H1 thresholds, the complete typed V0-044 proposal, its selected plan, and
the independently failed typed V0-043 result. Production then accepts one exact
`LMBKernel`; it accepts no caller-selected row list, evidence budget/cap, alternate
frontier, transition callback, ground solver, J0 result, target policy, or promotion
decision. The verifier adds only `claimed_result`.

The failed frontier is necessary but nonauthorizing. Before any ground access, a
separate authority replays V0-045, typed V0-044, and typed V0-043 and requires the
canonical H1 `delta=0` `UNRESOLVED_POLICY_PATH_DISTINCTION`. Under the fixed selected
plan and fixed uniform distinct-action concretizer, one reachable obligation has mass
upper one and exactly four missing rows of weight `1/4` each. In the declared
row-completion evidence family, leaving any row vacuous permits failure upper
`1/4>0`. The authority therefore emits four row-necessity proofs and authorizes exactly
those four rows. Request preparation records zero kernel calls and zero ground search.
No global experiment/acquisition minimum is claimed.

The exact in-memory LMB authority freezes tile types `(0,1,0,1,1,0)`, type count two,
capacity three, maximum layers two, empty blockers for tiles zero/one, blockers `{0,1}`
for tiles two through five, and kernel source digest
`fa38ca4724420cc9834a50ee83b57a97721434404a9e76f0994b1aecb22b5323`.
Before `step`, acquisition verifies exact kernel configuration/source and every
registered state’s legal-action catalogue. It invokes exactly the four authorized rows.
The outcomes contain no reward, failure, or terminal event; one successor is registered
and three are known external states. Operational acquisition records four exact-kernel
calls, four positive rows, zero extra-row access, zero environment interactions, zero
generative samples, and zero synthetic evidence rollouts.

The reusable base model remains byte-identical. A new content-addressed
`QueryLocalOverlayContextV1`, `QueryLocalBuildEpochV1`, and
`QueryScopedPartialRAPMV2` bind the complete failure/evidence chain. Exactly the four
missing rows become observed singletons and affected semantic realizations are
recomputed, changing coverage from `7/4` observed/missing to `11/0`. The overlay is
`query_neutral=false`, `acquisition_query_neutral_attested=false`, and
`promotion_authorized=false`. It still claims neither transition closure nor exact
quotient because three exact successors are outside registered state coverage. The
overlay build performs zero additional kernel calls.

Threshold rebasing changes only the model identity. Query-scoped planning enumerates
and internally audits both complete H1 plans with zero kernel calls and remains
proposal-only. Independent fixed-plan audit returns:

```text
outcome = CERTIFIED_FIXED_PLAN
reward lower / upper = 0 / 0
failure lower / upper = 0 / 0
raw / normalized regret = 0 / 0
operational exact-kernel calls = 4
```

Known external successors are sound at H1 because no positive remaining horizon follows
the final transition. This is not H2 transition closure or multi-step recovery.
Promotion is frozen to `RETAIN_QUERY_LOCAL_OVERLAY_ONLY`; local contextual reuse is
allowed, while base promotion, multi-query promotion Gate, and held-out promotion Gate
all remain false/unrun.

Canonical V0-046 identities are:

```text
kernel authority = 2bb62669839fbde2cb4703c1ff71b71eb95cddcfdba5b3102a1833c5258164a0
evidence request = 1ff845f3eecc05a098b3437c7e4b8356bcd28ea1dd0d4cc4ace8e52bc382cd2c
evidence bundle = 17c8783b3ab489322359bb9ed7e463c4540e9ed1d4d6036d639c1cc9a6bc8543
overlay BuildEpoch = ff0a14c296c8d5d122ff0f635ad8909dcfd2294274c99c3ac1da0412e8d947d2
query-scoped model = 7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df
query-scoped proposal = 9a408b15377b10bf6450d91c0e1e26d9e7dd9ac129abc7462ce15ca69187ad3c
fixed-plan certificate = ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303
complete result = 8c37b241d15b06f05dfe34189b37e324addd2c93605d4c718868d8a0544cf057
```

The independent verifier replays source synthesis, base planning/audit, exact evidence,
overlay construction, query-scoped planning, and final audit and requires byte-identical
output. Its repeated kernel calls are evaluation replay and do not alter the operational
four-call record. V0-046 does not establish a complete Phase 3E WorkVector.

Contract 1.9.0 proves one actual certificate-failure → scoped-minimum row evidence →
immutable overlay → abstract replan/re-audit loop. It does not prove raw symbolization,
unknown-DSL/semantic invention, general causal minimality, an adaptive acquisition
policy, statistical or learned dynamics, multi-step external-boundary recovery,
cross-query base promotion, generalization, scale, or sample saving. The fixed 4096-
candidate coordinate search remains charged offline construction work and the four
exact calls remain charged online acquisition work.

V0-047, frozen below, now executes the next distinct multi-step positive control.
V0-046 remains the immutable H1 regression and is not retroactively promoted. Its
detailed normative identity and acceptance table remains
`specs/QUERY_LOCAL_EVIDENCE_REFINEMENT.md`.

Contract 1.9.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.10.0: multi-step query-local RAPM evolution

V0-047 registers implementation schema `1.0.0` and profile
`lmb_h2_multistep_query_local_exact_refinement_v0`. Production consumes the full
V0-045 result, the canonical H2 typed V0-044 proposal and its selected plan, the
independently failed typed V0-043 audit, and one exact canonical LMB kernel. It
accepts no caller-selected row/state list, acquisition cap, alternate frontier,
transition callback, direct ground optimizer, target plan, or promotion decision.
The verifier adds only the claimed complete result.

The first failed frontier is at `time_index=0, remaining_horizon=2`. Its fixed
realization has exactly four missing rows, each with concretizer probability and
row-exposure upper `1/4`. The first request authorizes those four rows with zero
preparation kernel/search calls and makes no global-minimum claim. Exactly four
transition calls reveal one registered and three distinct external nonterminal
successors.

Boundary registration derives those three states only from signed evidence. Exactly
three direct boundary action-catalogue calls register nine legal rows; it performs zero
transition replay and zero ground search. The system reevaluates the exact fixed V0-045 programs
on those states/actions. All three reuse state coordinate `(3,)` and semantic labels
`(False,)` and `(True,)`; no new coordinate is supplied or invented.

The first immutable `QueryScopedPartialRAPMV3` has 20 registered rows and coverage
`11 observed / 9 missing`. V3 is a separate content domain and must remain
query-owned, non-query-neutral, nonpromotable, non-exact, and not transition-closed;
the V0-045 base is byte-identical. Model-only enumeration evaluates four H2 plans.
Independent audit moves the earliest frontier to
`time_index=1, remaining_horizon=1` with external coverage no longer failed.

Exact numerical ties are resolved only after the frozen value/risk selection tier by
`NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1`; the time-ordered semantic
boolean schedule is compared before `plan_id`. The serialized rule prevents an
unrelated content-hash change from choosing a different contingent plan and cannot
weaken any numerical certificate obligation.

The second authority binds the first epoch, proposal, and independent failed audit.
It requests the union of three selected-plan rows with positive risk exposure and all
nine unrestricted value challengers under zero regret: `3 risk / 9 value / 9 distinct`.
Exactly nine further transition calls yield three safe one-match outcomes and six
terminal failures. The final V3 epoch binds the first as `previous_model_id`, retains
20 registered rows, and changes coverage to `20/0` with cumulative transition calls
13. Zero registered missing rows is not a global transition-closure claim because
some horizon-end nonterminal successors remain external.

Final model-only replanning evaluates four plans, and independent audit certifies:

```text
outcome = CERTIFIED_FIXED_PLAN
reward lower / upper = 1 / 1
failure lower / upper = 0 / 0
normalized regret = 0
external coverage certified = true
```

The canonical operational trace is four first-round transition calls, three boundary
catalogue calls, nine second-round transition calls, two model-only replans, eight
candidate-plan audits, zero planner/auditor kernel calls, and zero direct ground-
optimization calls. Evaluation verifier replay does not alter those operational
counts. Each transition performs one internal legality enumeration; the 13 checks
are included in transition work and are not additional catalogue acquisitions.
`sample_efficiency_claimed=false`; the trace measures the sample tax but does
not claim an improvement over direct optimization.

Contract 1.10.0 proves the first authentic multi-step within-query
certificate-failure → local evidence → versioned model → replan/re-audit → later
frontier → second evidence → certified-plan loop. It does not prove raw
symbolization, unknown-DSL invention, learned/statistical dynamics, general causal
minimality, cross-query base promotion, held-out/cross-domain generalization, scale,
economics, or sample saving. The next construction Gate is preregistered cross-query/
held-out reuse and promotion with leakage controls and matched acquisition traces.
Only measured traces may justify a later Laplace-style operator or KG-OP-style
offline/online meta-prior.

Canonical identities and all acceptance/attack tests are normative in
`specs/MULTISTEP_QUERY_LOCAL_REFINEMENT.md`.

Contract 1.10.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.11.0: preregistered cross-query promotion and held-out reuse

V0-048 registers schema `1.0.0` and profile
`lmb_preregistered_h1_cross_query_promotion_v0`. Before any V0-047 result or
kernel is supplied, preregistration freezes a distinct H1 target at LMB state
`removed_mask=11, buffer=(1,2)`, with zero risk and normalized-regret
tolerances. The state is absent from the V0-045 observation registry and differs
from the V0-047 H2 source initial state. The preregistration API has no source-
refinement result or kernel; the already-frozen source runner has no target or
promotion-protocol parameter.

The promotion authority independently replays the complete V0-047 chain. It
must select the complete final model—20 observed rows, all 13 exact evidence
records, and all three boundary catalogues—with zero target-filtered rows. The
V0-045 base remains byte-identical. The resulting
`PreregisteredReusablePartialRAPMV4` is a new immutable epoch, not an in-place
mutation. It binds the source result, protocol, eligibility proof, promoted row
set, exact evidence set, authorized initial state, and reuse horizon cap one.

V4 must retain:

```text
query_neutral = true
acquisition_query_neutral_attested = false
promotion_scope_query_neutral_attested = true
promotion_authorized = true
base_model_mutated = false
unrestricted_reuse_claimed = false
transition_closure_claimed = false
exact_quotient_claimed = false
```

Thus the promoted transition facts are query-neutral only inside the registered
reuse scope; their source acquisition is not retroactively declared query neutral.
The generic auditor rejects target distributions or horizons outside that scope.

The held-out consumer receives the log/profile/authority and promoted build only.
It accepts no kernel, transition callback, target override, ground solver, J0, or
caller cap. It evaluates two H1 deterministic abstract plans and independently
certifies:

```text
reward lower / upper = 1 / 1
unrestricted reward upper = 1
failure lower / upper = 0 / 0
normalized regret = 0
external coverage certified = true
warm target transition / catalogue calls = 0 / 0
direct ground-optimizer calls = 0
```

A distinct evaluation-only cold trace requests the target's complete three-action
catalogue once and executes its three transitions. One action gives the safe
one-match reward and two terminate in failure. Every outcome must exactly equal its
promoted source evidence. The three `step`-internal legality checks are included in
the transition calls and are not additional catalogue acquisition.

The four work lanes remain separate:

```text
source V0-047 acquisition        = 13 transitions + 3 catalogues
promotion independent replay     = 13 transitions + 3 catalogues
warm held-out operational query  = 0 transitions + 0 catalogues
cold held-out evaluation trace   = 3 transitions + 1 catalogue
```

The cold trace is evidence acquisition only; it does not claim an end-to-end cold
planner, include source-cost amortization, or establish sample efficiency. Official
scalar cost and break-even remain null and `SAMPLE_EFFICIENCY_GATE_NOT_RUN` remains
non-blocking.

Contract 1.11.0 closes one preregistered cross-query scoped-promotion positive
control. It does not prove unrestricted reuse, arbitrary-support/horizon promotion,
statistical or cross-domain generalization, learned dynamics, feature invention,
portable observer truth, scale, sample saving, or an aggregate Gate. The next
construction Gate is a preregistered family of held-out logical occurrences with
promotion amortization and matched end-to-end cold baselines. Those traces will
identify the real tax before any Laplace-style operator or KG-OP-style meta-prior is
frozen.

Canonical identities, exact claim boundaries, and acceptance/attack tests are
normative in `specs/CROSS_QUERY_PROMOTION.md`.

Contract 1.11.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.12.0: preregistered held-out family and matched amortization

V0-049 registers schema `1.0.0` and profile
`lmb_preregistered_h1_heldout_family_amortization_v0`. Before source acquisition it
freezes three H1 target QuerySpecs at LMB states `removed_mask=11,19,35` and ten
logical occurrences ordered `Q1,Q2,Q3,Q1,Q2,Q3,Q1,Q2,Q3,Q1`. All target states are
absent from V0-045, distinct from the source initial state, and carry reward/risk/
regret parameters `1/0/0` under the canonical reward basis. Preregistration has no
source-result or kernel input; the V0-047 source runner remains target blind.

Promotion reuses the unchanged V0-048 complete-source authority. Its parent V4 must
contain all 20 rows, 13 exact evidence records and three boundary catalogues with no
target filtering. A new immutable `PreregisteredReusablePartialRAPMV5` binds that
complete parent, the family protocol, a three-target eligibility proof and exactly
three authorized initial-state IDs with reuse horizon cap one. V5 retains nonneutral
acquisition provenance and forbids base mutation, unrestricted reuse, transition
closure and exact-quotient claims.

Each warm occurrence receives no kernel, transition callback or ground optimizer. It
enumerates two semantic plans, audits both, and independently audits the selected
plan. All ten must certify reward/failure/normalized-regret `1/0/0`, with zero target
transition and catalogue calls. Repeated occurrences are executed again; V0-049 does
not cache a prior plan or certificate.

Each matched cold planner receives only the observation log, preregistered QuerySpec,
logical occurrence and canonical kernel. It cannot see the promoted model or source
result. It makes one complete action-catalogue call, three deterministic transition
calls, three step-internal legality checks, evaluates all three ground actions and
selects the unique safe reward-one action. Only after selection may a separate pairer
verify exact equality with the source catalogue/evidence.

Native lanes remain distinct:

```text
source acquisition operational = 13 transitions + 3 catalogues
promotion replay evaluation = 13 transitions + 3 catalogues
warm target operational per occurrence = 0 transitions + 0 catalogues + 2 plans + 3 audits
cold direct operational per occurrence = 3 transitions + 1 catalogue + 3 actions + 1 optimizer
```

For prefix `N`, source-inclusive warm acquisition is `(13,3)`, verification-inclusive
diagnostic work is `(26,6)`, and cold direct acquisition is `(3N,N)`. Source-inclusive
warm first strictly componentwise dominates at `N=5`; verification-inclusive warm
first dominates at `N=9`. These are diagnostic vector relations only:

```text
official_scalar_cost = null
official_N_break_even = null
sample_efficiency_claimed = false
```

Exact-kernel calls are not relabelled as samples. Three deterministic target states,
seven repeated occurrences, no stochastic inference and no scalar exchange rate are
insufficient for a sample-efficiency or generalization claim. The exact family trace
does establish `20` warm plan candidates and `30` exact fixed-plan audits after target
ground acquisition has fallen to zero. This licenses the next experiment—an identity-
bound certificate memoization/incremental-proof operator—but does not select or claim
that operator in V0-049.

Canonical identities and all acceptance/attack tests are normative in
`specs/HELDOUT_FAMILY_AMORTIZATION.md`.

Contract 1.12.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.13.0: exact identity-bound certificate memoization

V0-050 registers schema `1.0.0`, profile
`lmb_identity_bound_certificate_memoization_v0`, and success status
`CERTIFIED_IDENTITY_BOUND_PROOF_REUSE_CONTROL`. It retains the exact V0-049 V5
model, three preregistered queries, ten-occurrence order, two complete plan
candidates per occurrence, selection/tie-break semantics, and independent
selected-plan audit. The no-reuse arm is the unchanged V0-049 warm workload; the
memo arm receives only the observation log, semantics profile, observation authority,
and V0-049 promotion. It receives no kernel, source refinement result, cold result, or
control-arm artifact, and its cache begins at the canonical empty state.

Each occurrence issues two role-typed `CANDIDATE_RANKING_AUDIT` requests and one
separately keyed `INDEPENDENT_SELECTED_PLAN_CERTIFICATE` request. A candidate result
may be certified or may expose a failed proof frontier; the selected role must contain
a complete fixed-plan certificate. Equal inner audit bytes do not allow one role to
authorize the other.

`FixedPlanAuditMemoKeyV1` binds the complete semantic identity of the request:
model/base/source/protocol/promotion/eligibility; observation log, semantics and
authority; target query; threshold binding, complete thresholds and return-bound
proof; complete contingent plan; planner and tie break; auditor schema/profile/source;
proof role; and, for selected certification, the frozen planner-result ID. The
registered auditor and family-planner source digests are part of memo semantics.
Memo semantics and planner/tie-break semantics have distinct content-ID domain tags;
a schema string alone cannot substitute for domain separation. Logical occurrence ID
is excluded from this semantic key only so an exact repeated
request may hit; every use still produces a new occurrence/query/sequence/role-bound
receipt.

A trusted miss executes the full exact auditor once and freezes its execution
attestation, complete result, optional certificate, append-only insertion, and current
use receipt. A hit must first revalidate the live planner context, match the complete
key exactly, and bind the earlier trusted miss in a fresh receipt. The 30-receipt
trace is replayed from the empty-state ID. Entries cannot be overwritten, reordered,
cross-role reused, silently replaced after a mismatch, or imported as authority from
serialized/copied runtime objects. The memoized family execution is owner-bound
process-local authority; an independent verifier mints new authority only after full
semantic and trace replay.

The matched goldens are:

```text
logical proof requests = 30 in each arm
plan candidates = 20 in each arm
independent selected-plan certificates = 10 in each arm
no-reuse complete audit executions = 30
memo complete audit executions = 9
memo misses / inserts / hits / lookups = 9 / 9 / 21 / 30
final memo entries = 9
target transition / catalogue calls = 0 / 0 in each arm
memo full-audit prefix = 3,6,9,9,9,9,9,9,9,9
no-reuse full-audit prefix = 3,6,9,12,15,18,21,24,27,30
first strict full-audit reduction prefix = 4
```

All ten threshold bindings, selected planner artifacts, outer audit artifacts,
certificates, and cold direct reward/failure/regret results must remain byte-identical
to the no-reuse/cold controls. The 21 avoided executions give the narrow exact-proof
computation reduction `21/30=7/10`; lookup, identity validation, hashing, receipts,
I/O and standalone evaluation replay remain explicit nonnegative work. No total-work,
wall-clock, scalar-cost, or break-even conclusion follows.

Changing model/source/promotion, observation authority, query, thresholds/risk/regret/
reward/horizon/goal/return proof, plan, planner/tie break, auditor semantics/source,
proof role, or selected planner result invalidates the key. Changing only a registered
occurrence ID may hit the same semantic entry but must create a new bound receipt.
Unknown occurrences, malformed content IDs, stale or poisoned entries, cross-role
substitution, owner-copy replay, and forged cache/trace/work fields fail closed.

V0-050 therefore establishes only exact-repeat proof reuse. It does not establish:

```text
incremental_proof_claimed = false
cross_identity_reuse_claimed = false
persistent_cross_process_cache_claimed = false
sample_tax_operator_claimed = false
sample_efficiency_claimed = false
statistical_generalization_claimed = false
overall_workload_economics_claimed = false
```

Cross-query or changed-threshold incremental proof is a later Gate. It requires a new
identity-bound proof-dependency DAG and re-derivation artifact that enumerates reused
obligations and recomputes every changed ancestor; it may not relax or reinterpret the
V0-050 exact key. Canonical identities and all acceptance/attack tests are normative
in `specs/CERTIFICATE_MEMOIZATION.md`.

Contract 1.13.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```


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

Phase3EAccountedDynamicRoutingV1:
  contract_version = 1.0.0
  profile_key = phase3e_accounted_dynamic_routing_v0
  counter_registry_id, comparison_profile_id, actual_projection_profile_id
  logical_occurrence_id, route_attempt_id, decision_point_id, transaction_id
  frontier_snapshot_id, causal_evidence_id, cardinality_evidence_ids
  route_upper_formula_ids, route_upper_derivation_proof_ids
  local_upper_id, fallback_upper_id, route_decision_id, access_event_log_id
  runtime_factory_cardinality_ids
  sealed_executor_construction_receipt_id, postconstruction_access_event_log_id
  sealed_executor_execution_merge_proof_id
  sealed_executor_failure_evidence_id, sealed_executor_failure_merge_proof_id
  sealed_failure_source_triples=(factory, delegate-or-typed-null, merged)
  partial_common_accounting_ids
  operational_work_vector_ids, evaluation_work_vector_ids
  typed_verification_attestation_ids, route_terminal_artifact_id
  occurrence_terminal_artifact_id, occurrence_terminal_semantic_result_id
  rebuild_policy_id, rebuild_event_ids, occurrence_closure_ids, campaign_summary_id
  workload_vector_spec_id, vector_prefix_ids, worst_frontier_ids
  official_execution_allowed = false
  official_scalar_cost = null
  official_N_break_even = null
  counter_completeness_gate_status = COUNTER_COMPLETENESS_GATE_NOT_RUN
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
21. Phase 3D causal search uses certificate slack and all tied active extremizers; a
    reachable DirectBad residual that cannot close a failed root obligation is not
    authorized by that transaction.
22. Phase 3D worker authority consists only of capability, request, and sparse slice;
    presence of the trusted source boundary in the bundle does not mount it in the
    isolated runtime.
23. Every Phase 3D exponential search has a declared cap and distinct exhausted
    status; an incomplete prefix cannot be returned as an exact result.
24. Local action choice is one global deterministic value-risk composition across all
    authorized members/cells, never independent minimum-risk selection.
25. Phase 3D leaves Phase 3C schemas, goldens, and claims unchanged.
26. Operational Phase 3D consumes and preserves a verified frozen Phase 3C bundle and
    its locality, authorization, and pre-certificate `U_all`; it performs zero model
    construction/closure and zero ground steps before local authorization. Its complete
    144-action binding catalogue supplies pre-authorization legality/cost queries.
    Verifier reconstruction and exact lift are evaluation-only.
27. Phase 3D operational post-audit can step only exact overlay pairs through
    `PatchedAuditKernelView`; unpatched decisions remain envelope-evaluated. Operational
    exact lift is forbidden and its exact-hybrid fields remain null.
28. Phase 3E freezes verified marginal route uppers and the route decision before any
    route-specific ground transition, compiler, worker, stitch, or post-audit access.
29. Every Phase 3E operational charged leaf is present, including native zero, and
    projects exactly once to one shared additive or peak axis; evaluation, provenance,
    diagnostic, and derived-only fields cannot enter operational comparison cost.
30. Local selection requires strict componentwise dominance and `local_allowed=true`;
    equality, incomparability, stale/missing evidence, cap exhaustion, no sound cover,
    or local-cap impossibility deterministically selects fallback.
31. Host full solver replay, unrestricted ground upper recomputation, exact lift, and
    J0 are forbidden in the 1.0.0 operational lane and remain separately charged
    evaluation work.
32. A complete hash chain establishes bytes and binding only. It cannot change a
    noncertificate closure or cap exhaustion into a plan/infeasibility certificate,
    and no registered logical occurrence may be removed from a Gate denominator.
33. A route-upper transport envelope is not generation evidence. Its complete
    eight-axis vector must replay from the exact registered cardinality set, one
    formula term per operational leaf, hard-cap minima/structural guards and the
    current context/decision/transaction/frontier identities.
34. A typed verification attestation is accepted only after the registered semantic
    verifier recomputes its result and charges an operational verification record.
    A role without an implemented authority fails closed even when its claimed outcome
    belongs to the legal vocabulary.
35. Contract 1.0 workload ordering is vector-valued. Until a later ledger revision
    freezes a scalar, every prefix/campaign artifact keeps scalar cost and
    `N_break_even` null and the scalar/economics Gates `NOT_RUN`.
36. Every preselection read, including the failed certificate and action catalogue,
    binds the exact prepared identity; inapplicable fallback frontier/proof fields use
    content-addressed typed nulls rather than dummy IDs or omission.
37. Route-decision authorization contains exactly the causal result, both route-upper
    results and one matching cardinality verification per upper. Missing, duplicate or
    extra semantic results invalidate authorization.
38. A local candidate binds exact capability, worker, stitch and post-audit artifacts.
    A negative local solver result closes after materialize/compile/worker, forbids
    stitch and post-audit artifacts, and may continue only at a fresh fallback decision.
39. A failed transaction-1 post-audit creates a fresh decision that may choose local
    transaction 2 or direct fallback without inventing transaction 2. Both route
    adapters preserve every observed work prefix incrementally when later execution
    fails.
40. Each sealed candidate route derives `RuntimeFactoryCardinalityV1` from its exact
    frozen manifest/cap and binds that ID in its route-specific cardinality source
    chain before comparison; after selection the factory rechecks the chosen chain.
    The registered sealed safe-chain fallback uses the preselection identity
    `C_route=5815=C_factory(3)+C_solver(5812)`: cardinality incorporates the reserve
    before the route-total cap is applied, never as a post-hoc `+3`. A total `5812`
    with reserve `3` yields worker share `5809` and a cap-rejection/noncertificate
    path. The positive upper proof leaf is `5815`; a reserve-zero legacy payload keeps
    its original schema, domain and content ID.
41. A successful sealed construction receipt binds the exact factory work and the
    final selected-route `AccessEventLogV1` returned by `Phase3ERunResultV1`; an earlier
    or foreign log cannot authorize the result.
42. A sealed failure retains exact factory, delegate-or-typed-null, and merged
    WorkVector/comparison/projection triples. A rejected continuation may retain
    observed verifier work as `PARTIAL_ACCOUNTED_COMMON`, but that evidence is neither
    a successful receipt nor continuation/certificate authority. The failure merge is
    not yet a separate FQ7 or independent-bundle semantic authority.
43. `Phase3EOccurrenceTerminalArtifactV1`, not a route-attempt terminal, is the
    evaluation-lane occurrence authority for `PROTOCOL_FAILURE` and
    `FALLBACK_CAP_EXHAUSTED`; both retain counts `0/0/1` and every denominator.
44. Nonsemantic `VALID` is derived only by registered check-kind replay over typed
    evidence; a caller cannot supply evidence IDs. Plan source records are disjoint
    from sealed-core records. Every occurrence runtime result independently replays
    its aggregate, ordered run/transaction correspondence, final closure and terminal
    authority, rejecting stale or rearranged histories.
45. V0-038 production accepts only the exact `LMBKernel` and frozen
    `SuiteBuildCoverage` and internally constructs the complete canonical registry/
    specification. Restricted registries belong only to a separately named non-
    production control and cannot influence the production trace or claim.
46. V0-038 enumerates the complete registered feature power set and all adjacent-value
    exact-rational midpoint atoms. A candidate succeeds only by equality with the
    exact behavioural target partition; under- and oversplitting are typed negative
    mismatches rather than exact realizations.
47. Exact candidates are selected by the frozen tuple `(feature_count, split_count,
    feature_names, partition_id)`. Registry reordering, process boundaries and
    canonical round trips cannot alter that selection or any content ID.
48. `NO_EXACT_FEATURE_REALIZATION` publishes a bidirectional typed partition-mismatch
    witness but no tree, realized model or certificate. `EXACT_FEATURE_REALIZATION`
    does not open official execution, scalar/break-even, counter-completeness,
    workload-economics or aggregate Phase 3/3E status.
49. V0-039 production accepts only the exact kernel and frozen coverage, internally
    fixes the complete eleven-state/one-action grammars, and has no construction import
    or input path to a behavioural target/signature, query, value, policy or held-out
    result.
50. A V0-039 candidate is exact only after label-set, within-state pre-mixture action-
    alias and cross-state same-label one-step dynamics obligations all hold exactly.
    Internally recomputed raw signatures are proof evidence, not a target quotient.
51. V0-039 production evaluates all 4096 candidates before selecting by the frozen
    order. Restricted exact, no-exact and cap controls cannot publish or verify as a
    production model/certificate; their separate role-locked verifier cannot substitute
    for production verification, which requires canonical complete registries and
    exact production result types/provenance.
52. V0-039 content IDs, canonical transport types, nested runtime types, source-digest
    anchors and independent reconstruction bind the complete state/action registry-to-
    portable-model graph; evaluation-only behavioural comparison cannot feed back.
53. `EXACT_DIRECT_HOMOMORPHISM` means exact homomorphism inside fixed grammars and
    exact finite coverage. It never implies feature invention, learned/partial
    dynamics, scale/generalization or an official/aggregate Gate.
54. V0-040 production derives its proposal only from unanimous exact source evidence;
    no caller can choose the production preferred hypothesis. Target task and coverage
    IDs are absent from the source set, and proposal bytes never confer acceptance.
55. V0-040 broad-support mass is metadata with no executed candidate schedule. Only
    the exact target audit may publish a model; mismatch requires fallback and is never
    infeasibility. Exact-kernel calls, unique rows and interaction samples remain
    distinct.
56. V0-040 independent replay rebuilds source evidence and the target audit/model.
    Production and external-control profiles, runners and verifiers are role-separated;
    renaming or re-signing one cannot cross the boundary.
57. `SAMPLE_EFFICIENCY_GATE_NOT_RUN` is non-blocking. A prior or future heuristic may
    propose evidence locations but cannot narrow a sound envelope or certify itself.
58. V0-041 production receives only exact kernel and coverage and instantiates exactly
    eight state/four action ASTs from the frozen typed templates. Named V0-039 feature
    semantics are neither inputs nor hidden registry entries.
59. V0-041 evaluates all 4096 subset candidates and accepts only the same direct exact
    state-action homomorphism obligations used for its generated semantics. A no-exact
    or cap-exhausted control cannot publish a model/certificate.
60. V0-041's generated ASTs, registry, complete trace, implementation digests,
    quotient and portable model are independently rebuilt. The generated-coordinate
    result means fixed-DSL program generation only, not unknown-semantic invention,
    partial/learned dynamics, generalization or sample efficiency.

61. V0-042 builder/verifier authority begins with the exact four-input source graph;
    no kernel, query, planner or target channel is present, and a locally coherent
    re-sign is rejected unless its complete authority ID is externally allowlisted.
62. The canonical acquisition is literal and pre-query: 8 states, 11 legal rows,
    7 distinct `offline_source/OFFLINE_LOGGED_OBSERVATION` events and 19 native zeros.
    Acquisition and construction query-input counters are independently zero.
63. A Portable partial model internally derives all cell/action/row/concretizer/
    realization cross-links, observed/missing partitions and exact weighted ambiguity.
    A retained authority ID cannot authorize altered derived bytes.
64. Missing evidence is one coupled joint simplex over active/external continuation and
    terminal success/failure. Independent marginal boxes, external-state aliasing,
    duplicate semantic names and nonuniform concretizers fail closed. Horizon is
    limited by the bound `semantics_horizon_cap=6`.
65. V0-042 authority is conditional and retained in memory. Hashes prove integrity,
    not observer/catalogue/stationarity truth; no cross-process/public transport
    authority is claimed, and new fixtures require a registry/contract revision.
66. The manual fixed coordinates and conditional partial RAPM establish neither
    automatic coordinate synthesis nor planning, a plan/infeasibility/exact-quotient
    certificate, learned dynamics, generalization or sample efficiency. The sample
    Gate remains non-blocking and all official/economics/counter locks remain.

67. V0-043 always reconstructs the exact V0-042 source graph/model before accessing
    thresholds or plan fields. Its public surface has the seven frozen audit inputs and
    one additional claimed-result verifier input; kernel, planner, J0 and ground-search
    authority are absent.
    Threshold payload/ID binds exact `goal_id="default"`; foreign strings, non-string
    values and string-like ducks are invariant violations, not additional registered
    goals.
68. Threshold/model/plan IDs and horizon match; `H<=6`; stages are contiguous and
    complete over active cells; the selector is deterministic. Initial support contains
    exact active ground-state IDs, not cells, and has exact unit mass.
69. The sole V0-043 scale proof binds the canonical source identities, nonnegative
    `match=1,terminal_clear=1` basis and `R_max=4`; tolerances come only from the frozen
    `{0,1/20}` regret and `{0,1/20,1/10}` risk registries. A changed scale, basis or
    identity is an invariant violation.
70. The unrestricted comparison is a sound upper over the complete registered ground
    catalogue, never J0 or an exact optimum. Value certification is pointwise over every
    initial support state, risk is distributional, and reachable external/unknown
    continuation with remaining horizon above one independently blocks certification.
71. Bellman rows charge one shared joint unknown mass exactly once. Destination
    reachability uppers and `unresolved_exposure_sum` are proof diagnostics, not
    probabilities or independently summable transition mass.
72. `CERTIFIED_FIXED_PLAN` binds the complete fixed-plan proof chain and claims neither
    planning, optimality nor infeasibility. `FAILED_PROOF_FRONTIER` is only an earliest
    `NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1`; it grants no local authority and no causal
    necessity/sufficiency or infeasibility claim.
73. Legitimate missing/pointwise/external/known-threshold cases are negative regressions.
    Forged, malformed, stale, self-signed, mutable/duck or coherently re-signed inputs and
    results are invariant violations, never normal frontier outcomes. V0-043 opens no
    official, scalar, economics, counter-completeness, sample-efficiency or aggregate
    Gate.
74. V0-044 production/verifier signatures are exactly the registered six/seven inputs.
    Its single threshold input must carry the same content-bound default goal; it cannot
    introduce a second QuerySpec or goal profile.
    Complete V0-042 reconstruction precedes threshold access; no kernel, transition,
    ground, `J0`, feasibility-oracle, second-query or production caller-cap channel is
    reachable.
75. Per-stage assignment count is the product of every active cell's complete semantic-
    action-domain size. Candidate count is exactly `S^H`; within production cap all and
    only complete deterministic global plans are enumerated and audited once.
76. Selection is lexicographically tiered: internal V0-043 pass precedes risk-feasible
    reward-max, which precedes minimum-risk fallback; the registered reward/risk/plan-ID
    keys are deterministic and cannot be reordered.
77. `PLAN_PROPOSED` is never certificate authority. Every selected plan requires
    independent V0-043 replay, and proposal-level feasible, infeasible-query and optimal-
    ground-policy claims remain false even when the internal audit passed.
78. Production cap is exactly 65536 under the registered cap-profile ID and cannot be
    caller-selected. Over-cap returns typed zero-candidate-work `CAP_EXHAUSTED`; a named
    lower-cap control is nonproduction and cannot pass the public verifier.
79. Planner telemetry reconciles candidate evaluations, V0-043 audits and
    `1+audit_count` source reconstructions while external-transition and ground-search
    calls remain zero. It is model-work telemetry, not sample-saving/economics evidence.
80. H3 and H1 may share the exact V0-042 model/build only while retaining distinct
    threshold/result IDs. This two-query control is bounded in-catalogue reuse, not
    arbitrary-query generalization. Content IDs alone do not replace full deterministic
    source/enumeration/audit/selection replay.


## Acceptance tests

- Mutating `H`, registered reward/goal fields, or `delta` leaves the Phase 0.5 coverage
  descriptor unchanged; mutating `rho0` leaves `structural_id` unchanged but changes
  `query_id` and the descriptor-specific `build_id`.
- Mutating each structural field invalidates the RAPM build key.
- Two builds with identical structure/source but different coverage declaration hashes
  or covered-state counts have different build IDs.
- A query with any positive-mass initial state outside the recorded transition closure
  is rejected before planning; it cannot reuse a certificate or RAPM cache entry.
- Phase 3D independently reproduces the `24/96` authorized capability scope,
  `1/0/1+1`, 257-assignment, and 25-assignment goldens; deleting a retained sparse
  port/form or forging a cap counter fails replay. Operational work separately
  reconciles 16 materialization steps/64 positive outcomes and eight restricted
  post-audit steps to 24 total, with zero accounting/out-of-scope steps and no exact
  hybrid replay.
- Phase 3D source-boundary tests monkeypatch the Phase 3C constructor, transition
  closure, partition/quotient/RAPM builders, and operational unrestricted-upper solver
  to fail if called; valid runs still preserve source model/epoch/run/manifest/locality/
  authorization/pre-certificate bytes and provenance, while malformed or coherently
  re-signed source artifacts fail verification/replay. The binding-time 144-action
  catalogue, rather than fresh pre-authorization calls, must serve causal and ancestor
  legality/cost lookup.
- The standalone Phase 3D verifier's evaluation-only reconstruction/lift reproduces
  exact failure `317/16000` with eight patched and twelve abstract decisions before J0;
  those operations never enter operational work counters or post-certificate exact
  fields.
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
- Contract-1.0 component attacks cover canonical/domain IDs; exact native counter
  completeness and reconciliation; eight-axis actual projection; 34-leaf route-upper
  derivation with 13 native cap minima and six structural guards; strict-dominance
  selection; pre-freeze access; transaction/rebuild closure; logical-occurrence
  denominators; scalar-free prefix frontiers; and partial semantic authority. These
  tests must retain `official_execution_allowed=false` and both Phase 3E Gates
  `NOT_RUN` until the integrated production and independent bundle paths also pass.
- Sealed-route attacks mutate manifest cardinality/source binding, the success
  receipt's final access-log ID, every factory/delegate/merged failure-proof reference,
  the all-ID/all-typed-null delegate rule, failure stage, and post-failure log; each
  mutation must fail exact replay.
- Rejected-continuation attacks remove, duplicate, overlap, change lane/registry, or
  stale-bind an observed verifier record in `PARTIAL_ACCOUNTED_COMMON`; each must fail,
  and no such evidence may mint a successful charge receipt, continuation authority,
  plan certificate or infeasibility certificate. A protocol-failure occurrence
  noncertificate remains the only allowed terminal use.
- V0-038 production API/type and static-source audits expose only exact kernel and
  coverage inputs, reject caller registry/spec arguments and query/J0/Q/value/policy/
  held-out/planning channels, and allow the explicit exact behavioural-ground-model
  target builder. Restricted subsets run only through the negative-control API.
- The full eleven-feature V0-038 trace contains exactly 2048 candidates, is stable
  under registry reordering and selects only `action_count`, midpoint thresholds
  `(3/2,5/2)`, two applied splits, total `25 -> 5` and active `18 -> 3`, with the
  realized partition equal to the exact behavioural target and a singleton envelope.
- Independent V0-038 replay reconstructs every subset/atom/tree, the target
  partition/trace/adapter/model, candidate trace/certificate, realized
  partition/quotient and portable model/registry. It rejects modified or coherently
  re-signed registry/spec/certificate constants or semantic artifacts, a changed
  independently frozen implementation digest, list/string transport substitution and
  nested runtime proxies. A restricted incomplete grammar returns typed
  `NO_EXACT_FEATURE_REALIZATION`, a bidirectional mismatch witness and no positive
  artifacts.
- The separate seed-0 canonical-initial negative control retains 36 states, an 11-cell
  exact target and a 7-cell `action_count` candidate; its trace contains both
  `TARGET_SEPARATED_FEATURE_ALIASED` and `TARGET_MERGED_FEATURE_SEPARATED`. None of
  these numbers may replace the 25-state exact-realization golden.
- Two fresh Python subprocesses load the same unchanged V0-038 portable RAPM and solve
  the registered in-coverage `H=3` match-plus-clear and `H=2` match-only queries. This
  test does not count as sealed production execution, held-out evaluation or a full
  Gate.
- V0-039 source/API tests expose only kernel/coverage, reject target/query channels and
  forbidden imports, and construct successfully in a fresh process after poisoning
  `acfqp.abstraction.behavioral`.
- The complete V0-039 production trace evaluates 4096/4096 candidates, selects state
  `action_count`, action `completes_match`, thresholds `(3/2,5/2)`, and reproduces
  `25/18 -> 5/3`, four abstract entries, singleton envelope and pre-mixture action-
  alias verification. All three direct mismatch-witness kinds occur.
- V0-039 restricted controls reproduce `NO_EXACT_DIRECT_HOMOMORPHISM`, typed
  `CANDIDATE_CAP_EXHAUSTED` with zero evaluations, and
  `RESTRICTED_CONTROL_EXACT_FOUND` without model/certificate; none verifies as the
  production profile. The role-locked control verifier accepts only control provenance,
  while production verification rejects restricted provenance, incomplete registries
  and duck-typed results.
- V0-039 typed artifact round trips and independent rebuild reject coherent re-signing,
  list/string transport changes, nested proxies, truncated traces and state/action
  implementation-source substitution. The evaluation-only behavioural oracle later
  matches the direct partition/model exactly, and one unchanged portable model serves
  two fresh-process in-coverage queries.

- V0-040 production-prior construction accepts the two canonical source records only
  when both exact audits support the identical hypothesis; a nonexact/nonunanimous
  source tuple or caller-selected production proposal is rejected.
- The held-out target mask-7 coverage ID is absent from mask-11/mask-13 sources. The
  exact target audit is the sole acceptance authority and reproduces source-offline
  `14/14/14` and target `21/7/7` exact-call/unique/eligible counts with zero
  interactions and one target candidate evaluation.
- V0-040 transport, task/coverage identity, renamed-profile, coherent re-signing and
  duck-type attacks fail independent replay. The external empty-hypothesis control
  returns mismatch/fallback after `3/3/7` target call/unique/eligible counts, publishes
  no model/certificate and cannot verify as production. The accepted model serves two
  in-coverage queries unchanged.
- V0-041 API/source tests expose only kernel/coverage and raw typed DSL primitives,
  with no V0-039 named-feature, QuerySpec, target/signature or planning channel.
- The V0-041 golden has eight state/four action ASTs, evaluates 4096/4096 candidates,
  selects `cardinality(legal_actions)` and
  `buffer_at_type(buffer_counts,selected_tile_type)`, and reproduces `(3/2,5/2)`,
  `25/18 -> 5/3`, four entries and a singleton envelope.
- V0-041 candidate-cap and state-only controls respectively return zero-evaluation cap
  exhaustion and 256-evaluation no-exact results without a model/certificate. Typed-AST,
  duck-result, trace, content and evaluator/enumerator/compiler/audit source-digest
  attacks fail, and the independent verifier reconstructs the complete result.

- V0-042 production signatures contain exactly log, proposal, semantics profile and
  preregistered authority; the literal fixture contains no closure, kernel action or
  transition call. Full source-graph reconstruction accepts only the canonical
  allowlisted authority and rejects a coherently re-signed catalogue or observation.
- The golden has 8 registered states, 11 legal rows, 7 observed singletons, 4 missing
  unit-simplex rows, `semantics_horizon_cap=6`, exactly 7 offline-source logged events
  and native zero in the other 19 evidence cells.
- Independent reconstruction rejects deleted/fabricated/replayed/relabeled evidence,
  catalogue deletion, registered-as-external or terminal external successors, nested
  ducks, duplicate semantic names, nonuniform concretizers, ground-row ID/cross-link
  changes, realization-only missing-to-singleton forgery, unknown-mass shrink and
  altered joint-simplex coupling. Outside registered support requires rebuild/fallback.
- V0-042 artifacts keep all plan, quotient, infeasibility, automatic-coordinate,
  transport and official-Gate claims false; the sample-efficiency Gate remains
  explicitly non-blocking.

- V0-043 audit/verifier signatures are exactly the registered seven/eight inputs. They
  reconstruct V0-042 before threshold/plan access, import no kernel/planner, make zero
  external-transition and ground-search calls, and reproduce the same canonical result.
- Return-proof replay reproduces ID
  `6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98`,
  the canonical identities/basis, `R_max=4`, exact tolerance registries and exact-ground-
  state support. Changed scale/weight/identity, cell support, foreign plan/model, horizon
  overflow and noncontiguous/incomplete stages are invariant violations.
- Threshold replay requires literal `goal_id="default"` in the content-addressed
  payload. A foreign string, integer or string-like duck fails as an invariant violation
  without changing the seven/eight-input APIs.
- The H3 observed-path control returns `CERTIFIED_FIXED_PLAN` with unrestricted upper 4,
  plan interval `[4,4]`, zero distribution/max-support regret, zero failure, external-
  coverage pass and 33 unrestricted rows. Unrelated missing rows remain in the model but
  do not enter its reachable proof obligations.
- The H1 missing-state negative regression returns `FAILED_PROOF_FRONTIER` with
  unrestricted upper 3, plan lower 0, normalized regret `3/4`, failure upper 1 and the
  earliest unresolved `(0,1)` hint; it never claims infeasibility or local authority.
- A 1/100 bad support point fails its pointwise `3/4` regret obligation even though
  distribution regret is `3/400<1/20` and risk `1/100` passes. At H2 the same reachable
  unknown fails external coverage. A selected singleton/nonmatching plan produces a
  known-threshold hint rather than blaming unselected missing rows.
- Joint-simplex tests charge unknown once and enforce failure-implies-terminal.
  Self-signed row deletion, changed bound/frontier, erased unknown, mutable/duck nested
  input, content-ID/identity substitution and coherent re-signing are invariant
  violations under full exact verifier replay, never normal negative regressions.
- Certificate and frontier artifacts retain all planner, optimality, infeasibility,
  causal/local-authorization, exact-closure, learning/generalization, sample-efficiency
  and official-Gate claims false.

- V0-044 producer/verifier signatures are exactly the frozen six/seven inputs; source-
  first replay occurs before threshold access, and kernel/transition/ground/J0/caller-
  cap injection is unreachable. The consumed threshold content-binds the same default
  goal; no second QuerySpec or additional goal profile enters enumeration.
- H3 reproduces `S=2`, `8/8` candidates, 8 V0-043 audits, 9 source reconstructions, the
  tier-1 selection mode, frozen selected plan ID, reward/failure `4/4` and `0/0`, zero
  regrets and matching independent V0-043 certificate.
- H1 reuses the same model/build with different threshold/result IDs, evaluates two
  candidates and returns minimum-risk fallback with reward `0/3`, failure upper one,
  risk infeasible and nonauthorizing unresolved V0-043 frontier.
- The private cap-4 H3 control returns `CAP_EXHAUSTED` for required count eight with zero
  evaluations/audits, one reconstruction, empty summaries, no plan and public-verifier
  rejection; production refuses a caller cap.
- Selection tests freeze tier precedence and registered tie-breaks, and reject candidate
  summary, selected-plan ID and selection-mode tampering.
- Full replay rejects source/model/threshold/trace/result substitution, nested duck
  objects, coherent re-signing, premature threshold access and nonproduction-role
  promotion.
- Traces reconcile `audit_count=evaluated_count`,
  `reconstruction_count=1+audit_count`, zero transition/ground calls and false economics
  claim; no counter is relabelled as an interaction/sample or saving.
- Every proposal/cap/two-query artifact keeps certificate, feasible/infeasible-query,
  ground-optimality/J0, exact-closure, coordinate-invention, causal/local/fallback,
  learning/generalization/scale, sample-saving/economics and official-Gate claims false.

- V0-045 producer/verifier signatures are exactly three/four source inputs and expose
  no query, coordinate subset, cap, kernel, target, V0-041 result, planner/audit or
  callback channel. Runtime digest checks and full retained replay reject changed
  registry/evaluator/compiler/selector implementations.
- The exact 8-state/11-row value table contains all eight state and four action AST
  columns; the trace evaluates `4096/4096` candidates and selects
  `cardinality(legal_actions)`,
  `buffer_at_type(buffer_counts,selected_tile_type)` and action atom `<=3/2`.
- The selected result has six total/four active cells, five abstract entries/actions,
  six realizations, seven point rows, four missing rows and entry classes four
  `POINT_IDENTIFIED` plus one `UNOBSERVED_UNKNOWN`. Missing rows contribute neither
  equality nor mismatch evidence.
- The original nonempty `tuple[bool,...]` semantic-action schema remains unchanged.
  V2 integer values compile through exact midpoint atoms, and the typed pure builder
  rejects changed atoms, partial member label availability, nested substitutions and
  source/proposal/table mismatch. It is never accepted as stand-alone authority.
- The full V0-045 verifier reconstructs values, all candidates, selection, proposal,
  build, model, telemetry and certificate. Kernel blindness, unallowlisted authority,
  source/result substitution and a separately named cap-4095 closure fail closed.
- Typed V0-044 replays V0-045 exactly once, then runs candidate audits on the fixed
  verified model: H3 has `8/8` plans/audits; H1 has `2/2`; internal source-replay count
  is zero. Its selected plan remains nonauthorizing.
- Independent typed V0-043 explicitly binds the V0-045 result/certificate, proposal,
  build and model to thresholds, plan and the unchanged inner audit. H3 certifies
  reward/failure `4/0`; all-missing H1 returns `[0,3]`, failure upper one and an
  unresolved nonauthorizing frontier. A bare model/build/table/proposal is rejected.
- Historical manual V0-042--V0-044 focused tests preserve their existing results and
  IDs. Typed V0-045/V0-044/V0-043 content-ID goldens are frozen in their focused tests.

## Out of scope

Neural encoders, learned/statistical world models, MCTS, first-hit options, SMDP duration, POMDP/belief adapters, visual perception, infinite horizon, cross-domain meta-controllers, interpreting a supplied `D4` group as an automatically discovered abstraction, interpreting Phase 3A exact-model cross-orbit aggregation as oracle-free unknown-quotient discovery, interpreting Phase 3B exact one-step synthesis as predicate invention or local hybrid planning, interpreting V0-038's target-supervised selection as target-free discovery, interpreting V0-039's direct fixed-grammar exact homomorphism as feature invention, scalable/unknown-domain discovery or held-out generalization, or interpreting Phase 3D as workload break-even or a full Phase 3/5 pass.


V0-040 cannot be cited as learned/meta-prior ranking, an executed broad-tail schedule,
interaction reduction, global minimality or cross-domain generalization. V0-041 cannot
be cited as unconstrained semantic invention, partial/learned dynamics or
unknown-domain discovery merely because its selected coordinates are generated ASTs.
V0-042 cannot be cited as automatic coordinate discovery, an exact or learned world
model, observer/catalogue verification, portable authenticity, planning, a plan or
infeasibility certificate, transition closure, reuse beyond its registered catalogue/
horizon, generalization or sample saving merely because missing rows are preserved
soundly.
V0-043 cannot be cited as a planner, policy-discovery result, J0/optimality replay,
infeasibility proof, causal/slack-aware frontier, local-recovery authorization, model
exactness/transition closure, workload/counter completeness or official terminal. Its
certificate is conditional on the externally preregistered in-memory V0-042 authority
and on the supplied frozen plan. External-coverage pass means only that this selected
plan cannot escape the active model while future horizon remains; it says nothing about
whole-model transition closure.

V0-044 cannot be cited as a certificate, feasible-plan or infeasible-query result,
`J0`/ground-optimal planner, exact quotient/transition closure, automatic coordinate
invention, causal/slack-aware frontier, local-recovery/fallback authorization,
learned/statistical model, generalization/transfer/scale, sample reduction/economics or
official terminal. Its cap establishes only bounded exhaustive abstract search; its
selected plan remains conditional on the V0-042 trust root and requires independent
V0-043 audit.

V0-045 cannot be cited as symbolization of raw/visual observations, discovery of an
unknown primitive/operator/DSL, a neural or statistical latent model, exact quotient,
true dynamics, observer/catalogue truth, portable authenticity, unrestricted reuse,
ground-optimal planning, infeasibility, held-out/cross-domain generalization, scale or
sample saving. Its coordinate discovery occurs only inside one fixed human DSL over an
already-symbolized finite log. The typed pure builder and typed V0-044 internal audit
are not certificate authorities; only complete V0-045 replay followed by independent
typed V0-043 may certify the selected fixed plan.

## Known failure modes

State explosion, incomplete predicate grammar, no common semantic action, overly conservative envelopes, infeasible chance constraints, build cost that never amortizes, incorrect state/action group transforms, and a cache key that omits or misstates build coverage. For the exact `D4` baseline, a nonzero width is an invariant failure rather than acceptable conservatism. For the aliased profile, hard-coding its two cell IDs instead of extracting and ranking exact witnesses invalidates the CEGAR-discovery claim. For Phase 3A, using held-out fields during atom selection, accepting a cross-orbit cell reachable only outside the registered policies, or calling the eight-cell G2048 interval model an exact homomorphism invalidates the claim. For V0-039, unequal label sets, premature action mixing, unequal cross-state label dynamics, an incomplete 4096-candidate production trace, or an insufficient cap are typed failures and cannot be promoted to a direct certificate.


For V0-040, source disagreement, source/target coverage collision, profile-role
confusion, proposal-as-certificate authority or treating exact-kernel queries as
interaction samples invalidates the control. For V0-041, a hidden named-feature input,
noncanonical AST registry, incomplete 4096 trace, pre-mixture aliasing error or altered
implementation digest invalidates the generated-coordinate certificate.

For V0-042, treating self-consistent hashes as source truth, accepting a changed graph
under an old allowlisted ID, independently varying joint marginals, losing a missing
row through a derived realization, or claiming transport from retained in-memory
authority invalidates the partial-model result.
For V0-043, treating the unrestricted sound upper as J0 or an exact optimum, accepting
distribution-average regret while one support point fails, summing destination
reachability uppers as probabilities, or promoting a failed hint to infeasibility/
causal/local authority invalidates the claim. An H1 unknown does not create a future-
coverage escape, although its value or risk obligation can still fail; at H>1 a
reachable selected unknown or known external continuation must block certification.

Individual content IDs or dataclass validity are not semantic proof: authority comes
only from exact replay of the full source/threshold/plan/result graph.


For V0-044, incomplete action domains/enumeration, accepting a caller production cap,
auditing any candidate after over-cap detection, promoting a private control result,
reordering the three selection tiers/tie-breaks, replacing the selected plan or summary,
or counting model replay as environment sampling invalidates the claim. Internal
`CERTIFIED_FIXED_PLAN` is a selection label only; suppressing the mandatory independent
V0-043 audit or inferring feasibility/infeasibility from proposal/cap status is
unsound.

For V0-045, using raw integer action values as semantic labels, relaxing V1 labels to
integers or empty tuples, intersecting unequal member action-label sets, treating a
missing row as equality/mismatch evidence, trusting a caller-supplied typed table or
pure build, reusing V0-041 runtime/certificate ancestry, or repeating full synthesis as
if every planner candidate were a new model invalidates the claim. Typed consumers
must first replay one complete V0-045 result; the planner may then audit candidates on
that fixed verified model, while the selected plan still requires a separate full-chain
typed V0-043 replay.

## Open risks

Later claims about shared grammar/coordinates and practical amortization remain empirical. They do not weaken Phase 0.5 soundness obligations. V0-027 closes the immediate cross-automorphism state-alias positive control; V0-028 establishes the no-Q/value-signature portable world-model path; V0-029 executes the first strict local repair; and V0-030 closes joint finite local composition, slack-aware causality, and finite-domain sparse capability. V0-038 closes target-supervised automatic exact realization inside one fixed LMB grammar/coverage. V0-039 removes that construction-time target/signature dependency for the same finite LMB slice by direct homomorphism proof, but retains the exact ground kernel, fixed grammar and exact coverage. Automatic feature invention, partial/learned-model discovery, larger/unknown domains, held-out/cross-domain generalization, dependent-horizon recovery, workload economics/dynamic routing, and the complete statistical Phase 3/Phase 5 Gates remain open empirical work.

V0-040 closes only the source-unanimous proposal versus target-certificate authority
boundary and records sample-tax telemetry; it deliberately leaves the sample-efficiency
Gate non-blocking and unrun. V0-041 advances the mainline to generated coordinate
programs but retains a fixed human DSL, complete exact kernel and finite coverage.
Unknown-semantic invention, partial/learned dynamics, larger/unknown-domain evidence,
held-out/cross-domain generalization, an empirically designed tax-reduction operator,
and the aggregate statistical Gates remain open.
V0-042 closes conditional partial-dynamics materialization from one externally trusted
finite observation graph. V0-045 now selects coordinates observation-only inside the
fixed typed DSL, builds the same-schema partial RAPM, lets typed V0-044 plan on one
verified fixed model, and lets independent typed V0-043 certify or return a
nonauthorizing frontier. This closes the narrow symbolic-log mainline, not raw
symbolization, learned/statistical dynamics, portable source truth, larger/unknown
domains or generalization.

V0-046 now closes that loop for the fixed H1 zero-risk row-completion control. Separate
full-chain authority proves four individually necessary rows, charges exactly four
operational exact-kernel calls, preserves the base, constructs a query-owned V2 model,
and obtains an independent reward/failure/regret-zero certificate after abstract
replanning. It does not generalize causal minimality, multi-step external-boundary
recovery, or base promotion; a bare failed frontier remains nonauthorizing.

V0-047 now generalizes the mechanism to a genuine H2 two-round trace. Four first-round
rows expose three active boundary states and nine legal actions; the frozen V0-045
coordinates are reused, the first V3 epoch moves the frontier to time one, and nine
second-round value/risk rows produce a final reward/failure/regret `1/0/0`
certificate. The base remains immutable and no ground optimizer is invoked.

This closes multi-step within-query model evolution only. Preregistered multi-query/
held-out reuse and promotion, portable source authority, raw symbolization,
statistical/learned dynamics, larger or unknown domains and generalization remain
open. Matched-budget sample-efficiency evaluation and a Laplace-style tax-reduction
operator remain non-blocking follow-up work to be designed from the now-recorded
acquisition/refinement telemetry, not inferred from this one trace.
