# K7 H1 Guardian-Owned External Process Journal V1

Status: additive construction contract `2.0.59-E-C-E5B-B1`.

Profile key: `construction_k7_h1_external_process_journal_v1`.

## Exact boundary: an ordered escrow-record protocol

This slice supplies a guardian-owned, content-addressed process-record journal
that a later E5B integration may consume.  It is not an E3 V2 executor, does
not change E3 V1, and does not prove the order in which processes were born.
Its only ordered record slots are:

1. `SUPERVISOR`;
2. `PIDFD_PROBE`;
3. `BROKER`;
4. `WORKER`;
5. `BUSINESS`.

For each slot the guardian first persists `ESCROW_RECORD_INTENT_PREPARED`, then
persists an escrow-record permit.  That permit is **not** a kernel launch gate.
V1 has no post-permit PID-birth observation, so neither record order nor the
positive local fixture proves launch order or production topology.  The
`launch_identity_id` is an opaque identity join only.

The state machine nevertheless prevents a later escrow record from erasing
important lifecycle distinctions.  `PIDFD_PROBE` must have pidfd death
readiness and a creator reap report before `BROKER` may be prepared.  `WORKER`
must have the same pair before `BUSINESS` may be prepared.  This is a record
admission rule, not evidence that V1 caused any process launch.

## Two prebound creator channels

Before genesis the guardian adopts exactly two physically and semantically
distinct blocking `AF_UNIX/SOCK_SEQPACKET` receive endpoints with
`SO_PASSCRED=1`, `CLOEXEC`, stable identities, and expected UID/GID:

- `SUPERVISOR_CREATOR` carries `SUPERVISOR`, `PIDFD_PROBE`, and `BROKER`;
- `BROKER_CREATOR` carries `WORKER` and `BUSINESS`.

The `SUPERVISOR` record is a self-escrow: SCM sender PID, pidfd `Pid`, and the
sender-reported shared PID observation agree.  That PID freezes the sender for
later supervisor-channel records.  The `BROKER` receipt similarly freezes the
broker-channel sender before either role record.  SCM credentials authenticate
the packet sender; they do not independently prove that the sender created the
referenced process or that it is a sealed/authenticated supervisor.

## Exact pidfd escrow packet, opaque environmental bindings

An accepted escrow packet contains exactly one `SCM_RIGHTS` descriptor and one
kernel `SCM_CREDENTIALS` record.  Truncation, extra or malformed ancillary
records, unknown fields, noncanonical JSON, a non-`CLOEXEC` received FD, PID
reuse across slots, or a changed endpoint fails closed; every received right
is closed on rejection.

The packet and receipt bind slot, intent, permit, creator channel, opaque
launch identity, opaque cgroup identity, opaque shared-PID-cell identity,
pidfd `fdinfo` PID, sender-reported shared PID, process-start ticks, and SCM
PID/UID/GID.  The guardian rereads pidfd identity, `fdinfo` PID, `/proc` start
ticks, and endpoint identity while accepting escrow.

V1 does **not** pin a cgroup FD or verify `/proc/<pid>/cgroup` membership.  It
does **not** map or read a guardian-owned shared PID cell.  Consequently:

```text
cgroup_membership_verified = false
shared_pid_cell_guardian_read_present = false
pid_cell_untamperability_present = false
process_birth_after_permit_verified = false
```

The cgroup value is an opaque content binding and the shared PID value is a
sender observation checked for consistency with the pidfd—not environmental
membership or untamperability authority.

## ACK and creator-release ordering

The guardian persists an ACK preparation, revalidates the complete retained
journal inventory, and then sends the ACK.  Creator release has two records:

1. `CREATOR_RELEASE_PREPARED_UNSENT`, with authorization explicitly false;
2. only after the release message send succeeds,
   `CREATOR_RELEASE_SENT_AND_AUTHORIZED`.

