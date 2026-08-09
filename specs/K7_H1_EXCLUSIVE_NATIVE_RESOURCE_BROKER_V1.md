# K7 H1 Exclusive Native-Resource Broker V1

Status: additive construction contract `2.0.59-E-C-E3`.

Profile key: `construction_k7_h1_exclusive_native_resource_broker_v1`.

## Exact boundary

E3 supplies a new native authority; it does not widen the authority of E1 or
E2.  E1/V8 `PRESENT_LIVE` proves a process-local same-OFD triple, and E2/V9
can close that triple, but neither proves that the final legal OFD reference
was closed.  E3 therefore accepts no serialized or live V8 disposition.  Its
only success disposition is:

```text
BROKER_EXCLUSIVE_PRESENT
```

This disposition is issued only by a sealed-source fresh-exec broker that
creates ten new target resources itself, launches and exactly reaps the two
authorized roles, drains their channels, inventories its own remaining OFD
aliases and closes those aliases in the registered reverse order.

The implementation does not edit or relabel V8, V9 or any historical
artifact.  A V8 `PRESENT_LIVE` object is absent from the E3 public API.

## Registered payload topology

The provisioning order remains the V6 normal-open order:

| V6 ordinal | Role | Site |
|---:|---|---|
| 7 | WORKER | `sealed_runtime_archive` |
| 9 | WORKER | `ipc_binding_candidate` |
| 11 | WORKER | `execution_topology_profile` |
| 13 | BUSINESS | `sealed_runtime_archive` |
| 15 | BUSINESS | `business_request_candidate` |
| 17 | BUSINESS | `owned_engine_source` |
| 19 | BUSINESS | `owned_engine_authority_document` |
| 21 | BUSINESS | `kernel_replay_document` |
| 23 | BUSINESS | `query_replay_document` |
| 25 | BUSINESS | `fallback_cap_profile` |

Cleanup closes these exact resources in reverse order at ordinals `43..52`.
The three WORKER payloads and seven BUSINESS payloads are disjoint role sets.

## Source versus target authority

The caller stages ten immutable source memfds and transfers them over the
authenticated provisioning channel.  A source FD is not the target resource.
For every slot the fresh-exec broker:

1. requires one bounded regular source memfd with the complete
   `F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE` set;
2. replays its registered size and SHA-256;
3. copies the bytes into a new broker-created sealable memfd;
4. applies the complete immutable seal set;
5. opens `/proc/self/fd/<creator>` as a new read-only target OFD;
6. closes the creator's read-write OFD;
7. retains exactly one target master and one `F_DUPFD_CLOEXEC` audit anchor;
8. proves that source and target have different `(device, inode)` identities;
9. closes the broker copy of the source FD.

The supervisor may retain the source OFD.  Because E3 created a different
target inode and OFD, that retained source is not a target alias.  Importing an
already-created target OFD is not an E3 success path.

## Sealed-source fresh exec

The complete E3 module bytes are copied to a fully sealed memfd.  The broker
is launched as a distinct process with:

```text
python -I -S -B /proc/self/fd/<sealed-source-fd> ...
```

The source SHA-256, byte count and interpreter SHA-256 are frozen before
launch.  The profile ID and source-manifest ID are passed into, recorded by
and content-bound to both the session genesis and completion.  The child
rereads and checks the sealed source before accepting any payload.  The
bootstrap environment contains only `LANG`, `LC_ALL` and `TZ`.
The broker sets `PR_SET_DUMPABLE=0`, `PR_SET_NO_NEW_PRIVS=1` and requires zero
inheritable, permitted, effective and ambient capabilities.

The running interpreter is pinned by opening `/proc/self/exe`.  Its bytes are
read and hashed from that FD, its device/inode/extent are recorded in genesis,
and the same still-open FD is used for every role `execveat(AT_EMPTY_PATH)`.
There is no path-based hash-then-open step between interpreter verification
and role execution.  The supervisor also reads its interpreter manifest from
one `/proc/self/exe` FD; a launch-path race can therefore only reach a broker
whose actual image fails the child's genesis hash/identity check.

