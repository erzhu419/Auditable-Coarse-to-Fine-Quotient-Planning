# Multi-step query-local RAPM evolution (V0-047)

Status: frozen deterministic positive control
Implementation schema: `1.0.0`
Profile: `lmb_h2_multistep_query_local_exact_refinement_v0`
Contract target: `1.10.0`

## Purpose

V0-047 is the first complete multi-step instance of the construction loop:

```text
observation-only reusable partial RAPM
  -> abstract contingent planning
  -> failed sound certificate
  -> proof-authorized local ground evidence
  -> immutable query-owned model epoch
  -> model-only replanning and independent audit
  -> later-stage failed-proof frontier
  -> second proof-authorized local ground evidence
  -> immutable second epoch
  -> certified abstract contingent plan
```

It extends V0-046 from an H1 row-completion control to an H2 path on which
time-zero evidence exposes three previously external active states and the next
certificate failure occurs at time one.  The V0-045 base is reconstructed and
retained byte-for-byte; it is never edited or relabelled as closed.

This profile is still a finite canonical positive control.  It does not claim
general causal minimality, unknown-DSL invention, learned dynamics, statistical
consistency, cross-query promotion, sample saving, or aggregate Gate closure.

## Frozen source and query

The source is the complete verified V0-045 artifact chain for the canonical
six-tile layered matching-buffer observation fixture.  Its reusable base model
has:

- 8 registered states;
- 11 registered state-action rows;
- 7 observed singleton rows;
- 4 missing vacuous rows;
- the observation-only selected state coordinate
  `cardinality(legal_actions)`;
- the observation-only selected action coordinate
  `buffer_at_type(buffer_counts, selected_tile_type)`, compiled to the boolean
  atom `<= 3/2`.

The V0-047 query starts at the sole active state whose four legal rows are all
missing and freezes:

```text
horizon = 2
risk_tolerance = 0
normalized_regret_tolerance = 0
reward_weights = canonical match + terminal-clear weights
policy class = deterministic finite-horizon abstract contingent plan
concretizer = the frozen uniform V0-045 concretizer
```

The producer must consume the full typed V0-044 proposal and independently
failed typed V0-043 audit.  A bare frontier, caller-provided row list,
caller-provided state list, caller-provided cap, or self-signed model cannot
authorize ground access.

## Round one: time-zero row completion

The verified source audit has an earliest frontier at:

```text
time_index = 0
remaining_horizon = 2
value_failed = true
risk_failed = true
```

The selected semantic realization has four missing rows, each with concretizer
probability `1/4` and reachable state mass upper `1`.  Therefore each row has a
current row-exposure upper of `1/4`.  The round-one authority requests exactly
those four rows and records:

```text
request_preparation_kernel_calls = 0
request_preparation_ground_search_calls = 0
maximum_exact_kernel_queries = 4
global_minimum_claimed = false
```

The exact LMB executor validates its frozen source/configuration and performs
exactly four deterministic `step` calls.  Their successors contain:

- one state already registered by V0-045;
- three distinct nonterminal external states.

The evidence contains the complete canonical successor state observation, not
only an opaque external reference.  Thus later boundary registration does not
replay any transition.

## Boundary registration and coordinate reuse

The three nonterminal external successors are derived from the round-one
evidence.  The caller cannot select or omit them.  For each state, the trusted
kernel returns its complete legal-action catalogue once:

```text
new boundary states = 3
new boundary ground rows = 9
direct action-catalogue queries = 3
transition queries during boundary expansion = 0
ground search calls = 0
```

Kernel identity is checked by exact runtime type, frozen configuration, structural
identity, and implementation-source digest. That check must not replay the eight
already verified base action catalogues. Instrumented ground-access replay sees 16
method calls: three direct boundary catalogue requests and 13 legality checks made
inside the 13 transition calls. The latter are charged inside transition work and are
not counted again as catalogue acquisition; no other caller or base replay is allowed.

V0-047 does not invent another coordinate.  It evaluates the exact V0-045
selected expression programs and compiled action atom on the three new states
and their actions.  All three states have state-coordinate value `(3,)` and
join the existing `(3,)` strategic coordinate signature.  The resulting cell
contains the old registered state plus the three boundary states, and every
member exposes exactly the two semantic labels:

```text
(False,)
(True,)
```

This is genuine within-query reuse of an observation-only synthesized
coordinate on previously unregistered states.  It is not held-out or
cross-domain validation and does not authorize promotion to the reusable base.

## First immutable V3 epoch

`QueryScopedPartialRAPMV3` is a distinct content domain and schema.  It permits
query-local boundary states and action catalogues while requiring:

```text
query_neutral = false
transition_closure_claimed = false
exact_quotient_claimed = false
plan_certificate_claimed = false
infeasibility_claimed = false
acquisition_query_neutral_attested = false
query_local_overlay_authority_required = true
boundary_catalogue_authority_required = true
base_model_mutated = false
promotion_authorized = false
```

The first epoch contains 20 registered rows: the original 11 plus the 9 new
boundary rows.  Its evidence coverage is:

```text
observed singleton rows = 11
missing vacuous rows = 9
```

All cells, actions, concretizers, ground rows, ambiguity simplexes, and semantic
realizations are replayed through the unchanged `PortablePartialRAPMV1`
structural validator.  The temporary V1 object is only a validator and is not
retained as a misleading query-neutral artifact.

## Stable semantic tie breaking

The first-epoch robust numerical bounds leave two stage-one action schedules
exactly tied.  A plan must not change because an unrelated schema edit changes
a content hash.  V0-047 therefore freezes:

```text
NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1
```

The original numerical selection tier remains authoritative:

1. certified plans before noncertified plans;
2. then the existing reward/risk ordering;
3. only among exact numerical ties, compare the time-ordered semantic boolean
   label schedule over cells ordered by their typed coordinate/member values;
4. use `plan_id` only after the semantic keys are also identical.

The rule and selected semantic key are serialized in the proposal artifact.
It does not weaken any value/risk Gate and performs no kernel query.  It is a
deterministic action-encoding rule, not a Laplace-style sample-reduction
operator or learned meta-prior.

After model-only enumeration of four plans and an independent selected-plan
audit, the failed-proof frontier moves to:

```text
time_index = 1
remaining_horizon = 1
reason = UNRESOLVED_POLICY_PATH_DISTINCTION
external_coverage_failed = false
```

## Round two: joint value-risk proof scope

The second request is derived only after the first epoch, plan, and independent
failed audit are frozen.  It is the union of:

- 3 selected-plan rows that retain positive unresolved risk exposure;
- 9 time-one missing ground rows that remain unrestricted value challengers
  under the zero-regret threshold.

The union contains exactly all 9 boundary rows.  Thus:

```text
selected-plan risk rows = 3
unrestricted value-challenger rows = 9
requested distinct rows = 9
maximum exact-kernel queries = 9
global_minimum_claimed = false
```

The distinction between the native roles is retained even though both project
to one exact transition query per distinct row.  The authority claims a
complete current frontier-local value/risk scope, not a global minimum over all
possible acquisition strategies.

The nine exact outcomes contain:

- three nonfailure transitions with one unit of `match` reward;
- six terminal failures with zero reward.

No additional row is accessed.

## Final epoch and certificate

The second immutable V3 epoch binds the first model as `previous_model_id` and
the second request/bundle as its new evidence source.  Its registered catalogue
still contains 20 rows, now with:

```text
observed singleton rows = 20
missing vacuous rows = 0
cumulative exact transition queries = 13
registered query-local states = 3
```

Zero missing rows over the registered query-local catalogue does not imply
global transition closure: some time-one nonterminal successors remain outside
the catalogue, but they occur at horizon truncation and therefore do not create
an H2 continuation obligation.

The final model-only planner enumerates four plans and chooses the `(False,)`
semantic action in the reused `(3,)` cell.  Independent audit must produce:

```text
outcome = CERTIFIED_FIXED_PLAN
policy_reward_lower = policy_reward_upper = 1
policy_failure_lower = policy_failure_upper = 0
normalized_distribution_regret = 0
external_coverage_certified = true
```

The planner and both independent audits perform zero exact-kernel calls.  No
direct ground optimizer is invoked.

## Telemetry and the sample-tax boundary

The canonical work trace is:

```text
round-one transition calls = 4
direct boundary action-catalogue calls = 3
round-two transition calls = 9
cumulative transition calls = 13
step-internal legality checks = 13 (included in transition calls)
model-only replanning passes = 2
candidate plan audits = 8
kernel calls during planning/audit = 0
direct ground-optimization calls = 0
```

This is the first real multi-step acquisition trace on which later sample-tax
work can operate.  V0-047 records the tax but does not impose a sample-efficiency
Gate and does not claim improvement over direct optimization.  A later revision
may compare heuristic operators or offline/online meta-priors against this
frozen trace without rewriting its claim.

## Canonical identities

The deterministic canonical replay currently produces:

```text
round_one_request_id = 8deedc2abc78cb4b91d866f2e77e311a8ed1f0336db8e41fc8b20fa330714636
boundary_expansion_id = 6b9770c03a9473c5ecf47437d9fe82eaf550524576a03932572ae47a78ae1ddf
first_model_id = e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba
first_plan_proposal_id = b5db44c042eaa656980f942430c2fee6eda6fcf6ec8c0a1af1142b723ec006e4
round_two_request_id = dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf
final_model_id = a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315
final_audit_id = 81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529
telemetry_id = bd65b6748493283b3d6f8b6b6345354dc44df01cdad92e3fc1d053f9f13cea03
result_id = 9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42
```

Canonical IDs are regression anchors, not substitutes for semantic
verification.  The independent verifier replays the complete V0-045 source,
typed base proposal/audit, both requests, all 13 transition outcomes, boundary
catalogues, both V3 models, both planners, both selected-plan audits, telemetry,
and final document equality.

## Required regressions

The frozen profile requires tests for:

1. no caller-selected row/state/cap parameters;
2. exact four-row first request and four transition calls;
3. exact three-state/nine-row boundary expansion with zero transition replay;
4. exactly 3 direct catalogue requests, 13 step-internal legality checks, and 0
   hidden base replays;
5. evaluation of the V0-045 coordinate programs on new states;
6. immutable base and V3 claim flags;
7. first coverage `11/9` and frontier movement from time zero to time one;
8. semantic rather than hash-only numerical tie breaking;
9. exact second request roles `3 risk / 9 value / 9 distinct`;
10. exact second bundle outcomes and no extra row access;
11. final coverage `20/0`, reward/risk/regret `1/0/0`, and no ground optimizer;
12. omission, role removal, and promotion-escalation attacks;
13. complete independent deterministic replay.

## Next construction gate

V0-047 closes the first real multi-step within-query refinement loop.  The next
construction gate is not another H2 fixture.  It must test whether an overlay or
coordinate learned from prior logical occurrences can be promoted or reused on
preregistered held-out queries without importing query-local leakage, and it
must begin comparing acquisition traces.  Only after those traces expose the
actual bottleneck should a Laplace-style heuristic operator or KG-OP-style
offline/online meta-prior be frozen as a sample-tax intervention.
