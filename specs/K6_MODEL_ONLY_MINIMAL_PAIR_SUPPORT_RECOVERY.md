# K6 Model-Only Minimal-Pair Support Recovery

Status: normative V0-070 bounded-Gate contract
Contract: `1.34.0`
Profile: `k6_model_only_minimal_pair_support_recovery_v0`

## Purpose

V0-069 found 49 eligible transaction-1 selected-policy rows on the K6
8,192-draw mixed model. Every distinct-row single-zero-`OTHER`
counterfactual remained uncertified. V0-070 tests the next smallest causal
support hypothesis without opening a combinatorial or observational search:

```text
the current failed contingent policy can be certified only after jointly
recovering two distinct support rows
```

This is a bounded `k <= 2` Gate on the frozen transaction-1 selected-policy
frontier. It is not arbitrary subset search, a third transaction, or a
sample-efficiency claim.

## Frozen execution

The only legal sequence is:

```text
freeze the V0-069 NO_SOUND_DIFFERENT_ROW_COVER result
  -> reconstruct a fresh candidate registry from the transaction-1
     mixed-model selected-policy frontier
  -> replay every singleton on the frozen current policy
  -> if every singleton fails, enumerate canonical unordered pairs
  -> for each pair, jointly set exactly those two OTHER intervals to zero
  -> recompute the complete fixed-policy H=1 -> H=2 recurrence
  -> retain sufficient fixed-policy pair covers
  -> compute exact pre-materialization cardinality and draw upper
  -> select at most one budget-admissible pair
  -> freeze one joint authorization before opening either fresh stream
  -> promote both rows, rebuild complete H2 closure, and perform at most
     one full quotient robust replan
  -> stop
```

The model-only phase may not call an observer, a kernel, an exact evaluator,
the global 16,384 checkpoint, a promotion authority, or the full robust
policy search.

## Minimality and claim scope

Candidate cardinality is searched in the fixed order `1, 2`. All registered
singletons must independently remain failed before any pair is considered.
All unordered pairs of the freshly reconstructed registry are then tested.

The fixed-policy replay is a sufficient screen for the current contingent
plan. It intentionally may miss a pair that certifies only after a policy
switch. Therefore a positive result proves only:

```text
MIN_CARDINALITY_WITHIN_TX1_SELECTED_POLICY_FRONTIER_UP_TO_K2
```

It does not prove global subset minimality or absence of a different
certifiable policy under an unselected pair.

Each joint overlay recomputes the full H2 recurrence. Summing singleton
deltas, assuming row independence, or using a one-step surrogate is
forbidden. The conservative regret test retains the parent unrestricted
ground reward upper; zeroing `OTHER` cannot improve that comparator.

## Combination and sampling controls

The registered caps are:

| Quantity | Hard cap |
|---|---:|
| eligible rows | 64 |
| singleton model-only evaluations | 64 |
| unordered pair model-only evaluations | 2,016 |
| subset cardinality | 2 |
| selected pair count | 1 |
| operational full joint replans | 1 |
| promoted rows | 2 |
| fresh validation draws per promoted row | 2,048 |
| newly admitted child catalogues | 19 |
| newly acquired child action rows | 19 |
| validation draws per new child action row | 8,192 |
| discovery draws per new child action row | 64 |
| incremental observer draws | 160,960 |
| maximum global checkpoint | 8,192 |

The draw upper is computed before sampling:

```text
pair promotion draws = 2 * 2,048 = 4,096
new-child row draws  = 64 + 8,192 = 8,256
incremental upper    = 4,096 + 8,256 * new_child_action_rows
```

The cap of 19 rows is deliberate:

```text
4,096 + 19 * 8,256 = 160,960 < 163,840
4,096 + 20 * 8,256 = 169,216 > 163,840
```

Thus the selected local continuation must use fewer new observations than
advancing the existing quotient route from the transaction-1 prefix to the
global 16,384 checkpoint. This is only an avoided-future-tax comparison.

Among fixed-policy covers that satisfy all caps, select deterministically by:

```text
(incremental_draw_upper,
 -minimum_certificate_slack,
 canonical_pair_planner_row_ids)
```

Only the selected pair may be materialized. Pair evaluation may be scheduled
in parallel, but worker count and completion order are absent from content
identity.

## Matched-direct boundary

The registered physical sample boundary is frozen:

```text
matched direct K6 @ 8,192                 = 165,120
quotient transaction-1 prefix             = 414,848
remaining quotient suffix to global 16,384 = 163,840
matched-direct headroom                    = -249,728
```

The quotient prefix already exceeds matched direct by 249,728 observations.
No pair result can reverse that historical cost, even with zero new draws.
Every artifact therefore carries:

```text
matched_direct_sample_advantage_eligible = false
sample_efficiency_claimed = false
```

The local `163,840` boundary may only support an
`avoids_further_global_checkpoint_tax` diagnostic.

## Identity and no-reuse

The Gate context binds the V0-069 negative run, transaction-1 closure,
bridge, model, audit, frontier, threshold, selected policy, and cap profile.
V0-069 singleton evidence IDs are explicitly quarantined. They may establish
historical provenance, but they are not V0-070 causal authority.

The candidate registry is reconstructed from the current frontier and exact
source-row projections. The two selected parents must be distinct from one
another and from transaction 1 by:

- planner-row and partial-row identity;
- ground binding;
- physical evidence;
- support-epoch authority.

Both selected parents must be epoch 1 and have proposal-only novel
descriptors. The joint authorization freezes before either selected
validation stream is opened.

Each promoted row uses a fresh epoch-2 validation stream. The two fresh
streams must be mutually disjoint and disjoint from all discovery and
validation observations in every parent row. Old observations remain
proposal-only and cannot estimate the promoted epoch probabilities.

The final closure contains exactly three epoch-2 bindings: immutable
transaction 1 plus the two jointly authorized rows. Every other retained row
is byte-identical. Newly required child rows are fresh epoch-1 rows. If both
parents require the same new child row, it is acquired once and carries
union provenance; duplicate physical charging is forbidden.

Changing the parent model, audit, frontier, selected plan, threshold,
candidate registry, pair, cap, cardinality evidence, or transaction history
invalidates the authorization.

## Terminal outcomes

- `CERTIFIED_AT_8192_AFTER_JOINT_PAIR`
- `FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR`
- `NO_SOUND_FIXED_PLAN_PAIR_COVER`
- `PAIR_COUNTERFACTUAL_CAP_EXHAUSTED`
- `PAIR_COVER_SAMPLE_BUDGET_DOMINATED`
- `MATERIALIZATION_CAP_EXHAUSTED`
- `PROTOCOL_FAILURE`

If no pair is a sound fixed-plan cover, the Gate closes with zero observer
draws, zero exact calls, zero full replans, and zero 16,384 access. If covers
exist but every exact pre-materialization upper violates a cap or the
160,960-draw boundary, it closes as
`PAIR_COVER_SAMPLE_BUDGET_DOMINATED`, also before sampling.

No outcome authorizes cardinality 3, a third transaction, or infeasibility.
Cap exhaustion is a typed noncertificate.

## Independent verification

The standalone verifier:

1. reconstructs the candidate registry from the frozen source authorities;
2. independently implements interval-simplex extreme expectations;
3. independently replays the selected H1 actions followed by the H2 root
   action for every singleton and pair;
4. checks canonical enumeration, identities, selection, caps, and the
   matched-direct boundary;
5. verifies zero observer/exact/full-search access on nonmaterialized paths;
6. on a materialized path, rebuilds the closure and model, semantically
   replays the one final full robust audit, and verifies sample disjointness.

The verifier is evaluation-only. Its replay work is not operational route
work.

## Acceptance and attacks

The implementation must test:

1. the real K6@8,192 V0-069 parent has 49 fresh V0-070 candidates;
2. all 49 fresh singleton replays fail before pair enumeration;
3. at most `C(49,2) = 1,176` canonical pairs are evaluated;
4. every pair changes exactly two distinct rows and recomputes H1 then H2;
5. no-cover and budget-dominated paths perform zero observer, exact,
   promotion, full-replan, and 16,384 work;
6. a stale model/audit/frontier/threshold/selected-policy identity fails;
7. a singleton transplant or V0-069 evidence reuse fails;
8. duplicate, reversed, missing, or noncandidate pair identities fail;
9. a forged fixed-policy result, cost upper, or selected pair fails
   independent replay;
10. observer or exact access before authorization is a protocol failure;
11. the selected pair authorization precedes both fresh streams;
12. fresh streams are mutually and parent disjoint;
13. the final closure has exactly three epoch-2 bindings and complete action
    coverage;
14. no third transaction, cardinality 3, or global 16,384 checkpoint is
    reachable;
15. serial and parallel model-only schedules yield identical content IDs.

Items 11--13 are conditional acceptance obligations for any result that
actually reaches materialization. The registered negative result does not
claim that branch was exercised; it must satisfy the zero-access side of
item 5 instead.

## Claim boundary

This Gate tests whether a minimal joint support distinction, within the
current transaction-1 selected-policy frontier and cardinality at most two,
can certify the current K6 contingent plan before further global sampling.
It does not establish automatic coordinate invention, arbitrary-horizon
learning, cross-domain transfer, IID correctness, total-work advantage,
matched-direct sample advantage, or completion of the overall research
objective. Official execution, scalar, break-even, workload-economics, and
counter-completeness locks remain unchanged.

## Registered result

The complete K6@8,192 replay reconstructed 49 fresh candidates. All 49
singletons remained failed, after which the model-only Gate evaluated every
canonical unordered pair:

```text
eligible rows                     = 49
singleton overlays                = 49
singleton fixed-plan covers       = 0
unordered pair overlays           = 1,176
pair fixed-plan covers            = 0
outcome                           = NO_SOUND_FIXED_PLAN_PAIR_COVER
incremental observer draws        = 0
operational full joint replans    = 0
exact calls                       = 0
global 16,384 checkpoint accesses = 0
```

An independent fixed-policy recurrence replayed all 1,225 subset
obligations. A separate finite positive control shows that the joint
recurrence can detect pair interactions missed by every singleton. The
registered K6 result never reached authorization or materialization, so it
is not positive evidence for the dormant pair-materialization branch.

This closes only the cardinality-at-most-two fixed-plan hypothesis. It does
not license a brute-force cardinality-three search. The next sample-tax
intervention should use a source-frozen, target-evidence-gated acquisition
prior to rank proof obligations while retaining the unchanged target-local
sound certificate and a no-prior control.
