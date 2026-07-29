# Source-Frozen Certificate-Sensitive Greedy Acquisition

Status: proposed normative V0-071 target contract; implementation Gate not yet closed; current completed construction contract remains `1.34.0`
Target contract: `1.35.0` (not ratified as the current completed contract)
Schema: `1.0.0`
Profile: `source_frozen_certificate_sensitive_greedy_acquisition_v0`

## Purpose

V0-070 closed the registered K6 fixed-policy support hypothesis at
cardinality at most two:

```text
49 singleton overlays  -> 0 fixed-plan covers
1,176 pair overlays    -> 0 fixed-plan covers
```

That result does not justify enumerating triples. It shows that support
acquisition should be chosen as part of the planning-and-certification
loop, rather than by continuing a combinatorial model-only subset search.

V0-071 freezes a bounded SC-OLH-KG-style intervention:

```text
source-only records
  -> source-frozen proposal score
  -> current target failed-certificate sensitivity
  -> authorize one target row
  -> acquire fresh target-local evidence
  -> rebuild/replan/audit
  -> optionally repeat once from the new failed proof
  -> stop
```

The source prior proposes where to inspect. The unchanged target-local
confidence model and sound plan auditor remain the only statistical
certificate authority.

## Retrospective status

The current K6 occurrence is a retrospective development fixture. Its
observations, failures, policies, candidate registry, and V0-068--V0-070
results were inspected before V0-071 was frozen. Consequently:

```text
confirmatory_heldout_result = false
sample_efficiency_claimed = false
broad_transfer_claimed = false
```

Even if the registered K6 retrospective run later reduces target draws or
certifies a plan, it can establish only implementation feasibility,
authority separation, and a hypothesis for a future experiment. It cannot
establish a sample-efficiency or generalization result.

The production V0-071 algorithm must still be source/target isolated. The
retrospective label is a scientific claim boundary, not permission for the
source-prior builder to consume K6 target evidence.

The current checked-in implementation is only the authority-separation and
sequential-control slice. Its positive fixture uses a typed synthetic
materializer, and the real K6 adapter stops at a frozen authorization, cap, or
no-gain result. In particular:

```text
source_trial_semantic_replay_implemented = false
raw_target_materializer_implemented      = false
independent_bundle_verifier_implemented  = false
v0_071_gate_closed                       = false
```

`SourceLocalTrialV1` is presently an aggregation input, not proof that its
reported gain was recomputed from the referenced source model, audit, and raw
evidence. Synthetic tests may manufacture such inputs only when the resulting
campaign is explicitly marked mechanics-only. They cannot support the
source-only, transfer, sample-efficiency, or independent-verification claims
below. A later implementation must add semantic source replay and a real
post-authorization observer before this contract can close.

## Frozen source authority

The source archive, source contexts, row descriptors, fit procedure,
hyperparameters, feature normalization, tie-breaking rule, implementation
digest, and resulting prior identity must be frozen before any V0-071 target
arm is executed.

The source builder may consume only registered source-lane partial models,
failed audits, and raw-observation roll-forwards. It receives no exact source
or target truth. The registered context-free feature schema is:

```text
remaining_horizon
selected-row category
portable state coordinate document
portable action coordinate document
portable support coordinate document
support_count
novel_count
OTHER upper bound
risk-deficit reduction
regret-deficit reduction
predicted materialization draws
```

Context keys, content IDs, source/target role labels, and outcome identities
are stripped from the portable coordinate documents before fitting. Feature
schema and canonicalization are part of the prior identity.

Within each source context, eligible rows receive exact rational normalized
midranks in `[0,1]`, where larger means greater source gain per draw and exact
ties receive their average normalized position. The archive retains their
mean, worst value, and disagreement:

```text
q             = mean source midrank
worst_midrank = minimum source midrank
disagreement  = q - worst_midrank
```

The frozen disagreement threshold is `1/4`. No target observation may be used
to form these statistics.

It may not consume:

