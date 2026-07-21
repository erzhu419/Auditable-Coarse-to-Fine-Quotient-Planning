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
- **Phase 3A construction slice:** the V0-027 two-domain exact-model/oracle positive
  control. `PHASE3A_SLICE_PASS` is paired with
  `PHASE3_AGGREGATE_NOT_RUN`; malformed construction/replay uses
  `PHASE3A_INVARIANT_VIOLATION`.
- **Phase 3B portable campaign:** the V0-028 two-domain exact one-step behavioural
  world-model build plus fresh-process repeated planning. A pass is paired with
  `PHASE3_AGGREGATE_NOT_RUN`, `LOCAL_HYBRID_GATE_NOT_RUN`, and
  `WORKLOAD_ECONOMICS_GATE_NOT_RUN`.
- **Phase 3C local-recovery slice:** the V0-029 single-domain positive control that
  executes one certificate-triggered strictly local overlay while preserving its base
  RAPM/BuildEpoch. Its pass opens only `LOCAL_HYBRID_GATE_PASS`, not aggregate Phase 3
  or workload economics.
- **Phase 3D general local-recovery Gate:** the V0-030 finite, cap-aware positive
  control that closes joint value/risk composition, slack-aware causal localization,
  and sparse worker authority. Its pass is not aggregate Phase 3 or economics.
- **Phase 3E accounted dynamic-routing profile:** the contract-`1.0.0`, V0-032
  estimate-before-execute consumer profile. Its schema and acceptance obligations are
  frozen, but neither official execution nor the counter/economics Gates are open
  before their complete implementation and independent replay.

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

### Phase 3A true-state-alias oracle construction-slice gate

This gate directly follows the observation that V0-026's active histogram cells were
already complete `D4` orbits. In each domain it must produce an active cell where one
lifted training policy graph jointly reaches states from multiple complete known-
automorphism orbits, using train-only exact-model/oracle construction and held-out
evaluation on the frozen RAPMs:

```text
freeze two-domain benchmark/query/split/seed registries
-> build suite-support-union all-action closure from training queries only
-> G2048: exact train J0 table and audited two-atom oracle partition
-> LMB: query-independent exact behavioural partition refinement
-> freeze coverage, partition, semantic adapter, RAPM, and construction hashes
-> release registered held-out queries
-> validate held-out support without extending coverage
-> run J0, Jkappa, nominal J2, exact audit, and independent ground lift
-> audit complete physical automorphism orbits and policy reachability
-> emit contract-0.6 bundle and claim-boundary report
```

The G2048 total golden is `192 -> 8`; active states/cells are `68 -> 7`, active `D4`
state orbits/cells are `9 -> 7`, complete `D4` state-action orbits/abstract pairs are
`18 -> 14`, and ground active state-action pairs are `144 -> 14`. One of two mixed
active cells has members from distinct `D4` orbits jointly reached by one policy graph.
Its two training rows comprise the canonical `H=2`
safe-chain query and the strict cross-`D4` `H=1` bridge. The bridge witnesses
`(0,2,2,2)` and `(0,2,4,2)` must be jointly reached in one cell, belong to different
`D4` orbits, select `AWAY`, and reproduce reward `13/400`, failure `199/5000`, and
sound `U_F=1/25`. LMB totals are `25 -> 5`; active states/cells are
`18 -> 3`, total physical state orbits/cells `13 -> 5`, active orbits/cells `10 -> 3`,
physical state-action orbits/abstract pairs `16 -> 4`, and ground pairs `40 -> 4`; all
three active cells contain distinct-orbit members jointly reached by the same training
policy graph. The `5x` compression threshold is evaluated
on active states/cells (`68/7` and `18/3`), not on terminal/failure collapse.

Every registered train and held-out row must certify, reproduce the V0-027 rational
goldens, have exact J0-to-lifted reward gap zero and exact failure gap zero, and have
normalized regret upper bound zero. Reuse is claimed only across the registered two-
domain held-out suite: G2048 varies initial support/distribution and horizon; LMB
varies reward basis, horizon, and risk. Passing returns
`PHASE3A_SLICE_PASS/PHASE3_AGGREGATE_NOT_RUN`. It neither satisfies nor contributes a
sample to the full Phase 3 oracle or human-grammar aggregate Gate.

