# Preregistered Cross-Query Promotion and Held-Out Reuse (V0-048)

## Status

Normative for contract `1.11.0`, implementation schema `1.0.0`, and profile:

```text
lmb_preregistered_h1_cross_query_promotion_v0
```

V0-048 is a narrow exact positive control for one transition from a query-owned
model epoch to a reusable, scope-limited model epoch. It does not alter the V0-045
base, retroactively relabel V0-047, or open any aggregate Gate.

## Claim

The system can preregister a query that is distinct from the source query and absent
from the original observation graph, independently replay the complete V0-047 source,
promote the complete final state/action/transition model rather than a target-selected
subset, and answer the preregistered query by model-only planning and independent
value/risk audit with zero target ground calls.

The promoted model is reusable only inside an explicit initial-state and horizon
scope. The source acquisition was query directed, so the artifact must retain:

```text
acquisition_query_neutral_attested = false
```

Promotion establishes scoped semantic reuse; it does not rewrite the acquisition as
query neutral and does not authorize unrestricted queries.

## Frozen source and preregistered target

The source is the canonical V0-047 H2 logical occurrence:

```text
source initial state = removed_mask 3, buffer (1,1), active
source horizon = 2
source risk tolerance = 0
source normalized-regret tolerance = 0
source transition acquisition = 13
source direct boundary catalogues = 3
source final V3 coverage = 20 observed / 0 missing
```

Before any V0-047 result or exact kernel is supplied, the protocol freezes the
distinct target:

```text
target initial state = removed_mask 11, buffer (1,2), active
target horizon = 1
target risk tolerance = 0
target normalized-regret tolerance = 0
reward weights = match 1, terminal_clear 1
```

The target state is not among the eight V0-045 registered observation states, and its
state ID differs from the source initial state ID. The preregistration producer accepts
only the observation log, semantics profile, observation authority, V0-045 synthesis
result, and source thresholds. It accepts neither a V0-047 result nor a kernel.

The frozen V0-047 source runner parameter list is:

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

It contains no target query, promotion protocol, promotion candidate set, or target
threshold. Therefore source acquisition cannot use the held-out target as an input.

## Promotion authority

Promotion independently replays the full V0-047 source chain. Eligibility requires:

1. exact equality with the preregistration reconstructed from pre-source inputs;
2. the canonical V0-047 source result and exact kernel authority;
3. final coverage `20/0`;
4. all 13 exact evidence records and all three boundary catalogues;
5. the complete set of 20 final ground rows as the promotion candidate;
6. zero target-filtered rows;
7. exactly three target rows contained in that complete set;
8. unchanged V0-045 base bytes.

The promotion replay's `13` transitions and three direct catalogue calls belong to the
independent verification/evaluation lane. They are not charged again as warm target
planning work.

## PreregisteredReusablePartialRAPMV4

The promoted model has a separate content domain and immutable epoch. It copies the
complete verified final V3 semantic model and binds the source result, preregistration,
eligibility proof, 20 promoted row IDs, 13 exact evidence IDs, authorized target state,
and reuse horizon cap.

Required flags are:

```text
query_neutral = true
acquisition_query_neutral_attested = false
promotion_scope_query_neutral_attested = true
query_local_overlay_authority_required = false
boundary_catalogue_authority_required = true
promotion_authorized = true
base_model_mutated = false
unrestricted_reuse_claimed = false
transition_closure_claimed = false
exact_quotient_claimed = false
plan_certificate_claimed = false
infeasibility_claimed = false
```

Here `query_neutral=true` means that the promoted transition facts may be consumed
without carrying the source plan or threshold inside the registered reuse scope. It
does not mean the acquisition selection was query neutral, and it does not permit a
new initial state or horizon outside:

```text
authorized_initial_state_ids = (preregistered target state ID,)
reuse_horizon_cap = 1
```

The independent partial-model auditor rejects any threshold outside that scope.

## Held-out planning and certification

The held-out consumer API accepts only:

```text
observation_log
semantics_profile
observation_authority
promotion
```

It has no kernel, transition callback, target override, ground solver, J0 result, or
caller cap. It binds the preregistered target to V4, enumerates the two deterministic
H1 abstract plans, and internally audits both. The selected plan requires a separate
audit invocation.

The target has three legal ground actions. The semantic `True` action selects tile 4,
completes the type-1 match, receives reward one, and does not fail. The two semantic
`False` actions terminate in failure. The exact held-out certificate is:

```text
planner candidates / audits = 2 / 2
selected outcome = INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
reward lower / upper = 1 / 1
unrestricted reward upper = 1
failure lower / upper = 0 / 0
normalized regret = 0
external coverage certified = true
warm target transition calls = 0
warm target direct catalogue calls = 0
direct ground optimizer calls = 0
```

