# K7 H1 Native-Capability Guardian V1

Status: additive construction contract `2.0.59-E-C-E1`.

Profile key: `construction_k7_h1_native_capability_guardian_v1`.

## Exact boundary

E1 closes one narrow gap: a durable V6 callback receipt is not itself a live
Linux kernel capability. E1 joins the exact V6 callback/result/receipt chain
to a process-local holder for a resource of declared class `OFD` or `PIDFD`.
It does not execute failed-prefix cleanup and does not grant current access.

Initialization accepts any newly opened, exact, live and pristine
phase-aware lease for the admitted attempt. It does **not** require Python
identity with the lease that created C-D. While the caller holds the registered
`PHASE -> GATE -> NORMAL` order, E1 replays and checks:

- the OPEN rejection gate and pristine normal prefix at ordinal 1;
- the stable Owner cutoff/join with no pending or incomplete pair;
- the exact V6 spec, allocation, twelve predeclared slots and genesis cursor;
- the issuer-owned C-D admission and all occurrence, attempt, decision,
transaction, phase, normal, Owner and V6 identities.

The marker ID is carried by every guarded binding and Guardian snapshot, so a
successor cutoff join need not read a private process field.

A changed gate, Owner tail, normal ordinal, V6 cursor, allocation, process or
lease mapping fails closed.

## Durable C-D replay and irreversible one-shot marker

The in-memory C-D object is insufficient. E1 opens C-D from the pinned phase
base and requires both its attempt-local primary and phase-base seal to be
regular mode-`0400` hard links with identical device/inode, `nlink == 2`,
canonical bytes and content ID. The phase base, C-D root and exact attempt
directory are pinned by file descriptor. Temp, repair and foreign entries are
rejected. E1 performs no C-D repair or publication.

Those pins remain open through Guardian marker publication. Before closing
them E1 rechecks every base/root/attempt/primary/seal namespace mapping plus
the primary/seal mode, link topology and byte identity.

Initialization is consumed by a durable tombstone under the phase base. The
tombstone has one attempt-local primary and one phase-base hard-link seal and
binds the Guardian spec, C-D admission, V6 spec/allocation/genesis, PID,
diagnostic native thread ID and process-start ticks. Any existing primary or
seal permanently rejects another initialization, even if all Python registries
were cleared. A crash after primary `fsync` but before seal creation burns the
attempt permanently; E1 never repairs or resumes that marker.

The publisher's return value is not marker evidence. Before entering the
process registry E1 independently reopens the marker primary and seal through
the pinned phase-base descriptor and revalidates mode `0400`, common
device/inode, `nlink == 2`, exact canonical bytes/content ID and root/attempt/
primary/seal namespace mappings. Returning the expected ID without writing the
marker therefore fails closed.

## Broker, mutex and fork contract

E1 token authority uses the strong object identity returned by
`threading.current_thread()`. Numeric Python/native thread IDs in E1 are
serialized only as diagnostics and never authorize an E1 token call.
Guardian, acquisition, pending-binding and final-binding tokens retain their
originating `Thread` object, broker PID, process-start incarnation and
unforgeable in-memory incarnation. The immutable upstream V6 bootstrap still
contains its earlier numeric `get_ident()` broker check; E1 revalidates that
input but does not claim to retroactively strengthen V6 itself.

One process-wide `RLock` atomically covers live Guardian/allocation registries,
pending descriptor tracking, OFD duplicate scans, triple reservation,
verification, rollback and test disposal. It is supplemental to the existing
storage lock order:

- no path holds the capability `RLock` while acquiring PHASE, NORMAL, Owner,
  V6 or storage-flock authority;
- V6 replay/bind completes and releases its storage locks before E1 enters the
  capability `RLock`;
- `observe` performs its pin inside the V6 callback, but no path is
  `RLock -> V6`.

Python `register_at_fork` takes the same barrier before `fork`. In the child it
closes every observed raw/adoption-temporary descriptor and every installed
master/witness/anchor triple, poisons copied handles and clears copied
registries. The parent state is unchanged. This protection applies to Python's
registered fork path; raw libc or C-extension forks that bypass Python atfork
handlers are outside E1.

