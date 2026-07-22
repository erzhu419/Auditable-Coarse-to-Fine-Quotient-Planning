# Preregistered Held-Out Family and Matched Amortization (V0-049)

## Status

Normative for contract `1.12.0`, implementation schema `1.0.0`, and profile:

```text
lmb_preregistered_h1_heldout_family_amortization_v0
```

V0-049 extends the single-target V0-048 positive control into a frozen workload of
multiple logical occurrences. It measures exact native work vectors and prefix
relations. It does not freeze a scalar cost, an official break-even value, a
sample-efficiency claim, or a sample-tax intervention.

## Claim

The system can preregister three distinct H1 held-out queries and a ten-occurrence
workload before source acquisition, promote the complete verified V0-047 model once
into a separate three-state reusable epoch, answer every warm occurrence without a
target kernel call, and match each result against a complete source-blind exact H1
ground planner.

The result supports scoped multi-occurrence model reuse and exact vector amortization
mechanics. It is not statistical generalization: the three states are known members of
the complete V0-047 final model, and seven of the ten logical occurrences repeat one of
those three QuerySpecs.

## Frozen source and target family

The source remains the canonical V0-047 occurrence:

```text
source state = removed_mask 3, buffer (1,1), active
source horizon = 2
source acquisition = 13 exact transitions + 3 direct boundary catalogues
source final model = 20 observed / 0 missing rows
```

Before a V0-047 result or kernel is supplied, the family protocol freezes these three
distinct target QuerySpecs:

```text
Q1 = removed_mask 11, buffer (1,2), active, H=1
Q2 = removed_mask 19, buffer (1,2), active, H=1
Q3 = removed_mask 35, buffer (2,1), active, H=1
reward weights = match 1, terminal_clear 1
risk tolerance = 0
normalized-regret tolerance = 0
```

All three target states are absent from the V0-045 observation registry and distinct
from the V0-047 source initial state. Each has exactly three legal ground actions: one
action completes a match with reward one and failure zero, while two actions enter
failure.

The preregistered logical-occurrence order is:

```text
Q1, Q2, Q3, Q1, Q2, Q3, Q1, Q2, Q3, Q1
```

Thus the workload contains three unique QuerySpecs, ten logical occurrences, and
seven repeated occurrences. Repetition is explicit workload reuse, not ten distinct
states.

## Leakage and access boundary

The preregistration API accepts only:

```text
observation_log
semantics_profile
observation_authority
observed_synthesis_result
source_thresholds
```

It accepts no source result or kernel. The V0-047 source runner retains its frozen
eight inputs and has no family protocol, target, occurrence order, or cold result.

The warm occurrence API accepts:

```text
observation_log
semantics_profile
observation_authority
family_promotion
logical_occurrence
```

It accepts no kernel, transition callback, ground optimizer, or cold result.

The cold direct API accepts only:

```text
observation_log
family_query
logical_occurrence
kernel
```

It accepts no promotion, reusable model, source result, source evidence, warm plan, or
warm audit. Source evidence matching occurs only after the cold optimizer has frozen
its result.

## Complete promotion and V5 family epoch

Promotion first invokes the unchanged V0-048 complete-source verifier. It therefore
performs one independent V0-047 replay and produces the exact V4 singleton parent. The
family eligibility proof then requires:

```text
complete promoted rows = 20
source exact evidence = 13
source boundary catalogues = 3
family target rows = 3 + 3 + 3 = 9
target-filtered rows = 0
```

`PreregisteredReusablePartialRAPMV5` is a new immutable epoch; V4 is not widened in
place. V5 binds the complete V4 parent, family protocol, family eligibility proof, and
the three sorted authorized initial-state IDs. Its scope is:

```text
authorized initial states = {Q1 state, Q2 state, Q3 state}
reuse horizon cap = 1
promotion epoch = 2
query_neutral = true inside the registered scope
acquisition_query_neutral_attested = false
promotion_scope_query_neutral_attested = true
base_model_mutated = false
unrestricted_reuse_claimed = false
transition_closure_claimed = false
exact_quotient_claimed = false
```

The partial-model auditor rejects any fourth state or horizon above one.

## Warm model-only route

For every logical occurrence, the warm route enumerates two deterministic semantic
plans, internally audits both, chooses under the frozen V0-048 numeric/semantic tie
rule, and independently audits the selected plan. Every occurrence certifies:

```text
reward lower / upper = 1 / 1
failure upper = 0
normalized regret = 0
external coverage certified = true
target exact transition calls = 0
target direct catalogue calls = 0
direct ground optimizer calls = 0
model plan candidates = 2
fixed-plan audits = 3
```

Repeated occurrences deliberately execute planning and certification again. V0-049
does not yet cache a prior plan or certificate.

## Matched cold end-to-end route

For every occurrence, the cold route starts from the QuerySpec and exact kernel only.
It obtains the complete legal-action catalogue, executes all three H1 transitions,
enumerates all three deterministic ground actions, and selects the unique zero-risk
reward-one action. Its frozen native work is:

```text
exact transition calls = 3
direct catalogue calls = 1
step-internal legality checks = 3
ground action candidates = 3
direct ground optimizer calls = 1
promotion inputs = 0
source-result inputs = 0
```

After selection, the pairer verifies that the catalogue and all three outcomes match
the source evidence byte-for-byte. Warm and cold reward, failure, and normalized
regret must be exactly equal for all ten occurrences.

