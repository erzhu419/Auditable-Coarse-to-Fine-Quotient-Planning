# Audit Ladder

## Definitions

- **J0:** exact symbolic state, legal ground primitive actions, exact kernel, exact constrained finite-horizon DP.
- **J1:** replace only state representation with an interval state quotient; retain ground-action identities.
- **J2:** additionally use semantic actions and the frozen concretizer.
- **J3/J4/J5:** respectively replace the model, restrict search, and replace symbolic observation; all are post-V0.
- **Evidence labels:** `oracle_truth`, `exact_sound`, `statistical_high_probability`, `diagnostic_only`.
- **Audit channels:** value/regret, failure risk, action availability/restriction, transition/reward width, and accounting.
- **Construction-dependency audit:** builder API/data-flow evidence plus static source
  audits that the behavioural builder and portable planner exclude
  Q/value/policy/query/evaluation signatures; it is not a whole-run import-DAG proof.
- **Local ground frontier:** the earliest antichain of policy-reachable atomic
  selected-action `DirectBad` residuals in the proof-dependency DAG, together with its
  exact model dependencies; propagated ancestor-bound failures do not enter it, and it
  is empty until a contingent plan fails audit.

## Normative decisions

V0 implements J0–J2. Every comparison uses the same initial states/distributions, horizon, hidden layout, failure definition, and (for sampled replay diagnostics) realized random tapes. `J_i-J_{i+1}` is a replacement-order-dependent telescoping identity, not a causal decomposition.

Before J1/J2 planning or certificate lookup, the query support is validated against the
RAPM's explicit `query_support_transition_closure`. The build identity commits to its
canonical initial-declaration hash, covered-state count, and no-outside-reuse flag.
`rho0` remains query semantics; matching a structural ID alone is never sufficient to
reuse an abstract model or proof. An uncovered initial state rejects reuse before any
nominal proposal and cannot be repaired by pretending the missing region has a wide
envelope.

J0 and J2 selectors are deterministic finite-horizon Markov policies. A stochastic frozen concretizer is part of J2 action realization; it does not permit randomized selectors, query-time policy mixtures, or frontier convexification.

The constrained planner keeps a nondominated frontier `F_h(z)={(L_R,U_F,subpolicy)}`. Entry `a` dominates `b` iff its lower return is no smaller and its failure upper bound is no greater, with at least one strict inequality. At query threshold `delta`, select maximum `L_R` among entries with `U_F<=delta`; nominal quantities may only order otherwise admissible candidates.

The production certificate is exact-sound backward induction over the complete reachable graph:

```text
regret_bound = E_rho0[U_all(H,phi(x)) - L_pi(H,phi(x))]
risk_bound   = E_rho0[U_F(H,phi(x),pi)]
accept iff regret_bound <= 0.05 and risk_bound <= delta
```

For a requirement that holds for each possible initial state rather than only in expectation, the artifact additionally records and checks the maximum pointwise bound over `supp(rho0)`. Phase 0.5 reports both.

Regret evidence always records the raw value gap, exact `Rmax(q)` and its proof ID, and
the resulting normalized regret. Frontier pruning compares deterministic contingent
policies only; it never manufactures a convex combination.

On J0-capable instances also report `Delta_action = V_ground* - V_kappa-restricted*` as `oracle_truth`. It is diagnostic and is never substituted for the production certificate.

Phase 3A records all three quantities separately for every query:

```text
J0       = unrestricted deterministic ground constrained optimum,
Jkappa   = deterministic ground optimum under the frozen semantic concretizer,
J2_lift  = independent ground evaluation of the lifted abstract selector.
```

It reports `J0-Jkappa` as the action-restriction gap, `Jkappa-J2_lift` as the
state-alias selector gap, and `J0-J2_lift` as the full gap. A sound audit remains the
certificate; equality to J0 is a registered positive-control check, not a replacement
for `U_all/L_pi/U_F`.

The safe-chain exact `D4` positive control is a special J0-versus-exact-J2 equality
audit. It first verifies the registered group is an automorphism of legal actions,
reward, one-time failure cost, exact kernel, and terminal semantics on the complete
reachable state-time graph. Its J2 cells are complete equal-stage state orbits;
semantic actions are stabilizer orbits; and `kappa` is uniform over distinct inverse
ground actions. Every representative must induce exactly the same abstract tuple, so
the nominal model and independently checked sound envelope both collapse to that point.

This audit requires `V_h^*(x)=Vbar_h^*([x,h])` for every reachable node, equal ground
and lifted constrained return/risk, failure `99/5000`, and `Delta_action=0`. It performs
no refinement or fallback. A nonzero interval, nonsingleton transition set, illegal
concretizer support, representative disagreement, or J0 mismatch returns
`EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` and invalidates the known-symmetry certificate.

