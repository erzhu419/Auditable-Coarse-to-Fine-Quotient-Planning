# K7 broker resource session

**Milestone:** `V0-110B-2D-2B`

**Contract:** `2.0.9`
**Profile:** `v075_k7_broker_resource_session_v2`

## Purpose

This slice joins the executable v2 production-role manifest and its exact
worker/business launch contexts to the concrete nonsealed descriptor topology
required by the live broker. It prepares resources but launches no process,
sends no frame and issues no accounting receipt.

## Prepared topology

One process-local, single-use resource session creates:

- independent broker-to-worker and broker-to-business
  `AF_UNIX/SOCK_SEQPACKET` pairs;
- `SO_PASSCRED=1` on the two broker receive ends and disabled credentials on
  both child ends;
- one empty sealable result memfd with a business read-write description and
  distinct worker/broker read-only descriptions of the same inode; and
- one fresh deterministic-name output directory with distinct worker and
  broker directory descriptions, exposed to no business role capability.

All child capability FDs are pairwise distinct from each other and from the
four broker-owned FDs. Ordered role bundles exactly match the FD roles frozen
by the v2 bootstrap. Their content IDs serialize descriptor identities but
never raw descriptor numbers or an output path.

The session binds the exact manifest object, worker and business contexts, the
shared live IPC binding, request/route/broker-spec identities and nonce.
Equal-looking contexts built from a distinct binding object, swapped roles,
reused contexts, changed descriptors, queued packets, altered `SO_PASSCRED`,
nonempty result memfd or output contamination fail closed.

## Cleanup authority

A process-local guardian owns every prepared descriptor, a duplicate of the
output parent and the name/inode join. On close it revokes all channels and
memfd views, proves both directory views and the parent name still identify
the created empty inode, removes it, fsyncs the parent and then closes the
parent authority. Partial cleanup is exception-carried and retryable; a
forked process cannot use the guardian. The session and all role bundles are
unpickleable.

## Claim boundary

The resource session does not join an outer cgroup guardian, install a
role-specific sandbox, perform the native launches, authenticate any packet,
execute the five-frame protocol or survive a committed output. Those duties
require an explicit runtime transfer from the prepared/empty state.

It therefore authorizes no shared-resource resolution, `CounterRecord`,
`WorkVector`, `ComparisonVector`, terminal, certificate or official execution.
The next slice must add the role-specific Landlock/seccomp authority and live
PID/pidfd/SCM/reap/peak broker envelope.

## Additive runtime transfer (`2.0.15`)

`consume_for_runtime_v2()` now replays the complete prepared topology under
the guardian lock and irreversibly moves it to `RUNTIME_TRANSFERRED`. The old
session and capability bundles are then revoked. The unpickleable runtime
authority exposes fixed broker/worker/business FD roles, replays inode identity
on every access and monotonically retires the parent's child-role copies after
each independently proved clone.

Runtime cleanup never deletes a nonempty output directory. An empty directory
is unlinked while its verified FDs remain open; parent-directory fsync and FD
closure are separate monotone retry steps, so a failure after unlink does not
lose durability authority. The transfer itself still claims no launch,
protocol, output or accounting event.
