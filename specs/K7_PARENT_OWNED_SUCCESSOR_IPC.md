# K7 parent-owned successor IPC admission

Status: contract `1.95.0` structural prelaunch boundary; executor absent.

## Frozen identity graph

The successor profile binds the exact accounted-sealed K7 route profile and
the V0-102 OS-admission profile. Its bootstrap path is fixed, and its digest and
byte count are derived from exactly one matching entry in the sealed source
snapshot. The caller cannot supply bootstrap bytes, a digest or an alternate
program entry.

Each request binds the complete route identity graph, the full trusted signer
registry document, opaque-environment and sealed-secret commitments, session
identity, one request nonce, scientific occurrence and schedule, and an exact
mapping from that scientific occurrence to the Phase-3E logical occurrence.
Canonical-byte replay rejects missing, added or crossed identities.

## Future launched protocol

A future admitted execution must produce exactly two ordered semantic roles:

1. `CHILD_OWNED_K7_BUSINESS`
2. `PARENT_OWNED_ACCOUNTING_SUFFIX`

The child cannot claim cutoff, process reap, descendant exclusion, final
cgroup peak or the accounting suffix. Those belong to the parent supervisor.
This contract freezes the role boundary only; it produces neither frame.

## Current blocked result

The V0-102 probe currently returns `NOT_AVAILABLE`. Contract `1.95.0` converts
that evidence only into a route-bound structural prelaunch blocked result. It
records zero successor executor launches, zero child frames and zero parent
frames. It issues no attempt terminal and no noncertificate closure.

## Remaining runtime Gate

The next implementation must consume a real delegated-parent descriptor,
construct and validate an exclusive cgroup-v2 attempt leaf, enforce the
one-child/depth/descendant limits, atomically create the child in that leaf with
a pidfd, run the sealed bootstrap and subprocess-free signer loader, own cutoff
and reap, prove the leaf empty, read the final peak, emit the parent suffix and
atomically commit wrapper-complete output.

The request nonce also needs a supervisor-owned consumption ledger. Independent
source and lifecycle replay must then close the nine shared-resource values.
Until those conditions and the remaining `71 + 114 + 8` obligations close,
no CounterRecord, WorkVector, ComparisonVector or projection proof is allowed.
