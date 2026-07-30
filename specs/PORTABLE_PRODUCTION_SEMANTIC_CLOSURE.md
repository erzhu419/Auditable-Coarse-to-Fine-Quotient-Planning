# Portable Production Semantic Closure

**Status:** normative construction contract; production and target access locked  
**Ledger:** V0-076  
**Implemented revisions:** `1.60.0`–`1.77.0`
**Current completed public cut:** M0 + B1 + M1A + M1B ROOT + M2 root/public lineage/lifecycle/live-row-source/dynamic-child proposal projection

## Objective

This contract prevents a portable occurrence bundle from acquiring semantic
authority merely because its bytes, hashes and dependency topology verify.
Every role used by a production consumer must be reconstructed through its
producer semantics, bound to an iterative dependency proof and independently
classified as complete, unresolved or absent.

This work serves the project objective:

> Build a reusable abstract world model, plan primarily inside it, and recover
> only the ground distinctions needed when the current contingent plan cannot
> be certified.

It is not a separate endpoint and does not authorize a held-out campaign.

## Three non-equivalent claims

```text
portable byte/topology validity
!= producer-semantic reconstruction
!= private-law replay or production authorization
```

A verifier must never infer a stronger claim from a weaker one.

## Current role cuts

### M0 public graph

Inputs are the raw portable bundle, raw public-context closure and repository
root. The authority reconstructs eleven public roles for the registered
`NO_PRIOR` arm and exposes a bundle-bound, in-memory-only typed graph.

M0 does not establish source authority, code provenance, private replay,
all-arm coverage, the full portable semantic registry or production.

### B1 observer-open binding

B1 reconstructs the observer-open binding from raw public authorities and
binds it to the exact M0 namespace, authorization, reveal attestation and
anchor. It opens no observer and accepts no private input.

### M1A signed-batch graph

M1A reconstructs:

1. `OBSERVER_OPEN_BINDING`;
2. `SIGNED_BATCH_REQUEST`;
3. `SIGNED_BATCH_OUTCOME`;
4. `SIGNED_OBSERVATION_BATCH`;
5. `SIGNED_BATCH_JOURNAL_ENTRY`;
6. `SIGNED_BATCH_JOURNAL_CLOSURE`.

It checks the public projection of
`SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` but must classify that seventh
role as:

```text
UNRESOLVED_PRIVATE_REPLAY_CLAIM
```

Distinct outcome records are keyed by their nested canonical bytes. An
`outcome_id` may repeat across batches and is not a globally unique record key.

## M1A identity and dependency requirements

Each bound record commits:

- record ID and index;
- role;
- producer semantic ID;
- sorted direct dependency IDs;
- canonical artifact SHA-256;
- canonical artifact byte count.

The dependency proof is an iterative topological direct-edge DAG. A node is
jointly resolved only when it has a registered public resolver and every
direct dependency node is jointly resolved. Attestations store only direct
dependencies, resolved direct dependencies and the unresolved direct
frontier. They do not materialize transitive closures.

Mandatory regression:

```text
4096 chained records
-> no recursion
-> O(V+E) construction and rehash
```

Graph, DAG, attestation and aggregate IDs must be revalidated before every
serialized output. Mutation of a record index, semantic ID, dependency,
canonical bytes, attestation or DAG node must invalidate the old identity.

## New private-replay attestation

Contract `1.68.0` defines a new artifact; it does not modify or upgrade the
old closure-verification role.

The trusted construction freeze:

1. accepts the exact closure, binding and used stream graph;
2. accepts the private salt/environment and observer signer;
3. directly invokes the exact private verifier inside the same call;
4. checks the resulting verification against the public projection;
5. signs only after that call succeeds;
6. serializes no private salt, environment, law, tape or private key.

It has no caller-supplied `verification` parameter. Wrong private material or
private-verifier failure must produce no signature.

The public verifier proves only:

```text
private_replay_claim_observer_signed = true
private_replay_independently_recomputed = false
public_verifier_proves_private_replay_execution_order = false
execution_order_is_trusted_api_discipline_not_cryptographic_proof = true
```

A caller that holds the generic signer can directly sign a public claim.
Therefore contract `1.68.0` is construction-only.

## Required signer-owning production successor

Production must use a sealed service that owns:

- private salt/environment or their child-only secret handles;
- the non-exportable observer signer;
- observer session open;
- all observation and batch journal state;
- closure;
- exact private replay;
- final attestation signing.

The caller may send only preregistered public intent bytes and receive capped
canonical public frames. It may not send a signer, verification object,
private material, old closure or bare B3 artifact.

The successor portable bundle uses a new non-retroactive role:

```text
SEALED_OBSERVER_PRIVATE_REPLAY_ATTESTATION
```

Old bundles and old closure-verification records remain unchanged and
unresolved.

## Contract 1.69 Stage A boundary

Stage A now establishes the sealed-source child, separate sealed private
descriptor, child-only production-signer load, strict public request surface,
nonce handling, typed failure closure and native journal/work accounting.
It intentionally emits:

```text
SESSION_OWNERSHIP_NOT_YET_COMPLETE
observer_session_owned_from_open = false
private_replay_calls = 0
b3_sign_calls = 0
```

This artifact is a noncertificate transport precursor. It is not the required
signer-owning lifecycle and cannot upgrade an old closure or B3.

## M1B signed control cut

M1B reconstructs the signed control structure. It must distinguish:

- `FULL_PUBLIC`;
- `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED`;
- `NOT_PRESENT_IN_OCCURRENCE`.

Root semantic authority may close through M0/M1A. Child and promotion
authority cannot close until their dynamic-closure/promotion-decision
semantic authorities are reconstructed. A role absent from a root-only
occurrence is not complete and is not an inferred native zero.

Contract `1.70.0` implements this cut for all 16 registered control roles.
Every ROOT binding is replayed against the exact ordered M0 row, stage, lane,
observer epoch and draw interval. The root-only K7 construction therefore has
full public generic/ROOT roles and explicit absent CHILD/PROMOTION roles.
Present dynamic roles remain structural-only; M1A private verification is not
consumed.

## Contract 1.71 same-child lifecycle control

One fresh sealed-source child now owns signer load, reveal, observer open,
the fixed registered root batches, close, private replay and B3 signing for
the synthetic root-only K7 positive control. The request has no signer,
private-verification, old-closure, old-B3, observation-result or caller-session
input channel. Exact fixture and arm/start/count/cap bindings, typed failure
prefixes and distinct complete/failure journal kinds are publicly replayed.

This is a construction noncertificate. Its B3 is observer-signed, but the
public verifier neither reruns the private law nor provides cryptographic
process/order provenance. Contract 1.71 adds no portable role and does not
upgrade the historical M1A private-verification record.

## Contracts 1.72–1.73 M2 public cuts

Contract 1.72 reconstructs `OCCURRENCE_IDENTITY` and `ROOT_EXECUTION` as
`FULL_PUBLIC`. It binds exact M0 occurrence/schedule/intents to M1B
receipts, support freezes, semantic-authority references, resulting head and
open prefix, while independently rederiving the M1B record/dependency spine.

Contract 1.73 reconstructs `BATCH_PUBLIC_VERIFICATION` and
`BATCH_SEQUENCE_VERIFICATION` as `FULL_PUBLIC`. It also rebuilds the exact
public `CONSTRUCTION_LINEAGE` payload, including occurrence, namespace,
context and arm relationships. That lineage role remains
`STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` because
`SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` is still its unresolved private
frontier. Neither cut calls or consumes the private verifier.

## Contract 1.74 M2 construction-lifecycle cut

Contract 1.74 starts from hardened 1.73 raw replay. It closes
`LIFECYCLE_SUPPORT_EVIDENCE`, `LIFECYCLE_SUPPORT_FREEZE` and
`LIFECYCLE_EVENT` as `FULL_PUBLIC`, and verifies the complete public
construction-lifecycle byte projection.

Lifecycle support evidence also receives content-addressed authority-local
source edges. Portable-declared, authority-local semantic and effective
dependency views remain separate. `CONSTRUCTION_LIFECYCLE` and
`CONSTRUCTION_LIFECYCLE_VERIFICATION` remain structural-only on the exact
M1A private closure-verification frontier. This cut performs no private replay
and consumes no B3 claim.

## Contract 1.75 M2 live-epoch cut

Contract 1.75 starts from hardened 1.74 raw replay. It reconstructs live
epochs only through the producer's portable non-operational path:

```text
replay_parent = false
register_operational = false
portable_prefix_replay = true
```

Every epoch is rebuilt from the current occurrence, route, open prefix,
controlled appends, support freezes and independently reconstructed parent.
Its complete canonical bytes and ID must match the portable record. Embedded
row sources are unioned by distinct `binding_id`; duplicate IDs must have
identical bytes, and the resulting map must equal the standalone portable
row-source registry without omissions or extras.

`LIVE_ROW_SOURCE_BINDING` is `FULL_PUBLIC`. `LIVE_MODEL_EPOCH` remains
`STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` on exactly `NUMERICAL_MODEL` and
`NUMERICAL_PLANNING_PROOF`. The three dependency views inherited from 1.74
remain distinct. No operational epoch registry, claimed typed epoch, private
input, signer, B3, kernel, J0, K7 or held-out authority is accepted.

## Contract 1.76 M2 dynamic-child proposal cut

Contract 1.76 starts from hardened 1.75 raw replay and calls only the current
dynamic-child producer's byte verifier with the exact reconstructed epoch and
namespace. It compares complete portable registries for:

1. causal edges;
2. child states;
3. discovery intents;
4. validation templates;
5. the singleton closure;
6. the singleton closure verification.

Empty registries are explicit. Every present target record receives an
authority-local source binding to the exact `LIVE_MODEL_EPOCH`,
`NUMERICAL_MODEL` and `NUMERICAL_PLANNING_PROOF` record identities. Edge and
state bindings additionally commit the exact numerical row, support
descriptor, live row source, observation row and support freeze scalars.
Forward authority-local edges are handled by iterative Kahn replay; portable,
authority-local and effective dependency views remain separate.

The registered root-only cap-exceeded cut has four structural-only roles:
causal edge, state, closure and closure verification. Discovery and validation
intent roles are absent. Every present frontier is exactly the numerical model
and numerical planning proof; none is `FULL_PUBLIC`. Operational freeze,
legacy contract-1.51 authority, observer/worker/private/B3/kernel/J0/K7 and
held-out inputs remain forbidden.

## Contract 1.77 M2 numerical-planning cut

Contract 1.77 begins with hardened 1.76 raw replay. It collects the complete
deduplicated union of `NUMERICAL_MODEL` and `NUMERICAL_PLANNING_PROOF`
objects from every reconstructed live epoch and reruns the public exact
numerical planner for every epoch and its frozen route. Replayed model and
proof bytes and IDs must equal the standalone portable registries exactly.

Each model is bound to the exact occurrence record, every relevant
open-prefix verification and every matching live row-source record across all
epochs that contain that model. Row ID, row-binding ID, support-freeze ID and
source digest commitments are epoch-qualified. Each proof is bound to its
exact model record and occurrence. `LIVE_MODEL_EPOCH`,
`SIGNED_CONTROL_RECONCILIATION`, `CLOSED_RECONCILIATION` and
`MULTIROUND_RESULT` are forbidden reverse model dependencies. Portable,
authority-local and effective dependency lanes remain distinct, and the
complete graph is recomputed with a bounded forward-safe Kahn walk.

`NUMERICAL_MODEL` and `NUMERICAL_PLANNING_PROOF` are `FULL_PUBLIC`. This
transitively closes every live epoch and the four present dynamic-child roles.
`CONSTRUCTION_PLANNING_INPUT` remains structural-only with itself as its exact
unresolved frontier. The public lineage cut does not provide an issuer-owned
typed private lineage, so this contract neither calls the planning-input
compiler nor constructs an object with a private issuer. Private/operational
inputs, B3, observer/worker execution, kernel, J0, K7, held-out data,
production and certificates remain forbidden.

## Mandatory locks

```text
official_execution_allowed = false
fresh_heldout_access_allowed = false
scientific_endpoint_credit_allowed = false
plan_certificate_issuance_allowed = false
infeasibility_certificate_issuance_allowed = false
portable_semantic_registry_complete = false
source_authority_complete = false
code_provenance_complete = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

These locks may move only after the remaining semantic roles, source/code
provenance, all-path accounting, campaign closure and independent
complete-bundle verifier pass. Only then may a new final
preregistration, manifest, anchor and fresh held-out identities be frozen.
