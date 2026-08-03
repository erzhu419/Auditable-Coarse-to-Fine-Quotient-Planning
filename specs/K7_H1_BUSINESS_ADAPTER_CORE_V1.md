# K7 H1 business-adapter construction core V1

Status: Contract `2.0.55`, construction-only. No process is launched and no
production request/result authority is issued.

This slice freezes the H1 request/result, three-role descriptor topology, and
five-frame IPC schemas needed by the later two-process runtime. It does not
replace the missing observed current-access authority or formal 182-term V7
route authority.

## Request boundary

`H1ProductionBusinessRequestV1` is a reserved, unimplemented production type.
Its production factory always fails closed. The construction factory emits
only `H1ProductionBusinessRequestCandidateV1`, with
`production_request_authority = false` and an explicit future-consumer
rejection requirement. Python can allocate an uninitialized reserved-class
shell via `object.__new__`; therefore exact class identity is never authority.
The normative `require_h1_production_business_request_authority_v1` and result
counterpart always reject. The current claim is only that no valid production
authority can be issued or verified.

The fixture requires two role-separated, content-addressed candidates:
`H1ProductionCurrentAccessCandidateV1` and
`H1FormalV7FallbackDecisionCandidateV1`. Both state that they are
construction-only, have no production authority, and must be rejected by
production consumers. They must bind the same route-freeze barrier and route-
freeze sequence. A structural Protocol mock can model those fields for this
test fixture, but it cannot mint either future authority.

The request candidate binds the exact H1 recipe and preexecution bytes; the
candidate current-access log; a candidate formal V7 context, point, upper and
`FALLBACK` decision; all eight durable exact-infeasibility coordinates
(`structural`, `query`, `BuildEpoch`, `kernel`, `threshold`, `reward`, `policy
class`, and `complete search profile`) plus their exact aggregate identity;
plan/occurrence/attempt; fallback cap, cardinality, formula and derivation;
the exact V6 registry/stage/comparison/projection profiles; sealed owned-engine
source digest/extent/authority; route segment, recorder, and kernel/query replay
documents.

The request accepts immutable durable proof bytes, not caller-chosen kernel or
query labels. It independently replays the durable proof against the exact
identity, creates the canonical `G2048Kernel(2)` H=1 query without a ground
transition, and derives `OwnedEngineSearchSemanticsV4`. A compatibility bridge
checks the durable structural/query/threshold/reward/policy/search metadata and
configuration against that derivation. It does not prove equality of the two
transition tables or kernel source closures. The request embeds the semantics
document, its aggregate ID, all seven V4 component IDs, the durable proof
digest/extent, and the bridge ID.
Its kernel/query replay document IDs are the derived V4 kernel/query semantic
IDs; arbitrary caller labels are not accepted.

This bridge fingerprints the current direct in-process canonical replay only.
It is not evidence that a sealed fresh-exec child loaded the same runtime,
kernel/query documents, code, or transition semantics. The bridge and request
therefore set fresh-exec transition authority to false and require production
consumers to reject them. Production still requires a sealed fresh-exec replay
and observed process/transition-boundary join.

Sequence fields are exact integers (booleans are rejected) and must satisfy:

```text
predecision_read_barrier_sequence
< decision_verification_sequence
< route_decision_freeze_sequence
< request_issuance_sequence
```

The Contract 2.0.52 current candidate is rejected by exact type. The Contract
2.0.50 upper and decision IDs are rejected. The candidate input API contains
no kernel, QuerySpec, result, CounterRecord or WorkVector parameter. Its
current-access candidate must report observed zero values for kernel,
outcome, planner, J0, fallback and postrun reads. Structural Protocol mocks
exercise only the candidate schema.

## Result boundary

The same separation applies to results. The production result type/factory is
blocked; `H1ProductionBusinessResultCandidateV1` is construction-only. It
requires an exact completed source-owned V4 transcript and verifies the
transcript-owned `OwnedEngineFinishedExecutionBindingV4` against the supplied
execution. A transcript from the right request cannot authorize an altered
result, frontier, selected policy, cap outcome, or WorkVector. It accepts only:

- canonical H1 `INFEASIBLE_CERTIFIED`: one exact frontier point with reward
  `83/2624`, failure `383/410`, no selected policy, 16 composed candidates,
  208 events and exact owned counts `56/8/16/16/96/16/0`; or
- `CAP_EXHAUSTED`: incomplete search, empty frontier and selected fields,
  one typed exhausted-cap name, one cap rejection, and a completed retained
  owned prefix. It is never promoted to infeasibility.

