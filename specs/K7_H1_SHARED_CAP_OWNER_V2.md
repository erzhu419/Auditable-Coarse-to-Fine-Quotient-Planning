# K7 H1 shared-cap/source owner V2

Status: Contract 2.0.58 construction authority; production execution remains
locked pending the exact operand/formal-route join.

## Closed boundary

This contract replaces the historical nine non-callable V2 sentinels with one
H1-specific issuer-retained owner kernel. Its structural owner-site manifest
declares exactly these nine intended owner methods:

| path | reducer | owner method |
|---|---|---|
| `common.hash_invocations` | SUM | `record_hash_invocation` |
| `common.integrity_checks` | SUM | `record_integrity_check` |
| `common.protocol_checks` | SUM | `record_protocol_check` |
| `io.mounted_bytes_peak` | MAX | `open_mounted_payload` |
| `io.output_bytes` | SUM | `begin_route_output` |
| `io.read_bytes` | SUM | `read_registered_payload` |
| `io.staged_bytes` | SUM | `stage_registered_payload` |
| `memory.working_bytes_peak` | MAX | `bind_working_hierarchy` |
| `process.launches` | SUM | `launch_registered_role` |

That manifest binds caller-provided archive/topology IDs plus the structural
rows. It does not bind source bytes, a normalized AST, loaded symbols or method
semantics and is not production source authority.

Paths are embedded at their methods; there is no caller-selectable generic
`record(path, value)` surface.  A reservation is admitted and retained before
the wrapped callback can run.  Success settles the exact callback-provided result;
callback or settlement failure charges the full reservation and closes the
owner as `PROTOCOL_FAILURE`.  A hard-cap rejection occurs before the callback,
is not infeasibility, and consumes the one registered
`control.cap_rejections` allowance.

Every rejected admission also emits an atomic receipt/event pair with the
attempted path, reservation, candidate, hard cap, cumulative control counts
and `side_effect_started=false`. Pair-ID hashing is explicitly assigned to a
non-operational provenance suffix so it cannot recursively charge the hash
counter whose journal it seals.

If a trusted callback returns a known value above its reservation, the owner
preserves that full observed value and records
`OBSERVED_UPPER_BOUND_VIOLATION`; it never truncates known work to the upper.
Only a callback failure for which no exact result exists is conservatively
charged at the reservation.

Every settled operation appends one receipt and one semantic event under the
same runtime and monotonic atomic-pair sequence.  Construction-exercise pairs
are explicitly `formal_accounting_eligible=false`; the later native-accounting
contract must issue the formal receipts after the production join.

The construction kernel holds one process-local `RLock` across each callback.
This prevents concurrent callers from racing reservation against settlement,
and same-owner callback reentrancy is rejected before the nested side effect.
It does not prove cross-thread callback liveness and does not reject a
same-thread callback that mutates a different owner. Those properties remain
production broker obligations. Read-only same-thread snapshots remain
available inside callbacks and return deep copies. Mount/output/memory tokens
carry retained canonical seals, and each mount-open sequence has a distinct
token identity.

## Non-circular profile

`H1SharedCapProfileV2` is frozen before route selection and contains no:

- `DecisionPoint` identity;
- route-upper identity;
- route-decision identity;
- selected route; or
- decision-freeze identity or sequence.

It binds the predecision context, production current-access authority, route
attempt, H1 execution topology, source archive, nine hard caps, control-check
cap, memory topology and retained `memory.peak` OFD plan.  Consequently, it can
be an input to operand construction without depending on the upper or decision
that operand construction will produce.

## Exact H1 lifecycle

Memory binding is the first owner operation.  Its admitted formula is:

```text
min(memory hard cap,
    outer hierarchy cap,
    broker parent cap + worker role cap + business role cap)
```

Thus BROKER is never omitted from the candidate.  The binding records all
three roles and the same retained `memory.peak` OFD plan.  The peak may be read
once, after trusted reap of both descendants.  Binding creates the path's one
aggregate admission and keeps that reservation live; the retained-OFD read
settles it without generating a second `control.cap_checks` event. Exact read
success records `EXACT_SUCCESS`. A failed callback records
`FAILED_UPPER_ONLY`, conservatively charges the reservation, and becomes a
terminal reservation settlement inside this owner, not an attempt terminal. A
known overrun records
`OBSERVED_UPPER_BOUND_VIOLATION`. Neither terminal failure can be retried, and
the retry is rejected before its callback; both may be consumed by honest
failed cleanup without being misreported as an exact observation.

