# Transfer-Guided Adaptive Observation Acquisition

Status: **NONAUTHORIZING DRAFT prerequisite**; this document, its current
content IDs, and any commit containing only this draft are not a confirmatory
anchor and do not authorize a target tape to be opened

Proposed contract: `1.36.0`

Schema: `2.0.0`

Profile: `transfer_guided_adaptive_observation_acquisition_v1`

Confirmatory family generation:
`v072_anchor_clean_confirmatory_family_generation_1`

## Purpose and claim boundary

V0-068 established an observation-driven partial statistical RAPM, but its
registered graph arm consumed more target draws than matched direct planning.
V0-069 and V0-070 then ruled out registered one-row and two-row fixed-plan
support repairs for K6. V0-071 implemented the access-order and
certificate-sensitive-selection mechanics, but its source trials are not
semantically replayed, its positive path is synthetic, and its feature key
contains sample-specific interval values. Its Gate is therefore not run.

V0-072 tests a bounded sample-tax-reduction operator:

```text
verified source raw-prefix roll-forwards
  -> sample-independent portable acquisition features
  -> source-only feature consensus with typed abstention
  -> current target failed-proof sensitivity
  -> freeze one row authorization
  -> acquire only fresh target-local raw observations
  -> exact lazy robust replan and sound audit
  -> rebuild the frontier and optionally repeat once
```

The source prior may change only the order in which target rows are observed.
It never enters a transition interval, reward, risk, regret, Bellman backup,
certificate, or infeasibility proof.

Passing this Gate would support a narrow statement: on the preregistered
held-out finite H2 family, a source-frozen acquisition operator reduces online
target observations while preserving the same statistical certificate
authority. It would not establish the complete reusable hidden-world-model
objective, arbitrary-horizon learning, raw symbolization, broad domain
transfer, exact IID execution, or total-work economics.

The first possible confirmatory anchor is the first `origin/main` commit that
contains both:

1. a finalized, non-null confirmatory execution manifest; and
2. the final preregistration ID that content-binds that manifest,

and whose parent does not contain that final preregistration ID. The anchor
commit is verified after it exists; it is not an input to either of those
content IDs. This avoids a circular hash dependency. The current null-manifest
draft preregistration ID is deliberately nonauthorizing and will change when
the execution manifest is frozen.

The semantic anchor verifier must recompute the configured repository URL,
remote `origin`, branch/ref `main`, remote-head containment, commit ancestry,
commit tree and every registered manifest/specification blob. Its attestation
ID is a deterministic consequence of those verified facts; no caller may
supply an attestation ID, nonce, seed, alternate commit, or equivalent source
of randomness. A later change to any bound implementation or profile digest
requires a new Gate and preregistration rather than a rerun under the old
anchor.

Until that anchor has been semantically verified, every registered target
observer must fail closed and the following values remain frozen:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## Exact planning prerequisite

The seven-vertex controls make complete Cartesian deterministic-policy
enumeration impractical. V0-072 must first add an exact lazy H2 planner:

1. all arithmetic remains `Fraction`;
2. the existing robust joint-simplex Bellman semantics and deterministic
   policy selection order remain unchanged;
3. only root-relevant continuation decisions are searched;
4. irrelevant assignments receive their canonical lexicographically minimal
   legal action;
5. local and partial-node pruning is permitted only with a checkable
   componentwise reward/risk dominance witness and a policy-key-safe tie
   condition;
6. a completion rectangle may prune a subtree only when an already completed
   policy soundly dominates its best possible reward lower bound and best
   possible failure upper bound;
7. every completed candidate is re-evaluated through the unchanged robust
   row evaluator before selection;
8. the zero-`OTHER` counterfactual is solved independently through the same
   exact path; and
9. resource exhaustion returns `EXACT_DP_RESOURCE_EXHAUSTED`, never an
   approximate audit.

The confirmatory resource limits are:

```text
max_branch_nodes           = 10,000,000
max_complete_policies      =  1,000,000
max_root_bound_evaluations = 10,000,000
```

These are hard caps, not approximation parameters. Reaching any cap yields
`EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE`; it cannot silently select the
best policy seen so far or invoke an unregistered approximate planner.

