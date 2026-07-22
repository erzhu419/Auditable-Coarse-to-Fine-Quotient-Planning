# Observation-Only Typed Coordinate Synthesis for a Partial RAPM

Status: **FROZEN under contract 1.8.0**

Profile: `lmb_query_free_observed_typed_coordinate_synthesis_v0`

Implementation schema: `1.0.0`

Typed V0-042 extension schema: `1.2.0`

Typed V0-044 planner schema: `1.1.0`

Typed V0-043 audit-wrapper schema: `1.2.0`

## 1. Objective and exact claim

V0-045 closes one deliberately narrow construction step:

```text
allowlisted, already-symbolized observation graph
-> evaluate a fixed human-designed typed DSL
-> exhaust all registered coordinate subsets
-> select one observation-consistent, non-vacuous abstraction
-> construct a reusable log-conditional partial RAPM
-> plan mainly in that model
-> independently audit the selected complete contingent plan
```

The reusable object is still `PortablePartialRAPMV1`; the plan remains a per-query
artifact. Construction receives no query. Missing legal rows remain explicit joint-
simplex uncertainty instead of being filled by a kernel, model rollout, or guessed
label.

This is the first observation-only fixed-DSL construction control. It is not a claim
that the system has symbolized raw sensory input, invented new primitives/operators,
learned a neural latent state, recovered a true or unique latent world model, or
established statistical consistency or cross-domain generalization.

## 2. Trust boundary and production API

The exact production inputs are:

```python
synthesize_observed_lmb_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> ObservedTypedPartialRAPMResultV1
```

The retained-runtime verifier adds only the claimed result:

```python
verify_observed_lmb_partial_rapm_v1(
    observation_log,
    semantics_profile,
    observation_authority,
    claimed_result,
) -> tuple[str, ...]
```

Before evaluating a coordinate, both paths replay the complete hardened V0-042
source graph and require its exact allowlisted authority. The current profile is
in-memory and log-conditional: hashes bind canonical bytes but do not prove observer
honesty, public transport authenticity, catalogue truth, or stationarity.

The API has no coordinate proposal, candidate cap, query, initial distribution,
horizon, reward/risk threshold, kernel, transition callback, planner, V0-043 result,
J0, ground solver, target quotient, behavioural signature, or callable adapter.
Closed structural constants are selected only by the exact registered
`(observation_authority_id, structural_id)` pair.

## 3. Fixed typed language and value table

The fixed language has eight state ASTs and four state-action ASTs. Its human-written
primitive/operator templates are the same mathematical language used by V0-041, but
V0-045 has a different registry authority and imports neither V0-041's runtime
evaluator nor its candidate, trace, certificate, exact target, model, or result.

State primitives are `legal_actions`, `remaining_tiles`, `buffer_counts`,
`buffer_capacity`, and integer literals `0,1,2`. The state-action primitive is
`selected_tile_type`. Registered operators are `cardinality`, `cardinality_tiles`,
`sum_vector`, `max_vector`, `count_equal`, `subtract`, `buffer_at_type`, and `equals`.

The observation-only evaluator materializes `FrozenTypedCoordinateValueTableV2` over
all eight registered states and all eleven legal ground rows. It never calls
`LMBKernel`. Raw table values are exact integers or booleans and are not themselves
semantic action labels.

Candidate space is exactly:

```text
2^8 state subsets * 2^4 action subsets = 4096 candidates
```

All 4096 candidates are evaluated before selection. No caller can lower the
production cap or supply a subset.

## 4. Typed proposal and preservation of the V1 schema

V0-045 emits `FrozenTypedCoordinateProposalV2`; it does not overload the manual
`FrozenCoordinateProposalV1` origin or enum.

The V1 consumer schema is unchanged:

```text
PartialSemanticActionV1.label_values = nonempty tuple[bool, ...]
```

In particular, V0-045 does not relax this field to arbitrary integers and does not
permit an empty label. Raw selected action-program values are compiled into closed
boolean atoms:

- a boolean expression becomes an identity atom;
- an integer expression becomes deterministic `<=` atoms at every adjacent exact
  midpoint represented in the complete source table;
- an empty action-program subset uses one `UNIVERSAL_TRUE` sentinel atom.

The final semantic label is the nonempty tuple of evaluated boolean atoms. Every
member of one active cell must expose exactly the same complete semantic-label set.
Intersection or silent deletion of member-specific actions is forbidden.

`build_observation_partial_rapm_from_typed_values_v2` is a pure internal derivation
from a claimed proposal and value table. It checks shape, midpoint compilation,
label-set equality, source bindings, concretizers, observed/missing rows, ambiguity,
and model invariants, but it is **not** independent synthesis authority: a caller can
otherwise choose opaque trace IDs and supply its own value table. No downstream
certificate may trust the V2 proposal, table, pure-build result, or bare portable
model in isolation.