The aliased safe-chain profile is instead an ordinary J2 interval audit with
`abstraction_source=deliberately_aliased_boundary_actions`.
It uses the same J0 and query but an order-dependent boundary-action adapter. The ten-
cell histogram base partition has no state-orbit error—each active histogram is one
`D4` orbit—but its cells do not make `canonical:first/last` equivariant. Exact audit
witnesses expose that state/action mismatch. The standard ranking selects two local
four-bit applications of the registered adjacency predicate. The final J2 policy is
reward-optimal and soundly feasible but not risk-identical to J0:

```text
J0:        reward=3/64, failure=99/5000
lifted J2: reward=3/64, failure=317/16000
sound J2:  regret_upper=0, U_F=397/20000 < 1/20.
```

The exact lifted-risk gap `1/80000` and envelope conservatism `3/80000` remain visible;
neither can be rounded away or described as exact policy preservation.

The Phase 3A construction slice audits one frozen train-built RAPM per domain against
both training and held-out queries. It first proves that held-out query records are not
inputs to coverage construction, G2048 oracle-atom selection, LMB behavioural
refinement, semantic-action construction, or RAPM hashing. It then validates held-out
support against the frozen suite closure and runs J0, Jkappa, nominal J2, exact sound
audit, and independent ground lift without rebuilding.

Cross-automorphism nontriviality is an audit channel: enumerate the complete known
physical automorphism group and, separately for each lifted training policy graph,
count the distinct physical orbits actually reached inside each active cell. Require
at least two reached orbits in one cell per domain. A cross-orbit cell with only one
reached orbit, or orbit members reached only across different query graphs, fails.
Terminal aggregation cannot satisfy this check. The G2048
control remains an interval quotient whose risk bound may be conservative; the LMB
behavioural model must have singleton realization sets. Passing every per-query audit
and golden comparison returns `PHASE3A_SLICE_PASS` together with
`PHASE3_AGGREGATE_NOT_RUN`, not a Phase 3 aggregate result.

G2048 makes the reachability test strict with a second training query. Its `H=1`
bridge gives positive mass to complete `D4` orbits of `(1,1,2,0)`, `(2,2,2,0)`, and
`(2,2,4,0)`. The audit requires non-orbit witnesses `(0,2,2,2)` and `(0,2,4,2)` to
be jointly present in one lifted decision graph and one oracle cell, with semantic
action `AWAY`; merely reaching different members under different queries is
insufficient.

The reuse audit is joint and limited to the registered two-domain held-out suite:
G2048 exercises initial-support/distribution and horizon changes at fixed reward/risk;
LMB exercises reward-basis, horizon, and risk changes at fixed support. It cannot emit
a per-domain “all axes covered” or arbitrary-query reuse claim.

Phase 3B audits a different boundary: whether a reusable world model is independently
portable and query-neutral enough that repeated contingent planning occurs primarily
inside it. Before any query, builder API/data-flow checks and static source audits must
show that the fixed-point builder used only complete exact one-step reward-feature,
failure/terminal, and successor behaviour and did not observe `Q*`, a value/frontier,
selected action/policy, query reward/risk/horizon, or evaluation result. This evidence
is scoped to the builder/planner boundaries; it is not a whole-run closed-import-DAG
claim.

After serialization, every registered occurrence is issued to a fresh Linux bubblewrap
mount/network namespace with staged copies of only `portable.py`,
`portable_planner.py`, and `portable_runtime.py`, the current read-only RAPM/query, and
an initially empty writable output. The checkout and other requests are not mounted;
Python runs with `-S`, and a content-addressed runtime attestation records inputs,
module origins, namespace status, and output. Portable query v1 binds cell `rho0`, `H`,
raw/normalized weights, normalizer/proof, risk, and exactly the supported `default`
structural stopping goal. The model's canonical `normalizer_rules` registry contains
unique proof IDs of kind `nonnegative_feature_caps_v1`. Each proof binds a complete,
unique, name-sorted `reward_basis` over every registered feature, including explicit
zero weights. Registered feature caps are uniquely sorted by name and nonnegative;
every positive-basis feature supplies a per-step and/or total cap. Query audit requires
a registered proof, raw weights exactly equal to its basis, exact
`normalized=raw/normalizer`, and
`normalizer >= sum_k w_k min(H*per_step_cap_k,total_cap_k)` over present caps; each
positive-weight feature must be covered. The process reconstructs a multi-stage abstract policy graph.
Only after every proposal freezes does the independent exact audit/J0/lift
evaluation phase load authoritative ground evidence; it may not appear in construction
or planner dependencies. Model identity and bytes remain unchanged across the campaign.

