# K7 H1 Phase-Aware Normal Prefix Pretransition V1

Status: construction-only component of contract `2.0.59-E-C-A`.

Profile key:
`construction_k7_h1_phase_aware_normal_prefix_pretransition_v1`.

## Closed scope

This profile executes only anchored lifecycle ordinals `1..40` while retaining
one ordered composite lease:

```text
PHASE EX -> REJECTION GATE EX -> NORMAL JOURNAL EX -> OWNER EX -> native callback
```

It does not call the historical dispatcher or any public Owner operation that
would reacquire the retained rejection gate. Every site contract is derived
from the frozen anchored program, handler registry and dispatch profile. The
caller supplies only the native callback required by the unique next site; it
cannot select an ordinal, path, upper, outcome or operation identity.

The positive claim is deliberately **pretransition only**. A successful
40-site prefix stops before ordinal 41. A failure or cap rejection produces a
durable poisoned prefix, but the attempt phase remains `NORMAL` and no cleanup
transition is minted. Consequently this profile is not complete normal-prefix
recovery and is not cleanup execution authority.

## Durable site protocol

Each site advances an immutable three-record grammar:

```text
intent -> optional callback result -> event
```

Intent is durable before Owner admission. For a callback site, Owner records a
native-start cell before invoking the callback, and the callback result is
durable before settlement. A native cell without a callback-result record is
closed conservatively by the implemented in-process recovery mechanics and the
callback is never run again. An existing exact callback result is settled
without replay. Deferred origins issue reservation events only; their
registered completions reuse and settle those reservations. Real process-exit
coverage for every intent/admission/callback/settlement/event boundary has not
yet been run, so the broader crash-recovery flags remain false.

The event binds the exact Owner sequence interval, before/after heads and every
new Owner record with its role and subject. Cap rejection is recovered under
the retained gate through its exact commit, Owner admission/pair and gate ACK;
the callback count remains zero. Any first non-success event poisons all later
normal dispatch.

On a dangling intent, recovery accepts only a strict prefix of that intent's
admitted, deferred-origin or rejection Owner grammar. An Owner append for any
other operation/site fails closed and cannot be absorbed into the site's event
delta.

## Journal high-water and allocation

The journal allocation binds the root, root lock, inode-bound high-water token,
attempt directory, journal lock and append cursor. Every record has a private
immutable file and an exact root hard-link seal. A separate token hard-link
frontier records the cursor sequence and cursor-record ID.

The append order is:

```text
record + root seal
-> successor high-water link + fsync(root)
-> cursor row + fsync(cursor)
-> predecessor unlink + fsync(root)
```

Replay accepts only the stable frontier or one adjacent pre/post-cursor crash
frontier. It may repair one uniquely determined staged record or one strict
torn cursor suffix. Cursor plus record/seal rollback below an intact
inode-bound frontier fails closed. Token/state replacement, foreign hard links,
allocation re-signing, gaps, duplicate records and out-of-scope ordinals fail
closed.

Initialization may reconstruct a missing genesis state only before an
allocation exists and only when the exact genesis cursor has no records or
seals. Once allocated, a missing state is rollback, not bootstrap.

These hard links provide crash consistency inside the inode-pinned private
root. They are not an external monotonic service and do not claim resistance
to any actor able to mutate or relink the bound root namespace, including a
same-UID or privileged actor that coherently removes records, seals and state
links. Such a threat requires an external monotonic witness.

## Runtime dependency and callback authority

All directly used upstream symbols are registered at import, projected into a
deterministic semantic closure and exposed to execution through an immutable
import-captured module view. The live source namespaces are rechecked before
freeze, lease acquisition and retained-lease use. Direct entrypoint
replacement and in-place registered constant drift therefore fail before new
authority is published; execution does not switch to a replacement module
attribute after the check.

The creating PID and thread alone may continue the lease. After a callback
returns or raises, PID/thread, dependency closure and retained locks are
revalidated before any callback record, settlement or event. A fork child
receives a dedicated abort and closes only inherited descriptor copies; it
cannot write the parent's journal. Foreign threads cannot consume the site,
and each lease authorizes at most one site attempt.

The callback still executes in the host interpreter. Registered namespace,
dependency-view, lease and durable-intent mutation is detected and fails
closed, but this is not an isolation boundary against arbitrary same-process
Python or interpreter/stdlib mutation. Production use continues to require the
already specified fresh-exec worker/business boundary; no hostile-callback or
production-execution claim is issued here.

Artifacts retain canonical bytes and return defensive document copies. They
are not caller-mintable or serializable authority handles.

## Claim boundary

The exact positive claims are:

- phase-aware **pretransition** execution of ordinals `1..40`;
- durable happy-path intent/callback/event ordering and exact Owner deltas;
- deterministic in-process recovery mechanics and fail-closed registered
  fault-injection controls for intent/callback/cap-rejection prefixes;
- exact Owner-delta and high-water replay for that prefix.

The following remain false or absent:

- atomic failure-event to `CLEANUP_ONLY` phase transition;
- real process-exit proof of all normal-prefix recovery boundaries;
- arbitrary same-process callback/interpreter isolation;
- complete admitted no-event recovery;
- ordinals `41..62`, cleanup journal/executor and conditional skip semantics;
- terminal output close/readback and the output/read fixed point;
- production current-access and formal V7 route authority;
- formal `CounterRecord -> WorkVector -> ComparisonVector` issuance;
- terminal/campaign closure and complete-bundle verification;
- official execution, scalar break-even, economics, Counter Completeness and
  sample-efficiency Gates.

The next additive contract must bind the poisoned event to one exact cleanup
pass and perform the monotonic phase transition under the retained composite
lease before cleanup work is authorized.