### Phase 3B portable RAPM campaign gate

This is the first gate framed around the project's primary object: build a reusable,
coverage-bounded auditable abstract world model once and perform repeated multi-step
contingent planning primarily inside it. Quotient construction and CEGAR remain
construction/repair subsystems. The registered chain is:

```text
freeze WorkloadSpec and per-domain build inputs
-> enumerate complete declared coverage and registered one-step feature semantics
-> refine terminal-kind cells by full exact one-step behaviour to a fixed point
-> audit builder API/data flow and behavioural/planner source imports
-> freeze and serialize one portable RAPM per domain
-> externally bind each BuildEpoch to its coverage/model IDs
-> canonical deserialize/reserialize identity check
-> launch an attested fresh bwrap process for each portable-query-v1 occurrence
-> freeze every portable-model proposal before any J0 call
-> independently exact-audit, run J0, and ground-lift as evaluation truth
-> record routes and implemented exact work-counter fields; leave scalar costs null
-> emit contract-0.7 bundle and bounded claim report
```

The workload contains eleven distinct ground queries: six G2048 and five LMB, with at
least eight distinct portable projections and four per domain, and multi-step queries
in both domains. The G2048 set contains
four `H=2` rows. The LMB set contains its earlier three rows plus canonical
`H=3,delta=1/10` and terminal-clear-only `H=3`. Duplicate/cache/diagnostic executions
do not satisfy the portable-query threshold.

Construction may use the complete exact one-step kernel, registered reward-feature
vector, entered-failure/terminal kind, and successor-block probabilities. It may not
use `Q*`, a value/frontier, selected policy/action, query reward weights, `delta`, `H`,
or evaluation output. This boundary is demonstrated through builder API/data flow and
static source audits, not a whole-run closed import DAG. The portable model embeds
coverage/coverage ID, state planning kinds, partition, nominal/exact-envelope entries,
action catalogs, concretizer, reward features, `normalizer_rules`, and `goal_ids`;
BuildEpoch is an external
binding and does not enter the model content ID.

Every occurrence runs in a fresh Linux bubblewrap mount/network namespace. It may load
only the three staged portable runtime modules, system Python libraries, the current
read-only model/query, and an initially empty writable output; the checkout and other
requests are not mounted, Python uses `-S`, and runtime evidence is content-addressed.
Portable query v1 binds cell `rho0`, horizon, raw/normalized weights,
normalizer/proof, risk, and exactly the `default` structural stopping goal. Its proof ID
must resolve in the uniquely proof-sorted registry. Each rule has
`kind=nonnegative_feature_caps_v1`, a complete uniquely name-sorted nonnegative
`reward_basis` containing every registered feature including zeros, and uniquely
name-sorted registered feature caps. Query validation requires raw weights exactly equal
to that rule's basis, so proof IDs cannot cross bases; every positive-weight feature
requires a nonnegative per-step and/or total cap,
`normalizer >= sum_k w_k min(H*per_step_cap_k,total_cap_k)`, and exact
`normalized=raw/normalizer`.