For every existing W5, K6, and K6-minus model inside the legacy cap, the new
planner must reproduce the old audit's canonical bytes. An independent proof
replay must validate every omitted action extension and prune witness.

## Verified source archive

The source archive is built only from the independently verified V0-068
campaign. Its API must not accept a gain, score, rank, selected checkpoint, or
caller-supplied source/target split.

The mechanically registered adjacent raw-prefix trials are:

```text
W5:       2048 -> 4096
K6:       2048 -> 4096 -> 8192 -> 16384
K6-minus: 2048 -> 4096 -> 8192 -> 16384
```

This yields seven ordinary epoch-1 prefix extensions. A pair is included only
when its parent quotient base audit failed. The K6 promoted mixed-epoch
transaction is excluded as
`MIXED_EPOCH_PROMOTION_EXCLUDED_V2`; a final checkpoint with no registered
successor is excluded as `NO_SUCCESSOR_CHECKPOINT_EXCLUDED_V2`.

For each trial the archive independently verifies:

- identical row binding and support epoch;
- strict raw-prefix identity;
- parent validation identities as a true subset of successor identities;
- exact suffix observations and incremental accepted draws;
- byte-identical replay of the parent model and failed selected policy;
- replacement of exactly one row by the successor prefix;
- an independent exact H1-to-H2 fixed-policy recurrence; and
- all risk/regret/slack changes as derived properties.

It may not call the V0-071 score builder, exact ground planner, J0, fallback,
or an exact hidden-law row.

### Portable feature separation

Cross-context matching uses only:

```text
PortableAcquisitionCoreFeatureV2
```

It contains remaining-horizon role, selected-row category, registered
relational state/action/support coordinate semantics and values, and
destination-category presence. It contains no:

- context, state, action, row, outcome, model, audit, or evidence ID;
- vertex label or graph name;
- sample count, support count, confidence endpoint, or `OTHER` upper bound;
- reward/risk/regret value; or
- source/target role label.

All sample-dependent values live in:

```text
IdentityBoundLocalSnapshotV2
```

and never participate in the source-target join. Changing only a raw-prefix
checkpoint must change the local snapshot while leaving the portable core
feature unchanged.

Within each source context, features are ranked only among features actually
observed in that context. Exact ties receive normalized exact midranks.
Coverage need not be a rectangular context-by-feature table.

For each feature:

```text
q             = mean context midrank
worst_midrank = minimum context midrank
disagreement  = q - worst_midrank
```

The frozen disagreement threshold is `1/4`, and at least two source contexts
must support the feature. Each feature independently receives one disposition:

```text
APPLIED
UNSEEN
INSUFFICIENT_CONTEXTS
DEGENERATE_CONTEXT_RANKING
HIGH_DISAGREEMENT
NONPOSITIVE_SOURCE_GAIN
SCHEMA_MISMATCH
```

Every non-`APPLIED` feature has multiplier exactly one. It cannot disable or
alter an unrelated feature.

## Target selector and real materializer

### Complete cold round-0 model

Every arm starts cold. It may not import a target row, confidence authority,
support epoch, or model from V0-068 or from another arm. The identical
round-0 observation-acquisition schedule is:

```text
all legal root physical rows:
    discovery prefix 64
    then validation prefix 2048
then active nonterminal root discovery successors:
    enumerate complete public legal-action catalogues
then every legal child physical row in the H1 closure:
    discovery prefix 64
    then validation prefix 2048
build the complete H2 ground model
for adaptive arms only, also build the quotient model
audit exactly once at the complete round-0 checkpoint
```

There is no audit, plan-dependent stopping, source-prior consultation, or
intermediate peeking during this schedule. The registered row caps are 96,
48, and 96 for K7, W7, and K7-minus-two. Thus the conservative all-context
initial accepted-draw cap for one arm is:

```text
(96 + 48 + 96) * (64 + 2048) = 506880.
```

All accepted round-0 draws enter the online endpoint. The cap is not permission
to skip a reachable public row; the execution manifest must bind the exact
closure enumerator and row-catalogue authority. “Complete H2” here means
complete public structural state/action closure under the registered observed
support; it does not mean complete hidden-law support or exact transition
probabilities.

Each round starts from one immutable partial RAPM, its selected policy, and a
failed sound audit. Before authorization the selector may use only these
objects, the public legal-action catalogues, the portable source prior, and
registered cardinalities. It may not call the target observer, enumerate
outcomes, launch a materializer, or inspect a later model.

