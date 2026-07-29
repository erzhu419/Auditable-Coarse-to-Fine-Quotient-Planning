# Observation-Discovered Partial-Support Gate

## Status and claim boundary

V0-068 is the first construction Gate after V0-067. It removes exact local
transition-support descriptors from the operational planner while retaining:

- symbolic state observations;
- a complete legal-action catalogue for each observed state;
- the pretrained V0-066 relational state/action skeleton;
- a registered finite H=2 query family;
- exact fallback and exact policy evaluation in separately charged lanes.

The operational path receives only complete realized transition tuples. It
does not receive an atom ordinal, atom count, spawn law, outcome-support list,
transition probability, or pre-enumerated reward/failure label.

The intended positive claim is limited to a discovery-frozen partial world
model:

```text
target discovery tuples
→ freeze observed support S_e
→ fresh validation tuples
→ target-local confidence sequence over S_e ∪ {OTHER}
→ robust partial RAPM
→ contingent planning and sound audit
→ optional failed-frontier support epoch
→ separately charged exact fallback when the cap is reached
```

Finite observations do not prove exact support completeness. Every certified
statistical row retains one explicit `OTHER` category with a generally
positive upper bound.

V0-068 does not claim raw perception, primitive or legal-action discovery,
unbounded open-world support, exact support recovery, source-dynamics
transfer, broad graph/domain generalization, changed-query reuse,
independent-planner verification, total-work economics, or completion of the
general reusable-hidden-world-model objective.

## Registered public contexts

The public context artifact contains only:

- an opaque context key and content ID;
- graph topology;
- root symbolic state;
- horizon;
- rank and reward caps needed to validate observations;
- risk and regret thresholds;
- observer and legal-action semantics IDs.

It must not serialize a spawn support, spawn probability, target role,
outcome cardinality, or exact-risk value.

The registered evaluation family contains:

1. a five-vertex positive graph context;
2. a six-vertex positive graph context with a hidden three-rank spawn law;
3. a six-vertex missing-edge no-cover context.

The changed six-vertex hidden law prevents the V0-066 binary support from
being silently reused as target support.

The missing-edge query freezes

```text
delta = 2847 / 20000.
```

This is a strict separator: the exact ground optimum has failure
`2277/16000`, while the base quotient lift has failure `11393/80000`.
Consequently the fixture is feasible on the ground but cannot be accepted by
the registered coarse quotient. It must reach the same exact feasible
fallback rule in both the direct and quotient comparison lanes when their
partial statistical proofs remain unresolved.

## Opaque transition observer

The only operational dynamics interface is:

```text
observe_transition(
    public_context_id,
    symbolic_state,
    legal_action,
    remaining_horizon,
    observation_lane,
    support_epoch_id,
    sample_index
)
→ ObservedJointTransition
```

An observed tuple contains:

- next symbolic state;
- realized normalized reward;
- failure and horizon-terminal flags;
- row, lane, epoch, and sample identities;
- a replayable raw commitment.

It contains no support-relative ordinal. The consumer must work if every
exact atom-enumeration function is replaced by an exception.

The exact atom enumerator and exact ground search exist only behind explicit
`EVALUATION_ONLY` or fallback authorities. Their work cannot be included in
the acquisition lane.

### Randomness qualification

The checked-in transition stream is a deterministic SplitMix64 counter replay
benchmark. It makes raw-prefix identity and attack replay reproducible, but it
does not itself prove that the generated words are IID. Consequently every
V0-068 statistical result must carry:

```text
exact_iid_implementation_claimed = false
formal_exact_iid_plan_certificate = false
statistical_claim_scope =
  CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_
  NOT_PROVEN_BY_DETERMINISTIC_REPLAY_IMPLEMENTATION
```

V0-068 may issue only a conditional registered-observation certificate. A
future formal-IID execution profile must precommit independently sampled raw
tapes, or freeze a separately justified computational-PRF assumption, before
observing outcomes. Standalone exact lift evaluation cannot upgrade this
randomness claim.

## Discovery/validation split

For every authorized state-action-time row, epoch 1 consumes a fixed
discovery segment and freezes:

```text
S_e = distinct joint outcome identities observed in discovery.
```

Discovery observations propose the event set but provide no confidence
evidence. Validation uses a different stream domain. Conditional on frozen
`S_e`, its fixed partition is:

```text
{Y = s : s ∈ S_e} ∪ {Y ∉ S_e}.
```

The last event is the single joint `OTHER` category. Validation observations
whose outcome is not in `S_e` remain `OTHER` for the entire epoch even when
their raw identities are recorded.