The general audit router returns `ABSTRACT_CERTIFIED` when both full-plan obligations
pass. Only otherwise may it form the earliest atomic `DirectBad` antichain and request
`LOCAL_GROUND_RECOVERY`; inability to repair routes to charged full fallback,
rebuild, or infeasibility. The Phase 3B campaign exercises only the first route, so an
empty local frontier and `LOCAL_HYBRID_GATE_NOT_RUN` are required rather than evidence
that local repair works.

Workload audit reconciles the implemented build state/action/outcome/refinement/byte
counters; per-occurrence load bytes, abstract candidates/frontier/decision nodes,
portable/live-ground audit reachability, local/fallback zeroes, and evaluation-only J0
candidates; plus their reconciliation totals. A scalar prefix equation requires a
preregistered cost functional. Phase 3B
freezes none, leaves scalar totals/break-even `null`, and reports
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

### Contract 0.8.0 certificate-triggered local-recovery audit

The Phase 3C profile executes, rather than merely exposes, the local route. Its audit
order is immutable:

```text
freeze base abstract proposal
-> fail complete exact-sound value/risk certificate
-> inventory atomic DirectBad residuals and proof dependencies
-> take the earliest direct-failure antichain
-> authorize the minimal ground/reverse-dependency slice
-> run isolated local repair on slice + redacted boundary only
-> stitch a mixed abstract/local policy
-> repeat the complete exact-sound certificate
-> freeze route
-> open J0 for evaluation only
```

`PropagatedBad` is diagnostic only: a root whose bound inherits downstream uncertainty
does not authorize root reopening. The registered `H=2, delta=1/20` occurrence must
produce two `h=1` frontier cells with 12 states, 32 frontier state-action pairs/128
outcomes, and 8 selected-action-concretizer ancestor pairs/32 outcomes. Total
authorization is `40 < 48` pairs and `160 < 192` outcomes versus the same-query
all-action graph and `40 < 144` covered pairs. The isolated worker mounts only the
32-pair frontier slice; ancestor support is a redacted boundary. Local repair may patch
only the eight-state `((1,1),(2,2))` cell (16 available state-action pairs/64 outcomes,
8 frozen decisions), while root and rare `((2,3),)` nodes remain abstract. A
whole-ground policy, any base-model mutation, or a J0-derived patch fails the route
audit.

The post-auditor is independent of the local selector and recomputes reward `3/64`,
sound failure `397/20000`, exact hybrid failure `317/16000`, and regret upper zero.
Only after that record freezes may the evaluation auditor compute J0 failure
`99/5000`. The companion `H=1, delta=0` occurrence must certify directly, with no
frontier or local artifact. The successful result tuple is
`PHASE3C_LOCAL_RECOVERY_PASS/LOCAL_HYBRID_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`;
fallback/rebuild counters are zero and `grammar_used=false`.

Independent replay reconstructs the kernel, closure, base model, query projections,
proposal, direct-proof DAG/frontier, minimal slice, isolated repair output, overlay,
hybrid graph, post-certificate, evaluation order, IDs and counters. Verification must
reject coordinated re-hashing of any route reversal, omitted/added/non-earliest
witness, under/over-authorized slice, out-of-scope patch, lost abstract node, changed
base/query/coverage, false or reused isolation attestation, early J0, hidden fallback,
forged post-certificate, or work-counter discrepancy. A SHA-256 manifest proves content
integrity under replay, not signer identity.

### Contract 0.9.0 slack-aware general local-recovery audit

Phase 3D replaces reachability-only DirectBad authorization with an exact causal audit:

```text
verify the complete frozen Phase 3C artifact bundle
-> bind its RAPM/BuildEpoch, locality, authorization, and pre-certificate upper
   with zero ground transitions
-> freeze failed selected plan and certificate obligations
-> evaluate reward-min/risk-max Bellman circuit with all tied active extremizers
-> search slack-aware ambiguity-discharge sets on the earliest DirectBad antichain
-> compile trusted boundary to a finite-domain-minimal sparse capability
-> mount only capability + occurrence request + sparse ground slice
-> jointly enumerate deterministic value/risk assignments under explicit caps
-> stitch and repeat the full authority audit
-> independently replay causal, compiler, solver, and hybrid evidence
```