## Native lanes and prefix accounting

V0-049 uses a profile-specific native work vector rather than claiming Phase 3E
`WorkVectorV1` completeness. Required lanes are:

```text
source acquisition operational = 13 transitions, 3 catalogues, 13 internal checks
promotion replay evaluation    = 13 transitions, 3 catalogues, 13 internal checks
warm target operational        = 0 transitions, 0 catalogues, 2 plans, 3 audits
cold direct operational        = 3 transitions, 1 catalogue, 3 actions, 1 optimizer
```

All structurally zero leaves are explicit. Promotion replay remains evaluation work
and is never charged as warm target operational work.

For prefix `N`, the exact acquisition vectors are:

```text
source-inclusive warm operational = (13 transitions, 3 catalogues)
verification-inclusive diagnostic = (26 transitions, 6 catalogues)
cold direct operational           = (3N transitions, N catalogues)
```

Componentwise relations are:

```text
source-inclusive:
  N=1..3  cold strictly smaller
  N=4     incomparable
  N=5..10 warm strictly smaller

verification-inclusive diagnostic:
  N=1..6  cold strictly smaller
  N=7..8  incomparable
  N=9..10 warm strictly smaller
```

The first warm-dominance prefixes `5` and `9` are diagnostic vector relations. They
are not `official_N_break_even` and must not be converted to a scalar claim.

At `N=10`:

```text
source-inclusive warm = 13 transitions + 3 catalogues
verification-inclusive = 26 transitions + 6 catalogues
cold direct = 30 transitions + 10 catalogues
warm model work = 20 candidates + 30 audits
cold optimizer work = 30 candidates + 10 optimizer calls
```

## Sample-tax interpretation

The family trace includes source acquisition and a complete cold route, closing the
two omissions recorded by V0-048. It still does not prove sample efficiency because:

- exact-kernel calls are not environment interactions or generative samples;
- only three deterministic target states are used;
- seven occurrences repeat an already registered QuerySpec;
- no stochastic confidence interval or held-out distribution is registered;
- axes have no scalar exchange rate;
- no tax-reduction intervention is executed.

The run reveals a concrete next hypothesis: target transition acquisition has been
removed, while every repeated warm occurrence still performs two candidate audits
plus one independent selected-plan audit. Wall-clock observations are diagnostic and
non-normative, but the exact `20 candidates / 30 audits` count justifies testing an
identity-bound certificate memoization or incremental-proof operator before assuming
that more dynamics acquisition is the dominant tax.

No operator is selected in V0-049:

```text
tax_operator_selected = false
dominant_tax_axis = null
sample_efficiency_claimed = false
official_scalar_cost = null
official_N_break_even = null
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## Canonical identities

```text
family_protocol_id = 96589cb7d925ca856e2c83ab8dfb3beb859225bde2cbe2311caf06e5111b8e58
family_eligibility_proof_id = 45cbb9b7f99ca88905876d11c2e1b600fc10d0d75c496cf5a2104a25f48398ab
family_v5_model_id = d60d051e9422a40f3088875fa6a47e34f153dae4967dfcff5faf9547837a5b12
family_promotion_build_id = 93522fbcd24003d5ca9d2554a0a9c38eaf3d50f501211a394a475f96d057f4d7
family_telemetry_id = 3df1ce57d3f7f1cee83da42cf422552c452498b1cd02ea904842c251cd0ec0cc
prefix_10_id = 28a8cbeac22b1c3116af2c00cd7996b7517e0e88959d313165dc7780edd4192e
family_result_id = 0445866669fdc2863856daf6986e855de71ba751e3b1f37b747b5490bf2880ba
```

These identities are regression anchors, not substitutes for semantic replay.

## Required regressions

1. family preregistration has no source result or kernel input;
2. source acquisition has no family target or protocol input;
3. all three target states are distinct and absent from V0-045;
4. the ten-occurrence order and repetition indices are frozen before source work;
5. complete 20-row promotion and all 13 evidence records are retained;
6. V5 authorizes exactly three initial states and H1 only;
7. every warm occurrence certifies `1/0/0` with zero target ground calls;
8. the cold API has no promotion/source input and executes `3+1` native ground work;
9. method-level tracing observes one explicit catalogue plus three step-internal
   legality checks without modifying the frozen kernel source;
10. every warm/cold certificate and every source evidence row matches exactly;
11. source, promotion evaluation, warm, and cold lanes remain distinct;
12. all ten prefix vectors and componentwise relations are exact;
13. scalar, break-even, sample-efficiency, scope, and work-vector escalation fail;
14. canonical IDs remain fixed;
15. a complete independent replay is byte-identical.

## Claim boundary and next Gate

V0-049 proves a finite exact multi-occurrence scoped-reuse and vector-amortization
control. It does not prove unrestricted reuse, statistical transfer, learned dynamics,
unknown-coordinate invention, large-state scalability, environment-sample reduction,
or official workload economics.

The next Gate should preregister and execute an identity-bound certificate-reuse
intervention with matched no-reuse controls. It must prove that cached or incremental
proofs are valid only for identical model/query/threshold/plan identities, invalidate
on every relevant identity change, preserve independent evaluation replay, and reduce
native audit/hash/serialization work without changing reward, risk, regret, or ground
access. Only after that experiment should the project decide whether the next tax
operator belongs to certificate reuse, coordinate/meta-prior transfer, or dynamics
acquisition.