The search helper's V1 WorkVector remains a diagnostic cross-check only.
Formal CounterRecord, WorkVector and ComparisonVector IDs are null and the
result sets semantic, terminal and formal-accounting authority to false.
Before either `INFEASIBLE_CERTIFIED` or `CAP_EXHAUSTED` can be emitted, the
result verifies that the V4 start node's semantics aggregate and all seven
components exactly equal the request-bound canonical replay.

## Exact role topology

The broker is the parent; only WORKER and BUSINESS are launched. Broker-owned
descriptors are preopened or returned by `clone3`; they are never described as
fresh-exec inherited. Only child descriptors have
`CHILD_INHERITED_FIXED_FD` origin. Pidfds have
`CLONE3_PIDFD_RESULT` origin.

- BROKER: worker/business channels, result read-only OFD, output directory,
  parent/child cgroup controls, two pidfds, and retained `memory.peak`.
- WORKER: broker channel and result read-only OFD only.
- BUSINESS: broker channel, result read-write OFD, and output directory.

Each `SOCK_SEQPACKET` endpoint has a distinct physical-object identity, while
the BROKER/child endpoints share one exact channel-pair ID. This models a
socketpair without pretending both endpoints are the same object.

The result is an `O_TMPFILE_REGULAR_FILE` inode with three distinct OFDs; only
BUSINESS can write it. Its future commit strategy is write, fsync, `linkat`,
`renameat2(RENAME_NOREPLACE)`, directory fsync, and reread. Thus the contract
does not claim an impossible rename of a memfd or an unavailable regular-file
seal. BUSINESS must then exit and be reaped before BROKER relays the pinned
result to WORKER. The
active capability FDs are separate from sealed read-only child inputs. WORKER
receives fixed FDs for its runtime archive, IPC-binding candidate, and topology
profile. BUSINESS receives fixed FDs for its runtime archive, request
candidate, owned-engine source and authority document, kernel/query replay
documents, and fallback cap profile. Every sealed input forbids ambient-path
fallback and SCM_RIGHTS delivery and has an explicit lifecycle close point.

The profile freezes 21 ordered lifecycle steps, from predecision input freeze,
formal verification, route freeze, and request sealing through both fresh-exec
children, owned search, result commit/relay/ACK, EOF, pidfd reap, broker suffix,
shared receipts, and formal accounting close. Every step remains marked
`runtime_implemented = false`. The WORKER-authored `BUSINESS_REQUEST` frame is
only the authorization signal relayed by BROKER. Child ambient repository and
private-key access are forbidden.

## Five-frame protocol

The only sequence is:

```text
WORKER_READY
-> BUSINESS_REQUEST
-> BUSINESS_RESULT
-> WORKER_ACK
-> WORKER_EOF
```

The binding includes the request/current/formal candidate IDs, route context,
point, upper and decision; all eight durable identity coordinates and exact
identity; plan/occurrence/attempt; cap and V6 registry; the common route-freeze
barrier; all four ordered sequence values; broker execution spec; and session
nonce.
`BUSINESS_REQUEST` is relayed to BUSINESS, which already holds the sealed
request FD. `BUSINESS_RESULT` is relayed unchanged to WORKER, which verifies
the read-only result bytes and emits `WORKER_ACK`. The result frame binds the
result ID, digest, extent and a typed commit-receipt candidate ID; the ACK
repeats that exact tuple and adds a typed worker-verification candidate ID.
The typed candidate documents explicitly say that write/fsync/linkat/rename/
reread, pre-relay BUSINESS exit/reap, and read-only distinct-OFD verification
have not been observed. Both are
nonauthoritative and must be rejected by production consumers. Every frame
payload uses an exact closed field set, exact content IDs/digests, and exact
integer validation; missing/extra fields and boolean-as-integer substitutions
fail closed. `PARENT_OUTPUT` is absent and forbidden. Binding, five frames,
commit/worker candidates, and transcript have role-separated content domains
and an exact predecessor chain.

## Remaining runtime wiring

Contract 2.0.55 does not yet supply:

1. the observed production current-access authority;
2. the formal V7 182-term upper/decision authority;
3. fresh-exec manifest/session joins and live fixed-FD installation, including
   sealed child replay of the request, runtime, kernel/query, cap, owned source/
   authority, transition/source equivalence, and the V4 compatibility bridge;
4. two native child launches, pidfd and SCM-credential authentication;
5. BUSINESS O_TMPFILE write/fsync/linkat/rename/reread, pre-relay exit/reap,
   and WORKER read-only ACK;
6. BROKER verification/reap and seven-role suffix rendering; or
7. nine shared-resource receipts and the 202-record accounting chain.

Therefore `official_execution_allowed = false`, scalar and break-even remain
null, and Counter Completeness, Workload Economics and Sample Efficiency all
remain `NOT_RUN`.
