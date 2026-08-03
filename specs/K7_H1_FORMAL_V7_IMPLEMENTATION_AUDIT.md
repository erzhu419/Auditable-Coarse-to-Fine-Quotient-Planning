# K7 H1 formal V7 implementation audit

Status: implementation audit only; not a numeric upper, route decision, or
execution authority.

This audit fixes the next construction boundary after the H1 current-identity
candidate and sealed owned fallback engine.  It prevents the historical V6
route upper, fixture-only output model, or post-run shared-resource values from
being relabelled as a formal preexecution V7 authority.

## Exact registry partition

The frozen V6 accounting registry has 209 leaves, of which 202 are required
and 182 are operational comparison terms.  For `DIRECT_FALLBACK`, exactly 24
required paths may be nonzero:

- 16 operational paths: seven owned fallback/control paths plus nine shared
  resource paths; and
- eight derived reconciliation paths.

A formal V7 upper therefore contains exactly 182 operational terms:

```text
166 stage-forbidden zeros
+ 7 owned fallback/control terms
+ 9 shared-resource terms
= 182 terms
```

The later formal CounterRecord set must still contain all 202 required paths:
the 182 operational terms, 12 diagnostic native zeros, and eight derived
reconciliation values.  Nonrequired leaves cannot replace a required leaf.

## Required identity chain

The formal chain must bind:

- the exact H1 recipe and its replayed preexecution bytes;
- a production current-identity authority backed by an observed access log,
  protocol sequence, and freeze barrier (the current construction candidate is
  insufficient);
- the V6 registry, stage, comparison, and actual-projection profiles;
- a new V6 `RouteDecisionContextV1` and direct `DecisionPointV1` carrying the
  exact structural/query/plan/threshold/BuildEpoch/occurrence/attempt
  identities and typed not-applicable local fields;
- the sealed V4 owned-engine authority;
- one formal route-cap profile and independently verified preexecution
  cardinality/operand evidence;
- an exact 182-term formula and eight-axis upper; and
- one generic `RouteUpperBoundEnvelopeV1` followed by one
  `MarginalRouteDecisionV1` selecting `FALLBACK` because the local upper is
  typed missing/not applicable.

Historical V6 upper and decision IDs are references only and must not survive
as the formal V7 upper or decision IDs.

## Nine shared-resource upper formulas

Every path has a path-specific admission count `A_p`.  Evidence and admission
work cannot be reused across paths.  A tight preexecution value is obtained by
replaying the registered formula from independently verified cardinalities and
extents, then taking the minimum with the registered hard cap `H_p`.

```text
hash/integrity/protocol:
  U_p = min(H_p, sum_g registered_count(g) * 1)

read/staged:
  U_p = min(H_p, sum_g multiplicity(g) * extent(g))

mounted:
  U_p = min(H_p, max_t sum_{distinct payload visible at t} extent(payload))

output:
  U_p = min(H_p, max_b exact_branch_output_fixed_point(b))

working memory:
  U_p = min(H_p, outer_cgroup_cap,
                    broker_parent_cap + worker_role_cap + business_role_cap)

process launches:
  U_p = min(H_p, worker_launches + business_launches) = 2
```

The output maximum ranges over the preregistered reachable production branch
set.  The 72-case branch fixture validates mechanics but is not production
branch semantics.  Mounted bytes deduplicate only one physical payload
identity visible at the same time.  Working-memory evidence must cover the
broker continuously and bind the same retained `memory.peak` OFD plan.

The combined control upper is:

```text
U_control.cap_checks = 56 + sum_p A_p
U_control.cap_rejections = 1
```

`56` is the exact owned H1 search upper.  The rejection upper cannot be zero
for a branch-complete route unless a separate preexecution authority proves
the cap-exhaustion branch unreachable.

## Reusable construction pieces

The following mechanics are reusable without changing their historical
claims:

- V6 registry/stage/comparison/actual-projection profiles;
- the `166 + 7 + 9` partition mechanics;
- generic route context, decision point, upper, and marginal decision schemas;
- the exact H1 recipe chain once replayed from its source bytes;
- the nine-source manifest formula schemas;
- the eight-role branch-output serializer/fixed-point algorithm;
- the sealed owned V3 search and V4 seven-site source authority; and
- the post-run live-envelope and nine-path semantic replayers for actual work.

## Missing authorities and implementation order

The following products remain mandatory:

1. `construction_k7_h1_production_current_access_authority_v1.py`: join the
   current candidate to an observed zero-forbidden-access log and route-time
   freeze barrier.
2. H1 business adapter, role manifest, resource topology, runtime profile, and
   branch DAG, including the real nine-owner operation sites.
3. `construction_k7_h1_direct_fallback_operand_upper_v1.py`: independently
   verify all nine catalogues, cardinalities, hard caps, branch-safe output
   fixed point, admission counts, and combined control bounds.
4. `construction_k7_h1_direct_fallback_formal_route_v7.py`: construct the
   exact 182 terms, eight axes, formal upper, and formal route decision before
   any route execution access.
5. Execute only the selected route through the H1 two-process broker.
6. `construction_k7_h1_direct_fallback_native_accounting_v1.py`: materialize
   202 CounterRecords, WorkVector, ComparisonVector, exact actual projection,
   and componentwise `actual <= selected upper` proof.
7. Emit branch-correct terminal/campaign closure and independently verify the
   complete durable bundle.

Until every preexecution authority above is present, no route execution or
formal accounting materialization is allowed.  All official execution,
economics, scalar/break-even, counter-completeness, and sample-efficiency locks
remain unchanged.