Passing requires one unchanged build epoch/RAPM per domain, canonical portable
round-trip equality, G2048 behavioural trace `2 -> 9 -> 10 -> 10` with state/action
compression `192 -> 10` and `144 -> 17`, LMB trace `3 -> 5 -> 5` with `25 -> 5` and
`40 -> 4`, an exact-sound
`ABSTRACT_CERTIFIED` multi-stage policy for every registered query, and independent
J0/lift agreement. It returns exactly
`PHASE3B_PORTABLE_RAPM_PASS/PHASE3_AGGREGATE_NOT_RUN/LOCAL_HYBRID_GATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.
Malformed construction, portability, isolation, or replay uses
`PHASE3B_INVARIANT_VIOLATION`.

The router/local-frontier interface is normative but not exercised here. A later local
hybrid may inspect ground states only after the full-plan certificate fails and only at
the earliest policy-reachable atomic `DirectBad` nodes plus exact model dependencies.
Phase 3B
has an empty local frontier and zero local/fallback charges. Likewise it records
the implemented separated build state/action/outcome/refinement/byte counters and
per-occurrence load, plan, portable/live-ground audit, local/fallback,
evaluation-only-J0, and reconciliation counters. Without a preregistered scalar cost functional it
leaves `C_world`, `C_ground`, and `N_break_even` null and does not run or pass the
workload-economics Gate.

This gate supports portable no-Q/value-signature exact world-model synthesis and reuse
on the frozen workload. It does not support automatic predicate invention, a working
local hybrid, amortized break-even, the full Phase 3/5 Gates, scale, or learning. It is
additive and does not modify V0-024--V0-027's result labels or historical claims.

### Phase 3C certificate-triggered local-recovery gate

Contract `0.8.0` registers
`phase3c_certificate_triggered_local_recovery_v0`. It is an additive execution slice,
not the aggregate Phase 3 Gate and not a modification of Phase 3B.

The gate reuses one byte-identical query-neutral eleven-cell stage-1 aliased safe-chain
RAPM and BuildEpoch for two occurrences:

1. canonical `H=1, delta=0` returns `ABSTRACT_CERTIFIED`, an empty frontier, and zero
   local/fallback/rebuild work;
2. canonical `H=2, delta=1/20` freezes an abstract proposal, fails its full-plan
   certificate, constructs the direct failed-proof frontier, runs local recovery, and
   returns a certified hybrid on `LOCAL_GROUND_RECOVERY`.

The second row passes only if the authoritative `DirectBad` antichain contains the two
reachable `h=1` cells (12 states); their ground frontier has exactly 32 state-action
pairs/128 outcomes and the strict selected-action ancestor dependency has 8 pairs/32
outcomes. Total authorization is `40 < 48` pairs and `160 < 192` outcomes versus the
same-query all-action graph, and `40 < 144` covered pairs. The isolated runtime mounts
only the 32-pair frontier ground slice plus a redacted ancestor boundary. The selected
overlay must be cardinality-minimal, bind the unchanged base model, and patch exactly
the eight-state `((1,1),(2,2))` cell (16 available pairs/64 outcomes, 8 frozen
decisions), with different legal ground actions for aliased reachable members. The
final graph must contain reachable local decisions and retain reachable
abstract root and rare `((2,3),)` decisions.

The independent post-certificate must report reward `3/64`, sound failure
`397/20000 < 1/20`, exact hybrid failure `317/16000`, and regret upper zero. J0 failure
`99/5000` is evaluation-only and starts after the overlay/hybrid/post-certificate IDs
freeze. Base-model/BuildEpoch mutation, coverage extension, a complete ground-policy
patch, early J0, hidden fallback/rebuild, or any nonminimal/out-of-scope patch fails the
gate. Fallback/rebuild counts are exactly zero; `grammar_used=false`.

The independent verifier must rebuild the kernel, coverage, stage-1 model and both
queries; reproduce proposal/audit/direct-proof DAG/frontier/minimal authorization;
rerun the isolated local solver; reconstruct overlay/hybrid/post-certificate; and only
then recompute J0, IDs, cross-links, counters and manifest. Coordinated re-signing does
not excuse a changed route/witness/slice/base/query/coverage/attestation/policy/audit/
counter. SHA-256 establishes integrity, not public-key authenticity.

Passing returns exactly
`PHASE3C_LOCAL_RECOVERY_PASS/LOCAL_HYBRID_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.
It proves certificate-triggered strictly local hybrid recovery for this positive
control. It does not prove predicate invention, unknown quotient discovery, workload
break-even, the full Phase 3/5 Gate, scale, learning, or generality.

### Phase 3D general local-recovery gate