An old validation segment may propose new identities for a later support
epoch, but it may not contribute probability counts to that later epoch.
Every later epoch requires a fresh validation domain and a new content-bound
confidence authority.

## Confidence allocation

The row-epoch tail budget is:

```text
beta = 1 / 64000.
```

At most sixteen discovered atoms are permitted. After discovery freezes a
partition of size:

```text
m = |S_e| + 1 ≤ 17,
```

each event receives:

```text
alpha_event = beta / m.
```

Every event uses the V0-067 uniform-Beta likelihood-mixture confidence
sequence. One alpha covers all registered validation checkpoints. A row
epoch therefore has conditional tail at most `beta`; the preregistered
row-epoch cap supplies the family-level union bound without assuming
independence.

The family cap is frozen before execution:

```text
maximum unique considered row-epoch authorities = 512
family tail upper = 512 / 64000 = 1 / 125
family confidence lower = 124 / 125
```

The family manifest contains every row authority considered by planning,
including failed checkpoints and rejected candidate profiles, not only rows
on the final selected policy. Direct and quotient labels over the identical
physical authority deduplicate statistically while retaining separate
logical work charges. Exceeding the cap is `CAP_EXHAUSTED` and cannot produce
a plan certificate.

Support, row, event, checkpoint, epoch, alpha authority, and stream-domain
identities are content-addressed. Missing, duplicated, stale, or cross-role
identities invalidate the certificate.

## Joint interval simplex

For one row epoch, confidence output is:

```text
p_i ∈ [l_i, u_i]       for each s_i ∈ S_e
p_other ∈ [l_o, u_o]
sum_i p_i + p_other = 1.
```

The verifier must establish that this polytope is nonempty. Bellman
minimization/maximization optimizes over this joint simplex. It must not:

- add the same `OTHER` upper bound to several destinations;
- independently realize every marginal upper endpoint;
- omit `OTHER`;
- force `u_o` to zero because no novel validation outcome occurred.

For a lower-value/safety certificate, `OTHER` has:

```text
failure value = 1
continuation value lower = 0
reward lower = 0 unless a separately frozen row-homogeneous reward law applies.
```

An out-of-registry active destination without a registered escape handler
fails closed.

The registered handler is the typed, query-bound
`ABSORBING_POLICY_ABORT_FAILURE` handler. During standalone exact lift, every
exact positive-probability outcome absent from the frozen row support is
mapped to that one absorbing failure destination before recursion. The
handler identity binds the context, query semantics, unique `OTHER`
destination and failure behavior; transplanting it across those identities
is invalid.

The only certificate-eligible model constructor is the authority-bound graph
bridge. Its verifier replays every observation row and confidence authority,
then rebuilds the event-to-typed-destination bijection, the unique `OTHER`,
reward bounds, complete reachable action catalogues, relational coordinates,
and the full distinct inverse-action concretizer. A bare interval model,
threshold object, or robust-planner replay is only a mathematical subroutine
and is not certificate evidence. Risk, regret tolerance, rank cap, and
`R_max = 3/64` are reconstructed from the registered public context.

## Robust H=2 planning

The direct planner solves the observed ground H=2 model. The quotient planner
groups observed state/action rows only through the pretrained relational
skeleton and any target-generated bounded refinement program. Both planners:

- use the same row confidence authorities;
- choose a deterministic semantic or ground policy;
- use a fixed uniform distinct-action concretizer for a semantic action;
- require a complete policy for every reachable observed continuation;
- treat `OTHER` adversarially once;
- stop only at the first plan satisfying risk and normalized-regret bounds.

The standalone exact evaluator may check the lifted policy after the
operational result is frozen. It cannot repair or retroactively issue the
operational certificate.

An exact fallback cap is evaluated only after a complete exact search. It is
a post-hoc work classification, not an interruptible hard-cap claim.
`FALLBACK_CAP_EXHAUSTED` is a noncertificate outcome and can never be
relabelled as infeasibility.

## Local support epoch

If a failed proof is causally attributable to `OTHER` on an earliest selected
row and that row recorded novel validation outcomes, one local expansion is
permitted:

```text
S_(e+1) = S_e ∪ observed-novel-outcome identities.
```

The old model and confidence authority remain immutable. The new row,
support epoch, validation stream, partial RAPM epoch, plan, and audit receive
new identities. Only the failed-frontier row is replaced. A new certificate
must be derived from the updated model.

Expansion without a failed missing-mass frontier, reuse of old validation
counts, or modification of the prior epoch is a protocol failure.