Only `verify_observed_lmb_partial_rapm_v1`, which reconstructs the source values,
all candidates, selection, proposal, build, model, telemetry, certificate, and final
result, establishes the V0-045 authority chain.

## 5. Candidate evidence and selection

For a candidate, observed deterministic rows are compared using the exact unweighted
reward-feature vector, failure/terminal markers, and terminal atom or successor cell/
external boundary. Congruence is checked before concretizer mixture, both within a
state and across states in one cell.

Missing rows are neither equality nor mismatch evidence. Each abstract entry is
classified as:

```text
POINT_IDENTIFIED
PARTIAL_UNKNOWN
UNOBSERVED_UNKNOWN
OBSERVED_CONTRADICTION
```

`OBSERVED_CONTRADICTION` and unequal member label sets reject the candidate. A
successful candidate also requires a nontrivial observed equality witness, separation
of an observed null/coarser conflict, a nontrivial point-identified entry, and strict
state/action compression.

The frozen lexicographic selection maximizes point-identified registered rows, then
observed equal-alias pairs; minimizes partial-unknown registered rows, abstract-entry
count, active/total cells, and program counts; and finally uses AST complexity,
registered IDs, partition and candidate IDs. Query visitation, reward weights, value,
risk, policy, and post-run outcomes never enter this key.

## 6. Canonical construction control

The only V0-045 production source currently registered has:

```text
registered states                         8
registered legal ground rows             11
observed / missing rows                   7 / 4
state / action ASTs                       8 / 4
candidates evaluated                      4096 / 4096
admissible / rejected candidates          3458 / 638

selected state program:
  cardinality(legal_actions)
selected action program:
  buffer_at_type(buffer_counts, selected_tile_type)
compiled action atom:
  integer <= 3/2

selected point / partial rows             7 / 0
observed equal-alias pairs                3
separated null conflicts                  18
nontrivial point entries                  3
total / active cells                      6 / 4
abstract entries                          5
semantic actions / realizations           5 / 6
entry classes                             4 POINT_IDENTIFIED
                                          1 UNOBSERVED_UNKNOWN
model observed / missing rows             7 / 4
semantics horizon cap                     6
```

The four missing rows form the all-unknown entry and retain unit unknown mass. Every
observed ground row remains a singleton. The produced model keeps the unchanged
`PortablePartialRAPMV1` schema, makes neither transition-closure nor exact-quotient
claim, and is byte-identical only under its own full V0-045 replay. It is not expected
to have the manual V0-042 model ID.

The frozen release content-ID goldens are:

```text
synthesis result       4834efc30b9ae292e33f83932525195df1997ae31f7c7898b452b6175815ded2
synthesis certificate  6b63e89ef44d5b8fe286db2168e595d1ddec9ac296845311f1e7bf5dbce22e84
candidate trace        4737d3fe32b7db8490f6903331e0ca11411d94b7b6bae3fe1afcbdf653582ebc
selected candidate     33051de900a743d03250477a6627b55e18d3c23277d67198760e03fb0e528ba3
action partition       0214cc53bef2bfd693cb14090d14ccc80665d4ff142cbe2fabbeb4d00cfe1ef7
typed proposal         cee1e3393a7686059e2f7d24647c5d3b906c9c9c0eff01683c116684b6c63123
partial build          7e3845fb4d92047c1bedf8cefb07504b2c5653250547e49cc8984502d84c7d2c
partial model          1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18
H3 planner result      4201c591132a6245df3a4989c7d9c9a9c2b9bab67132e679762b31ef2b1d3b6f
H3 selected plan       5397faf055fefeaaca2415f07ca2783c1ce580d719d20cea6befa3172dc53ace
H3 typed audit         24f4c930b0349fd90fc636efc787f5f39115abaf8e2824ebcced68473b917a87
H3 plan certificate    9e6750611397da8c2685480bc2de09e27fd79fe59c66009b0548cbd707de3ba0
H1 planner result      f9006103939f33ee744fd994e00240018ab445c75df1c4c23fba82d479bc6513
H1 selected plan       a199aa4177a5926a5b02947f9fd2b3cb48e92943476dea0463e2e5aeda66dde3
H1 planner-chain audit 5974cd305c6532b6e7d6888be1ce009a119f9b37b9a39a626210466bb8c96dff
H1 failed frontier     9d6f0803f365643d623368cdfed6b6666c5c8a00e3fd77fbdf41b00d1f354cab
```

The H1 IDs above bind the planner-selected complete contingent plan. The separate
auditor-only fixed-plan control deliberately has a different plan and therefore a
different typed result/frontier ID even though both expose the same H1 uncertainty.

## 7. Downstream typed consumers

A V0-045 model is useful only through a consumer that preserves its authority chain.
The typed V0-044 proposer therefore accepts exactly:

```text
observation log
semantics profile
observation authority
full ObservedTypedPartialRAPMResultV1
one FrozenPartialAuditThresholdsV1
```