The direct and adaptive model-construction entry points are distinct.
`MATCHED_DIRECT_GROUND` may construct only the ground-direct model; it may not
invoke a convenience entry point that also computes quotient coordinates or
a concretizer. Adaptive arms may build both views over one physically charged
row inventory. Sharing physical evidence never licenses charging it twice.

The registered policy class preserves the project-wide deterministic-selector
decision. A ground comparator selects one ground action at each state/time,
and an adaptive quotient selector selects one semantic abstract action at each
abstract state/time. The latter is realized through the model-build-time
frozen concretizer. For every reachable ground state and selected semantic
action, the operational artifact must retain:

```text
semantic action ID
distinct inverse ground-action IDs and action triples
exact uniform Fraction weights over those distinct actions
concretizer/model identity
```

The concretizer mixture is an action-realization/environment mechanism, not
query-time policy randomization. Exact evaluation must integrate this mixture
at every H2 state; it may not choose one convenient support action. The
deterministic ground optimum remains the regret comparator. The matched-direct
arm is the singleton-concretizer special case. Duplicate actions,
group-element multiplicity weights, nonuniform replacement weights, or a
semantic/action/model transplant are protocol failures.

The observation authority retains one row-bound `OTHER` event and provenance
identity per row. If the legacy robust planner is used, those identities may
be mapped to its single global `ABSORBING_POLICY_ABORT_FAILURE` destination
only through a content-addressed collapse proof. That proof must preserve
every non-`OTHER` mass, interval and reward exactly, map exactly one `OTHER`
mass per source row, and independently establish that all mapped destinations
have identical failure-one/continuation-lower-zero semantics. A bare custom
multi-`OTHER` container is not a planner input.

For each current failed-frontier row, a one-row zero-`OTHER`
counterfactual supplies a target-local positive sensitivity:

```text
gain(e) = max(0, counterfactual_slack(e) - current_slack)
base(e) = gain(e) / exact_preexecution_draw_upper(e)
```

The arm-specific score is:

```text
SOURCE:   base(e) * (1/2 + 3*q(e)/2)  when APPLIED, else base(e)
NO_PRIOR: base(e)
WRONG:    base(e) * (1/2 + 3*(1-q(e))/2) when APPLIED, else base(e)
OOD:      base(e)
```

The wrong arm reverses the same archive; it may not fit a second archive.
The OOD arm's arm-free schedule core and ranks must be byte-identical to
no-prior after typed abstention; their arm-bound IDs remain deliberately
different. Zero-gain rows remain ineligible under every arm.

The deterministic order is:

```text
(-score, -gain, exact_draw_upper, canonical_candidate_id)
```

After the authorization artifact is frozen, the real materializer:

1. promotes the authorized row using fresh discovery/validation stream
   domains, adding exactly 2048 validation draws and never rerunning parent
   discovery;
2. acquires only newly reachable child catalogue/action rows;
3. builds and verifies the new direct and quotient partial models;
4. runs the exact lazy robust planner;
5. emits a complete sound audit; and
6. records the actual accepted draws and all raw observation identities.

No caller may supply an audit status, a required-row set whose membership
decides certification, a selected policy, or a synthetic model ID.
Certification is derived only from the rebuilt planner-compatible model, the
exact lazy solve result, and the independently replayed proof. Before those
objects exist, materialization may emit only a typed pending-rebuild
noncertificate handoff.

The new-child cardinality is frozen before authorization. It is derived from
the promoted parent support union of all current validation
`novel_descriptors`, requires both positive target-local gain and a nonempty
novel set, and expands through complete public legal-action catalogues. It is
the content-addressed canonical list of distinct H1 physical-state/action rows
that are absent from the current model. A hidden-law enumeration, a
caller-supplied count, or a post-materialization count is invalid.

For round \(r\), let \(n_r\) be the number of those newly authorized child
action rows. Each receives a fresh discovery prefix of 64 and a fresh
validation prefix of 8192. The exact preexecution upper is:

```text
D_r = 2048 + n_r * (64 + 8192)
    = 2048 + 8256*n_r.
```

