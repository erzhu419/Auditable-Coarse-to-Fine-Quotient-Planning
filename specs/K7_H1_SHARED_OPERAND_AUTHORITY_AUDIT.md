# K7 H1 shared-operand authority audit

Status: design audit; not a numeric upper or execution authority.

This audit records why the nine shared-resource operands cannot be assigned
honest numbers until the H1 production topology is frozen.  Existing V2
WORKER/BUSINESS code is a root-cap reference implementation, not the H1
runtime required by Contract 2.0.50.

## Dependency order

The construction order is:

```text
H1 business adapter
-> H1 role/runtime profiles
-> no-ground current-identity authority
-> exact execution topology and branch DAG
-> common/read/stage/mount/output/memory catalogues
-> numeric V7 upper and formal route decision
-> selected-route execution
-> exact receipts
-> CounterRecord -> WorkVector -> ComparisonVector
```

Profiles, serializers and catalogues may be constructed before V7.  No
execution-side access is allowed before the formal route decision.

## Branch-wise upper equations

Let `B` be the preregistered reachable terminal branches and `prefix(b)` the
operations reachable before branch `b` closes.  Hash, integrity and protocol
upper counts are branch maxima over registered event multiplicities:

```text
U_hash      = max_b sum_{e in prefix(b)} m_hash(e,b)
U_integrity = max_b sum_{e in prefix(b)} m_integrity(e,b)
U_protocol  = max_b sum_{e in prefix(b)} m_protocol(e,b)
```

For payload family `g`, extent `E_g` and preregistered branch multiplicities:

```text
U_read  = max_b sum_g n_read(g,b)  * E_g
U_stage = max_b sum_g n_stage(g,b) * E_g
U_mount = max_b max_t sum_{p in UniqueActive_b(t)} E_p
U_output = max_b F_b
```

`F_b` is the exact branch-aware output fixed point.  Reads are charged per
actual read; stages are charged per target ingress; mount peak deduplicates
only a physically shared payload identity that is simultaneously visible.

The recommended memory topology is one route-wide outer hierarchy that
continuously contains broker, worker and business.  Its safe candidate is:

```text
U_memory = min(OUTER, BROKER_PARENT + WORKER + BUSINESS)
```

If outer contains children only, the safe form is instead:

```text
U_memory = BROKER_PARENT + min(OUTER_CHILDREN, WORKER + BUSINESS)
```

The former `min(OUTER, WORKER + BUSINESS)` is invalid because it omits broker
memory.

For the canonical H1 ground owner, the successful operational cap components
remain:

```text
8 + 16 + 16 + 96 + 16 + 56 = 208
```

Shared admission must be derived jointly by branch, rather than appended from
post-run actuals:

```text
U_control.checks = 56 + max_b(H_b + I_b + P_b + R_b + S_b + M_b
                              + O_b + W_b + L_b)
```

At most one `control.cap_rejections` event is allowed by a failed admission.
`process.launches` has all-branch upper 2; exact actual is the number of
verified positive pidfd edges (0, 1 or 2).  Ambiguous child existence cannot
issue an exact actual record and closes the attempt as `PROTOCOL_FAILURE`.

## Reference topology is not an H1 authority

The present root-cap topology has 15 COPY ingresses (`7` public payloads per
role plus one BUSINESS secret) and two interpreter BIND ingresses.  It has no
production TransferMountJournal stage/mount wiring, and cross-role physical
payload sharing is not frozen.

Even after precreating sealed descriptors, its success read expression is:

```text
10I + 10C + 3A + S + K + H + G + 2B + 2 + 4O + Z_W + Z_B
```

The dynamic zipimport terms `Z_W` and `Z_B` are outside the current receipt
recorder.  A window that includes sealed-memfd construction must also charge
complete creation readback.  Ambient repository/private-key filesystem reads
are not a closed payload catalogue.  H1 must use sealed-FD inputs or strict
read isolation before read/mount completeness can be claimed.

## Required typed authorities

### Production current identity

`H1ProductionCurrentIdentityAuthorityV1` must consume an independently
verified BuildEpoch/kernel-law attestation, authenticated QuerySpec, durable
proof verification attestation and their exact identity crosswalk.  Route-time
verification freezes all ground/planner calls at zero:

```text
kernel_step_calls = 0
ground_outcome_enumerations = 0
planner_calls = 0
j0_calls = 0
fallback_solver_calls = 0
claimant_identity_used_as_current = false
```

Full durable-proof semantics are established earlier in build/evaluation
lane; route time verifies only independent attestations and exact identity
bindings.

### Execution topology

`H1ExecutionTopologyProfileV1` freezes exact role order, zero helper launches,
payload sharing/duplication, COPY/BIND ingress, named read sites, visibility
open/close events, branch DAG, and business adapter/archive/runtime identities.

### Shared operand rows

Each `H1SharedOperandFamilyV1` row contains at least:

```text
path, family_key, owner_role, source_module, source_symbol,
source_archive_id, branch_guard, operation_kind, payload_instance_key,
payload_identity_rule, extent_authority_id, multiplicity_expression,
reuse_group_id, failure_settlement, actual_receipt_schema
```

Multiplicity uses a closed `CONST/SUM/REACH/MAX_BRANCH` AST.  Callables,
caller-supplied totals, wildcards and missing-as-zero are forbidden.

## Event semantics and remaining blockers

Operational hashes/checks must pass through registered wrappers.  Each
compound predicate invocation has a preregistered unit; raw hash operations in
the route window are a protocol failure.  Journal/content-ID sealing hashes
belong in a post-cutoff provenance/evaluation suffix to avoid recursive
charging.

Numeric V7 remains blocked by the missing H1 adapter/profiles, dynamic
zipimport and ambient reads, unfrozen physical payload sharing, incomplete
failure-prefix memory/launch evidence, absent branch-output authority and the
production shared-cap engine's `V7_AUTHORITY_PENDING` state.