## Matched cold acquisition trace

A separate evaluation-only routine starts from the same target state, makes one direct
complete action-catalogue call, and executes all three target transitions. Each fresh
outcome is compared exactly with its promoted source evidence record.

```text
cold direct catalogue calls = 1
cold exact transition calls = 3
cold step-internal legality checks = 3
cold failures / safe match outcomes = 2 / 1
cold ground-search calls = 0
cold direct ground-optimizer calls = 0
evaluation_lane_only = true
end_to_end_cold_planner_claimed = false
```

The three internal legality checks are part of the three transition calls and are not
additional catalogue acquisition. This trace measures target evidence that warm reuse
avoids. It does not include source acquisition amortization and does not execute or
claim a complete cold-start planning pipeline.

## Work and sample-efficiency boundary

The frozen telemetry keeps four lanes distinct:

```text
source acquisition                 = 13 transitions + 3 catalogues
promotion independent replay       = 13 transitions + 3 catalogues
warm held-out operational query    = 0 transitions + 0 catalogues
cold held-out evaluation trace     = 3 transitions + 1 catalogue
```

Consequently:

```text
source_cost_amortization_included = false
cold_end_to_end_planner_claimed = false
sample_efficiency_claimed = false
official_scalar_cost = null
official_N_break_even = null
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The result is evidence that reuse can avoid target acquisition in this registered
case. It is not yet a sample-efficiency result because there is one target, no
amortization curve, no matched end-to-end direct optimizer, and no statistical test.

## Canonical identities

```text
target_query_id = d651857a01ffd07170e4325e816b3acf79c7117cb140e23f6baad18e99621669
protocol_id = fb072250b7c99374439f9d84989a044a75cd6b61e364586812f516604b2cf0f4
eligibility_proof_id = b3c68790c55ef7aa48b3a9a020b24f7083a6db06367b65095cbf607e64a01172
promoted_model_id = 85315d41c9540decac2b8a089fecb75fb979ab0569a084b08539ca29b5b66cdd
promotion_result_id = a824f85817827a533c7f9afe3e05a73a7490aa91f63cac541cf51e890efb0500
threshold_binding_id = 1fdc52f557f0a77805f7f0965e18a7b64221c85d632b7686389040a6722705dc
plan_proposal_id = 7fc5db36d3dc16d2f2930c82fe4560e69b1a3419f536567e8e6c20c844eaf309
plan_audit_id = 9efdbe1667879c24ab5b20d72ff8b33fd372c632b8b1f45c591617e71f8e5572
cold_trace_id = 443d7c4e4f6a751a5092f60afdd0e6d82ecbacd3f038c8fa27ca0c9a28458fb7
telemetry_id = 384ab0c12872ba34f8183e1787cc566e6782cdf45369f0d7b99a08c32328caa8
result_id = 464a0b4b51d36c0fe251ec04b68c75f1b308958fa2eb721ccddd955629330993
```

These IDs are regression anchors, not substitutes for semantic replay.

## Required regressions

1. preregistration has no source result or kernel input;
2. the source runner has no target/protocol input;
3. source and target initial states are distinct and the target is absent from V0-045;
4. promotion independently replays V0-047 and selects all 20 rows;
5. target-filtered promotion and claim escalation fail closed;
6. V4 retains nonneutral acquisition provenance and scope-limited reuse;
7. the held-out consumer has no kernel and certifies exact reward/risk/regret `1/0/0`;
8. warm target work records zero transition/catalogue/ground-optimizer calls;
9. cold evaluation records one direct catalogue, three transitions, and three internal
   legality checks with no hidden access;
10. warm, source, promotion-replay, and cold-evaluation lanes remain separate;
11. canonical IDs remain unchanged;
12. full independent replay reproduces the complete result byte-for-byte.

## Claim boundary and next Gate

V0-048 closes one preregistered cross-query, held-out reuse and scoped-promotion
positive control. It does not prove:

- unrestricted base promotion;
- reuse for arbitrary initial states or horizons;
- coordinate invention or unknown-DSL discovery;
- partial/statistical/learned dynamics;
- portable observer or public transport authority;
- multi-domain or statistical generalization;
- a sample-saving intervention;
- workload economics or any aggregate Gate.

The next construction Gate is a preregistered family of multiple held-out logical
occurrences with promotion-amortization and matched end-to-end cold baselines. Those
traces can determine whether the dominant tax is coordinate discovery, boundary
catalogue acquisition, transition identification, certificate replay, or model
verification. Only then should a Laplace-semi-MDP-style heuristic operator or KG-OP-
style offline/online meta-prior be frozen as a tax-reduction intervention.
