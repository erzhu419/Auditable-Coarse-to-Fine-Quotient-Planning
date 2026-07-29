# Fresh total-lift parallel confirmatory campaign

Status: pre-anchor construction; target access forbidden

Proposed contract: `1.40.0`

Profile: `v075_fresh_total_lift_parallel_confirmatory_campaign_v0`

## Purpose

V0-075 is a fresh statistical replication of the repaired acquisition and
planning pipeline. It is not a third V0-072 attempt and it may consume no
V0-072 target observation, model, policy, certificate, result, durable prefix,
cache, or retry authority.

The construction integrates three boundaries that V0-074 deliberately left
separate:

1. a semantically verified, compact production source-proposal archive;
2. a new held-out target authority and tape namespace; and
3. lossless occurrence-level process execution with private durable journals,
   content-addressed result transport, strict canonical merge, complete
   reconciliation, and endpoint replay.

The reusable-world-model objective remains primary. Parallelism changes only
physical execution time; it must not change evidence, exact arithmetic,
selected plans, certificates, counters, or scientific identities.

## Locked state

Until every production boundary, tracked authority artifact, attack test and
independent verifier below passes:

```text
registered_target_execution_allowed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
SAMPLE_EFFICIENCY_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
```

No target observer may be opened during this construction state.

## Historical exclusion

The exclusion registry binds both immutable V0-072 failures:

```text
attempt 1 record =
ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f

attempt 2 record =
cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e
```

Those records are provenance and regression inputs only. The following are
forbidden V0-075 scientific inputs:

- either V0-072 manifest, preregistration, anchor or execution plan;
- every V0-072 occurrence, pairing-group, stream and seed identity;
- every V0-072 target commitment, observation, model, epoch, plan, audit,
  certificate, journal, result and endpoint;
- K7 evidence from either failed attempt;
- any retired development identity;
- any result, certificate, target cache, resume or reuse transport; and
- either historical attempt budget.

V0-075 has one new attempt starting at ordinal one. A failed or partially
completed execution burns every opened target tape and cannot resume under
the same chain.

## Fresh target family and hidden-environment boundary

The public graph structures remain the registered seven-vertex K7, W7 and
K7-minus-two templates so this replication tests the repaired pipeline rather
than claiming a new structural-generalization result. Each is wrapped by a new
V0-075 replicate-context identity.

The three exact laws originally proposed during construction were imported by
a public module and therefore became observable. They are permanently
classified as `CONSTRUCTION_FIXTURE_ONLY`; their laws, environment IDs,
preregistration draft and namespace may be used for regression tests but may
not enter a V0-075 production occurrence, target tape, result or scientific
claim.

The production public dependency graph contains no law value, law ID,
environment reveal, reveal salt or observer capability. Before a final
preregistration is frozen, a separately held private environment is bound by:

```text
opaque_environment_commitment =
  SHA256(
    acfqp:v075-private-hidden-environment-reveal:v1
    || 0x00
    || secret_salt[at least 32 bytes]
    || 0x00
    || canonical_private_environment_reveal
  )
```

Only the salted opaque commitment enters public identities. The private
environment and salt remain outside the repository and outside every planner
or target worker capability. A trusted observer may consume them only after a
real final preregistration and remote-main anchor authorize the one fresh
attempt. A closure-time verifier must replay every observation and verify the
reveal against the frozen commitment. Merely wrapping arbitrary content IDs in
V0-075 types is nonauthorizing.

Public-key signatures establish provenance only relative to a signer
registry. A caller-created, self-signed registry is not a trust root and
cannot open an observer. The production registry ID and exact public-key bytes
must be recomputed from the tracked final preregistration and the first
qualifying remote-main anchor by an independent semantic verifier. Only that
verified binding can authorize the private observer; the law-free public
namespace remains nonauthorizing by itself.

The H=2 query, reward, risk/regret thresholds, five-arm order, confidence
allocation, draw schedules, caps and context-major denominator remain fixed
before target access. Reusing their numerical values does not reuse a target
identity or tape.