Contract `0.9.0` registers `phase3d_general_local_recovery_v0`. It must begin by
verifying and binding a frozen Phase 3C artifact bundle, including its locality and
authorization documents as well as its run, manifest, RAPM, BuildEpoch, and local
pre-certificate. Operational execution may not
call the Phase 3C world constructor, `SuiteBuildCoverage.from_queries`/transition
closure, any partition/quotient/RAPM builder, or the ground action-unrestricted upper
routine; all such counters and all kernel steps before local authorization are zero.
The binding pass freezes a complete catalogue of all 144 covered ground actions for
causal analysis, legality, and capability costs without opening ground transitions. The
source local pre-certificate supplies frozen `U_all`. Only after the full abstract-plan
proof fails may the registered causal slice open ground dynamics; patched-cell
evaluation is then permitted for the sound post-stitch certificate. The independent
verifier may rebuild authoritative semantics only in the evaluation lane.

Its safe-chain branch must select the singleton common-cell causal family from the
earliest `DirectBad`
antichain using exact active reward-min/risk-max derivations and certificate slack.
Its 16 frontier pairs must be a strict subset of the source Phase 3C frontier's 32
pairs, while its eight reverse selected-dependency pairs must equal the source eight
exactly. The resulting `24/96` state-action/outcome figure is capability scope, not
executed work: the runner materializes only the `16/64` worker slice.

The trusted compiler must reduce the complete four-node/twenty-realization boundary to
one frontier input, zero exits, one reward-min form, and one risk-max form, with exact
equivalence and necessity witnesses over the fully enumerated finite admissible domain.
The source boundary remains a trusted audit artifact; the isolated worker mounts only
capability, request, and sparse slice. The worker must jointly enumerate deterministic
value/risk assignments under explicit caps, exhaust every lower-cardinality subset,
and return a distinct cap-exhausted status rather than certify an incomplete prefix.