Reservation, exact preexecution upper, and actual work are distinct fields.
Across two rounds, the union of distinct newly acquired child action rows is
at most 19. Rows cannot be reset, double-charged, or borrowed between arms.
The cumulative cap after \(R\in\{1,2\}\) rounds is:

```text
C_R = 2048*R
      + 8256*|union(new child rows authorized through round R)|
    <= 160960,

|union(new child rows)| <= 19.
```

If round 1 still fails, round 2 must rebuild its candidate registry from the
new model, new selected policy, new failed proof, and new frontier. Reusing
the round-1 registry, ranks, support epoch, or stream domains is a protocol
failure. Round 2 is a fresh materialization, not a continuation carrying stale
proof identities.

## Preregistered held-out structural family

This draft is an implementation prerequisite only. It is not the
preregistration anchor. Before the semantically verified anchor defined at the
top of this document exists:

```text
registered_target_tapes_opened       = false
registered_target_observations       = 0
registered_target_accepted_draws     = 0
registered_target_evaluation_results = 0
```

The registered observer, replay API, and evaluation runner must all reject the
current null-manifest preregistration. Development tests may draw only through
a domain-separated synthetic-control context/law/API with no shared
confirmatory context, law, stream, observation, evidence, model, work, or
endpoint ID. Such work is labeled
`DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE` and cannot be
promoted into the confirmatory family.

Development-control keys must describe the frozen synthetic environment, not
the expected success round or terminal result. A test profile named from a
desired certificate outcome is not an outcome-blind execution authority.

All contexts use:

```text
root ranks = (1,1,2,0,0,0,0)
H = 2
delta = 1/20
rank cap = 6
reward ceiling = 3/64
normalized regret tolerance = 1/20
```

The registered graphs are:

| Context key | Geometry | Frozen topology ID |
|---|---|---|
| `heldout_graph_k7_confirmatory_v1` | complete graph on seven vertices | `c4ad4934340b4fe0854a7f85d778a6ebec9a52337da6577426d5585a155a7b21` |
| `heldout_graph_w7_confirmatory_v1` | six-cycle plus one universal hub | `1e8b9ee52ed801d75d3ad6e5038b3abf6e4e6e639312b4eb57b45d4bd060a19e` |
| `heldout_graph_k7_minus_two_confirmatory_v1` | K7 without `(4,6)` and `(5,6)` | `4504dbc17e530161ca185d58efeae68e571a58190dca579f987a57700267a428` |

Their maximum initial physical-row counts are respectively `96`, `48`, and
`96`. A physical row may have its initial epoch and at most two promotion
epochs, hence at most three confidence epochs. The execution protocol permits
at most one promotion authority in each of two rounds per context. Therefore
the preregistered per-arm authority cap remains the conservative schedule
bound:

```text
sum_context(initial unique rows <= row cap
            + promotion authorities <= 2)
<= 2*(96 + 48 + 96)
= 480 <= 512.
```

The family-generation and content-domain separation are:

```text
confirmatory family generation
    v072_anchor_clean_confirmatory_family_generation_1

public context domain
    acfqp:v072-heldout-public-context:v2
hidden law domain
    acfqp:v072-hidden-spawn-law:v2
environment manifest domain
    acfqp:v072-heldout-environment-manifest:v2
preregistration domain
    acfqp:v072-adaptive-acquisition-preregistration:v2
```

Every ID is `SHA256(domain-tag || 0x00 || canonical-json)`. Domains and the
family generation may not be substituted or reused cross-role.

The hidden spawn laws are unchanged and frozen before target execution in a
separate content-addressed environment manifest:

| Context | Environment-only rank law |
|---|---|
| K7 | `(1,197/200), (2,1/100), (3,1/200)` |
| W7 | `(1,99/100), (2,1/100)` |
| K7-minus-two | `(1,49/50), (2,3/200), (3,1/200)` |

The public context documents do not serialize these laws. The current clean
draft identities are:

```text
K7 public context       5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a
W7 public context       48a6f36af9ef5ff1ba9920d783d2435cedd9458c8383f48ccf40412ff55f0dda
K7-minus-two context    52363b3d6e6508e6734418103be98da18cd7aafe6657d24de16c2547c630ba7a
K7 hidden law           434f67074a8be498fd8cc532fe780f4227f6f8233bc90a62fab6e8cb595a5f71
W7 hidden law           801683343ef1973337e534f2d36ac6c8493717d240ef05677abd3a2abb72559c
K7-minus-two law        b0803f306f3d5ac79abd6e87fc713caedcceae3411f3172f88d103cb7b540347
environment manifest    f1b158319b5c059786829fc6b5ca4cda60e0b49e9e173a3c70daa4c8a04100da
draft preregistration   7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2
```

The draft preregistration above has
`confirmatory_execution_manifest_id = null`,
`confirmatory_profile_finalized = false`,
`anchor_commit_id = null`, and `target_execution_allowed = false`. It is not
an execution credential. The context, law, and environment IDs are the current
clean-generation values; the final preregistration ID must change when the
non-null execution manifest is frozen.

It supersedes two nonauthorizing drafts:

- `8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29`,
  whose two-epoch field could not represent an initial confidence epoch plus
  both permitted promotions; and
- `e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4`,
  whose terminal registry omitted the matched-direct checkpoint-cap
  noncertificate.

None authorizes target access.

The following eight prior development identities are permanently retired:

```text
0f8061ac58630cced8f01bce01191ab0d02aff5cf64b4cc106f579ad53d02312
1f240bb0305012a9144b4039d9f2f9b13a0be18b23c0cc7c70dc2909f09ccc29
a5775190ea336702a7f4e1f06bdd93ec0bd0609f03f69ad7a72c2262e6645976
ad7dca2b9db96d98d0c8bd6608315264995d3dcb0b6457a4b2b5d073db494ab0
571d4cb2a7b2b55fc85012b2b417f397b57226df7ae4b00c47d0bb5f35639441
e8cb7a070c7d6bbdb93683367a8026f422a8ef397877b87d07a3c6c549820cde
f0d8db6165c3d0a125945b43b4b0d8e221b13ea7870021e96f18b91e218ed00e
495927b2c72c847086008b2b2c6e8f65ea4a2b5a45ce409c8c7ec3d4be915500
```

They have disposition
`DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE`. They cannot be
accepted as a current context, hidden law, environment, preregistration,
stream-lineage parent, observation, model, or endpoint identity.

### Confirmatory execution manifest and anchor

Before the final preregistration can be produced, one non-null
content-addressed execution manifest must freeze an ordered list of component
records. Every record contains:

```text
component_role
repository_relative_path
sha256_file_bytes
schema_or_protocol_id
content_id_or_typed_not_applicable
```

The ordered component-role list is:

```text
normative specification
preregistration authority
verified source-archive builder and independent verifier
portable-feature consensus authority
target preauthorization selector and selector verifier
registered observer, raw-commitment replay, and support-epoch-chain verifier
partial-support confidence authority
public legal-action catalogue and novel-child cardinality authority
cold H2 closure and relational/ground model builders
incremental materializer and fresh round-2 authority
exact lazy H2 planner and independent proof verifier
matched direct-ground baseline
independent exact ground evaluator
five-arm confirmatory campaign runner
standalone complete-bundle and endpoint verifier
counter/access-log/accepted-draw reconciliation authority
confirmatory tests and the exact test-command manifest
runtime/dependency lock and interpreter build identity
```

The manifest also binds the clean generation, all three public-context IDs,
all three law IDs, the environment-manifest ID, source-archive ID and
verification profile, arm order, terminal-code list, confidence profile,
checkpoint/cap profile, repository URL, target branch `main`, component tree
digest, and deterministic command/environment settings. Every digest and
applicable ID must be non-null. The development synthetic-control module and
all retired IDs are explicitly excluded from confirmatory execution.

The final preregistration content-binds this execution-manifest ID. The
execution manifest does not embed the final preregistration ID; the later
anchor attestation binds the pair to the first qualifying `origin/main`
commit and verifies that its parent lacks the final preregistration ID. A
commit containing only this draft, a null manifest, missing component
digests, or the draft preregistration ID is nonauthorizing.

No law, seed domain, threshold, graph, root, arm, schedule, cap, checkpoint,
terminal rule, endpoint, or component digest may be rerolled after the anchor
or after observing any confirmatory result.

## Matched arms and stopping

Every held-out context runs:

