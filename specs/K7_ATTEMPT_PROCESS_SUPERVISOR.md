# K7 attempt-wide process supervisor

**Contract:** `2.0.2`

**Milestone:** `V0-110A`

**Status:** implemented in-process pre-bind-through-parent-payload raw window;
semantic and formal Gates locked

This contract closes the process-window scope mismatch exposed by V0-109 without
promoting process-local observations into formal accounting. Its object is one
issuer-owned session whose raw observation window and active sink begin before
request binding/replay. On the implemented in-process wrapper/type paths, it
retains the observed process-launch prefix as either a closed immutable journal
or, if ordinary journal materialization fails, an explicitly nonformal
emergency prefix or raw-field snapshot. The implementation establishes only
this bounded in-process raw-prefix evidence.

Here, “attempt-wide” is only the name of the intended accounting scope: the
implemented cutoff ends after the typed parent-result payload is frozen and
before the post-cutoff envelope is formed. It does not establish a complete
publication window, crash-safe observation or independently no-loss
observation. Its canonical journal bytes are not independent operating-system
proof, so it cannot mark `process.launches` as `CONNECTED_EXACT`.

## Attempt boundary

The registered production wrapper creates one supervisor session for one
logical route attempt. It opens the session and activates its sink before
request binding/replay. The observed in-process prefix includes:

1. request-bound parent profile/source replay;
2. admission and nonce work;
3. delegated cgroup lease acquisition;
4. bootstrap and sealed-input preparation;
5. atomic child launch and supervision;
6. child-frame and two-frame replay;
7. typed parent-result payload freezing for the wrapper; and
8. success/failure journal closure while the process sink remains active.

Activating the sink after request replay is a protocol failure. A child-runtime
window, subprocess wrapper, cgroup leaf or returned summary cannot be relabelled
as this window. The bound identity must contain the exact request, route,
logical occurrence, route attempt, execution profile, counter registry, stage
profile and parent execution specification. A launch edge that reaches the
active sink before identity binding completes is retained by the write-ahead
lower bound and forces a protocol-failure prefix; it is not silently discarded.

Under the supported public API, the session capability is process-local,
single-use and unpickleable. A caller may supply none of the event sequence,
launch count, terminal prefix, closure status or aggregate value.

The production session-start call site and the runtime event-emission call site
are each pinned exactly once during their respective module imports. Each pin
retains the original function object, code object, globals mapping and an
import-time source snapshot. Under the cooperative public-API threat model, the
pinned production executor is the accepted session opener and the pinned atomic
runtime call site is the accepted emitter: ordinary module-symbol rebinding does
not transfer either role, and a second registration is rejected.

This pinning is not a security boundary. Code already able to mutate arbitrary
same-process underscore state, function globals, pinned objects or frozen
objects through mechanisms such as `object.__setattr__` is outside this raw
threat model. The pins therefore do not prove loaded-code integrity, exclude a
malicious same-process launch or establish OS truth. Exact authority requires
external isolation plus supervisor/kernel attestation rather than stronger
wording around these Python objects.

The typed parent result and the payload snapshot consumed by the wrapper are
frozen before the raw journal closes, and that close occurs before the active
sink is removed. The returned envelope is formed only after this cutoff. It is
a no-launch canonical wrapper over the already-frozen parent payload and closed
journal, not another attempt-owned execution phase and not evidence for a
complete external or durable publication window. If later envelope,
publication, cleanup or other helper work launches a process after this cutoff,
the current raw journal does not observe it. Such work must move inside the
active window or receive a separately specified externally observed scope.

## Raw process-launch event

The atomic runtime enters the process-local launch receiver immediately in the
parent branch after native `clone3` returns a positive child PID. The receiver's
write-ahead fact occurs before pidfd-value validation, descriptor cleanup,
signal unmasking or any other fallible post-clone work. A clone attempt that
fails before a child exists records no successful launch. A reached launch edge
whose later pidfd validation, setup, exec, business, replay or covered cleanup
fails cannot be rolled back to a prelaunch zero.

The receiver uses a write-ahead launch-edge lower bound. On entry from the
pinned launch site it first increments `launch_edge_entered_count` (which is
also serialized as `launch_edge_lower_bound`) and marks launch-event
materialization in progress. Only then does it obtain the pinned-call-site
provenance, acquire a timestamp, construct or hash the typed event, allocate its
canonical bytes, and append that event. Thus a provenance, timestamp, hashing,
allocation or serialization failure cannot turn a reached launch edge back
into a prelaunch zero. The closed prefix is forced to
`PROTOCOL_FAILURE`; it may legitimately contain a lower bound of one with zero
materialized event rows and
`launch_event_materialization_in_progress = true`. Such a prefix is diagnostic
raw evidence only and never authorizes a formal count.

