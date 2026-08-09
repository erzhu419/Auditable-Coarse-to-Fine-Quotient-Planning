# K7 H1 E4 In-Supervisor Authoritative Attestation V1

Status: bounded construction prerequisite
Proposed contract: `2.0.59-E-C-E5B-A`
Profile key: `construction_k7_h1_e4_in_supervisor_authoritative_attestation_v1`

## Scope

E5B-A closes one prerequisite for a future integrated E5B supervisor.  In the
same process and preparer thread that owns the exact retained E4 context, it
calls the existing E4 authoritative verifier over:

1. the exact issuer-retained `H1E3BoundOutputContinuationContextV1`;
2. an exact-runtime-type `H1ExclusiveBrokerCompletionV1`;
3. an exact-runtime-type `H1E3BoundOutputCompletionV1`.

E3 and E4 V1 do not expose process-local registries for completion-object
identity.  E5B-A therefore does not claim that those two completion objects
are the original Python objects returned by their issuers.  Their authority is
the full semantic reconstruction performed by the existing E4 verifier, not
object identity.  Only the retained E4 context and the E5B-A attestation itself
have exact retained-object identity at this boundary.

Only after that call returns exact `True` does E5B-A issue one
content-addressed
`IN_SUPERVISOR_E4_AUTHORITATIVE_ATTESTATION_PRESENT` artifact.

This is not integrated route execution.  It does not launch a supervisor,
guardian, E3 role, E4 writer or business process.  It does not perform cgroup
placement, read a route-wide peak, issue an FQ11 counter, or unlock any
official or scientific Gate.

## Why the attestation is required

E4 has two deliberately different verification boundaries:

- its authoritative verifier needs the exact process-local retained context,
  exact E3/E4 completion runtime types and reconstructs the full completion
  from the persisted output bytes;
- its portable checks can replay content structure and persisted files but do
  not possess the retained context authority.

A later external guardian cannot recreate the first boundary after the
supervisor exits.  E5B-A therefore records that the E4 preparer process and
thread crossed it while the retained context was live.  E5B-A does not
authenticate that process as the future expected sealed supervisor.  A
SHA-256 content ID is an integrity identity, not a signature and not proof
that an arbitrary portable mapping was legitimately issued.

## Exact authoritative input contract

The issuer accepts no mappings, subclasses or typed nulls on the authoritative
path.  Exact runtime types are mandatory.  Exact retained-object identity is
mandatory only for the context, because that is the only upstream authority
for which the existing E4 contract exposes an issuer registry:

| input | exact type |
|---|---|
| retained context | `H1E3BoundOutputContinuationContextV1` |
| upstream success | `H1ExclusiveBrokerCompletionV1` |
| output success | `H1E3BoundOutputCompletionV1` |

Before issuance, the current process and thread must equal the context's
frozen `preparer_pid` and `preparer_thread_id`.  The issuer then invokes:

```text
verify_h1_e3_bound_output_completion_v1(
    completion=exact_runtime_type_e4_completion,
    context=exact_retained_context,
    e3_completion=exact_runtime_type_e3_completion,
)
```

Returning anything except the exact boolean `True`, or raising for any
reason, prevents issuance.

The following cross-bindings are then replayed:

- E4 completion context ID equals the retained context ID;
- caller binding, logical occurrence and route attempt agree with the durable
  E4 role set;
- the context output-directory binding equals the E4 writer allocation;
- E4 upstream completion ID and session nonce equal the supplied runtime-type
  E3 completion;
- the E3 completion prebinding equals the retained context ID;
- the E3 authority disposition is `BROKER_EXCLUSIVE_PRESENT`;
- the E3 profile and source-manifest IDs equal the current registered objects;
- the E4 profile equals the current registered E4 profile.

## Content-bound identity chain

The attestation binds all identities needed by this boundary:

- E5B-A profile ID;
- E4 completion ID, canonical SHA-256 and canonical byte count;
- E4 retained-context ID;
- E3 completion ID and session nonce;
- E3 profile ID;
- E4 profile ID;
- E3 source-manifest ID, broker-source SHA-256/extent and interpreter
  SHA-256/extent/device/inode;
- caller binding ID, logical occurrence ID and route attempt ID;
- complete output-parent/name/directory identity from the E4 allocation;
- for all eight roles, in exact ordinal order 53 through 60:
  - role and file name;
  - role-witness, commit and ordinal-event IDs;
  - SHA-256 and byte count;
  - device, inode, mode and link count.

The attestation has its own V13 content domain.  Every field, including every
negative lock, participates in its content ID.

## Process locality, copying and fork

The authoritative attestation object is issuer-owned and registered by exact
object identity together with its canonical bytes, issuing PID and issuing
thread ID.  Authoritative re-verification requires that exact registered
object in that same process and thread and repeats the E4 authority call.