Safe-chain must exhaust 257 assignments and its operational sound post-audit must
reproduce reward `3/64` and failure upper `397/20000`. Operational ground work is
exactly 16 authorized-frontier materialization steps plus eight patched post-audit
steps, 24 total, while accounting/other/outside-support steps and exact-hybrid-lift
invocations are zero. The operational post-certificate's exact reward/failure fields
are null with status `EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`. The standalone
verifier's evaluation-only authoritative rebuild/lift must then reproduce exact failure
`317/16000`, eight patched decisions, twelve retained abstract decisions, and J0 truth.
The RAPM/BuildEpoch remain byte-identical throughout. The algebraic
two-cell/two-member control must exhaust 25 assignments, localize both cells, and reach
`(1,1/25)` under thresholds `(3/4,1/20)`; its independent minimum-risk counterfactual
has value zero.
Passing returns exactly
`PHASE3D_GENERAL_LOCAL_RECOVERY_PASS/GENERAL_LOCAL_RECOVERY_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

The executable and independent replay are:

```bash
acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d
python3 scripts/verify_phase3d.py artifacts/phase3d
```

This Gate supports only the declared finite-domain, capped, earliest-antichain claim.
Dependent-horizon one-shot recovery, information-theoretic capability minimality,
automatic predicate/quotient discovery, economics, scale, learning, and cross-domain
generality remain unproved. Accounted dynamic routing and scalar-free workload-vector
mechanics are next; the scalar workload-economics Gate waits for a later ledger
revision, and learned model synthesis follows it.

### Phase 3E accounted dynamic-routing implementation Gate

Contract `1.0.0` and profile `phase3e_accounted_dynamic_routing_v0` freeze the
implementation target but do not authorize an official workload run. The runner must
first plan and audit in the frozen reusable RAPM, identify a failed-proof frontier, and
derive causal/cardinality evidence without route-specific ground execution. It then
freezes full-SHA typed local and fallback uppers and selects local only under strict
componentwise dominance; every other valid comparison selects fallback.

The Gate remains closed until all of the following pass together:

- `CounterRegistryV1` records every required operational leaf and native zero on
  abstract, local, fallback, rebuild, infeasible, cap/protocol/integrity-failure paths;
- the exact projection maps every operational charged leaf once to the eight shared
  axes, with no evaluation/provenance/diagnostic or derived double charge;
- Phase 3B/3C/3D operational consumers perform no host full-solver, unrestricted
  ground-upper, exact-lift, or J0 replay;
- the Phase 3E consumer freezes its decision before transition materialization,
  compiler, worker, stitch, post-audit, or fallback execution;
- content-addressed caps, cardinalities, uppers, decisions, transactions, work vectors,
  attestations, and terminal artifacts reject every stale or cross-role identity;
- trusted budget replay enforces continuous transaction indices, at most two local
  transactions, and all frozen V0-032 hard caps;
- failed local plus fallback, rebuild/retry, complete infeasibility, cap exhaustion,
  and every noncertificate closure retain all work and remain in logical-occurrence
  denominators; and
- an independent verifier passes the access-order, missing/duplicate counter,
  projection, upper-violation, typed-attestation, terminal-class, and hash-chain attack
  suites.

The current working implementation also has a non-official one-decision
`run_phase3e`, registered-safe-chain causal/cardinality authority, generic
route-upper/decision replay, real isolated LOCAL and capped fallback adapters,
route-native aggregation/upper compliance, terminal/occurrence evidence, and generic
authority-gated second-decision control: after failed post-audit the new marginal
decision can select local transaction 2 or direct fallback without manufacturing a
transaction. Negative local worker results close after the legal three-stage prefix and
also require a fresh fallback decision. Phase 3B/3C/3D expose
no-full-replay modes and Phase 3D exposes a pre-execution estimate boundary. The
registered safe-chain LOCAL positive control executes `16+8` ground steps only after
decision freeze and closes with independent local-result and sound-post-audit semantic
results. Preselection binds failed-certificate/action-catalogue identities, charged
semantic evidence forms an exact decision/upper/cardinality dependency closure,
capability/worker/stitch/post-audit identities cannot be substituted, and both selected
routes preserve already observed work incrementally on failure.

This vertical-slice milestone still does not satisfy the implementation Gate. V0-033
closes the former four scoped P0 interfaces: non-cyclic terminal/certificate-verification accounting,
continuation `WORK_VECTOR` verification in the next common prefix, a sealed
post-freeze executor factory over a content-addressed runtime tree, and occurrence-level
typed noncertificate closure plus aggregate-terminal semantics. Within those interfaces,
manifest-derived `RuntimeFactoryCardinalityV1` now enters route uppers, successful
construction receipts bind the final access log, failed sealed execution has an exact
factory/delegate/merged decomposition, and rejected packages preserve observed verifier
work as `PARTIAL_ACCOUNTED_COMMON`. The sealed safe-chain fallback additionally
freezes `control.cap_checks=5815=3 factory+5812 worker`, tests total `5812` as a
worker-`5809` cap rejection, prohibits post-hoc reserve addition, and preserves the
reserve-zero legacy identity. Registered nonsemantic checks now replay typed evidence
and reject core/suffix record reuse; occurrence results reconstruct their ordered
aggregate, runs, transactions, closure and terminal authority at their own boundary.
These are scoped component closures, not the Phase
3E implementation Gate or the reusable-world-model research objective. Exact cached-
infeasibility and abstract-audit authority, a registered live dependent second-decision
benchmark, rebuild/retry and complete all-path native/hash instrumentation—including
planner/package control, every terminal branch, and the still-unassigned
`common.hash_invocations` leaf—an upstream
manifest-to-prepared-run consumer, and an independent bundle verifier still remain
absent. A scoped runtime pass cannot be relabelled as an official workload run.

Until then the required tuple is exactly:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
```

Vector prefix/worst-order mechanics may be tested, but no scalar or break-even claim
may be emitted. In particular, `ops + bytes/4096` is not an official surrogate.

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

run_phase3a_slice(registry):
  for domain in (G2048,LMB):
    coverage = suite_union_closure(registry.train_queries(domain))
    rapm = construct_from_train_only(domain,coverage)
    freeze(coverage,rapm)
    evaluate(registry.train_queries(domain) + registry.heldout_queries(domain))
    assert active_compression_at_least_5x()
    assert reached_cross_automorphism_active_cell()
    assert all_exact_reward_and_failure_gaps_zero()
  return PHASE3A_SLICE_PASS, PHASE3_AGGREGATE_NOT_RUN