The lower bound is still process-local volatile state. A sink failure before
receiver entry, interpreter abort or host/process crash can prevent its
preservation; this construction therefore does not prove no-loss capture.

The raw event itself binds only the observation edge available at that exact
point:

- attempt-session ID and monotonic journal sequence;
- the already-bound process-execution/request/route identity;
- observer process and thread identities; and
- one caller-independent observed launch value.

It deliberately does not claim a validated pidfd, completed child lifecycle or
successful parent result. The later immutable join of the launch event, raw
journal and typed parent result binds the observed edge to the result's child,
lease, pidfd-supervised lifecycle and full request/route identity. If that join
cannot be made, the launch remains only a postlaunch-failure prefix.

Under the supported public API, only the registered runtime launch site may
mint this event. Worker text, returned counters, inferred PID changes and a
caller-provided event document have no authority.

Every additional process launch introduced inside the registered active
window—worker, compiler, verifier, fallback or pre-cutoff helper—must create its
own event in that session. A new helper may not be hidden inside an existing
launch event or treated as free work. A helper introduced after the journal
cutoff is simply outside current raw coverage; retaining the present claim
requires either moving it before closure or defining a new externally observed
scope.

## Immutable prefix journal

The parent supervisor owns an append-only journal with contiguous internally
allocated sequence numbers. The production wrapper explicitly closes or
preserves a prefix for the implemented typed control paths, including:

- request-identity bind failure before parent execution;
- typed parent success and typed parent failure;
- an escaping parent exception before or after a recorded launch;
- parent-result payload-snapshot failure while the sink is active;
- post-close canonical-envelope finalization failure; and
- raw-journal materialization failure on the exercised wrapper path.

The closed journal records its terminal observation class and whether the
registered raw window reached normal closure. Missing suffix events remain
absent, never inferred zero. Cleanup performed by the parent executor before it
returns remains under the active sink; cleanup or helper work continuing after
the cutoff is outside this journal. No success/failure adapter may discard or
replace an earlier launch event.

Parent-result payload materialization for the wrapper occurs while the sink
remains active. The wrapper then closes the session in that same active
context. If the later no-launch envelope construction fails, its typed
finalization exception carries the already-closed raw-journal bytes. If
raw-journal construction itself fails on the covered path, the session is still
closed/unregistered and the typed finalization exception carries a canonical
emergency prefix with
`raw_journal_issued = false`, `closure_incomplete = true`, the write-ahead edge
lower bound and all event rows that had already materialized. That emergency
prefix explicitly disables formal vector authority and is not a raw-journal
substitute. If both raw-journal encoding and canonical emergency-prefix encoding
fail on the covered finalization path, the exception retains a nonformal tuple
of emergency raw fields. That tuple is neither canonical JSON, content-addressed
identity nor independently replayable bytes; it is only last-resort in-process
diagnostic retention.

These are in-memory exception-preservation semantics, not a durable write-ahead
log. The present implementation does not independently prove that an
interpreter abort, process kill, machine crash, native corruption or every
unexercised cleanup interleaving will emit either artifact. No such path may be
counted as covered merely because the wrapper catches `BaseException`.

For an ordinarily closed raw journal, content identity covers the ordered
canonical events, exact bound context, window-open evidence and closure reason.
Mutation, deletion, duplication, reordering, cross-attempt transplantation and
appending after freeze must fail under the supported object/API model. The
emergency raw-field snapshot has no such canonical identity or replay claim.

## Authority boundary

V0-110A produces a raw process-evidence prefix for its registered pre-bind
through parent-payload window and, when ordinary journal materialization
succeeds, same-process canonical snapshot replay. That replay proves byte and
local issuer consistency only under the cooperative raw threat model, not that
the operating system created no unobserved process. It is insufficient semantic
authority for the V6 `process.launches` leaf. In particular, the current
implementation does not provide:

- an external supervisor or kernel-issued observation of every process
  creation in the complete attempt scope;
- proof that no event was lost between window open and final cleanup;
- independent crash coverage or exhaustive coverage of every success, setup
  failure, execution failure, protocol failure and cleanup-failure path; or
- complete source/loaded-code proof excluding unregistered native, extension
  or helper launch sites, including post-cutoff helpers.

Therefore the strongest permitted connection state remains:

```text
process.launches = VERIFIED_ATTEMPT_WINDOW_RAW_SCOPE_INCOMPLETE
```