- a K6 target transition outcome or hidden support label;
- a K6 exact probability, exact policy, exact value, J0 result, or fallback
  result;
- a target certificate outcome produced after the arm begins;
- a post-acquisition row count, support identity, or stopping time;
- a V0-069/V0-070 success label synthesized from the target truth; or
- a target observation relabelled as source evidence.

Source fitting and target execution use disjoint evidence identities and
lanes. Outside the deliberately preregistered `OOD_ABSTENTION` control, a
stale, malformed, unsupported, or identity-mismatched prior disables the
prior-guided arm and yields a typed noncertificate. Inside that control, the
frozen feature-schema incompatibility must deterministically abstain to the
no-prior multiplier. Neither case authorizes a target certificate or an
infeasibility conclusion.

## Proposal-only prior

For every eligible target row `e`, the frozen prior emits only:

```text
(
  row_descriptor_id,
  source_context_count,
  source_mean_midrank,
  source_worst_midrank,
  source_disagreement,
  q
)
```

Here `q` is an exact rational in `[0,1]`. It is applicable only when:

```text
target feature schema and row role are source compatible
source_context_count >= 2
source_disagreement <= 1/4
target certificate gain > 0
the row's exact draw upper fits the remaining cap
```

Otherwise the prior abstains and the effective multiplier is exactly `1`.
When applicable, the source-consensus arm uses the bounded multiplier:

```text
m(q) = 1/2 + (3/2) q
```

The wrong control must use the same frozen prior, not a separately fitted or
caller-supplied archive, and applies:

```text
q_wrong = 1 - q
m_wrong = 1/2 + (3/2) q_wrong = 5/2 - m(q)
```

It reverses only the proposal ordering, never the target gain or eligibility.
The score may order eligible rows. It may not:

- alter target event counts;
- narrow an `OTHER`, reward, risk, or transition interval;
- change `delta`, the regret threshold, or the confidence allocation;
- remove a legal action, successor, counterexample, or fallback;
- certify support completeness, a quotient, a plan, feasibility, or
  infeasibility; or
- suppress the target-local audit after acquisition.

The prior does not enter any Bellman probability, reward, failure, value, or
regret expression. Removing every source score from the final certificate
must leave its numerical proof unchanged.

## Target-local certificate-sensitive selector

Each round starts from an immutable target model epoch and one independently
verified failed selected-plan certificate. The selector reconstructs the
eligible row registry from that epoch and failed proof. Caller-supplied
candidate lists are forbidden.

The target registry is a fresh content-addressed wrapper of the V0-070
`JointPairCandidateRegistry`; it does not reuse V0-070 pair evaluations as
authority. For each remaining row, the selector independently replaces
exactly that row's `OTHER` interval by zero on the current prefix model and
recomputes the frozen selected policy's exact-`Fraction` H1-to-H2 recurrence.
It does not combine rows.

Let `current_slack` and `new_slack(e)` be the registered aggregate
risk/regret certificate slack before and after that one-row counterfactual.
The target quantities are:

```text
gain(e) = max(0, new_slack(e) - current_slack)
base(e) = gain(e) / exact_preacquisition_draw_upper(e)
score(e) = base(e) * effective_source_multiplier(e)
```

This is a model-only acquisition score, not a certificate. It may use only
the current sound interval model and failed proof. It may not inspect a fresh
outcome, exact kernel row, J0 result, future epoch, or full-data transcript.
A prior, including the deliberately wrong control, cannot make a zero-gain
row positive.

The registered order is deterministic and content-addressed:

```text
(
  -score,
  -gain,
  exact_preacquisition_draw_upper,
  canonical_candidate_id
)
```

All arithmetic is exact rational arithmetic. All tuple fields and exact ties
are frozen before authorization. `NO_PRIOR` and an abstaining OOD prior use
multiplier exactly `1`. The wrong-prior control reverses `q` under its frozen
control rule but still multiplies the same positive target base and cannot
alter eligibility, caps, or proof arithmetic.