The whole-route output reservation must precede the first launch and remains
outstanding until exact finalization. Finalization is forbidden until the
known child-launch prefix is resolved, trusted reap and memory-peak settlement
are complete, and every mount is closed; no child may launch after
finalization. Exact success records `EXACT_SUCCESS`; callback failure records
`FAILED_UPPER_ONLY`; and a separately known overrun records
`OBSERVED_UPPER_BOUND_VIOLATION` without clipping. Each is an exact-once
terminal settlement of the one output reservation, not a typed attempt
classification. Any retry is rejected
before its callback. Only exact success can support normal closure; either
failure settlement can support noncertificate failed cleanup. After any
terminal output settlement, every further shared-resource mutation is
forbidden; only the appropriate normal or failed close may follow. Mounted
payloads open before child visibility, deduplicate a
simultaneously visible physical payload identity, and cannot close before
trusted descendant reap. Failed close leaves cleanup live and closes the route
as protocol failure.

Cap/protocol failure disables new route work but retains cleanup-only access
to known-prefix pidfd reap, the already-reserved memory peak read, mount close
and already-reserved output finalization. `close_failed_cleanup` preserves the
original failure mode while proving all known resources and reservations are
settled. The first failure is retained as the ordered `PRIMARY` cause. A later
failure admitted into the serialized operation window is appended as generic
`SECONDARY`, with `cleanup_phase` stating whether it arose in a cleanup method.
Its `observed_mode` describes that new failure, while the original mode is
embedded separately as `preserved_primary_mode`; a cleanup protocol failure
therefore cannot replace an earlier `CAP_EXHAUSTED`. Calls rejected before an
operation window because the owner is already closed are not claimed as chain
members. The issuer-retained chain has
contiguous ordinals and is revalidated before snapshot or explicit cause-chain
verification. A mount-open callback failure retains a typed native-existence
ambiguity even though no ordinary mount token was returned. A failure before
hierarchy binding creates no phantom memory/reap obligation; a one-child
prefix requires only that child's reap observation, and an observation for an
unlaunched role is rejected. An ambiguous native hierarchy bind, mount open or
launch still requires a later native existence-resolution authority and
cannot be silently treated as absent.

Trusted descendant reap is an exact-once in-memory lifecycle transition. The
construction owner retains one caller-provided content ID for every member of
the known launched-role prefix. A repeated reap call is a protocol failure and
cannot replace the already retained IDs. These IDs are neither role-bound nor
broker-native evidence; snapshots state both limitations explicitly. The later
production authority must validate native pidfd observation schemas and role
bindings.

The only successful launch order is:

```text
WORKER -> BUSINESS
```

The process hard cap and successful route actual are exactly two.  Closing the
owner requires both launches, trusted pidfd reap, the retained-OFD memory read,
output finalization, no active mounts and no outstanding reservation.

## Execution lock

`prepare_h1_shared_cap_owner_v2` returns a real callable owner handle in
`AWAITING_OPERAND_FORMAL_JOIN`.  Every production operation fails before its
callback while either the exact shared-operand authority or formal V7 route
authority is absent.  This contract deliberately does not provide a public
activation shortcut.

`prepare_h1_shared_cap_owner_construction_exercise_v2` exercises the same
kernel under a domain-separated, non-production mode.  It proves mechanics
only and cannot issue a route certificate, formal actual-compliance evidence,
official execution permission, or close any Gate.

The next contract must join this owner to the exact nine-operand authority and
the formal 182-term V7 fallback decision before enabling the production
callbacks.  The later runtime must additionally replace construction callback
observations with broker-owned native pidfd/OFD/output facts, provide native
existence resolution for ambiguous callbacks, and persist an atomic
single-consumption receipt across processes/restarts. The singleton currently
retained by this module is process-local and is not that production authority.

## Locks

```text
official_execution_allowed = false
formal_actual_compliance_eligible = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