All public context, law, environment, row, support, pairing, stream,
observation, occurrence, model, policy, audit, certificate and result objects
use new V0-075 schemas and content domains.

## Tape derivation

The target tape namespace is anchor-derived:

```text
target_tape_namespace_id =
  H(
    acfqp:v075-target-tape-namespace:v1,
    final_preregistration_id,
    remote_main_anchor_id,
    target_family_generation_id,
    opaque_environment_commitment_id,
    observer_profile_id
  )
```

The common-random-number seed authority is fixed before support
materialization:

```text
raw_word_pairing_key_id =
  H(
    acfqp:v075-arm-free-raw-word-pairing-key:v2,
    target_tape_namespace_id,
    replicate_context_id,
    row_binding_id,
    observer_epoch_index,
    lane
  )
```

All five arms at a row/epoch share this key. Support evidence and its complete
typed lineage remain in the stream-pair/evidence identity but cannot change
the raw-word key; this prevents a caller from rerolling the tape by proposing
a different support set. The arm remains in its stream and evidence
identities, and all draws/work remain separately charged. Worker count, PID,
worker number, launch/completion order and journal location enter no seed or
logical ID.

## Production source proposal archive

V0-075 may reuse only verified source-side V0-068/V0-072 evidence. The
pre-target compiler reads the tracked canonical V0-072 source recipe and
independently verifies:

- the complete source archive ID;
- production archive verification;
- independent archive-transform attestation;
- all seven consensus records and their ordered commitment;
- the three `APPLIED` feature lookups;
- source family/training split/campaign identities;
- the source campaign counter identity and complete offline-work reference;
  and
- the absence of every target/result/certificate/cache field.

The compact archive is proposal-only and `may_certify=false`. Source
construction work remains offline work and is never reported as zero. Target
workers read only this compact verified archive, never the source runtime
object graph or a reconstruction callback.

The tracked recipe does not contain the 21 native counter values. Its exact
source runtime is commit
`63cc0f5f78f64b7845319d1c1a5856212e3b8097` (tree
`8c88ef5e2747267a309834d155136c40ba926b61`). A complete work
materialization therefore requires an exact replay in a clean detached
worktree at that snapshot. The current tree rejects the replay because its
component and test-command identities differ. The registered detached replay
and same-process V0-075 materialization have now completed. Their immutable
public result is:

```text
source archive =
4b25945b07d94ace9a6af8cbf979a9133e3780b6306c0bc3b7d8055b2c25bf92

source work materialization =
302b6dbf8683f1a335b6e80a223771d9bf2c23ba013ecc847b9d0eab3691641d

verified public source-work bundle =
fad189d1b352ed816205e733a66880b24c0e0100dfd534db90c3e5d8f4f4d8a8

source prior adapter =
41a204b8b0a0c28d7b5c10417644635860e741544eef63e20f93d60e5f522e4e

charged offline draws = 1,006,720
target accesses = 0
```

A counters document, compact recipe or caller-supplied values cannot
substitute for that replay.

The implemented replay controller avoids the historical recipe helper's lazy
confirmatory-manifest import. In one isolated process it runs only the
registered V0-068 source campaign and its archive/verifier/component chain,
then independently compares every frozen input, output ID, ordered Merkle
commitment and compact artifact before dynamically loading the digest-bound
current V0-075 materializer against the same exact historical object types.
Its complete ACFQP import allowlist is frozen and target, held-out,
confirmatory, unknown, dirty or untracked code is rejected. The eight tracked
source artifacts and their independent tracked-source replay authority now
constitute the sole source-prior input to the later target campaign.

## Authority order

The one-way authority chain is:

```text
historical exclusion registry
  + target family generation
  + verified source proposal archive
  + salted opaque private-environment commitment
    -> V0-075 confirmatory execution manifest
      -> V0-075 final preregistration
        -> first qualifying origin/main anchor
          -> target tape namespace
            -> immutable 3 x 5 occurrence plan
```