```text
SOURCE_CONSENSUS_PRIOR
NO_PRIOR
WRONG_CONSENSUS_PRIOR
OOD_ABSTENTION
MATCHED_DIRECT_GROUND
```

This is exactly `3 contexts * 5 arms = 15` logical occurrences, ordered
context-major and then by the arm order above. There is no occurrence
replacement, campaign early stopping, or removal from a denominator.

All arms share the same cold schedule, caps, confidence allocation, and
deterministic raw-word authority. Common random numbers pair a word only when
the following complete arm-free key is identical:

```text
context
physical row
arm-free support set and support lineage
round
epoch
lane
checkpoint
random-word index
```

For registered execution the raw-word seed root is exactly:

```text
SHA256(
  registered-lane-seed-domain || 0x00 ||
  canonical-json{
    preregistration_id,
    environment_manifest_id,
    anchor_commit_sha,
    context_id,
    physical_row_binding_id,
    arm_free_support_semantics_id,
    round_index,
    epoch_semantics,
    lane,
    checkpoint
  }
)
```

SplitMix64 uses that root as a counter stream; outcome mapping uses the frozen
unbiased-rejection rule. The seed excludes arm, attestation ID, run/process
identity, wall-clock time and caller data. Arm enters the stream/evidence/work
identity layer, not the paired raw-word entropy. The exact-evaluation API is a
separate evaluation lane and additionally requires the frozen operational
terminal reference for the occurrence being evaluated.

The arm-bound stream ID, observation ID, evidence ID, support/model ID, and
work ID remain disjoint even for paired words. Pairing does not deduplicate
accepted draws, statistical evidence, confidence authorities, or charged
work. No cross-arm independence is claimed or used.

The direct arm uses the same observer and confidence machinery but builds a
ground-state model with no quotient sharing. After the same cold H2 closure,
it extends every fixed epoch-1 validation prefix chronologically at exactly:

```text
2048, 4096, 8192, 16384
```

At each complete checkpoint it performs a complete ground replan and audit
and stops at the first sound certificate. It has no source prior, quotient
sharing, local row promotion, or exact-law access. It may not inspect a
fallback result.

The adaptive arms audit only at:

```text
ROUND0_COMPLETE_VALIDATION_2048
ROUND1_COMPLETE_MATERIALIZATION
ROUND2_COMPLETE_FRESH_MATERIALIZATION
```

Intermediate peeking, an audit between discovery and validation, or a third
adaptive round is a protocol failure.

An arm stops only at:

```text
CONDITIONAL_PLAN_CERTIFICATE
EXACT_FEASIBLE_FALLBACK
EXACT_INFEASIBILITY_CERTIFICATE
NO_POSITIVE_GAIN_NONCERTIFICATE
INCREMENTAL_CAP_EXHAUSTED_NONCERTIFICATE
DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE
EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE
TWO_ROUND_CAP_EXHAUSTED_NONCERTIFICATE
PROTOCOL_FAILURE
INTEGRITY_FAILURE
```

Both an adaptive quotient plan certificate and a matched-direct plan
certificate use `CONDITIONAL_PLAN_CERTIFICATE`. Matched direct is a comparator,
not a fallback, so it may never mint `EXACT_FEASIBLE_FALLBACK`. That code is
reserved for a separately invoked exact fallback after a registered
acquisition stopping path. Certified occurrences alone carry an operational
selected-policy terminal and independent exact-evaluation result;
noncertificates carry an internally derived typed not-applicable evaluation
binding while remaining in the 15-occurrence denominator.

`DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE` applies only when the matched
direct arm reaches its complete 16,384-draw checkpoint without a sound
certificate. It is not an incremental/two-round exhaustion and is never an
infeasibility certificate.

Fallback may run only after a registered acquisition stopping path. A
fallback plan or infeasibility proof can close the occurrence, but it is not a
successful acquisition endpoint. `NO_POSITIVE_GAIN`, incremental-cap,
exact-DP-resource, and two-round-cap exhaustion are noncertificates, never
infeasibility. Protocol or integrity failure invalidates the confirmatory run.

### Confidence allocation

Each physical row permits one initial confidence epoch and at most two
promotion epochs. This per-row cap of three is distinct from the total
authority cap: there are at most two promotion authorities per context because
there are only two adaptive rounds. For one arm the conservative registered
bound is:

```text
sum_context(initial unique rows <= row cap
            + promotion authorities <= 2)
<= 2*(96 + 48 + 96)
= 480
```

arm-bound row-epoch authorities are possible. Across all five arms:

```text
5*480 = 2400 <= 5*512.
```

The row-epoch error budget is:

```text
beta = 1/300000.
```

Within one row epoch, event alpha is
`beta/(support_cardinality + 1)` with at most 16 registered support
descriptors; the extra event is `OTHER`. Across the campaign, a finite union
bound gives:

```text
joint tail <= 2400/300000 = 1/125
joint confidence >= 124/125.
```

This proof requires no independence between rows, epochs, contexts, or arms.

### Randomness claim boundary

The implementation uses a reproducible SplitMix64 raw-word tape under
domain-separated deterministic identities. This is not a formal exact-IID
implementation: a finite deterministic pseudorandom tape is not itself an IID
probability space, and word-to-outcome mapping is not promoted into such a
claim. Statistical coverage is therefore stated conditional on the idealized
IID transition model. V0-072 does not claim a formal exact-IID implementation
or a plan certificate whose IID premise is proved by SplitMix64.

## Acceptance tests and scientific endpoints

Correctness prerequisites:

1. the anchor is the first qualifying `origin/main` commit, its parent lacks
   the final preregistration ID, and zero registered target observations
   precede it;
2. every execution-manifest component digest and semantic ID verifies;
3. source and target physical evidence identity sets are disjoint;
4. source archive gains and midranks replay independently;
5. no source-derived quantity appears in a numerical certificate;
6. all claimed plan certificates pass independent exact ground evaluation;
7. wrong and OOD controls issue zero false certificates;
8. OOD and no-prior arm-free schedule cores and ranks are byte-identical
   after typed abstention while their arm-bound IDs remain disjoint;
9. all preauthorization target-observer and materialization counters are zero;
10. round 2 uses a different frontier, authorization, epoch, registry, and
    fresh stream lineage;
11. every arm-bound accepted draw reconciles to one unique raw commitment,
    including paired common-random-number words as separately charged draws;
12. all cold, failed, and incremental acquisition work is retained;
13. all 15 occurrences close under one registered terminal code and remain in
    every denominator; and
14. legacy and exact-lazy planner audit bytes agree on all in-cap controls.

Only after those prerequisites pass are sample endpoints read:

Primary operator endpoint:

```text
sum online accepted target draws(SOURCE)
  < sum online accepted target draws(NO_PRIOR)
```

Matched sample-tax endpoint:

```text
sum online accepted target draws(SOURCE)
  <= sum online accepted target draws(MATCHED_DIRECT_GROUND)
```

Both comparisons require SOURCE certificate coverage and exact-evaluation
validity to be noninferior to the comparator in every context. SOURCE must
produce an independently exact-evaluation-valid
`CONDITIONAL_PLAN_CERTIFICATE` in all three registered contexts. Fallback
closure does not satisfy this positive-coverage requirement. A reduction
obtained by earlier fallback or noncertificate closure is a failure, not a
win.

Online accepted target draws include the complete cold model, every failed
acquisition, and every incremental acquisition. Common-random-number pairing
does not discount this count. The archive's historical source cost is the
cardinality of the union of independently verified source raw-observation IDs
and is reported separately as offline cost. V0-072 may report online
target-draw reduction and a homogeneous sample-only amortization curve, but it
may not call that curve official economic break-even or combine draws with
compute, bytes, or launches.

The Gate passes only if all mandatory contexts and arms close without
protocol/integrity failure, all correctness prerequisites hold, the primary
operator endpoint holds strictly, and the matched sample-tax endpoint holds.
Otherwise `SAMPLE_EFFICIENCY_GATE` remains `NOT_RUN` or closes failed with its
typed reason.

## Remaining path to the total objective

Even a passing V0-072 is still a finite H2, already-symbolized, registered
family result. The next construction stages must extend the same loop to:

- a genuinely different observation/domain adapter under a shared portable
  acquisition feature semantics;
- horizons beyond two with incremental proof dependencies;
- persistent partial/statistical dynamics learned without complete target
  closure;
- source-prior admission from held-out multi-domain episodes rather than one
  graph family; and
- workload-level reuse and total operational economics.