run_phase3b_campaign(workload):
  freeze workload
  for domain in (G2048,LMB):
    rapm = full_one_step_behavioural_fixed_point(domain,workload.coverage(domain))
    audit builder API/data flow and behavioural/planner source imports
    serialize_and_verify_canonical_roundtrip(rapm)
    epoch = externally_bind(rapm.coverage_id,rapm.model_id,construction_provenance)
  for q in workload.ordered_queries:
    pq = portable_query_v1(rapm[q.domain],q,goal=default)
    result = fresh_bwrap_process_plan_only(rapm[q.domain],pq,python=-S)
  freeze all workload proposals before J0 starts
  for result in frozen_results:
    exact_audit_J0_and_ground_lift(result)
    require result.route == ABSTRACT_CERTIFIED
    require independent_J0_and_ground_lift_agree(result,q)
  reconcile_all_workload_cost_prefixes()
  return PHASE3B_PORTABLE_RAPM_PASS,
         PHASE3_AGGREGATE_NOT_RUN,
         LOCAL_HYBRID_GATE_NOT_RUN,
         WORKLOAD_ECONOMICS_GATE_NOT_RUN
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
- Phase 3A held-out queries are absent from the construction dependency graph; support
  validation after freezing cannot extend or rebuild the RAPM.
- Phase 3A Gate arithmetic uses active states/cells and records terminal/total counts
  separately. A cross-automorphism witness passes only when one lifted training policy
  graph reaches at least two physical-orbit members inside the same active cell.
- A construction-slice pass cannot be promoted to the full Phase 3 aggregate status.
- A Phase 3B external build epoch and portable RAPM are immutable across all domain
  queries; no query/result enters the builder API/data flow. Epoch and extensional
  model IDs are separate content-addressed objects.
- Phase 3B fresh planner occurrences attest their bubblewrap mount/network namespace,
  three staged modules, `-S`, read-only current inputs, initially empty output, and
  absence of the checkout/other requests.
- Local recovery cannot occur before a failed certificate and is limited to the
  earliest policy-reachable atomic `DirectBad` proof frontier; Phase 3B never exercises
  it.
- A Phase 3B pass cannot be promoted to full Phase 3, local-hybrid, economics, or Phase
  5 status and cannot relabel an earlier positive control.

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
- Phase 3A tests reproduce the 20-state G2048 training-support union, total/active/
  orbit/action counts `192/8`, `68/7`, `9/7`, `18/14`, and `144/14`, plus LMB
  `25/5`, `18/3`, `13/5`, `10/3`, `16/4`, and `40/4`.
- Reordering or mutating held-out rows cannot change a construction hash. All nine
  registered evaluations have zero exact reward and failure gaps; an uncovered support,
  held-out dependency, terminal-only mixed cell, or missing aggregate-not-run status
  fails the slice.
- Phase 3B tests independently rebuild both kernels, coverages, one-step fixed-point
  models, and G2048/LMB authority normalizer registries; they reproject six/five queries,
  require the three LMB proof IDs to bind `(match,terminal_clear)` bases
  `(1,1),(1,0),(0,1)` without cross-use,
  recompute portable/live-ground audits, serialized-`kappa` lift and J0, check content
  IDs/cross-links/counters, and can replay
  the attested isolated planner occurrences. They also check unchanged per-domain IDs,
  strict state/action compression, exact-sound certificates, and J0/lift equality.
- Injecting Q/value/policy/query/evaluation input at the builder/planner audit boundary, deleting a portable
  dependency, mutating an epoch between queries, or recording a non-abstract route
  returns `PHASE3B_INVARIANT_VIOLATION`.
- Work-counter tests reconcile build/load/plan/audit/local/fallback components, preserve
  evaluation J0 separately, and require scalar costs/break-even null; missing any
  required not-run status fails the gate.