The exact post-bootstrap FD inventory is:

- standard descriptors `0,1,2`;
- one authenticated supervisor channel;
- two distinct cgroup-v2 leaf directory FDs;
- one retained read-only `/proc/self/exe` FD whose bytes were hashed and which
  is later used directly by role `execveat(AT_EMPTY_PATH)`;
- at most the CPython `mmap`-owned duplicate of the shared launch journal.

An interpreter-opened `/dev/urandom` FD is accepted only when it is CLOEXEC,
recorded and closed before `BROKER_READY`.  No arbitrary runtime FD is added
to the allowlist.  The shared launch-journal FD is bound by device, inode and
extent.

## Role clone, PIDFD and cgroup binding

The caller must supply two distinct, empty, preconfigured cgroup-v2 leaf FDs.
Each leaf must have:

```text
pids.max = 1
pids.current = 0
cgroup.max.depth = 0
cgroup.max.descendants = 0
cgroup.events populated = 0
```

An ordinary directory cannot substitute for a cgroup fixture.  E3 never
creates a synthetic positive result when delegation or `CLONE_INTO_CGROUP`
permission is unavailable.

WORKER and BUSINESS launch sequentially through one real call to:

```text
clone3(
  CLONE_PIDFD |
  CLONE_PARENT_SETTID |
  CLONE_CLEAR_SIGHAND |
  CLONE_INTO_CGROUP
)
```

`CLONE_PARENT_SETTID` writes the new PID into a supervisor-shared launch cell
as part of the kernel clone transition.  `CLONE_PIDFD` atomically publishes
the broker PIDFD.  The broker immediately transfers a duplicate PIDFD to the
supervisor as an SCM_RIGHTS escrow capability.  The supervisor requires:

```text
clone result PID
= shared parent-tid PID
= pidfd fdinfo Pid
= registered role PID
```

Each role then performs an `execveat(AT_EMPTY_PATH)` of the pinned interpreter
and a fully sealed role source.  Only standard descriptors, the one role
channel and that role's target duplicates survive exec.  The role closes its
source FD, makes every remaining nonstandard FD CLOEXEC, inventories
`/proc/self/fd`, reapplies and reads back `PR_SET_DUMPABLE=0` and
`PR_SET_NO_NEW_PRIVS=1`, and only then sends `ROLE_READY`.  The credential
attestation binds both read-back facts.  The pre-clone child applies the same
controls before exec; Linux may reset dumpability during exec, so the narrow
exec-to-bootstrap interval is not represented as a globally observable
no-duplication proof.  It is outside the registered legal transfer ledger and
success is issued only after the post-exec READY boundary is verified.

The broker binds the READY message's kernel SCM credentials to the clone PID,
pidfd PID, role, session nonce, exact post-exec FD inventory,
`/proc/<pid>/cgroup` hash and the sole PID in the registered `cgroup.procs`.
Self-reported PID or cgroup text alone is never sufficient.

## SCM policy and EOF

All authority channels are Unix `SOCK_SEQPACKET` channels with `SO_PASSCRED`.
Every received non-EOF packet must contain exactly one `SCM_CREDENTIALS`
record for the expected process.

The only registered SCM_RIGHTS transfers are:

- ten source descriptors from supervisor to broker during provisioning;
- one role pidfd from broker to supervisor immediately after each clone.

Receivers use `MSG_CMSG_CLOEXEC`.  If a packet contains a wrong count,
unknown ancillary type, truncation or any otherwise-unexpected descriptor,
all descriptors installed by `recvmsg` are closed before the packet is
rejected.

After `GO`, each role closes all payload duplicates, sends one `ROLE_CLOSED`,
half-closes and closes its channel.  The broker reads the channel through exact
EOF.  Extra packets, bytes or queued SCM_RIGHTS make the attempt fail; EOF is
not inferred from role exit alone.

## Exact reaps and ordinals 41--42

For each role, E3 waits for pidfd readiness, performs:

```text
waitid(P_PIDFD, ..., WEXITED | WNOWAIT)
waitid(P_PIDFD, ..., WEXITED)
```

