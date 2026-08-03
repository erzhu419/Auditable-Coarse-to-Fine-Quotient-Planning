# Contract 2.0.47: construction shared-cap admission authority

Status: implemented construction contract; production join remains blocked.

Profile key: `construction_shared_cap_authority_v1`.

Ledger key: `V0-110B-2E-36`.

## Decision

The canonical H1 `DIRECT_FALLBACK` route now has one issuer-owned, one-shot
admission session for the nine V6 shared-resource paths:

- `common.hash_invocations`;
- `common.integrity_checks`;
- `common.protocol_checks`;
- `io.mounted_bytes_peak`;
- `io.output_bytes`;
- `io.read_bytes`;
- `io.staged_bytes`;
- `memory.working_bytes_peak`;
- `process.launches`.

This contract proves the cap mechanics only.  Its source-site IDs are
`PREREGISTERED_CONSTRUCTION_ONLY_UNVERIFIED`; no production owner or formal
route decision consumes the session yet.

## Identity and activation

The profile is bound to the exact official V6 registry, stage profile,
comparison profile, route context, decision point, route attempt and all nine
finite caps.  Eight new roles have distinct central content-ID domains for the
profile, construction decision candidate, prerequisite, session, reservation,
mount token, receipt and snapshot.

Activation requires an issuer-owned construction-only `FALLBACK` candidate and
a clean replayed pre-freeze access prefix.  These objects state explicitly:

```text
formal_v6_route_decision_authority_present = false
authorizes_production_route_execution = false
construction_cap_mechanics_only = true
blocker = V7_FORMAL_ROUTE_DECISION_AUTHORITY_MISSING
```

One `(profile_id, route_attempt_id)` can issue exactly one live budget session.
Direct construction and same-ID reminting cannot fork the budget.

## Admission semantics

Every target admission creates exactly one atomic, nonrecursive
`control.cap_checks` event.  The meta-check that admits this event is not
charged recursively.

SUM paths reserve before the side effect and settle afterward.  A successful
bounded read may commit its returned byte count and refund the unused reserve.
If an exception or unverifiable callback prefix occurs, the full reservation
is conservatively committed.  A callback cannot hide work by catching an
internal protocol failure, mutating the session topology, reservation or
receipt, and then returning or raising another exception.

`io.staged_bytes` is admitted only for a named
`COPY_INTO_EXECUTION_SANDBOX` or `BIND_INTO_EXECUTION_SANDBOX`.  Generic IPC is
not staging.

MAX working bytes retain the largest admitted observation.  Mounted bytes use
simultaneous distinct-payload semantics: duplicate references to one payload
do not multiply the current visible payload, while the historical peak is
retained after close.

## Fail-closed state

Profiles, candidates, prerequisites, sessions, reservations, mount tokens,
receipts and snapshots retain issuer-side canonical seals.  Fixed session
identity and the complete trusted runtime state are replayed on every public
entry.  `object.__new__`, unbound calls, copy/serialization, mutation,
recomputed-ID, foreign, stale and duplicate-capability attacks fail with typed
protocol outcomes.

Every protocol transition first restores the last issuer-sealed state and
fully settles all outstanding SUM reservations once.  A genuine mounted token
may still execute terminal cleanup after `PROTOCOL_FAILED`; current visibility
returns to zero while the peak and failure receipt remain.  Callback error
provenance is retained as the exception cause.

Cap exhaustion is:

```text
ATTEMPT_CLOSURE_NONCERTIFICATE.FALLBACK_CAP_EXHAUSTED
```

Protocol corruption is:

```text
ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE
```

Neither outcome is an infeasibility certificate.

## Intentionally open production blockers

This contract does not make the Contract-2.0.46 upper executable.  The
following remain mandatory:

1. an exact nine-path production source-site manifest and live owner wiring;
2. aggregate pre-execution cap formulas for all reads, sandbox ingress,
   mounted visibility, total route output, process launches and working set;
3. a V7 formal route-upper and route-decision authority;
4. a brokered direct-fallback successor with cap admission before each side
   effect, trusted child-read evidence and hierarchy-aware cgroup peak replay;
5. `178 + 7 + 9 + 8 = 202` formal CounterRecords, the 182-term operational
   projection, an independent verifier and FQ9 closure.

Therefore all official, scalar, break-even, Counter Completeness, workload
economics and sample-efficiency states remain locked or `NOT_RUN`.