- Phase 3C tests reproduce the direct frontier, strict authorization, isolated minimal
  overlay, mixed policy, immutable base and post-audit goldens; independent replay
  rejects coordinated re-hashing of route/witness/slice/patch/base/query/attestation/
  evaluation-order/certificate/counter forgeries.
- Phase 3D tests first reject malformed Phase 3C source bundles and prove forbidden
  constructors/builders/closure/ground-upper routines are never called, source RAPM/
  epoch bytes and provenance links are preserved, source locality/authorization are
  embedded, the complete 144-action binding catalogue is used, and all
  binding/pre-authorization transition counters are zero. They then prove current
  frontier `16` is a strict subset of source `32`, reverse support `8` equals source
  `8`, and reproduce the `24/96` capability scope, `1/0/1+1` sparse capability, and
  257/25 exact search counts. Access accounting must be exactly 16 materialization plus
  eight patched sound-audit steps, with other/outside `step` calls zero and operational exact
  fields null. Evaluation-only replay must recover `317/16000`, the `8/12` decision
  split, and J0; forged active derivations, mounted source boundaries, capability
  extras/deletions, local choices, caps, or counters fail.

## Out of scope

Implementing Phase 1–7 in the Phase 0.5 milestone, claiming their Gates from smoke fixtures, crediting the supplied `D4` positive control with automatic quotient/predicate discovery, crediting the aliased profile with predicate invention or unknown-symmetry discovery, crediting the Phase 3A exact-model slice with a full Phase 3 pass or oracle-free unknown-quotient discovery, crediting Phase 3B with a local-hybrid result, or crediting Phase 3D with break-even or a full Phase 3/5 result.

## Known failure modes

The coarse policy can be immediately infeasible, no predicate may separate the witness, every useful split may exceed rate, and an accepted split may still end in charged fallback. These are valid measured outcomes, but Phase 0.5 still requires a fixture with one accepted split. An implicit default support, incomplete all-action closure, or coverage-free cache key is unsound. In the exact `D4` gate, incomplete orbit closure, action-transform errors, stabilizer multiplicity bias, or nonzero envelopes are hard validation failures and are never repaired by refinement. In the aliased gate, replacing the deliberate boundary adapter with equivariant actions, forcing a third split after certification, or hiding the final risk gap changes the registered experiment. In Phase 3A, held-out leakage, thresholding compression on terminal collapse, or reporting a cross-orbit cell unreachable by the training policy invalidates the slice.

## Open risks

Resolved `V0-RISK-001` proves that the frozen canonical `2x2` G2048 query is ground-infeasible for every registered positive risk threshold (`383/410` first-step failure). The Phase 0.5 expected ending for that regression remains mandatory refinement followed by fully charged fallback and `INFEASIBLE_QUERY`, not a safe quotient certificate. Resolved `V0-RISK-002` freezes the separately keyed safe-chain route as a no-split exact `D4` positive control; implementation must not silently tune either fixture or infer CEGAR success from that control.

Resolved `V0-RISK-003` is enforced by explicit query-support transition closure and a
coverage-specific build identity. This resolution does not claim unrestricted reuse
across arbitrary initial distributions.

V0-026 closes the small feasible aliased-CEGAR positive-control contract. It does not
close the later empirical question of automatically generating strategic predicates or
discovering useful quotients on larger fixtures.

V0-027 closes the next exact-model/oracle construction slice and removes the immediate
“all active cells are already one known-symmetry orbit” limitation. Oracle-free
predicate/quotient discovery, the human-grammar branch, larger seeds, and the complete
Phase 3 `60/20/40` aggregate remain unrun.

V0-028 closes the no-Q/value-signature portable world-model campaign slice. V0-029
closes the first certificate-triggered strict local-ground-recovery positive control.
V0-030 resolves `V0-RISK-004..006` for current-earliest-antichain causal search,
finite-domain sparse capability, and capped joint deterministic composition. Deeper
recovery, workload economics/dynamic routing, larger workloads, and the full Phase 3/5
Gates remain explicitly unrun.

Later Gate denominators and statistical aggregation details also need a preregistered analysis plan before Phase 3 test evaluation; the threshold values above are already frozen.