A send failure therefore leaves a prepared-unsent record and cannot advance
the next slot.  The guardian retains its escrow pidfd until a later death/reap
record retires it or crash closure closes it.

## Death observation and creator reap are different facts

The guardian's non-consuming death observation uses pidfd `poll(POLLIN)`.  It
does not call `waitid` on a nonchild and supplies no exit status.  After the
death record is persisted, the guardian notifies the prebound creator channel.
The creator-side helper performs a real consuming `waitid(P_PID, WEXITED |
WNOHANG)` on its direct child and submits a typed report on that channel.  The
guardian joins the report to the receipt/death IDs and SCM sender PID/UID/GID.

The creator report is authenticated sender testimony plus a trusted helper
path; it is not independent guardian proof that arbitrary sender code actually
called `waitid`.  A separate optional construction test seam permits the
guardian to consume `waitid(P_PIDFD)` only for its direct `SUPERVISOR` child.
It remains explicitly outside normal guardian-reap claims.

## Retained records, fork boundary, and close quarantine

Every persisted mode-`0400` record FD remains retained through the next
persist/send freeze and final crash-closure persist.  Before each transition,
the guardian verifies the exact directory inventory, retained FD identities,
complete bytes/hashes, and final name-to-inode mappings.  File and directory
`fsync` are process-level persistence mechanics only; no power-loss or
machine-crash durability/recovery claim is made.

A process-wide at-fork barrier tracks live journals.  In the fork child it raw
closes copied directory, journal-record, receive-endpoint, escrow-pidfd, and
quarantine descriptors and poisons the copied journal.  Creator-side send
endpoints are deliberately not journal-owned and may be purposefully inherited
by a creator fixture; this exception is explicit and does not preserve any
guardian authority in the child.

Crash closure persists the exact prefix and then attempts to close guardian
copies.  Before every fallible canonical close it publishes a distinct
`F_DUPFD_CLOEXEC` witness for the same open-file description.  A non-`EBADF`
close failure enters process-local quarantine only while Linux
`kcmp(KCMP_FILE)` still proves that the canonical number and private witness
name the same OFD.  Retry repeats that proof before closing the canonical FD;
an already-closed or same-inode/same-target replacement is retired from journal
ownership and is never closed.  The private original-OFD witness is then closed
with a bounded no-nested-witness rule.  Canonical and witness descriptors share
the same fork barrier, child raw-close set, and closure quarantine lifetime.
Inode-like `fstat` identity alone is explicitly insufficient for retry
authority.  Retry never repeats protocol effects.  Closure bytes state that
descriptor close outcome and cleanup completion are unproven.  Closed record
bytes remain structural diagnostics and are explicitly not authority without a
future independent disk replayer.

## Explicit nonclaims

V1 does not claim or implement:

- real E3 V2/E5B execution integration or a real launch gate;
- process birth order or the production five-process topology;
- an authenticated/sealed supervisor or semantic creator relationship;
- cgroup membership or guardian-read shared PID authority;
- machine-crash durability, restart recovery, or PID-cell untamperability;
- complete process-window and success/failure/cleanup-path coverage;
- normal guardian reap semantics for all slots;
- `process.launches`, FQ11, `CounterRecord`, `WorkVector`, or
  `ComparisonVector` authority;
- current-access, formal V7, terminal, official execution, or scalar economics
  authority.

All such flags remain false and both economics Gates remain `NOT_RUN`.

## Focused acceptance tests

Tests cover V14 domain separation; ordered intent/permit records; distinct
creator channels; real pidfd/SCM escrow; five distinct local PID records;
probe-before-broker and worker-before-business reap gates; pidfd-poll death;
creator SCM reap reports; optional direct-child guardian wait; ACK/release
ordering; malformed/multiple rights, wrong sender, changed identity/start tick,
inventory mutation, at-fork poisoning, prepared-unsent release failure, and
identity-bound close quarantine/retry.  The local process fixture is protocol
coverage only and makes no launch-order/topology claim.