It must not be serialized as `CONNECTED_EXACT`, an eligible shared-resource
resolution, a receipt or a `CounterRecord`. A numeric raw count may be retained
for diagnosis, but it cannot enter a formal WorkVector or ComparisonVector.
Future exact promotion requires external isolation and supervisor/kernel
attestation independently tied to the attempt identity, spanning the intended
publication/cleanup cutoff and proving both no-loss event coverage and complete
failure/cleanup-path coverage. Replaying the current canonical journal—or the
noncanonical emergency raw fields—even with an exhaustive source inventory, is
not sufficient by itself.

## Memory-path continuation

V0-109's child-cgroup `memory.peak` remains exact only for the child-runtime
window and cannot cover parent replay, preparation, publication or cleanup.
A later contract may close attempt-wide peak semantics by either:

1. placing the complete attempt inside one delegated exclusive parent scope,
   resetting its hierarchical `memory.peak` before request replay and reading
   it only after all descendants and cleanup are closed; or
2. freezing and enforcing a sound attempt-wide working-memory bound whose
   scope includes the parent and every child/helper.

Neither route requires converting the existing parent work into a fresh worker.
Process isolation may be used only when independently justified; it is not a
prerequisite invented for accounting convenience. Conversely, if a future
design does launch a worker, that launch must remain explicit in the unified
process journal and within the measured hierarchy or enforced bound. It may not
be hidden to improve either process or memory accounting.

This contract freezes only those two admissible future directions. It does
not select one, assert that the current delegated scope has the required
hierarchical ownership, or upgrade `memory.working_bytes_peak`.

## Acceptance tests for implementation

Implementation of V0-110A must demonstrate:

1. the original production executor and atomic-runtime call sites are pinned
   once at module import/finalization; ordinary public-symbol rebinding, foreign
   callers and repeat registration do not acquire their accepted roles;
2. the registered production wrapper opens the session and activates the sink
   before request replay/identity binding;
3. the write-ahead launch edge reaches the receiver immediately in the positive
   parent branch, before pidfd validation and any fallible post-clone work, and
   normal materialization yields exactly one raw event;
4. the write-ahead lower bound advances before provenance and event
   timestamp/hash/byte materialization, and injected materialization failure
   closes a nonformal `PROTOCOL_FAILURE` prefix without reverting to zero;
5. pre-clone failure records zero observed launches without inferring other
   missing work as zero;
6. covered post-clone setup, execution, replay and parent-result payload-freeze
   failures retain the write-ahead lower bound and any already materialized
   launch event;
7. the exercised wrapper/type paths—identity-bind failure, typed parent result,
   escaping parent exception, payload-freeze failure, envelope-finalization
   failure, journal-materialization failure and dual encoding failure—retain a
   closed raw journal, explicitly nonformal emergency prefix, or noncanonical
   raw-field snapshot as applicable;
8. the parent-result payload freezes and the journal closes while the sink is
   active; the post-cutoff envelope is only a no-launch canonical join and does
   not claim complete publication coverage;
9. sequence deletion, duplication, reordering and cross-attempt transplantation
   fail closed;
10. caller-minted counts/events and shallow cached-ID mutation fail closed;
11. a future injected helper launch inside the active window either produces a
   second event or causes protocol failure; and
12. the event/journal/result join binds successful pidfd lifecycle and route
   identity without retroactively altering the earlier raw event; and
13. all formal/official locks remain false after both success and failure tests.

Items above are wrapper/type-path acceptance tests, not independent proof of
every exception, cleanup interleaving or crash path. Crash persistence, no-loss
observation and exhaustive success/failure/cleanup coverage remain out of scope
until external isolation and supervisor/kernel attestation establish them.
Arbitrary same-process underscore/global mutation and `object.__setattr__` are
also outside these raw acceptance tests and must not be presented as resisted
security attacks.

## Locked conclusions

Until external isolation and supervisor/kernel attestation prove no lost
process events and complete success/failure/cleanup-path coverage:

- `process.launches` is not `CONNECTED_EXACT`;
- `memory.working_bytes_peak` remains child-window incomplete;
- the other seven shared-resource paths remain unconnected;
- all-nine shared-resource semantic closure remains false;
- no shared-resource receipt set, `CounterRecord`, `WorkVector`,
  `ComparisonVector` or projection proof exists;
- no attempt terminal, plan/infeasibility certificate or scientific endpoint
  is authorized; and
- official execution, counter-completeness, economics, science and certificate
  Gates remain false, locked or `NOT_RUN`.
