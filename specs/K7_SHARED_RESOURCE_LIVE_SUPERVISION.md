# K7 shared-resource live supervision

Status: contract `1.92.0` construction boundary; no completed Gate claim.

This specification defines the next executable boundary for the nine V6
shared-resource paths.  It does not authorize a `CounterRecord`, `WorkVector`,
`ComparisonVector`, scientific endpoint, or certificate.  Those artifacts
remain forbidden until the independent verifier also closes the remaining
`71 + 114 + 8` obligations and consumes all 202 paths exactly once.

## Objective

Run the unchanged K7 root-cap occurrence inside a fresh sealed-source child,
while a trusted outer supervisor records the entire attempt from the first
registered payload access through operational terminalization.  The output is
raw, identity-bound source evidence for exactly:

```text
common.hash_invocations
common.integrity_checks
common.protocol_checks
io.read_bytes
io.staged_bytes
io.output_bytes
process.launches
io.mounted_bytes_peak
memory.working_bytes_peak
```

The supervisor may close these source-evidence obligations only after a
separately implemented verifier replays the sealed source, execution identity,
measurement definitions, event order, reducers, and cutoff.  Merely producing
nine numeric fields is not completion evidence.

## Execution boundary

One logical occurrence owns one route attempt, one decision point, one fresh
process group, one sealed source snapshot, one sealed private payload, and one
measurement window.  The child reconstructs the fixed K7 namespace, schedule,
pre-open authority, private environment, and production signer internally.
The request cannot provide any of those typed authorities.

The child-side schema currently exercises two ordered frames:

1. the immutable business result and partial-native transcript root;
2. a child-side accounting prefix carrying window/cutoff markers and source
   journals.

Those two frames are not the final shared-resource authority.  A child cannot
observe its own final reap, hidden descendants, post-exit cgroup peak, or the
bytes later committed by the parent artifact writer.  The authoritative
suffix must therefore be a third, **parent-owned final envelope**, frozen only
after the child has exited and the process group has been reaped.  The existing
Stage-A transport still admits one child output frame; until a successor
transport and the parent final envelope are connected, the two-frame schema is
only a parser/identity negative control and live execution remains forbidden.

The child must finish all business computation before freezing the operational
cutoff.  Work needed to terminalize the business result may occur after the
transcript terminal and before the cutoff.  After the cutoff, only bounded
accounting/provenance serialization already determined at the cutoff may run.
Any further kernel, planner, compiler, observer, solver, or policy work is a
protocol failure.

Missing, duplicate, reordered, oversized, or extra child frames, or a missing,
cross-identity, or prematurely frozen parent envelope, close the attempt as a
noncertificate failure and retain all supervisor-observed prefix work.

## Frozen measurement semantics

### Registered-payload byte accounting

Byte counters use logical registered transfer boundaries, not filesystem block
traffic and not an estimate from a returned object graph.

- `io.read_bytes` sums each registered payload consumption at its owner.  It
  includes request bytes, sealed private bytes, the complete source-archive
  verification pass, and the exact loaded-source byte manifest.  A charge key
  prevents a logical read from being counted twice.
- `io.staged_bytes` sums bytes copied or sealed specifically for this child:
  source archive, private payload, and any registered immutable auxiliary
  payload.  Interpreter, standard-library, native-extension, and host-runtime
  installation bytes are frozen infrastructure and are excluded.
- `io.output_bytes` includes every operational result, trace, counter, vector,
  projection, and manifest byte actually committed by the attempt.  IPC frame
  headers and diagnostic stderr are reported separately and do not replace
  artifact-byte accounting.

When an output embeds `io.output_bytes`, the current structural renderer builds
exactly eight ordered role-labelled canonical JSON candidate blobs in memory
and solves their deterministic byte-count fixed point.  It verifies neither
the business semantics of those role labels nor a write.  Its total excludes
the fixed-point trace/result and the later outer-finalization wrapper objects,
which remain in-memory and non-operational.  No operational write is authorized
until a future atomic writer jointly renders the final role bytes, commits them
once, and re-verifies the committed total.  Accounting/provenance hashes used
during fixed-point construction remain excluded from
`common.hash_invocations`.

### Hash accounting

`common.hash_invocations` counts registered business content-ID digest
finalizations.  Every allowed purpose is explicit and source-bound.  Unknown
purposes fail closed.  Hashes used only to build accounting events,
transcripts, receipts, attestations, or their content IDs are registered as
accounting/provenance exclusions; recorder updates are non-hashing and cannot
recursively charge themselves.  Global monkeypatching of `hashlib` is not an
authority.