and requires the same PID plus zero exit.  Closing a pidfd never substitutes
for the consume operation.  Only after the reap may the broker require the
role cgroup to become empty.

Ordinal 41 is the composite `EXACT_ROLE_REAPS_COMPLETE` event containing the
two role-reap IDs.  Ordinal 42 reads each retained leaf's `memory.peak` and
records their maximum as the peak-working-bytes interface value.  Cgroup
emptiness is additional tree evidence, not a substitute for the direct
pidfd reaps.

## Last-legal-reference close at ordinals 43--52

Both roles must be reaped, both cgroups empty, both channels drained through
EOF and the role executable/source descriptors closed before any target close.
For each registered payload, in ordinal order `43..52`, the single-threaded
broker:

1. scans every live `/proc/self/fd` entry;
2. uses Linux `kcmp(KCMP_FILE)` to find every broker FD sharing the target OFD;
3. requires the exact set `{master, anchor}`;
4. closes master;
5. repeats the scan and requires the exact singleton `{anchor}`;
6. closes anchor;
7. emits `LAST_LEGAL_REFERENCE_CLOSED`.

An injected third `dup` is therefore detected before close.  Unsupported or
denied `kcmp` has no inode-based fallback.

The claim is deliberately **last legal reference**, derived from the sealed
broker program, exact transfer ledger, role reaps, cgroup emptiness, channel
drain and broker inventory.  Linux exposes no general user-space global OFD
reference counter, so the artifact explicitly records:

```text
global_kernel_reference_count_observed = false
mount_resource_release_proven = false
```

## Native cleanup barrier

Success emits one `NativeCleanupBarrierV1` binding exactly:

```text
completed_normal_ordinals = [41, ..., 52]
normal_ordinal_41_to_52_success_events_issued = true
native_cleanup_complete = true
authority_disposition = BROKER_EXCLUSIVE_PRESENT
```

The barrier states that it is the prerequisite for output ordinal 53, but this
slice does not execute or authorize output work:

```text
output_ordinals_53_to_62_authorized = false
production_output_leaf_authority_present = false
```

## Crash and protocol failure

The supervisor temporarily becomes a Linux child subreaper before launching
the broker.  Each role's kernel-written shared PID and, when published, escrow
pidfd remain available if the broker dies.  The supervisor kills and reaps the
exact known reparented role PID and requires both role cgroups to become empty.
Broker process death closes all of its target aliases; role reap closes role
aliases.  `crash_cleanup_complete=true` additionally requires confirmed broker
termination and consume-reap through its pidfd.  A timeout, missing status or
still-live broker forces that fact to false even when both role and cgroup maps
are otherwise true.

The execution deadline and cleanup deadline are distinct.  Expiry of the
execution deadline starts one new bounded `5000 ms` cleanup window; it does not
reuse an already-expired timestamp.  The typed closure records that independent
window and may set `crash_cleanup_complete=true` only when the broker pidfd was
consume-reaped, every known role was reaped, and both role cgroups were observed
empty within that cleanup window.

Every post-launch protocol exception for which supervisor controls can be
restored closes as:

```text
ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE
broker_exclusive_present = false
normal_ordinal_41_to_52_success_events_issued = false
native_cleanup_barrier_issued = false
```

Crash cleanup facts cannot be relabelled as the normal ordinal-by-ordinal
barrier.  Before returning either success or a typed crash closure, the public
runner restores and reads back the caller's signal mask and prior subreaper
setting, then closes all source, pidfd, cgroup-duplicate, channel and journal
descriptors.  A restoration error is never swallowed: a would-be success is
converted to a noncertificate when a retry restores the controls, while a
persistent restoration failure raises fail-closed and cannot return a success
artifact.

The focused real-kernel fixture injects process death after target creation,
after WORKER pidfd escrow, after both exact reaps and during ordinal 47.  Each
injection must finish subreaper/pidfd/cgroup cleanup while retaining all
barrier and success flags as false.

## Feature-gated real kernel fixture

