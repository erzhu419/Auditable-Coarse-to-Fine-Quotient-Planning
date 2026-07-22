# Query-local evidence and immutable refinement

Status: frozen V0-046 scoped construction result
Contract: `1.9.0`
Implementation schema: `1.0.0`
Profile: `lmb_h1_query_local_exact_row_refinement_v0`

## 1. Purpose

V0-046 closes one narrow instance of the project’s central control loop:

```text
observation-only reusable partial RAPM
-> abstract contingent-plan proposal
-> independent failed fixed-plan certificate
-> separately authorized query-local evidence
-> immutable query-owned RAPM overlay
-> abstract replanning
-> independent fixed-plan certification
```

It starts from the canonical V0-045 H1 all-missing result. It does not accept a
caller-selected row set, evidence budget, alternative frontier, transition callback,
ground solver, J0 result, or target policy. The failed V0-043 frontier remains a
nonauthorizing diagnostic object. A separate authority first replays the full V0-045,
typed V0-044, and typed V0-043 chain and then derives the exact evidence request.

The result is a positive control for certificate-triggered local evidence and model
refinement. It is not a general causal-minimality theorem, a learned acquisition
policy, an unknown-domain strategy, or evidence of sample savings.

## 2. Frozen source chain

The source model is the V0-045 observation-only typed-coordinate partial RAPM:

```text
base model rows:          11
observed singleton rows:   7
missing vacuous rows:      4
base model ID:
1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18
```

The query starts at the registered active state with removed mask `3`, buffer
`(1,1)`, horizon `H=1`, risk tolerance `delta=0`, unit canonical reward weights,
normalized-regret tolerance zero, and the canonical LMB return-bound proof.

The typed V0-044 planner enumerates two complete deterministic abstract plans and
selects the frozen minimum-risk fallback plan. Independent typed V0-043 replay returns:

```text
outcome: FAILED_PROOF_FRONTIER
reason: UNRESOLVED_POLICY_PATH_DISTINCTION
reward interval: [0,3]
failure upper: 1
local recovery authorized by frontier: false
```

V0-046 requires this complete identity-bound failure chain. A bare frontier, inner
audit, portable model, pure-build result, or reconstructed lookalike cannot authorize
ground access.

## 3. Scoped row-necessity authority

The authorization theorem is deliberately limited to:

```text
fixed H1 query
fixed selected plan
fixed concretizer
row-completion evidence family
row-wise vacuous missing uncertainty
delta = 0
```

The failed obligation reaches one semantic realization with mass upper one. Its four
missing ground rows are the complete support of a uniform distinct-action concretizer,
so every row has probability `1/4`. If any one row remains vacuous while the other
three are resolved, that row alone permits failure mass `1/4 > delta`. Therefore each
of the four rows is individually necessary, and the unique requested row set within
this frozen row-completion family is all four rows.

The request records four typed `QueryLocalRowNecessityProofV1` objects:

```text
concretizer probability per row:       1/4
reachable state-mass upper:              1
leave-one-out failure upper per row:    1/4
risk tolerance:                           0
request-preparation kernel calls:         0
request-preparation ground searches:      0
maximum authorized exact-kernel calls:    4
global minimum claimed:               false
```

This proves cardinality-minimal completion only inside the declared fixed-plan,
fixed-concretizer row-query family. It does not prove that four is minimal among all
possible experiments, representation changes, policy changes, causal interventions,
or information-gathering strategies.

## 4. Exact acquisition authority and accounting

The in-memory exact LMB kernel authority freezes:

```text
tile types:  (0,1,0,1,1,0)
type count:  2
capacity:    3
max layers:  2
blockers:    none for tiles 0/1; {0,1} for tiles 2/3/4/5
kernel implementation SHA-256:
fa38ca4724420cc9834a50ee83b57a97721434404a9e76f0994b1aecb22b5323
```

Before the first `step`, the executor checks exact kernel type/configuration/source
digest and equality between every registered state’s kernel legal-action set and the
trusted V0-042 action catalogue. It then invokes the exact transition interface once
for each authorized row and no other row.

The canonical acquisition result is:

```text
authorized exact-kernel calls: 4
positive outcome rows:         4
extra ground-row access:       0
environment interactions:      0
generative samples:             0
synthetic evidence rollouts:    0
registered successors:         1
external successors:           3
failure outcomes:              0
terminal outcomes:             0
reward features:               empty on all four rows
```

The four exact-kernel calls are operational acquisition work and may not be hidden by
the zero environment-interaction fields. Independent verification executes the exact
kernel again in an evaluation replay; those calls do not change the recorded
operational count. V0-046 does not claim complete Phase 3E WorkVector accounting.

## 5. Immutable query-owned overlay

The reusable V0-045 base object and ID remain byte-identical. Acquisition creates a
new content-addressed `QueryLocalOverlayContextV1`, `QueryLocalBuildEpochV1`, and
`QueryScopedPartialRAPMV2` rather than mutating or relabelling the base.

The query-scoped model:

- binds the base model, V0-045 result, source thresholds, selected source plan, failed
  typed audit, evidence request, evidence bundle, and overlay context;
