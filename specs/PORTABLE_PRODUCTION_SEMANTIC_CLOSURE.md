# Portable Production Semantic Closure

**Status:** normative construction contract; production and target access locked  
**Ledger:** V0-076  
**Implemented revisions:** `1.60.0`–`1.70.0`
**Current completed public cut:** M0 + B1 + M1A + M1B ROOT

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

These locks may move only after the remaining semantic roles, signer-owning
service, source/code provenance, all-path accounting, campaign closure and
independent complete-bundle verifier pass. Only then may a new final
preregistration, manifest, anchor and fresh held-out identities be frozen.