It replays the full V0-045 result exactly once, freezes the verified portable model,
then enumerates all within-cap deterministic global plans and applies the common
V0-043 verified-model core to each candidate. It does not repeat source synthesis per
candidate. Its trace binds the V0-045 result/certificate, proposal, build, model,
threshold and plan identities and records:

```text
retained_v0045_full_replay_count = 1
internal_audit_source_replay_count = 0
fixed_plan_audit_count = candidate_evaluated_count
```

The proposer remains a ranking authority only. It cannot certify its selected plan.
The independent typed V0-043 entry accepts the same full V0-045 result plus thresholds
and one frozen plan, reruns the complete V0-045 verifier, then invokes the same bound
core. `TypedPartialSoundAuditResultV2` explicitly binds the V0-045 result,
V0-045 certificate, typed proposal, partial build, portable model, thresholds, plan,
and unchanged inner V0-043 audit. A bare model, table, proposal, build, callback, or
caller-supplied verifier cannot enter this public certificate boundary.

Canonical downstream controls are:

```text
observed-state H3:
  per-stage assignments = 2; plans = 8 / 8
  typed internal audits = 8
  selection = INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
  selected reward L/U = 4/4; failure L/U = 0/0
  independent typed V0-043 = CERTIFIED_FIXED_PLAN

all-missing-state H1:
  plans = 2 / 2
  selection = MIN_FAILURE_RISK_FALLBACK
  selected reward L/U = 0/3; failure upper = 1
  independent typed V0-043 = FAILED_PROOF_FRONTIER
  reason = UNRESOLVED_POLICY_PATH_DISTINCTION
  local recovery authorized = false
```

The old manual V0-042/V0-043/V0-044 APIs and artifacts retain their historical bytes,
IDs, counters, and claims.

## 8. Implemented verification and negative regressions

The implemented suite checks the exact three/four-input synthesis surfaces; complete
4096 trace; selected AST/atom and structural goldens; full 8/11 value-table coverage;
missing preservation; kernel blindness; implementation-source digest changes; V1
nonempty-boolean action-label preservation; typed midpoint and exact label-set replay;
nested source/result/value/proposal type rejection; unallowlisted authorities; a
separately named cap-4095 nonproduction closure; full typed proposer replay; and H3/H1
independent typed audit.

Some broader proposal-era controls remain future profiles rather than current
production claims: separately registered all-missing, one-observation, and
DSL-inexpressible source authorities; the earlier 39/40 source; portable public-source
authenticity; and statistical/held-out/cross-domain studies. They may not reuse the
current allowlist or be cited as passed V0-045 controls.

## 9. Telemetry and the sample-tax boundary

The seven offline observations are historical evidence cost. During synthesis,
environment interactions, generative samples, exact-kernel calls, synthetic rollouts,
and query inputs are all zero. Candidate, expression, comparison, missing-status,
predicate, compression, and ambiguity counters describe deterministic model work; they
are not environment samples and are not complete Phase 3E WorkVector accounting.

Zero new acquisition during synthesis does not imply zero abstraction sample tax.
V0-045 does not claim a matched-budget saving, sample-complexity improvement, or a
Laplace-style tax-reduction operator. That operator remains deliberately downstream of
the first complete evidence/refinement flow, where actual acquisition bottlenecks can
be measured.

## 10. Claim boundary and next Gate

V0-045 supports only this statement:

> On one finite, already-symbolized LMB observation/action catalogue with an
> allowlisted in-memory authority, the system exhaustively selected observationally
> separating coordinates from a fixed human-designed typed DSL, constructed a reusable
> log-conditional partial RAPM, planned in it, and independently certified one H3 plan;
> an all-missing H1 query instead produced an unresolved nonauthorizing frontier.

It does not support raw unsymbolized-state discovery, neural/continuous latent models,
unknown primitive/operator/DSL invention, exact homomorphism, true-world-model
identification, observer-truth proof, transition closure, ground optimality,
infeasibility, statistical consistency, held-out or cross-domain generalization,
scalability, sample saving, or an aggregate Gate.

The next construction Gate is certificate-triggered evidence and model evolution:

```text
freeze immutable V0-045 base model and failed typed V0-043 certificate
-> separately prove the minimum query-local ground evidence scope
-> acquire and charge only authorized rows
-> create a versioned query-local overlay/new BuildEpoch; never mutate the base
-> rebuild/refine, replan, and independently re-audit
-> promote only after preregistered multi-query/held-out checks
-> otherwise retain the overlay locally or use charged fallback
```

`FAILED_PROOF_FRONTIER` remains a nonauthorizing diagnostic. It cannot itself permit
ground access, infer causality, modify the reusable model, or prove infeasibility.

## 11. Gate state

V0-045 is frozen as a scoped construction/control result, but no official accounting,
economics, scalar, or sample-efficiency Gate is opened:

```text
implementation_status = OBSERVATION_CONSISTENT_TYPED_PARTIAL_RAPM
normative_status = FROZEN
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```