Rows with `gain = 0` are ineligible for authorization. If every remaining
row has zero gain, the arm closes `NO_POSITIVE_GAIN` without target access.

Sensitivity ranking is recomputed after round 1 only if the sound
post-acquisition audit still fails. Round 2 must use the new model epoch,
new selected plan, new failed proof, and a fresh candidate registry.
Round-1 ranks cannot be replayed as round-2 authority.

## Greedy two-round protocol

The only legal target sequence is:

```text
freeze arm context and initial failed certificate
  -> construct current candidate registry
  -> evaluate at most 64 one-row zero-OTHER sensitivity counterfactuals
  -> compute source/neutral proposal and exact scores
  -> freeze round-1 selection and exact work upper
  -> authorize exactly one row
  -> acquire only that row and any causally required child closure
  -> build an immutable next model epoch
  -> perform one complete robust replan and sound audit
  -> if certified, stop
  -> otherwise freeze the new failed certificate and registry
  -> recompute scores
  -> freeze round-2 selection and exact work upper
  -> authorize exactly one different row
  -> acquire only that row and any causally required child closure
  -> build one final immutable epoch
  -> perform one complete robust replan and sound audit
  -> stop
```

Each round is one greedy decision followed by real target evidence and a
complete replan. A one-row zero-`OTHER` counterfactual is legal only as the
registered pre-authorization sensitivity calculation; it is never accepted
as a target certificate. The runner does not evaluate row pairs, enumerate
subsets, or construct a cardinality-3 candidate.

The following paths are unreachable:

```text
pair counterfactual enumeration
k = 3 subset enumeration
joint pair authorization
third acquisition round
global 16,384 checkpoint
```

A successful two-round result means that two sequentially authorized rows,
with replanning between them, sufficed for that arm. It does not establish
minimal subset cardinality or identify a globally optimal acquisition
schedule.

## Frozen caps

The V0-071 retrospective profile freezes the following hard caps:

| Quantity | Hard cap |
|---|---:|
| eligible rows per round | 64 |
| acquisition rounds per arm | 2 |
| one-row zero-`OTHER` evaluations per round | 64 |
| one-row zero-`OTHER` evaluations over an arm | 128 |
| selected parent rows per round | 1 |
| selected parent rows over an arm | 2 |
| operational full robust replans per arm | 2 |
| newly acquired child action rows over an arm | 19 |
| incremental target observer draws per arm | 160,960 |
| maximum global checkpoint | 8,192 |
| pair evaluations | 0 |
| cardinality-3 evaluations | 0 |

The deterministic single-row materialization uppers are:

```text
remaining_horizon = 1 -> 80,480 draws
remaining_horizon = 2 -> 160,960 draws
```

The `160,960` bound is shared across both rounds, not reset per round. A
round-2 H2 candidate can therefore fail the remaining cap even when it ranks
first; the runner may not replace the cap result with post-hoc actual work.
Every selected row and newly required child row is charged once by physical
observation identity. Reusing one child row in both round closures preserves
union provenance but cannot charge or sample it twice.

Before each authorization, the runner must compute an exact
pre-materialization upper for all work still permitted in that arm and
verify it against the remaining shared caps. A cap failure closes that arm
as a typed noncertificate before any over-cap observation is requested.
Post-run actual work cannot be used to retroactively authorize the route.

## Four matched arms

The retrospective campaign freezes four target arms over the same K6 public
context, initial model epoch, QuerySpec, thresholds, candidate grammar,
confidence allocation, evidence interface, per-round caps, robust planner,
and sound auditor:

| Arm | Prior disposition | Target planning |
|---|---|---|
| `SOURCE_CONSENSUS_PRIOR` | use `1/2 + (3/2)q` only after the source-count, compatibility, disagreement, positive-gain, and cap guards pass | the registered certificate-sensitive greedy loop |
| `NO_PRIOR` | every multiplier is exactly `1` | the same greedy loop |
| `OOD_ABSTENTION` | an incompatible feature schema forces every multiplier to exactly `1`; effective schedule must equal `NO_PRIOR` | the same greedy loop |
| `WRONG_CONSENSUS_PRIOR` | apply `q -> 1-q` to the same frozen source prior as a negative control, without changing zero-gain or cap eligibility | the same greedy loop |

`OOD_ABSTAINED` is a prior disposition, not a terminal acquisition outcome.
The OOD arm must be byte-semantically equivalent to the no-prior scoring
schedule after removing arm-label provenance.

All four arms receive the same maximum information authority. Common random
numbers may pair observations only when two arms authorize the same row,
round, epoch semantics, and checkpoint. Shared physical replay must retain
separate counterfactual arm accounting and cannot leak one arm's stopping
decision into another.

The existing matched direct-ground K6 trace remains a separately identified
reference boundary. It is not silently counted as a fifth member of the
four-arm acquisition ablation, and it cannot be rewritten or resampled after
seeing V0-071 outcomes.

The campaign reports, per arm and prefix:

- target generative draws and exact-kernel native zeros;
- selected row identities and ranks;
- newly admitted catalogues and child rows;
- full replan and audit counts;
- plan-certificate, fallback, cap, and noncertificate outcomes;
- source-lane work separately from target-online work; and
- paired and physical-unique evidence counts without collapsing them.

No scalar or winner field is authoritative. A retrospective ordering or draw
difference is descriptive only.

## Confidence and certificate authority

V0-071 reuses the V0-068 target-local partial-support confidence contract.
Every acquired epoch retains an explicit `OTHER` event unless fresh
target-local evidence and an already registered sound authority justify a
narrower bound. Source evidence, source scores, sensitivity scores, and
synthetic/model-only rollouts contribute zero probability counts.

The confidence family, event partition, tail allocation, checkpoint, and
support-epoch identity are bound before the corresponding target stream is
opened. Discovery and validation streams are disjoint. A validation outcome
that was not in the epoch's frozen discovery set remains `OTHER` for that
epoch.

After materialization, the complete robust planner and sound auditor operate
on the resulting target model exactly as in the no-prior arm. A certificate
must be derivable after deleting the prior and sensitivity artifacts from
the numerical proof inputs. Exact evaluation may run only as a separately
charged evaluation control after the operational terminal artifact freezes;
it cannot promote a failed statistical result.

## Identity and immutable epochs

The preregistration binds:

- contract, schema, profile, and implementation digest;
- source archive, source split, descriptor, fit, and prior identities;
- retrospective target context and non-confirmatory status;
- initial K6 model epoch, selected plan, failed audit, QuerySpec, and
  thresholds;
- candidate-registry constructor and causal-cone semantics;
- certificate-sensitivity formula and deterministic tie-break;
- all four arm profiles and common-random-number rule;
- confidence, observer, cap, planner, auditor, and fallback profiles; and
- the next held-out Gate recipe, while omitting its future evidence.

Every round binds the parent model epoch, selected policy, failed-proof
frontier, candidate registry, scores, selected row, cap evidence,
authorization, stream domains, child-closure manifest, next model epoch,
replan, and audit.

Round 2 requires a new authorization and a strictly later model epoch.
Changing any bound identity invalidates all descendants. Retaining an
unaffected old row is permitted only by exact immutable row identity; a
promoted row receives a new epoch binding. No artifact may mutate the
V0-068 transaction-1 closure in place.

## Access order

Before a round authorization is frozen, the operational runner may read only:

- the frozen source prior or neutral-prior marker;
- the current target partial RAPM and immutable row records;
- the current failed selected-plan certificate and proof-dependency data;
- the public structural/action catalogue;
- the registered scoring, cap, confidence, and identity profiles; and
- metadata needed to compute exact pre-acquisition cardinality and work
  uppers.

Before authorization it must not:

- invoke the transition observer or exact kernel;
- open a discovery or validation stream;
- enumerate a hidden transition support;
- promote a row or materialize a child closure;
- run the next-epoch robust planner or auditor;
- read a later-round selection, full-data result, exact lift, or fallback;
- evaluate any pair or other multirow subset; or
- launch a worker attributable to target acquisition or planning.

Immediately before every `GreedySupportAuthorizationV1` freezes, the native
operational counters must show:

```text
observer calls                 = 0
promotion calls                = 0
full-replan calls              = 0
exact calls                    = 0
pair evaluations               = 0
cardinality-3 evaluations      = 0
```

The zeroes are scoped to work attributable to that not-yet-authorized round;
already closed round-1 work remains preserved when round 2 is considered.

Every access has a monotone sequence number and arm/round identity. An early
forbidden access closes the arm as `PROTOCOL_FAILURE` and invalidates the
retrospective campaign; discarding the access record cannot repair it.

## Artifacts

The implementation must emit content-addressed typed artifacts for:

1. `CertificateAcquisitionFeatureSchemaV1`;
2. `SourceRowAcquisitionTrialV1`;
3. `SourceCertificateArchiveV1`;
4. `SourceFrozenCertificatePriorV1`;
5. `TargetCertificateNeedEvidenceV1`;
6. `PriorApplicabilityV1`;
7. `CertificateSensitiveRankingV1`;
8. `GreedySupportAuthorizationV1`;
9. `GreedySupportRoundV1`;
10. `CertificateSensitiveAcquisitionRunV1`;
11. `MatchedPriorCampaignV1`;
12. `IndependentVerificationV1`; and
13. a separate evaluation-only exact-control artifact when executed.

The round and run artifacts must embed or reference the candidate-registry,
exact cap evidence, access log, raw-stream manifest, immutable overlay,
complete replan/audit, work vector, and terminal classification required to
replay that result.

All IDs use the project domain-tagged canonical-JSON SHA-256 convention.
Artifact role is part of the domain. The same bytes cannot serve as both a
source prior and target certificate, or as both an operational and
evaluation artifact.

## Terminal outcomes

Per-arm terminal outcomes are:

- `CERTIFIED_AFTER_ROUND_1`;
- `CERTIFIED_AFTER_ROUND_2`;
- `FAILED_AFTER_TWO_ROUNDS`;
- `DRAW_CAP_EXHAUSTED`;
- `NO_POSITIVE_GAIN`;
- `PROTOCOL_FAILURE`; and
- `INTEGRITY_FAILURE`.

Only the first two are plan certificates, and only if the unchanged
target-local sound audit verifies them. Cap exhaustion, absence of a
positive-gain row, and two-round exhaustion are noncertificates; none means
infeasible. `OOD_ABSTAINED` is recorded in `PriorApplicabilityV1` while the
arm continues with the exact no-prior schedule. A registered exact fallback
may close the query under its own authority, but its result and work remain
separate from the statistical acquisition certificate.

Those two real-certificate outcomes are not implemented in the current
mechanics slice. Its only positive endpoints are explicitly named
`SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_1/2` and carry
`synthetic_fixture_only=true`; they are control-flow results, not target
acquisition certificates.

## Independent verification

The standalone verifier must:

1. reconstruct the source prior from source-only records;
2. prove that no K6 target evidence entered source fitting or scoring;
3. reconstruct every round's registry, all one-row exact-`Fraction`
   recurrences, gains, draw uppers, multipliers, and total order;
4. verify the four arm identities, matched caps, and paired-prefix rules;
5. replay authorization and access order;
6. independently rebuild confidence bounds from raw target observations;
7. verify stream disjointness, epoch immutability, child-row
   deduplication, and exact work accounting;
8. semantically rebuild every materialized target model and replay the
   complete robust plan audit;
9. verify that removing source/sensitivity artifacts leaves each numerical
   certificate unchanged;
10. verify all terminal classifications and claim locks; and
11. reject any retrospective result presented as confirmatory.