The manifest binds exact component blobs, dependency/interpreter locks,
production worker registry, counter/access schemas, V0-074 total-lift
mechanism, exact evaluator, reconciliation, endpoint verifier and exact test
command. It does not contain the final-preregistration ID. The final
preregistration binds the manifest in only the forward direction.

The anchor verifier reads committed Git objects and requires the first
qualifying `origin/main` commit whose parent and ancestry never contained the
same final-preregistration or target-family-generation sentinel. Claims,
attestations, old anchors and duck types are nonauthorizing.

## Process execution and transport

After the complete plan is frozen, each occurrence executes in one fresh spawn
process. Typed capability/sentinel objects are never pickled. Child input is
canonical bytes plus exact committed identities; the child reconstructs and
verifies its own authority before target access.

The parent creates each private journal before launch. Children append
content-addressed stage checkpoints and actual work before publishing a
result. Large result documents use a bounded content-addressed chunk manifest
with strict parsing; no opaque pickle is authoritative.

Scientific occurrence ordinals `0..14` map explicitly to transport ordinals
`1..15`. The parent retains every journal and verifies every result before
merging strictly by scientific ordinal. Sequential and parallel canonical
scientific outputs must be byte-identical on one read-only replay fixture;
this test may not generate a second scientific evidence set.

Any missing, duplicate, reordered, transplanted, malformed or failed child
prevents scientific merge and endpoint construction. Every launched journal,
known work item and typed unknown tail remains in the failure closure. PID is
diagnostic only and cannot prove process freshness or uniqueness.

## Exact lift and containment

The V0-074 total partial-support rule is mandatory:

```text
environment failure
  -> exact environment failure

modeled selected child
  -> require its bound selected decision
  -> integrate the complete fixed concretizer

exact child outside frozen modeled support
  -> ABSORBING_POLICY_ABORT_FAILURE
  -> failure 1
  -> continuation reward 0
```

Each exact row must have a disjoint and exhaustive environment-failure,
modeled-recurse and policy-abort partition. Total failure equals environment
failure plus policy-abort failure. Exact reward, failure and normalized regret
must be checked against the independently replayed operational envelope.

A malformed binding, missing modeled decision, omitted/duplicate branch or
forged envelope is `PROTOCOL_FAILURE`. A valid fresh statistical envelope that
does not contain the exact value/risk/regret is
`STATISTICAL_ENVELOPE_MISS_NONCERTIFICATE`, not a protocol error.

## Terminal and Gate semantics

All fifteen registered occurrences remain in every denominator. A complete
valid campaign may return:

```text
SAMPLE_EFFICIENCY_GATE_PASS
SAMPLE_EFFICIENCY_GATE_FAIL
```

`PASS` requires complete exact-valid plan-certificate coverage plus:

```text
SOURCE draws < NO_PRIOR draws
SOURCE draws <= MATCHED_DIRECT draws
```

in every registered context. A valid complete campaign missing that endpoint
returns scientific `FAIL`. Integrity/protocol failure invalidates the run and
is neither `PASS` nor scientific `FAIL`. A noncertificate occurrence prevents
positive certificate coverage but cannot be removed from the denominator.

Even a V0-075 sample-efficiency pass does not open official execution,
economics, counter-completeness, scalar/break-even or total-objective claims.

## Construction order

1. Implement the V0-075 authority and identity layer with zero target access.
2. Implement and independently verify the compact source proposal archive.
3. Extract and lock the profile-neutral exact H2 graph transition core.
4. Implement the new V0-075 observer and tape domains.
5. Implement strict canonical occurrence transport and private journals.
6. Add V0-075 adaptive/direct wrappers and total-lift terminal evaluation.
7. Add reconciliation, endpoint, attempt journal and complete-bundle verifier.
8. Pass synthetic, historical-exclusion, tamper and sequential/parallel replay
   tests.
9. Freeze tracked manifest/preregistration artifacts in the first qualifying
   commit, push `origin/main`, independently mint the anchor, and only then
   open the one fresh campaign attempt.