## Immediate triple adoption

`observe_h1_guarded_native_present_v1` is the only present-observation entry.
Before it returns, under the process mutex, E1:

1. records the observed raw descriptor as pending;
2. creates three distinct `F_DUPFD_CLOEXEC` aliases of the same OFD;
3. retains master and witness in the live cell and retains the third anchor
   only in the process-wide registry (the anchor is not a cell field);
4. verifies CLOEXEC, `fstat` and `/proc/self/fdinfo` on all three aliases;
5. proves all three pairwise identities with Linux `kcmp(KCMP_FILE)`;
6. scans every live slot/allocation in this trusted broker process and rejects
   an already-held OFD;
7. atomically installs the cell and anchor, then closes the caller's original
   descriptor on every caller-owned adoption outcome.

The acquisition object holds the installed cell, never a raw descriptor.
Constructor/registration failure, callback exception, multiple observations,
invalid return, V6 result failure or pending-result validation failure revokes
the cell and closes the complete triple. Fork during adoption closes pending
raw and temporary aliases in the child.

Every later use rechecks the triple. Replacing master and witness with the same
different OFD still fails against the registry anchor. Unsupported, blocked or
failing `kcmp` has no inode-only fallback.

## V6 sequence and live binding token

The guarded path preserves the exact public sequence:

1. durable V6 `START`;
2. one sealed callback and immediate E1 observation;
3. durable V6 callback result;
4. the exact separately committed normal-site event;
5. durable V6 receipt or known-absence resolution;
6. process-local E1 binding.

Public `initialize`, `execute`, `bind` and `snapshot` reject immediately while
an acquisition callback is active. Only the present and absence observation
APIs are legal in that callback. The mutable callback window carries an active
bit plus process, original Thread, Guardian and one-use window incarnation;
the bit/incarnation are revoked before the ContextVar is reset. Consequently a
copied `contextvars.Context` cannot call an observe API after callback return.

`H1GuardedNativeBindingV1` is a live, nonserializable process-local token, not
a durable capability artifact. Its `document`, `status` and `binding_id`
accessors each revalidate the Guardian/incarnation/original Thread, the exact
current state binding ID and, for `PRESENT_LIVE`, the complete descriptor
triple. Poison, fork, thread crossing, state replacement or descriptor
invalidation makes every accessor reject. V6 receipt/absence documents remain
durable evidence; serialized E1 binding bytes alone confer no live authority.

States are:

- `PRESENT_LIVE`: exact V6 present receipt plus a currently verified triple;
- `ABSENT`: exact V6 known absence and no live cell;
- `UNRESOLVED`: no complete live join, including a direct V6 bypass, durable
  start/result without E1 binding, or invalidated local provenance.

## Exact claim limits and trust assumptions

For an `OFD` slot E1 proves only same-open-file-description identity supplied
by the trusted callback. For a `PIDFD` slot it additionally requires pidfd
`fdinfo` shape. It does not prove a mount path, filesystem object name, inode
meaning, child PID identity, exclusive ownership, resource liveness,
successful release or that a capability is safe to close.

Process-wide duplicate exclusion means one trusted broker process only. It is
not cross-process uniqueness. `kcmp` verification assumes trusted broker code
does not maliciously mutate the process FD table concurrently. Python private
attributes and the registry anchor are not a hostile-same-process security
boundary; resisting registry-plus-triple tampering requires a future
independent credential broker.

## Explicit nonclaims

E1 does not implement or authorize:

- cutoff cleanup tokens, cleanup action journal entries or cleanup effects;
- close, reap, mount release, memory release, output finalization/readback or
  output-owner close;
- exclusive native-resource ownership or a `released` state;
- broker-restart recovery or cross-process credential service;
- ordinals `41..62`, attempt closure or terminal classification;
- production output-leaf, execution or current-access authority;
- FQ11 `CounterRecord -> WorkVector -> ComparisonVector` issuance;
- formal V7 route authority, official execution, scalar economics or either
  locked economics Gate.

All corresponding authority flags remain false.