### Integrity and protocol accounting

The unit is one invocation of a preregistered semantic obligation, not one
Python branch and not one caller-supplied total.  Each obligation fixes owner
module, symbol, stage, kind, and PASS/FAIL charging.  The event is appended
before a failed obligation raises.  Accounting self-validation belongs to the
post-cutoff provenance/evaluation lane unless the protocol explicitly makes it
part of operational execution.

### Process accounting

`process.launches` is emitted only by the outer process supervisor after a
successful operating-system launch.  The registered K7 profile permits one
child and forbids unregistered descendants.  Source replay must establish that
the sealed child has no alternate launch site.  Launch attempts and exits stay
diagnostic/derived and cannot be substituted for the native launch leaf.

### Capacity accounting

`io.mounted_bytes_peak` is the maximum simultaneous byte size of unique,
intentionally bound attempt payloads.  It includes sealed source, private, and
auxiliary payloads and any bounded writable sandbox payload.  Host runtime and
standard-library installations are fixed infrastructure and are excluded.

`memory.working_bytes_peak` requires an exclusive process-group cgroup-v2
`memory.peak` reading.  When the host cannot delegate such a cgroup, the only
allowed fallback is a preregistered, enforced finite address-space/working-set
cap, recorded as `VERIFIED_UPPER_BOUND`.  A child-reported RSS value, one
process's `VmHWM`, or a sample-based poll may be diagnostic but cannot become
the formal peak.

SUM paths are reduced by exact addition.  Peak paths are reduced only by MAX.
Neither reducer may be substituted for the other.

## Independent verification

The independent verifier must consume canonical bytes and reconstruct:

- source/runtime/program/profile/request identities;
- occurrence, route-attempt, decision-point, transcript-terminal and window
  joins;
- the sealed source manifest and exact loaded-source set;
- every registered hash purpose and named obligation;
- byte-transfer charge keys and duplicate exclusion;
- process-group launch/exit topology;
- mount manifest and cgroup measurement, or the enforced cap fallback;
- the child-frame order, the parent final envelope, final reap, and absence of
  post-cutoff business work; and
- one exact SUM/MAX value for each of the nine V6 paths.

The verifier then issues semantic shared-resource resolutions into the V0-099
evidence closure.  It does not derive any of the other 193 path resolutions.

## Implemented construction cut

Contract `1.92.0` implements four fail-closed structural primitives:

- a single-window live event meter with separate SUM/MAX reducers, registered
  hash purposes, named PASS/FAIL obligations, explicit zero claims and typed
  unavailability;
- an in-memory, capped, deterministic eight-role `io.output_bytes` fixed-point
  solver with double rendering and two post-convergence replays; and
- a canonical, identity-bound K7 child-frame schema whose parser rejects
  missing/reordered/extra frames, duplicate identities, nonfinite JSON and the
  Python `bool == int` ambiguity; and
- a structural post-cutoff envelope/finalization join that enforces local ID
  distinctness and the numeric order `cutoff < reap < descendant scan < final
  peak < terminal`, never substitutes the pre-cutoff peak for the final peak,
  and still grants no semantic authority.

The structural envelope accepts opaque source IDs and ordered integers; it is
not evidence that a real supervisor observed those events.  The current cut
does **not** connect a real K7 child, a supervisor-issued post-reap envelope,
the typed K7 route graph, a global event journal, cgroup/mount provenance, an
atomic output writer with wrapper-byte closure, a source-byte semantic
verifier, or a formal vector materializer.  A live snapshot therefore keeps
`io.output_bytes` typed unavailable.  Structural replay is not semantic
verification.

## Mandatory attacks

Tests must reject source, runtime, request, occurrence, route, terminal,
window, method, monitor, reducer, charge-key, child-frame, and suffix
transplants; an unknown hash purpose; an unregistered predicate; a missing
FAIL event; duplicate byte charging; staged/read/output substitution; a hidden
descendant process; a peak from child self-report; a changed resource cap;
post-cutoff business work; output-byte nonconvergence; and prefix-work loss on
timeout, crash, cap exhaustion, or malformed output.

## Locked state

Until a fresh live bundle passes that verifier:

```text
nine_shared_resource_paths_semantically_closed = false
counter_records_issued = false
work_vector_issued = false
comparison_vector_issued = false
official_execution_allowed = false
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
```