- replaces exactly the four requested `MISSING_VACUOUS` rows with exact singleton rows;
- recomputes every affected concretizer-weighted semantic realization;
- changes observed/missing coverage from `7/4` to `11/0`;
- remains `query_neutral=false` and `acquisition_query_neutral_attested=false`;
- keeps `transition_closure_claimed=false` and `exact_quotient_claimed=false` because
  three exact successors remain known external boundary destinations;
- claims neither plan certificate nor infeasibility by construction;
- freezes `base_model_mutated=false` and `promotion_authorized=false`.

The overlay build itself performs zero kernel calls; all four calls belong to the
separate evidence bundle.

## 6. Replanning and independent certification

The source query fields are rebased unchanged onto the new query-scoped model ID. The
query-scoped planner enumerates the complete two-plan deterministic domain, internally
audits both plans, and selects with the existing V0-044 hierarchy. It performs zero
kernel calls and remains proposal-only.

Independent audit of the selected overlay plan produces:

```text
outcome: CERTIFIED_FIXED_PLAN
candidate plans / internal audits: 2 / 2
policy reward lower / upper:       0 / 0
policy failure lower / upper:      0 / 0
raw / normalized regret:           0 / 0
operational exact-kernel calls:         4
```

Known external successors do not invalidate this H1 certificate because they occur
after the final controlled step and no positive remaining horizon is assigned to their
continuation. This does not imply H2 or longer-horizon closure.

The proposal is not the certificate authority. Only the independently replayed
`PartialSoundAuditResultV1` and its fixed-plan certificate authorize the final
`QUERY_LOCAL_PLAN_CERTIFIED` status.

## 7. Promotion boundary

The completed overlay may be reused only inside its exact query/authority context.
V0-046 freezes:

```text
local_reuse_allowed: true
base_promotion_authorized: false
preregistered_multi_query_gate_run: false
preregistered_held_out_gate_run: false
disposition: RETAIN_QUERY_LOCAL_OVERLAY_ONLY
```

Promotion into the query-neutral reusable base requires a later preregistered
multi-query/held-out authority. Exact local success alone is insufficient.

## 8. Frozen content identities

```text
kernel authority:
2bb62669839fbde2cb4703c1ff71b71eb95cddcfdba5b3102a1833c5258164a0
source thresholds:
87538aef2520bcaab9a86843cac0d61d9601bfb3cd661061a5454ef73cbaeb2b
source plan proposal:
f9006103939f33ee744fd994e00240018ab445c75df1c4c23fba82d479bc6513
source selected plan:
a199aa4177a5926a5b02947f9fd2b3cb48e92943476dea0463e2e5aeda66dde3
failed typed audit:
5974cd305c6532b6e7d6888be1ce009a119f9b37b9a39a626210466bb8c96dff
failed frontier:
9d6f0803f365643d623368cdfed6b6666c5c8a00e3fd77fbdf41b00d1f354cab
evidence request:
1ff845f3eecc05a098b3437c7e4b8356bcd28ea1dd0d4cc4ace8e52bc382cd2c
evidence bundle:
17c8783b3ab489322359bb9ed7e463c4540e9ed1d4d6036d639c1cc9a6bc8543
overlay context:
7589dd139e5b1a528839580626d30f508719be9280d7f263bee924ba8d441404
overlay BuildEpoch:
ff0a14c296c8d5d122ff0f635ad8909dcfd2294274c99c3ac1da0412e8d947d2
query-scoped model:
7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df
query-scoped plan proposal:
9a408b15377b10bf6450d91c0e1e26d9e7dd9ac129abc7462ce15ca69187ad3c
query-scoped fixed-plan certificate:
ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303
complete refinement result:
8c37b241d15b06f05dfe34189b37e324addd2c93605d4c718868d8a0544cf057
```

These hashes establish deterministic content identity and replay equality. They do not
establish public authenticity, observer honesty, or statistical truth.

## 9. Acceptance and claim boundary

Acceptance requires:

1. complete V0-045, typed V0-044, and failed typed V0-043 replay;
2. four and only four row-necessity proofs and requested rows;
3. zero ground access while preparing the request;
4. exactly four authorized operational exact-kernel calls and no extra row access;
5. byte-identical reusable base before and after construction;
6. a distinct query-owned V2 model with eleven observed and zero missing rows;
7. complete two-plan abstract replanning with zero additional kernel calls;
8. independent `CERTIFIED_FIXED_PLAN` replay with reward, failure, and regret all zero;
9. no promotion, sample-efficiency, official-execution, infeasibility, exact-quotient,
   transition-closure, learned-dynamics, or general-minimality claim;
10. an independent full-chain verifier result identical to the claimed result.

V0-046 demonstrates one authentic certificate-triggered local-refinement loop after
observation-only coordinate synthesis. It does not establish raw symbolization,
automatic unknown-DSL invention, partial/statistical dynamics learning, multi-step
external-boundary recovery, cross-query promotion, cross-domain generalization, scale,
or a sample-complexity advantage over direct optimization.

The next construction work generalizes this authority from the H1 row-completion
control to multi-step failed-proof frontiers and active distinctions, then measures
offline construction work and online ground calls against direct optimization before
designing any Laplace-semi-MDP-style heuristic operator or KG-OP-style meta-prior.

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