The object rejects shallow copy, deep copy and pickle.  A second object built
from identical bytes is not the registered issued object.  After `fork`, the
child PID differs and can neither issue nor authoritatively reverify the
parent's attestation.  Independently, E4 clears its process-local context
authority in the child.

These controls do not claim resistance to an attacker that can arbitrarily
mutate private Python module state.  The explicit lock remains:

```text
same_process_private_state_adversary_resistance_claimed = false
```

## Guardian replay boundary

A guardian may receive the attestation document, E4 completion document and
bound output-directory path.  Its only permitted verification is:

```text
attestation content-ID and complete-field replay
+ E4 completion structural replay
+ persisted eight-file byte/inode replay
```

The persisted replay independently enforces:

- the bound parent device/inode/mode and directory basename;
- the bound directory device/inode/mode;
- exactly the eight registered file names and no ninth wrapper;
- eight distinct regular inodes;
- mode `0400`, link count one and the exact extent for every role;
- stable descriptor and name identity before and after each read;
- canonical bytes equal to the E4 durable role document;
- SHA-256, extent, device and inode equal the E4 commit/inventory;
- a pinned parent-directory descriptor and child open relative to that parent;
- stable parent path, child name and directory identity after the final read;
- a final device/inode/mode/link-count/extent inventory for all eight paths
  while all eight originally read descriptors remain retained.

The guardian does not receive an exact retained context and must not call the
E4 authoritative verifier.  Its replay result therefore freezes:

```text
same_process_e4_authoritative_verifier_invoked = false
exact_retained_context_available = false
same_process_authority_reperformed = false
same_process_authority_inferred = false
may_substitute_same_process_authority = false
```

The guardian result is independently content-addressed in its own V13 domain.
It proves only portable structural and persisted-file replay.  It cannot mint,
replace, upgrade or infer the in-supervisor authority attestation.

## Coherent re-signing

The portable attestation verifier reconstructs the entire expected payload
from the supplied E4 completion structure and the registered E3/E4 profile and
source objects.  It compares that reconstruction field-for-field after
validating the supplied content ID.  Consequently, changing a lock, an E3 or
E4 identity, an output inode, or an authority boolean in the attestation alone
and recomputing SHA-256 still fails the reconstruction.

This does not turn SHA-256 into a signature.  The portable verifier only
establishes that a document is the unique expected structural image of the
provided completion under the current profile.  Coordinately replacing and
re-signing the supplied completion, persisted files and attestation remains a
nonauthoritative structural image and is not rejected as an authenticity
claim.  Only the exact registered same-process attestation object plus repeated
E4 authority call establishes authority.

## V13 domains

V13 adds exactly three disjoint content domains:

1. E5B-A profile;
2. in-supervisor E4 authoritative attestation;
3. guardian structural and persisted-file replay.

V10 E3, V11 E4 and V12 E5A objects remain in their original domains.

## Required attacks

Default tests must cover:

1. caller-minted profile, attestation and guardian replay objects;
2. wrong exact input types and crossed E3/context/completion identities;
3. proof that issuance and authoritative re-verification call the E4
   authoritative verifier;
4. shallow-copy, deep-copy, pickle and same-byte clone rejection;
5. foreign-thread issuance and authoritative re-verification rejection;
6. fork-child issuance and authoritative re-verification rejection while
   allowing only the explicitly nonauthoritative guardian replay;
7. attestation-only coherent re-signing of identity, authority and
   guardian-substitution fields;
8. changed output mode, bytes, inode set, extra file or crossed directory,
   including parent rename/symlink and mid-replay file replacement attacks;
9. proof that guardian replay never invokes the E4 authoritative verifier.

## Locked claims

The following remain false or `NOT_RUN`:

- guardian replay substitutes same-process authority;
- guardian infers same-process authority;
- content hash is a signature;
- same-process private-state adversary resistance;
- exact E3 completion object-identity retention;
- exact E4 completion object-identity retention;
- authenticated expected-supervisor binding;
- E5B integrated route execution;
- route-wide actual-peak authority;
- route-wide peak, production output-leaf and FQ11 completeness authority;
- formal CounterRecords, WorkVector, ComparisonVector and actual-projection proof;
- current-access and formal V7 authority;
- peak scope remains `PEAK_SCOPE_UNRESOLVED`;
- official execution, scalar cost and break-even;
- `COUNTER_COMPLETENESS_GATE` and `WORKLOAD_ECONOMICS_GATE`.

Passing E5B-A proves only that a future supervisor has an additive mechanism
to preserve the already-existing E4 same-process authority result before an
external guardian is reduced to portable replay.  It does not complete E5B or
the nine shared-resource sources.