The first two arrows are operationally normative. Source Phase 3C `locality` and
`authorization` documents are verified and embedded alongside its RAPM, BuildEpoch,
run, manifest, and pre-certificate. The binding scan freezes a complete catalogue of
all 144 covered ground actions; causal construction, action legality, and capability
costing must use that catalogue rather than opening the kernel. The runner may not call
`construct_phase3c_world`, `SuiteBuildCoverage.from_queries`/transition closure,
partition/quotient/RAPM construction, or
an action-unrestricted ground-upper routine. The abstract pre-audit reevaluates the
selected policy against the frozen serialized envelope and the source pre-certificate's
content-addressed `U_all`. Ground transitions become available only after that proof
fails: operational execution materializes exactly 16 causal-frontier pairs and later
steps exactly eight patched pairs for the sound post-stitch audit. Its total is
therefore 24 ground `step` calls, with zero accounting/other `step` calls and zero steps
outside the authorized-or-patched support. The operational runner does not perform an
exact full-hybrid lift; its exact fields remain null under
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`. An independent verifier may rebuild
and lift everything, but only as evaluation-side evidence.

For safe-chain, baseline risk is `5099/10000` and the failed-obligation deficit is
`4599/10000`. Discharging the common cell yields `397/20000` (gain `9801/20000`),
whereas the rare cell yields `10197/20000` (gain `1/20000`) and cannot close the
obligation. The causal family is therefore the common singleton. Its 16 frontier pairs
form a strict subset of the source Phase 3C frontier's 32 pairs, while its eight reverse
selected-dependency pairs equal the source eight exactly. The resulting `24/96`
pairs/outcomes describe capability scope, not work performed: only the 16/64 frontier
slice is materialized before planning, and the reverse 8/32 is supplied by frozen
authority evidence. The compiler proves the four-node/twenty-row
source boundary extensionally equal to one input, zero exits, one reward-min form, and
one risk-max form on the complete finite admissible port domain. The source and proof
remain trusted bundle artifacts but are absent from worker mounts.

The exact global solver exhausts 257 safe-chain assignments and 25 assignments in the
two-cell/two-member trade-off control. It must reproduce respectively
`(reward,risk)=(3/64,397/20000)` and `(1,1/25)`; the latter distinguishes the joint
search from the value-zero independent minimum-risk rule. The first pair is the
operational sound post-audit result. Only the standalone verifier's evaluation-only
authoritative rebuild/lift may additionally report exact hybrid failure `317/16000`,
eight patched decisions, twelve retained abstract decisions, and J0 truth. A cap hit is
an explicit noncertificate, never a pass. Successful replay returns
`PHASE3D_GENERAL_LOCAL_RECOVERY_PASS/GENERAL_LOCAL_RECOVERY_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

Run and independently audit the bundle with:

```bash
acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d
python3 scripts/verify_phase3d.py artifacts/phase3d
```

### Contract 1.0.0 accounted dynamic-routing foundation audit

Phase 3E is an execution discipline around the scientific object established by
Phases 3A--3D, not a replacement for it.  The primary object remains a reusable
abstract world model in which multi-step contingent plans are synthesized and
audited.  Ground distinctions become eligible only when that model cannot certify
the selected plan at the registered value and risk thresholds; even then, the route
may reopen only the failed-proof causal region or invoke a charged full fallback.

The current contract-1.0 implementation closes the following component-level audit
surfaces:

- full, domain-separated SHA-256 identities over strict canonical JSON for the new
  accounting, routing, workload, campaign, and access-protocol artifacts;
- the canonical native counter registry, explicit observed native zeroes,
  route-family separation, reconciliation records, and exact projection to the eight
  shared resource axes with the registered sum/max reducers;
- exact actual projection from referenced work records, common-prefix versus marginal
  separation, context-bound selected-upper compliance mechanics, and
  provenance-preserving occurrence sums;
- typed route contexts, frontier/causal/cardinality/cap/transaction identities,
  strict-dominance marginal selection, trusted budget replay, terminal class/code,
  rebuild policy, logical-occurrence closure, and scalar-free vector-prefix/worst-order
  mechanics;
- exact marginal route-upper arithmetic from complete explicit pre-execution count
  claims,
  all 34 operational leaves, the official projection, 13 native local hard-cap
  minima, and six structural-cap guards, with a replayable formula/proof identity that
  explicitly carries `authorizes_route_selection=false`;
- a fail-closed semantic-verifier registry whose work-vector, actual-projection,
  access-protocol and terminal-classification roles replay authoritatively while
  cardinality, route-upper, route-decision and the other unresolved FQ7 roles return
  `NOT_IMPLEMENTED`; plan and infeasibility terminal labels therefore cannot acquire
  authority from a hash-only attestation; and
- fail-closed estimate-before-execute access logs plus explicit Phase 3B/3C/3D
  operational no-full-replay modes.  Phase 3D can prepare its failed-plan, causal and
  action-catalogue estimate context without a kernel step, materialization, compiler,
  or worker launch.

The component replay order is:

```text
strict canonical decode and domain-ID verification
-> counter-registry and native-zero/reconciliation verification
-> materialize canonical WorkVectorV1
-> exact projection to ComparisonVectorV1
-> replay context/frontier/causal/cardinality/cap/formula/upper arithmetic
-> require semantic cardinality/upper/decision authority (currently fail closed)
-> verify decision-freeze access prefix
-> permit only the selected route's post-freeze event family
-> recompute actual projection and per-axis selected-upper compliance
-> replay transaction indices/budgets and preserve failed-attempt work
-> derive logical-occurrence closure and scalar-free workload prefixes
```

Unit and attack tests currently reject noncanonical or cross-domain IDs; missing,
duplicate, unknown, wrongly typed, wrongly scoped, or implicitly zero counter leaves;
local/fallback family mixing; byte double charging; forged actual comparisons and
self-signed workload vectors; stale or rebound formulas/uppers; foreign selected
uppers; incomplete cardinality inputs; structural-cap overrun;
negative causal evidence reopened by a cheap local estimate; unimplemented semantic
roles represented by plausible attestations; discontinuous or substituted
transactions; cross-occurrence sums; pre-freeze execution; reversed local execution
stages; fallback paths with local artifacts; deleted/reordered access events;
hash-only campaign terminals; hidden noncertificate occurrences; worker-frontier
self-uppers; and injected legacy scalar or break-even claims.

This is not yet a run-level Phase 3E certificate.  Production-native instrumentation
has not been connected across every operational and failure path; a real direct
fallback route, the second-transaction execution loop, the complete role-authority
semantic verifier registry, an end-to-end `run_phase3e`, and an independent bundle
verifier remain absent.  Consequently no typed terminal produced by these component
tests establishes plan feasibility or infeasibility, and the locked result remains:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
```

## Pseudocode / schema

```text
frontier(z,h):
  enumerate each admissible semantic action
  compose exact child frontier entries over all outcomes
  derive sound (L_R,U_F)
  attach contingent child choices
  remove dominated duplicates deterministically

audit_or_fallback(rapm,q,pi):
  require build_coverage.mode == query_support_transition_closure
  require supp(q.rho0) subseteq build_coverage.covered_states
  require build_id commits to the complete coverage descriptor
  if production_profile and exact J0 proves infeasible for identical
     (structural_id, build_id, kernel_hash, query_hash):
    return INFEASIBLE_QUERY without refinement
  bounds = backward_audit(all reachable (z,h))
  if bounds pass: return CERTIFIED
  if refinement can continue: return counterexample
  result = J0.solve_same_query(q)
  return GROUND_FALLBACK or INFEASIBLE_QUERY, with full charges

audit_exact_D4(quotient,q):
  verify exhaustive state/action/kernel automorphisms
  verify canonicalizer-independent action orbits
  verify distinct inverse-action concretizer support and exact masses
  verify representative-independent point dynamics and singleton envelope
  compare every reachable value plus constrained root return/risk against J0
  return CERTIFIED if all exact equalities hold
  else EXACT_D4_QUOTIENT_INVARIANT_VIOLATION without refinement/fallback

audit_refine_aliased_safe_chain(rapm,q):
  assert complete coverage count == 192 and base leaves == 10
  repeat exact proposal audit and extract all reachable witnesses
  jointly rank every separating six-feature grammar candidate
  accept one ordinary local split or return the normative terminal status
  stop immediately when aggregate and all eight pointwise audits certify

audit_phase3a(construction,Q_train,Q_heldout):
  verify construction_dependency_graph excludes Q_heldout
  verify same frozen coverage_id, partition_id, adapter_id, rapm_id for every query
  verify heldout supports are subsets of suite coverage
  verify same-policy jointly reached cross-automorphism active cells
  for q in Q_train + Q_heldout:
    J0 = solve_unrestricted_ground(q)
    Jkappa = solve_concretizer_restricted_ground(q)
    proposal = solve_nominal_RAPM(q)
    sound = exact_full_plan_audit(proposal,q)
    lifted = evaluate_lift_on_ground(proposal,q)
    require registered exact values and sound.certified
  return PHASE3A_SLICE_PASS, PHASE3_AGGREGATE_NOT_RUN

audit_phase3b(workload, portable_models):
  audit builder API/data flow and behavioural/planner source imports
  verify canonical portable roundtrip and one immutable model per domain
  for q in workload.ordered_queries:
    pq = project_to_portable_query_v1(q, portable_model(q.domain))
    result = launch_fresh_bwrap_process(portable_model(q.domain), pq)
    verify attested read-only inputs, three staged modules, -S, namespaces, empty output
    freeze result
  assert all proposals frozen before J0 starts
  for result in frozen_results:
    certificate = independent_exact_audit(result)
    require certificate.certified and certificate.route == ABSTRACT_CERTIFIED
    compare independent_J0_and_ground_lift(result,result.query)
  verify separated_work_counters and empty local_ground_frontier summary
  return PHASE3B_PORTABLE_RAPM_PASS,
         PHASE3_AGGREGATE_NOT_RUN,
         LOCAL_HYBRID_GATE_NOT_RUN,
         WORKLOAD_ECONOMICS_GATE_NOT_RUN