The positive test requires two explicitly registered delegated cgroup-v2
leaves through:

```text
ACFQP_E3_WORKER_CGROUP
ACFQP_E3_BUSINESS_CGROUP
```

Without those leaves the default suite tests a typed
`CGROUP_AUTHORITY_REQUIRED` result and skips the real positive path.  Passing
ordinary directories produces `CGROUP_AUTHORITY_INVALID`.  If the kernel
later rejects `CLONE_INTO_CGROUP`, the broker returns a noncertificate; the
test may be run only in a truly delegated fixture and never monkeypatches a
positive syscall outcome.

Missing and invalid cgroup inputs are classified first using read-only FD and
control-file checks, before thread-count or runtime capability admission.  For
valid cgroups, admission then executes real, self-cleaning capability probes:
a short-lived child exercises pidfd open, pidfd signal and both `waitid(P_PIDFD)`
observations and is always consume-reaped; the subreaper probe performs real
GET/SET calls by changing to the opposite value and then restoring and reading
back the exact prior value.  A restoration failure raises fail-closed rather
than returning unavailable with potentially leaked state.  An ordinary failed
probe returns typed unavailable before broker launch.
A failure during preparation before `Popen` is an untyped fail-closed boundary,
not a post-launch crash closure.

## Output and FQ11 interface locks

### Optional output-continuation prebinding

The public runner accepts an optional
`prebound_output_continuation_context_id`.  The only accepted caller values
are `None` or one exact lowercase 64-hex content ID.  Before broker launch,
`None` is irreversibly normalized to:

```json
{"kind":"NOT_APPLICABLE","reason":"OUTPUT_CONTINUATION_NOT_PREBOUND"}
```

The resulting exact value is encoded in a one-field canonical-JSON broker argv
input and is content-bound under the single field
`prebound_output_continuation_context_id` in session genesis,
the native cleanup barrier, completion, and any post-launch crash closure.  The
fresh-exec broker parses only canonical JSON and echoes the value; the
supervisor rejects a missing, malformed, wrong, or crossed echo before source
provisioning.  Completion verification requires exact equality across genesis,
barrier, completion, and the supervisor-held launch input.

The typed null is durable evidence that no continuation identity was bound at
launch.  A later wrapper cannot replace it in the existing artifact: doing so
changes the content ID, and recomputing only an outer ID still fails the nested
identity-equality checks.  Prebinding is identity plumbing only.  It does not
authorize or execute output work and does not create a downstream continuation
artifact or authority.

E3 emits the cleanup barrier and raw native evidence only.  It does not build
output ordinals `53..62`, resolve their output-byte fixed point, register new
FQ11 counter semantics or issue:

- `CounterRecordV1`;
- `WorkVectorV1`;
- `ComparisonVectorV1`;
- actual-projection proof;
- terminal plan/infeasibility certificate;
- official execution or economics result.

All corresponding flags remain false.  A later consumer must count every real
launch separately: one short-lived pidfd capability-probe child for each valid
admission attempt, the fresh-exec broker when admitted, and each launched
WORKER/BUSINESS role.  Repeating the public capability probe and then executing
the broker incurs two distinct probe-child launches.  The consumer must replay
E3 receipts into a registered native-receipt projection; it cannot treat OS
pidfd/cgroup/kcmp operations as MDP `kernel_transition_calls`.

## Explicit nonclaims and threat boundary

E3 does not prove:

- physical unmount or mount-namespace destruction;
- physical memory reclamation beyond cgroup peak/empty observations;
- absence of references obtained by root, `CAP_SYS_PTRACE`, kernel/eBPF code
  or an adversary outside the dumpable/no-new-privs boundary;
- exclusivity of an imported target OFD;
- correctness of arbitrary modified broker/interpreter bytes;
- recovery after the supervisor itself dies or the machine loses power;
- output closure, FQ11 completeness, scalar economics or the total project
  objective.

The sealed broker, interpreter hash, Linux kernel, cgroup delegation,
`/proc`, pidfd/waitid semantics, SCM credential delivery and `kcmp` are in the
E3 trusted computing base.