Promotion additionally requires a content-addressed expansion authorization.
The verifier tests each selected `OTHER`-positive row by clearing only that
row's `OTHER` coordinate and rerunning the same robust solver. It authorizes
only the deterministic earliest individually causal row and binds the parent
bridge/model/audit/assignments/threshold/frontier and exact novel identities.
The promoted row uses fresh validation and produces a pending immutable model
epoch; the old closure is never edited in place.

The registered campaign executes exactly one such transaction on K6 at the
8192 checkpoint after both the base quotient and every registered coordinate
candidate fail. It freezes:

```text
promoted-row fresh validation = 2048
new-child validation checkpoint = 8192
new child catalogues = 7
new child rows = 30
incremental observer draws = 249728
```

The mixed-epoch replan remains a real failed frontier:

```text
failure upper = 1321268563 / 17179869184
normalized regret upper = 1300423631 / 38654705664
status = FAILED_PROOF_FRONTIER
```

Since the risk upper is greater than `1/20`, this transaction is not a
certificate. Its work and immutable failed result remain in the campaign,
and the registered runner continues to the next global checkpoint. V0-068
does not authorize a second promoted row; a later contract must add a
different-row transaction budget and a new frontier/epoch identity.

On the integrated K6 route, cold direct first certifies at 8192, while the
quotient route first certifies at 16384 after the failed local transaction.
Their unique raw-observation totals are respectively `165120` and `578688`.
Thus local promotion narrows one missing-support frontier but does not
certify earlier; its evidence remains added cost. It neither removes the
unknown-support sample tax nor establishes a matched observation advantage.

## Matched direct control and accounting

Positive quotient occurrences are compared with cold direct-ground
occurrences that receive the same public contexts, opaque observer,
discovery size, checkpoints, caps, confidence allocation, raw seeds, and
fallback rule. Direct planning may not pre-enumerate the exact H=2 closure.

The primary construction result and any observation-saving result are
separate:

```text
construction_gate_passed
matched_observation_advantage
```

The Gate can establish the first without asserting the second. A sample
advantage requires a strict aggregate saving and no positive-context harm
against the matched sequential direct control.

Counters distinguish:

- discovery transition calls;
- validation transition calls;
- random-word and rejection work;
- support epochs and promoted outcomes;
- robust model/audit work;
- fallback exact rows;
- standalone evaluation exact rows.

Operational exact support/probability queries must be zero.

Only unique raw observation-prefix calls are eligible for the matched
observation comparison. Random-word/rejection work, logical rebuild work,
model/audit work, promotion work, fallback exact rows and standalone exact
rows are still reported separately; V0-068 does not infer total-work or
economics dominance from that one endpoint.

The only Gate-eligible verification is the complete campaign verifier. It
mechanically reconstructs the all-considered chronology, replays every raw
closure and promoted row, rebuilds the confidence-family manifest, verifies
typed bridge/audit/freeze/lift/fallback roles, and reruns the campaign.
Passing a bare bridge, family authority, interval audit or selected-plan
artifact is insufficient. This remains same-implementation semantic replay,
not an independently implemented planning algorithm.

## Required attacks

The Gate includes at least:

1. exact atom enumeration monkeypatched to raise during operational planning;
2. public spawn-law/support injection;
3. support-relative ordinal or atom-count side-channel injection;
4. discovery/validation stream-domain aliasing;
5. post-validation mutation of `S_e`;
6. reuse of validation samples after epoch expansion;
7. novel-outcome deletion or relabeling;
8. omitted, narrowed, or duplicated `OTHER`;
9. infeasible interval simplex;
10. stale support/epoch/model/frontier transplant;
11. expansion without a missing-mass causal frontier;
12. support, row, or epoch cap exhaustion mislabeled as infeasible;
13. alpha-authority duplication, reuse, or family undercount;
14. quotient/direct raw-prefix mismatch;
15. exact fallback/evaluation work charged as acquisition;
16. missing reachable policy assignment;
17. cross-context evidence transplant;
18. raw transition or commitment tampering;
19. a certificate artifact that sets every reachable `OTHER.upper` to zero.
20. omission of a rejected coordinate candidate from the all-considered
    family manifest;
21. an exact lift or fallback call before a typed operational route freeze;
22. a bare lower-level authority presented without complete campaign replay;
23. a fallback cap exhausted result relabelled as infeasible;
24. an `OTHER` escape handler transplanted across context/query identities.

## Locked outcomes

Until the real registered campaign, semantic replay, attacks, and stable
repository regression all pass:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```