local_frontier(policy_graph,audit):
  bad = reachable nodes with failed value/risk obligation
  return {u in bad : no strict policy-graph ancestor of u is in bad}

audit_phase3e_foundation(frozen_rapm, failed_plan, preexecution_evidence):
  require failed_plan is selected in and rejected by the reusable RAPM certificate
  prepare context/frontier/causal/cardinality evidence without route execution
  verify full domain IDs, registered caps, formulas, and exact eight-axis uppers
  freeze marginal route decision before any forbidden access
  execute only selected route family; retain common prefix separately
  recompute actual WorkVector and ComparisonVector from native records
  require actual <= selected upper on every shared axis
  replay transactions, terminal class, occurrence closure, and vector prefixes
  return COMPONENT_REPLAY_ONLY  # not an official plan/infeasibility certificate
```

## Invariants

1. Failure feasibility is decided with `U_F`, never nominal risk.
2. `U_all` uses all legal ground actions, not only `kappa` support.
3. Fallback preserves every `QuerySpec` field.
4. Evidence labels are not upgraded by good empirical agreement.
5. J0–J2 comparisons change only the named component.
6. The known-infeasible shortcut is production-only and requires identical structural
   ID, build ID, kernel hash, and query hash; the named Phase 0.5 canonical G2048
   regression still executes its required split and charged fallback.
7. The safe-chain exact `D4` audit never interprets an invariant violation as an
   ordinary counterexample requiring refinement.
8. Uniform concretizer weights are attached to distinct inverse ground-action IDs,
   never to stabilizer elements with duplicate images.
9. J1/J2 never read, optimize over, or certify a state outside the coverage committed
   by `build_id`; query-owned `rho0` is not inferred from a domain default.
10. The aliased J2 run uses full-V0 budgets and charges base leaves plus both four-bit
    splits; certification after the second accepted split forbids an additional
    tightening split.
11. Phase 3A construction is train-only; held-out queries share a frozen RAPM but not a
    construction dependency.
12. Cross-automorphism evidence is computed per lifted training policy graph using the
    complete registered physical automorphism group; one active cell must contain
    reached states from at least two of its physical orbits in that same graph.
13. `PHASE3A_SLICE_PASS` does not satisfy or alter the sample-size/aggregate thresholds
    of the full Phase 3 oracle Gate.
14. Phase 3B builder API/data flow and statically audited behavioural/planner imports are
    disjoint from J0/value/policy/evaluation truth. Fresh-process attestations prove the
    narrower per-occurrence runtime boundary; no whole-orchestrator closed DAG is claimed.
15. `LOCAL_GROUND_RECOVERY` is impossible when the full plan certifies; its frontier is
    policy-reachable, failed, earliest, and coverage-bounded.
16. Phase 3B's portable pass always co-occurs with all three frozen `*_NOT_RUN` statuses.
17. Phase 3D authorization excludes a DirectBad node unless a capped exact active-
    derivation counterfactual shows that an allowed causal set can close every failed
    root obligation.
18. Trusted Phase 3D source/capability evidence is auditable but never part of the
    three-file isolated worker authority.
19. Search-cap exhaustion cannot be relabelled certified; all lower-cardinality subsets
    and declared assignments must be exhausted before minimality is asserted.
20. Phase 3D operational audit starts from a verified frozen Phase 3C bundle and its
    embedded locality/authorization plus pre-certificate upper. Its complete 144-action
    binding catalogue supplies pre-authorization causal, legality, and cost queries;
    all model builders, coverage closure, pre-authorization kernel steps, and
    operational `U_all` recomputation remain zero.
21. Phase 3D's 16-pair causal frontier is a strict subset of the source 32-pair
    frontier, while its eight reverse-dependency pairs equal the source set exactly.
    `24/96` is capability scope, not executed work.
22. Operational ground work is exactly 16 materialization steps plus eight patched
    sound-post-audit steps; accounting/other/outside-support steps and exact-hybrid lift
    invocations are zero. Exact `317/16000`, the `8/12` decision split, and J0 belong
    only to standalone-verifier evaluation.
23. Contract-1.0 local recovery is downstream of an abstract full-plan certificate
    failure.  Accounting cost or route dominance can choose how to respond to that
    failure but can never authorize ground reopening on a certified abstract plan.
24. Phase 3E comparison is a deterministic projection of complete native work, not an
    independently reported summary.  Every operational charged leaf projects exactly
    once; evaluation/provenance/diagnostic and derived-only leaves project zero times.
25. Common-prefix work is charged once and is absent from both marginal route uppers.
    Local is selected only by strict componentwise dominance of all eight shared axes;
    equality, incomparability, stale evidence, or negative causal evidence selects
    fallback.
26. A route decision freezes before any transition materialization, compiler, route
    worker, stitch, post-audit, or fallback execution.  Forbidden early access is a
    protocol-failure noncertificate, regardless of the eventual numeric plan result.
27. Logical occurrences, rather than route attempts, define campaign denominators.
    Failed local, fallback, rebuild, retry, cap exhaustion, and noncertificate work
    cannot be removed from the occurrence aggregate.
28. Contract-1.0 component replay does not open official execution, counter
    completeness, workload economics, scalar cost, or break-even claims.

## Acceptance tests

- Frontier pruning retains trade-off points and removes exact duplicates deterministically.
- A nominally safe but envelope-unsafe policy is rejected.
- A better omitted action is visible in J0 and the unrestricted upper bound.
- Fallback receives byte-for-byte equivalent query semantics and its charges enter totals.
- J0–J2 report the same fixture and query hashes.
- Production known-infeasibility exits before refinement only after resolving a J0 proof
  with identical structural/build/kernel/query identities; the Phase 0.5 exception
  remains separately labelled.
- Mutating any one of those four proof identities prevents the shortcut.
- Reusing a known J0 proof preserves its original establishment cost and records the
  current validation/cache-lookup cost; neither is hidden from the audit trail.
- A build with a missing coverage field, mismatched support hash/count, or uncovered
  positive-mass query state is rejected before abstract proposal, refinement, or
  certificate reuse; the caller must rebuild or use an explicitly charged ground path.
- Safe-chain J0 and exact-J2 comparisons cover every reachable `(x,h)`, preserve root
  constrained return and failure `99/5000`, and have zero action-restriction gap.
- The comparison records strictly smaller exact-J2 state-time and total state-action
  counts before reporting graph compression.
- Perturbing one action transform, representative aggregate, envelope endpoint, or
  duplicated concretizer weight deterministically produces
  `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`.
- The aliased audit is initially unsafe (`L_pi=51/3200`, `U_F=19999/20000`, regret
  `99/3200`), remains unsafe after the first split (`L_pi=3/64`, `U_F=5099/10000`),
  and certifies after the second (`L_pi=3/64`, `U_F=397/20000`, regret zero).
- Independent ground lifting recomputes failure `317/16000`; each of the eight initial
  point audits has `U_F=397/20000` and certifies. Adding a fallback or claiming J0 risk
  equality fails the profile gate.
- Every Phase 3A row reproduces the V0-027 exact `J0=Jkappa=J2_lift` reward and failure
  values, exact reward lower bound, normalized regret upper bound zero, and a sound
  failure upper bound at or below its registered `delta`.
- G2048 audit goldens include total `192/8`, active state/cell `68/7`, active physical
  orbits/cells `9/7`, physical state-action orbits/entries `18/14`, ground pairs/entries
  `144/14`, two mixed active cells, and one cell with distinct-orbit members jointly
  reached by one training graph. Its 20-state training-support union and six rows are
  reproduced; the bridge row is reward `13/400`,
  failure `199/5000`, sound `U_F=1/25`, and both explicit witnesses are jointly
  reached. LMB includes total `25/5`,
  active state/cell `18/3`, active physical orbits/cells `10/3`, state-action orbits/
  entries `16/4`, and within all three active cells the same training graph reaches
  members from multiple physical orbits.
- A held-out query mutation changes only its query/evaluation identity. If it changes a
  construction hash or is observed by a builder, leakage validation fails; if its
  support is outside coverage, evaluation is rejected rather than rebuilding silently.
- Phase 3B builder API/data-flow and static source audits reject an injected
  Q/value/frontier/policy/query dependency at the builder/planner boundary even if final
  model bytes or values happen to match the legitimate build.
- Canonical round-trip and per-occurrence bubblewrap attestations prove that all eleven registered
  query plans use only one portable RAPM per domain before independent exact audit/J0/
  lift; every row then certifies and agrees, with multi-step queries in both domains.
- Construction replay reproduces G2048 trace/state/action counts
  `2 -> 9 -> 10 -> 10`, `192 -> 10`, `144 -> 17` and LMB
  `3 -> 5 -> 5`, `25 -> 5`, `40 -> 4`.
- A fabricated local route on a certified plan, an unreachable/non-earliest frontier
  node, a hidden ground import in the fresh planner, or an evaluation record referenced
  by construction fails the campaign.
- Workload recomputation keeps exact build/route counters additive and J0-evaluation
  work separate; scalar break-even remains null and no result changes the
  economics-not-run status.
- The verifier independently rebuilds both kernels, coverage closures, behavioural
  models, and G2048/LMB authority normalizer registries; it reprojects each query,
  including exact LMB proof-to-basis bindings `(1,1),(1,0),(0,1)` with no cross-use,
  recomputes portable-envelope and live exact audits,
  performs serialized-`kappa` lift and J0, checks all IDs/cross-links/counters, and can
  replay the isolated planner.
- Phase 3D replay verifies and embeds source Phase 3C locality/authorization, proves
  current frontier `16` is a strict subset of source `32` and reverse support `8` is
  exactly equal, and reproduces the `24/96` capability scope, `1/0/1+1` sparse
  capability, safe-chain 257 count, and synthetic 25 count.
- Operational access tests require a complete binding-time 144-action catalogue, zero
  pre-authorization transition calls, exactly `16+8=24` ground steps, and zero
  accounting/other/outside-support steps. The operational post-certificate carries
  `(3/64,397/20000)` with null exact-lift fields; independent evaluation alone must
  reproduce `317/16000` and the `8/12` local/abstract split. Forging active ties/slack,
  adding the source boundary to worker mounts, deleting or adding capability authority,
  or changing cap/access counters fails.
- Contract-1.0 identity tests reject noncanonical JSON, non-reduced rationals,
  nonfinite values, unsupported fields, truncated IDs, unregistered domains, and
  cross-role/domain reuse even when payload JSON is otherwise identical.
- Native accounting tests require every route/stage leaf and explicit observed zero,
  preserve local/fallback/rebuild provenance, replay route/solver/process closure, and
  reject missing/duplicate projection terms, generic branch-cost substitution, wrong
  lane/scope/reducer metadata, and serialized-byte double charging.
- Marginal routing tests require exact eight-axis coverage, strict componentwise local
  dominance, typed local/fallback optionality, stale-identity rejection, continuous
  transaction indices, all registered local hard caps, and fallback for every negative
  causal outcome.  Worker budget claims cannot override trusted replay.
- Access-order tests monkeypatch Phase 3D ground materialization/compiler/kernel entry
  points during estimate preparation, reject every execution event before decision
  freeze, invoke only the selected callback, and reject a fallback trace containing
  any local execution artifact or a deleted/reordered/rebound access event.
- Actual/workload/campaign tests reconstruct actual vectors and sum/max occurrence
  aggregates from referenced native work; reject upper overflow, forged or swapped
  vector references, scalar/crossing injection, hidden registered occurrences, retry
  overrun, and any attempt to classify fallback-cap exhaustion as infeasibility.
- These component tests do not satisfy the Phase 3E implementation Gate until the same
  checks cover production-native records on abstract, direct-fallback, second-local-
  transaction, rebuild, infeasible, protocol/integrity-failure, and independent bundle
  replay paths.

## Out of scope

J3 learned/statistical models, J4 bounded search/MCTS, J5 perception, causal attribution from the telescoping ladder, asymptotic guarantees beyond the enumerated finite model, using the supplied `D4` group as evidence of automatic symmetry or predicate discovery, using Phase 3A exact-model cross-orbit aliasing as evidence of oracle-free unknown-quotient discovery, crediting Phase 3B with local-hybrid evidence, crediting Phase 3D with dependent-horizon completeness, or crediting the Phase 3E component foundation with production counter completeness, workload economics, an official scalar/break-even, or a full Gate.

## Known failure modes

Frontier combinatorics, conservative rectangular composition, all policies exceeding `delta`, stale or incomplete build-coverage identity, and small numeric differences in derived display floats. Exact stored rationals remain authoritative. Conservative width is permitted—and expected by `3/80000` in the final aliased risk bound and by some G2048 Phase 3A risk rows—in ordinary interval quotients but is a hard error in the exact `D4` and LMB exact-behavioural profiles. Held-out leakage is a Phase 3A construction failure even when all final values happen to match.

## Open risks

Paired oracle-replacement ablations and component interactions are required before broad causal claims. More compact exact frontier representations may be needed beyond tiny instances. V0-028 removes Q/value signatures from the portable exact builder; V0-029 closes the first certificate-triggered recovery; V0-030 closes slack-aware earliest-antichain authorization, finite-domain sparse capability, and capped joint search; and V0-032 freezes and partially implements the accounted routing foundation. Production-native instrumentation, real fallback/retry execution, the remaining nine original FQ7 role-authority verifiers, end-to-end Phase 3E replay, dependent-horizon recovery, automatic feature invention, workload economics/dynamic routing, and statistical Gates remain open.