The source-score reconstruction and target confidence reconstruction must not
call the production scoring helper as their sole semantic authority. Full
robust planner replay may remain same-implementation only if that limitation
is explicit in the verification artifact.

## Required attacks and acceptance tests

The implementation must test:

1. source archive and prior freeze before target-arm execution;
2. source/target context, evidence, stream, and lane disjointness;
3. target evidence or exact K6 truth injected into the source builder fails;
4. a prior score inserted into a probability or certificate expression
   fails;
5. stale model, plan, proof, threshold, registry, cap, or prior identities
   fail;
6. caller-added, missing, duplicate, or reordered candidates fail;
7. sensitivity forgery and tie-break substitution fail independent replay;
8. the no-prior arm cannot inherit source ordering, and OOD abstention is
   exactly schedule-equivalent to no-prior;
9. all four arms share the same information authority and caps;
10. observer, kernel, promotion, replan, or worker access before
    authorization fails;
11. round 2 cannot reuse round-1 frontier, score table, authorization, or
    stream;
12. two rows in one authorization, pair evaluation, `k=3`, round 3, and the
    global 16,384 checkpoint are unreachable;
13. fresh streams are mutually disjoint and disjoint from every parent
    discovery/validation stream;
14. physical row reuse across matched arms is prefix-identical and never
    double-counted as new evidence;
15. cap exhaustion occurs before the first over-cap observation;
16. exact lift or fallback cannot upgrade a failed operational statistical
    certificate;
17. serial and parallel schedules yield identical content IDs and results;
18. retrospective/non-confirmatory and all sample-efficiency claim locks
    remain false; and
19. full bundle replay detects deleted access, work, raw-observation, or
    role-manifest records.

Tests involving authorization, observation, overlay materialization, round-2
replanning, or a positive plan certificate are conditional obligations for
an execution that reaches those branches. A registered path that closes
before materialization must instead prove native-zero observer, promotion,
replan, exact, fallback, and later-round access as applicable. No dormant
branch may be claimed as empirically exercised merely because a synthetic
unit fixture covers its schema.

A synthetic positive control must exercise a round-1 failed audit followed by
a round-2 target-local certificate. It validates sequential control flow
only; it has no K6 or sample-efficiency claim authority.

## Claim boundary

V0-071 may establish only that a source-frozen proposal can be integrated
with a certificate-sensitive, target-evidence-gated, at-most-two-round
acquisition loop without changing the target-local sound certificate.

The retrospective K6 campaign cannot establish:

- confirmatory sample efficiency or offline-cost amortization;
- broad source-to-target transfer;
- an advantage over matched direct-ground planning;
- global optimality of the acquisition schedule;
- pair, triple, or arbitrary subset discovery;
- arbitrary-horizon or open-world support learning;
- independent-planner correctness;
- official scalar cost, break-even, workload economics, or counter
  completeness; or
- completion of the reusable hidden-world-model research objective.

The official locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

No numerical K6 outcome is frozen in this specification before the
implementation and independent verifier return. Any materialization,
certification, draw-reduction, or arm-order result is conditional until then.

## Next preregistered Gate

Before inspecting its observations, the next Gate must freeze a genuinely
unseen held-out structural occurrence or domain, a source/target split,
target query and thresholds, four-arm profiles, caps, confidence allocation,
raw-stream authority, exact fallback, direct-ground reference, and
confirmatory analysis rule.

The held-out Gate must run the frozen V0-071 operator without retuning its
source features, scores, disagreement guard, tie-breaks, caps, or stopping
rule. It must retain all four
`SOURCE_CONSENSUS_PRIOR`/`NO_PRIOR`/`OOD_ABSTENTION`/
`WRONG_CONSENSUS_PRIOR` arms, charge offline and online evidence separately,
and preserve every noncertificate in the denominator. Only that unseen
preregistered experiment may test a confirmatory sample-tax reduction claim.
