# H2 stage-local temporal proof DAG (V0-052)

Status: normative implementation contract

Contract version: `1.15.0`

Schema version: `1.0.0`

Profile: `lmb_h2_stage_local_bellman_proof_dag_v0`

Passing status: `CERTIFIED_REGISTERED_H2_STAGE_LOCAL_BELLMAN_RECURRENCE_CONTROL`

## 1. Purpose and source boundary

V0-052 is the first registered H2 proof-factoring control. It consumes the unchanged
**final query-local H2 V3** produced by V0-047. It must not substitute V0-048/V0-049's
promoted V4/V5 H1 models, rebuild V0-047 under a new identity, or relabel this proof
layer as a world-model promotion. The V0-047 final V3 model, query, reward/risk
semantics, exact observation authority and selected action catalogue are frozen source
inputs. Their source goldens are:

```text
V0-047 result ID = 9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42
final V3 model ID = a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315
selected Gray-00 plan ID = 0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb
```

The semantics identity also pins every implementation source consumed by the
stage-local arithmetic and selection protocol:

```text
partial_sound_audit_v1.py = 661aee3732afda05c860f5dadae2b3545ecbbed7cee86f27517d1ea5dfcb7934
partial_model_planner_v1.py = b676c4f91d18ea9406ef1101d7072baccb519a05176496ccf6a867cedb6d4f7d
multistep_query_refinement_v1.py = d335b509311f6d87a6e2106d1090580f3c7c4cca8cd4eaa4209fff4038e54845
incremental_proof_dag_v1.py = f67a5d7fd47eddccca6124c859bf636230f76b228d37dcc399d8e3ce7dbfec6b
```

The exact source implementation pins are:

```text
V0-043 partial-audit source SHA-256 = 661aee3732afda05c860f5dadae2b3545ecbbed7cee86f27517d1ea5dfcb7934
V0-047 multi-step source SHA-256    = d335b509311f6d87a6e2106d1090580f3c7c4cca8cd4eaa4209fff4038e54845
V0-051 predecessor source SHA-256   = f67a5d7fd47eddccca6124c859bf636230f76b228d37dcc399d8e3ce7dbfec6b
```

V0-051 is pinned as a historical dependency/attack boundary only. Whole-horizon
V0-051 helper reuse is forbidden; V0-052 must construct and verify its H2 temporal
nodes directly.

The purpose is narrower than persistent proof caching or full incremental model
maintenance: expose the temporal Bellman and reachability dependencies of four H2
plans, reuse only stage-local facts whose exact semantic identities are unchanged, and
freshly rebuild every affected descendant and every request root.

## 2. Frozen workload

The action alphabet is the two registered semantic actions `A0` and `A1`. Before
execution, the protocol freezes this exact candidate order:

```text
A0A0 -> A0A1 -> A1A1 -> A1A0
```

There are exactly five proof requests:

1. candidate-role audit for `A0A0`;
2. candidate-role audit for `A0A1`;
3. candidate-role audit for `A1A1`;
4. candidate-role audit for `A1A0`;
5. an independently keyed selected-plan certificate for `A0A0` (Gray `00`).

The requests execute in exactly that order: all four candidates first, then the
selected request. Four plan-partitioned caches are keyed by complete plan ID; after
the fourth candidate, the selected request returns to the Gray-`00` partition. It has
a distinct proof role and root, and candidate evidence cannot authorize it.

The complete query, thresholds, source V3 epoch and action semantics are identical in
all five requests. This is a changed-plan control, not a changed-query, changed-
threshold, changed-model or changed-reward workload.

## 3. Eleven-slot dependency graph

Every request resolves the following eleven logical slots:

```text
U1 -> U0
P1 -> P0
C0 -> C1
D  <- U0, P0, C0, C1
E  <- D
F  <- D
G  <- C0, C1
R  <- U1, U0, P1, P0, C0, C1, D, E, F, G
```

Their meanings are:

- `U1,U0`: action-unrestricted Bellman proof at future stage 1 and root stage 0;
- `P1,P0`: fixed-policy Bellman proof for the plan's stage-local action and temporal
  continuation;
- `C0,C1`: forward reachable/support proof at stages 0 and 1;
- `D`: root/support value-risk metrics derived from `U0,P0,C0,C1`;
- `E`: regret verdict derived from `D`;
- `F`: risk verdict derived from `D`;
- `G`: external-coverage verdict derived from `C0,C1`;
- `R`: the complete request-, plan- and role-bound legacy-equivalent audit root.

The ordered parent list is part of every content identity. Missing or extra edges,
parent reordering, cycles, skipped affected descendants, and cross-stage substitution
are invalid.

## 4. Stage-local identity rule

Lower nodes bind only the exact source and **local temporal facet** required by their
semantics: stage index, local semantic action where applicable, local support, exact
recurrence parent IDs, and the fixed query/reward/risk or threshold facet where that
node actually consumes it. They do not bind the complete two-action plan, request ID,
proof role or selected-result ID merely to prevent legitimate temporal sharing.

Consequently:

- `U1` and `U0` are plan independent for the frozen source/query;
- `P1` keys the stage-1 action, while `P0` keys the stage-0 action and its exact `P1`
  parent;
- `C0` keys the stage-0 action/support transform, while `C1` keys the stage-1 action
  and exact `C0` parent;
- `D/E/F/G` are re-derived whenever their ordered lower parents or consumed facet
  changes.

`R` is deliberately different. It always binds the complete source, query,
thresholds, two-action plan, request, proof role and, for the selected role, the
selected planner result. All existing threshold-/plan-bound legacy V0-043 row and
result objects are materialized only at `R`; none is admissible as a lower stage-local
node.

The exact changed-stage invalidation cones are:

```text
stage-1 action change -> P1,P0,C1,D,E,F,G,R
stage-0 action change -> P0,C0,C1,D,E,F,G,R
```

`U1,U0` remain unchanged throughout this fixed-source plan workload. On the final
candidate transition `A1A1 -> A1A0`, the stage-1 action returns to an already computed
`A0` identity: `P1` is a historical global-cache hit, while every other affected slot
is freshly derived under its current parents. A previous matching suffix is reusable;
a previous complete-plan result is not.

## 5. Matched reset arms and exact counts

Each arm resolves `5 * 11 = 55` logical slots and emits an append-only receipt for
every resolution.

| Arm | Reset rule | Computes | Hits |
|---|---|---:|---:|
| `REQUEST_RESET` | empty before every proof request | 55 | 0 |
| `EXACT_PLAN_PARTITIONED` | four independent plan-ID caches; Gray-`00` selected reuse allowed | 45 | 10 |
| `GLOBAL_STAGE_DAG` | one initially empty cache for the full workload | 35 | 20 |

The cumulative request-prefix `(computes, hits)` values are frozen as:

```text
request reset:    (11,0), (22,0), (33,0), (44,0), (55,0)
plan-partitioned:(11,0), (22,0), (33,0), (44,0), (45,10)
global DAG:       (11,0), (19,3), (27,6), (34,10), (35,20)
```

The four plan-group contributions, listed in Gray order `00,01,11,10`, are:

```text
request reset:    (22,0),  (11,0), (11,0), (11,0)
plan-partitioned: (12,10), (11,0), (11,0), (11,0)
global DAG:       (12,10), (8,3),  (8,3),  (7,4)
```

The global per-slot `(computes, hits)` totals are:

```text
U1 (1,4)   U0 (1,4)
P1 (2,3)   P0 (4,1)
C0 (2,3)   C1 (4,1)
D  (4,1)   E  (4,1)   F (4,1)   G (4,1)
R  (5,0)
```

Aggregating the temporal slots into semantic groups gives the following exact
`(computes, hits)` counts:

| Arm | U | P | C | D | E | F | G | R |
|---|---|---|---|---|---|---|---|---|
| request reset | 10/0 | 10/0 | 10/0 | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 |
| plan-partitioned | 8/2 | 8/2 | 8/2 | 4/1 | 4/1 | 4/1 | 4/1 | 5/0 |
| global DAG | 2/8 | 6/4 | 6/4 | 4/1 | 4/1 | 4/1 | 4/1 | 5/0 |

Only `45 - 35 = 10` avoided constructions may be attributed to cross-plan temporal
reuse. The larger `55 - 35` difference includes the independent-selected request's
same-plan lower-node reuse and must not be presented as cross-plan savings.
These are proof-node counts, not transition samples, total work, bytes, or wall time.

## 6. Required equivalence and replay

For all five requests, `R` must reproduce the unchanged authoritative H2 audit result
for the same V0-047 final V3 source, plan, query, thresholds and role. The independently
selected root must contain the complete selected-plan certificate and cannot be
authorized by a candidate root.

The production runner performs no target ground transition, action-catalogue,
acquisition, refinement, promotion or ground-optimizer call. An independent verifier
must rebuild the unchanged V0-047 source, reconstruct all five authoritative audits,
replay every pre/post cache state and receipt, and recompute the three arms from a
canonical empty state.

## 7. Fail-closed attacks

The verifier rejects at least:

- use of V4/V5 or the V0-047 first `11/9` V3 epoch in place of the final `20/0` V3;
- plan order, action, stage, query, threshold, reward, source or role substitution;
- whole-plan identity hidden inside a lower node or a legacy row injected below `R`;
- missing/extra/reordered parents, stale descendants, cross-stage facts or cycles;
- prewarming, foreign cache import, overwrite, rollback, receipt deletion/reordering,
  owner-copy authority and content-domain substitution;
- a candidate root presented as the independent selected certificate;
- any uncharged target ground access or model promotion.

## 8. Sole positive claim and locked claims

Passing sets exactly:

```text
registered_h2_stage_local_bellman_recurrence_claimed = true
```

It does not set or imply any of the following:

```text
generic_h_gt_1_recurrence_claimed = false
cross_query_incremental_proof_claimed = false
changed_threshold_incremental_proof_claimed = false
changed_model_incremental_proof_claimed = false
changed_reward_incremental_proof_claimed = false
persistent_cache_claimed = false
closed_loop_incremental_repair_claimed = false
sample_reduction_claimed = false
sample_efficiency_claimed = false
workload_economics_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

This is a multi-step proof layer over one frozen RAPM. It is not another world-model
construction or promotion result.

## 9. Canonical identities

The implementation and replay freeze these canonical values:

```text
h2_temporal_manifest_id = e25068045e4585b9d7687fa2d935f2bf5bb8247fe689f6c06405113b34f4138d
h2_temporal_protocol_id = 3f29147af4b527830d73b52751edaeef214244a1cac9b8d0c45493edd28bb5dc
h2_temporal_semantics_profile_id = d05a05a5b0cee242f586fdadfed64df7082803d9055988fc22b5a521959f5849
h2_temporal_global_cache_id = 79fa6ad025eff7f286d1a690b1a5f9ec28f4363b3105dfec3d0dd33ef32e3f6c
h2_temporal_global_execution_id = 922a0c02e2ff4218a973280c090745bb34d1fd0212b729563229dffd90dd0916
h2_temporal_result_id = 6b6ca2b9925c54845f7bf9930a947bcaac2c0541db339594509218c323186618
```

No Gate may pass if replay differs from any frozen identity.

## 10. Next construction Gate

The next Gate must connect the authentic V0-047 model evolution to this temporal DAG:

```text
failed certificate on the first V3 epoch
-> acquire authorized query-local rows
-> freeze a new V3 epoch
-> invalidate only proof nodes whose model/stage facets changed
-> replan
-> independently re-audit
```

That Gate must use the real V0-047 first-to-final overlay row change and charge every
ground acquisition. It may not simulate model change by swapping an identity label,
claim persistent cross-process authority, or infer a sample-tax reduction from the
current frozen-model node counts.
