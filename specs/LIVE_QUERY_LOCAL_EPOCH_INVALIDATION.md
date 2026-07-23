# Live H2 query-local epoch invalidation (V0-053)

Status: normative implementation contract

Contract version: `1.16.0`

Schema version: `1.0.0`

Profile: `lmb_h2_live_query_local_epoch_invalidation_v0`

Passing status:
`CERTIFIED_REGISTERED_H2_LIVE_QUERY_LOCAL_EPOCH_INVALIDATION_CONTROL`

## 1. Purpose and claim boundary

V0-053 connects the authentic V0-047 first-to-final query-local model evolution to
the V0-052 H2 temporal proof DAG. It is the first registered control in which a failed
model-only certificate is frozen before local ground evidence is acquired, that
evidence creates an immutable successor model epoch, and only proof nodes whose exact
consumed facets or parents changed are rebuilt before replanning and independent
certification.

This is a live ordering and invalidation correctness control on one canonical H2
query. It is not satisfied by consuming a completed V0-047 result and reconstructing
an epoch/cache trace afterward. It does not claim generic changed-model incremental
proof, H greater than two, cross-query reuse, persistent caching, semantic policy
change, sample reduction, sample efficiency, total-work or wall-clock improvement,
economics, learned dynamics, coordinate invention, or official execution.

## 2. Production authority and live order

The production runner accepts exactly the eight upstream authorities already required
by V0-047:

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

It accepts no completed V0-047 result, first or final model, row/state list, plan,
invalidation closure, cache, control arm, expected result, legacy audit, ground
optimizer, or promotion choice. Its mandatory sequence is:

```text
verify the complete base failure chain
-> execute round one and evidence-derived boundary registration
-> freeze the first immutable V3 epoch
-> build four first-epoch candidate DAG roots
-> derive the first proposal from those roots
-> freeze a role-distinct independent selected failed root
-> derive and freeze the round-two request from that root/frontier
-> execute exactly its nine authorized ground rows
-> freeze the final immutable successor V3 epoch
-> derive the exact epoch delta and affected-descendant closure
-> build four final-epoch candidate DAG roots
-> derive the final proposal from those roots
-> freeze the final independent selected certificate
```

No round-two transition may occur before the first selected root is frozen. Production
constructs its stage-local roots directly; a whole-horizon V0-043 audit is an
evaluation-only independent-verifier authority. A consumer that accepts a completed
V0-047 result may emit only a separately labelled post-hoc replay control and may not
return the V0-053 passing status or positive claim.

## 3. Frozen V0-047 checkpoints

The first checkpoint is the V0-047 V3 model with:

```text
overlay_version = 1
observed rows = 11
missing rows = 9
selected audit outcome = FAILED_PROOF_FRONTIER
earliest time index = 1
remaining horizon = 1
reason = UNRESOLVED_POLICY_PATH_DISTINCTION
```

Its four candidate roots and role-distinct selected root must be frozen before any
second-round evidence access. The second request retains the exact native proof roles:

```text
selected-plan risk rows = 3
unrestricted value-challenger rows = 9
requested distinct rows = 9
global minimum claimed = false
```

Its operational execution performs exactly nine kernel steps and nine step-internal
legality checks, with zero direct boundary-catalogue calls, extra-row accesses, ground
searches, or ground optimizations. Step-internal legality is included in transition
work and is not charged again as catalogue work. The complete occurrence separately
retains the earlier four round-one steps and three direct boundary-catalogue calls.

The final checkpoint has:

```text
overlay_version = 2
previous_model_id = first V3 model ID
observed rows = 20
missing rows = 0
selected audit outcome = CERTIFIED_FIXED_PLAN
policy reward lower/upper = 1 / 1
policy failure lower/upper = 0 / 0
normalized distribution regret = 0
external coverage certified = true
```

The reusable base and first V3 documents remain byte-identical after their freeze.

## 4. Exact model delta

The epoch delta is derived from the two immutable model documents, never accepted from
the caller. It contains exactly the nine rows named by the round-two request and
evidence bundle, each changing from `MISSING_VACUOUS` to
`OBSERVED_SINGLETON`. No state/action catalogue, cell, semantic action, concretizer,
query, threshold, reward, horizon, or other row changes.

The nine rows were acquired from a time-one frontier, but they are stationary model
rows. Both unrestricted stages `U1/U0` scan them directly, and both fixed-policy
stages `P1/P0` directly consume the changed coord-3 realizations. `C1` directly
consumes their changed reachability facet. Therefore the exact direct consumed-facet
changes are:

```text
U1, U0, P1, P0, C1
```

Their affected descendants are:

```text
D, E, F, G, R
```

Only `C0` has an unchanged extensional input and may be reused across epochs. Numeric
or verdict equality cannot excuse reuse of any invalidated node.

## 5. Cross-epoch proof identities

Every proof request resolves the unchanged V0-052 topology:

```text
U1 -> U0
P1 -> P0
C0 -> C1
D  <- U0,P0,C0,C1
E,F <- D
G  <- C0,C1
R  <- U1,U0,P1,P0,C0,C1,D,E,F,G
```

Lower-node identities bind an allowlisted, content-addressed extensional model/stage
facet and exact ordered parent IDs. They may not bind the complete model ID merely to
force an epoch miss, and they may not omit a consumed row, realization, action,
support, reward, horizon, authority, formula, or parent merely to force a hit.

Every `R` remains freshly bound to the complete current model epoch, plan, query,
thresholds, request, proof role, and, for selected authority, the current proposal.
Existing V0-043 plan-/threshold-bound rows materialize only at `R`.

## 6. Replanning without a semantic policy change

Each epoch executes four candidate-role requests in Gray order:

```text
A0A0 -> A0A1 -> A1A1 -> A1A0
```

The proposal is derived from their DAG roots with the unchanged
numeric-then-semantic selection rule. A fifth request then constructs a separately
keyed independent selected root.

Both epochs select semantic schedule `A0A0` with key:

```text
(0,1,0,1,0,1,0,1)
```

The epoch-bound plan, proposal, request, and root identities must change, and the
planner must actually rerun. The semantic action schedule does not change. Unequal
plan IDs alone are therefore not evidence of a policy change and are not a sufficient
acceptance test.

All ten `R` roots must be byte-identical to the corresponding unchanged V0-043 audit
documents. Candidate roots cannot authorize either selected root. The first selected
root fails and the final selected root certifies the exact values in section 3.

## 7. Matched controls and exact counts

Two epochs times five requests times eleven slots give 110 logical resolutions in
every arm:

| Arm | Reset rule | Computes | Hits |
|---|---|---:|---:|
| `REQUEST_RESET` | empty before every request | 110 | 0 |
| `EPOCH_RESET_GLOBAL_DAG` | one empty global DAG per epoch | 70 | 40 |
| `GLOBAL_CROSS_EPOCH_FACET_DAG` | one initially empty facet DAG across both epochs | 68 | 42 |

The continuous arm's cumulative request-prefix counts are:

```text
computes = 11,19,27,34,35,45,53,60,67,68
hits     =  0, 3, 6,10,20,21,24,28,32,42
```

Its aggregate per-slot compute/hit totals are:

```text
U1 2/8   U0 2/8
P1 4/6   P0 8/2
C0 2/8   C1 8/2
D  8/2   E  8/2   F 8/2   G 8/2
R 10/0
```

At the final epoch, all five `C0` resolutions hit the two distinct `A0` and `A1`
entries constructed in the first epoch. Thus `70-68=2`, not five, is the exact count
of avoided distinct cross-epoch constructions. The controls share the same frozen
ground-evidence transaction and perform no additional operational sampling. These are
proof-node counts, not environment samples, total work, bytes, or wall time.

## 8. Independent replay and fail-closed attacks

The independent verifier accepts the eight production authorities plus the claimed
result. It independently reconstructs:

1. the complete V0-047 base, round-one, boundary, and round-two chain;
2. all 13 transitions and three direct boundary catalogues;
3. both immutable V3 epochs and the exact nine-row delta;
4. both four-candidate proposals and both independent selected roots;
5. all ten legacy-equivalent audit documents;
6. all three controls from canonical empty cache states;
7. every append-only cache pre/post state, resolution, receipt, closure, and count.

It then requires byte-identical claimed and reconstructed documents. Evaluation replay
ground work remains separate from operational ground work.

The verifier rejects at least:

- acquisition before the first selected failed root;
- a completed V0-047 result presented as live production authority;
- omission, addition, substitution, or reordering of any of the nine rows;
- final evidence leaked into a first-epoch node;
- mutation of the first epoch or reusable base after freeze;
- stale reuse of `U1/U0/P1/P0/C1` or any descendant;
- a false `C0` miss caused only by complete-model-ID partitioning;
- a false hit after mutation of any consumed stage facet or ordered parent;
- missing, extra, reordered, cyclic, or cross-stage edges;
- prewarming, foreign import, overwrite, rollback, receipt deletion/reordering, or
  owner-copy authority;
- candidate authority substituted for selected authority;
- an unequal model-bound plan ID presented as semantic-policy-change evidence;
- operational/evaluation ground-work mixing;
- mutation or substitution of the pinned V0-047/V0-052 implementation sources;
- wrong content domain, runtime type, source authority, query, threshold, reward,
  horizon, plan, request, role, model predecessor, or evidence binding.

## 9. Canonical identities

The following already-frozen V0-047 identities are mandatory source anchors:

```text
first V3 model ID = e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba
first proposal ID = b5db44c042eaa656980f942430c2fee6eda6fcf6ec8c0a1af1142b723ec006e4
round-two request ID = dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf
final V3 model ID = a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315
final audit ID = 81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529
V0-047 result ID = 9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42
```

These content IDs are integrity and binding anchors, not substitutes for the semantic
independent replay in section 8.

The deterministic V0-053 replay freezes the following domain-separated result roles:

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

Each role uses its registered content domain and schema. An ID from one role cannot
authorize another role even if an attacker constructs equal canonical payload bytes.
These hashes detect content or binding changes and anchor deterministic replay; they
do not prove live ordering, delta correctness, proof soundness, or certification
without the semantic checks in sections 2--8.

## 10. Sole positive claim and locked claims

Passing sets exactly:

```text
registered_h2_live_query_local_epoch_invalidation_claimed = true
```

The following remain false, null, or `NOT_RUN`:

```text
generic_changed_model_incremental_proof_claimed = false
generic_h_gt_1_recurrence_claimed = false
horizon_greater_than_two_claimed = false
semantic_policy_change_claimed = false
cross_query_incremental_proof_claimed = false
persistent_cache_claimed = false
sample_reduction_claimed = false
sample_efficiency_claimed = false
total_work_or_wallclock_reduction_claimed = false
workload_economics_claimed = false
learned_or_partial_dynamics_claimed = false
coordinate_invention_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## 11. Next construction Gate

The next Gate must move beyond this broad nine-row stationary update. It should use a
preregistered repeated H2 occurrence family with durable epoch/proof state and a
separate action-local sparse-delta fixture that causes a genuine semantic policy
change, while retaining matched no-reuse and cold-direct traces. Only after those
traces identify the actual acquisition/proof bottleneck may a Laplace-style heuristic
operator or KG-OP-style offline/online meta-prior become a mainline sample-tax
intervention.
