# K7 production role and durable-output core

**Milestone:** `V0-110B-2D-1`

**Contract:** `2.0.7`
**Profiles:** `v075_k7_production_role_manifest_v1`,
`v075_k7_business_entry_core_v1`,
`v075_k7_broker_worker_entry_core_v1`

## Purpose

This construction slice removes the caller-selected executable/argv/environment/
FD-role freedom left by the V0-110B-2C probe and implements the two role-local
protocol bodies needed by the future live broker. It deliberately stops before
the two cores are launched by a production broker. The split preserves the
evidence boundary: static role identity, role-local business publication and
worker output durability can be attacked independently before any live
sender-provenance or shared-resource claim is attempted.

## Production role manifest

The issuer-owned manifest is derived only from one exact current successor
request and the exact live prepared broker session for that request. It binds:

- request, route, prepared-session and broker-execution-spec identities;
- the sealed source snapshot/archive and transport/runtime identities;
- the registered interpreter digest and byte count;
- fixed role order `WORKER -> BUSINESS` and cgroups `worker`, `business`;
- the fixed frame-author vector
  `WORKER, WORKER, BUSINESS, WORKER, WORKER`;
- fixed dispatch program, argv, base environment and runtime environment
  contract for each role;
- ordered sealed-input roles, inherited FD roles, the sole writable role FDs
  and the complete forbidden broker-control FD set.

No public manifest factory argument can select a program, cgroup, argv,
environment or FD role. Every role-binding call now replays the complete nested
request/source authority and verifies that the retained guardian is owned by
the current PID, remains `PREPARED`, still holds the exact descriptors and
still names the same cgroups. A closed, fork-stale or descriptor-substituted
session cannot yield a role binding.

The dispatch digest is explicitly separate from an entry-module source digest.
This slice binds both future module paths and records their archive-member
digest/size as null and their presence as false; it fails if either path is
silently present without the successor contract being updated. Thus the
manifest freezes a non-launchable future dispatch contract, not executable
entry provenance. The executable process entries and v2 broker runtime are not
yet materialized. Its current `python -I -S -B -c` argv is therefore a template,
not an executable sealed-archive bootstrap: it neither inserts the archive FD
into `sys.path` nor can import an intentionally absent entry. V0-110B-2D-2 must
issue a new request/source archive and a new manifest/schema that binds each
present wrapper member, digest, byte count, symbol and archive-loading
bootstrap; it must not relabel or directly materialize this 2.0.7 template.
Python-private issuer sentinels are type/construction guards,
not capabilities against hostile code in the same address space; that boundary
must come from the isolated supervisor in the successor milestone.

## Business core

The business core accepts one exact fresh-exec request replay, the existing
sealed source and lifecycle-secret descriptors, one empty non-inheritable
read-write sealable memfd, one blocking `AF_UNIX/SOCK_SEQPACKET` endpoint and
a structurally exact broker IPC binding. Binding provenance is deliberately not
claimed until the live manifest/session join exists. It:

1. calls the existing V0-106 child-business executor exactly once;
2. publicly replays the returned canonical bundle;
3. snapshots and later revalidates the complete binding, including execution
   spec and nonce, and revalidates the untouched output memfd and endpoint;
4. writes the full bundle positionally, fsyncs it and applies the complete
   immutable seal set;
5. re-reads and publicly replays the sealed bytes;
6. emits exactly one canonical `BUSINESS_RESULT(bundle_id)` packet.

The large bundle stays in the memfd; the control channel carries only its
identity. Kernel `O_NONBLOCK` is checked directly rather than inferred from the
Python socket timeout cache. Publication operates on owned CLOEXEC duplicates,
so caller `dup2` replacement cannot redirect the actual write/send. A partial
pre-seal write is truncated and fsynced back to the empty state; if cleanup is
not possible, or if failure occurs after sealing or during send, a typed
`DIRTY_UNSEALED`, `SEALED_UNANNOUNCED` or `SEND_OUTCOME_UNKNOWN` boundary error
retains the bundle, immutable binding snapshot, descriptor identities and
publication facts. The complete result DTO is frozen before send, leaving no
fallible validation after a successful atomic SEQPACKET record.

The returned emission is process-local, unpickleable and explicitly a
non-authoritative historical DTO: its stored FD numbers are not live
capabilities, the Python-private issuer sentinel is not a same-address-space
security boundary, and the core does not claim an exclusive endpoint writer.

## Worker core and operational output

The worker core accepts only a read-only view of the business-result memfd, a
dedicated output-directory descriptor, a blocking
`AF_UNIX/SOCK_SEQPACKET` endpoint, the exact request replay and binding. Its
fixed sequence is:

```text
WORKER_READY
-> BUSINESS_REQUEST(0)
-> receive sole broker-forwarded BUSINESS_RESULT and peer write-half EOF
-> verify immutable memfd and nested public business bundle
-> commit canonical pre-reap operational output
-> PARENT_OUTPUT(byte_count, sha256)
-> WORKER_EOF(true)
```

The worker verifies the endpoint from kernel `SO_DOMAIN`/`SO_TYPE`, requires a
connected blocking CLOEXEC descriptor and allows up to the frozen 30-second
protocol window for a legitimate delayed broker half-close; an extra packet is
still rejected. An empty result memfd must remain unsealed for the business
writer, while a nonempty result must carry the complete seal set.

The output filename is not caller-selectable. Commit uses a private
`openat(O_EXCL|O_NOFOLLOW)` temporary inode, full write, file fsync,
`renameat2(RENAME_NOREPLACE)`, directory fsync and descriptor-pinned inode,
length, digest and canonical replay. A pre-existing name, symlink, crossed
bundle/frame, writable worker memfd or stream socket fails closed. Failure
before rename removes only the private temporary name; failure after rename
leaves visible evidence and the directory cannot be reused.

Temporary cleanup first proves that the name still denotes the inode created by
this call; a raced pre-existing or substituted name is never unlinked. Boundary
facts are immutable and bind the original directory plus committed inode and
completed fsync/rename stages. Recovery accepts only an issuer-created
post-rename boundary in that exact directory and cannot re-attest an identical
copy elsewhere. A successful completion retains the exact operational-output
and commit-receipt objects—not only their IDs—so a process wrapper can persist
their canonical preimages.

This core receives a bare directory descriptor and therefore does not prove an
exclusive output writer or post-return name stability. Its commit receipt
attests only the locally observed atomic sequence and records both limitations
as false. The production v2 runtime must supply the missing exclusive
directory/sandbox authority.

The committed document intentionally contains only the pre-reap operational
business result. It does not contain the final memory peak, reaps, cleanup or
complete accounting vector, avoiding a publication/final-peak self-reference.
A later post-reap supervisor envelope must bind those facts.

An in-process integration control uses separate broker-worker and
broker-business SEQPACKET channels, a real shared memfd inode with distinct RW
and RO open descriptions, broker relay plus write-half close, all five strict
frames, the complete structural transcript and durable output reread. It tests
the role-core composition without relabelling threads as the future isolated
process runtime.

## Claim boundary

This milestone does not create a production run. In particular, it does not:

- replace the V0-110B-2B direct peer socket with two broker endpoints;
- launch either frozen role or authenticate a sender with kernel credentials;
- install the worker-only output Landlock policy;
- prove one broker is the exclusive endpoint/output writer;
- retain crash-surviving launch evidence;
- close the complete attempt memory/publication/cleanup window;
- issue any of the nine shared-resource semantic receipts.

Therefore no shared-resource value, `CounterRecord`, `WorkVector`,
`ComparisonVector`, projection proof, terminal, certificate, scientific result
or official execution is authorized. Scalar/break-even remain null and the
counter-completeness, workload-economics and sample-efficiency Gates remain
`NOT_RUN`.

## Successor

`V0-110B-2D-2` must add an issuer-owned v2 prepared session, a newly issued
source archive/request/role-manifest version and live broker runtime with two
broker-mediated `SOCK_SEQPACKET + SO_PASSCRED` channels, executable
archive-loading role bootstraps, PID/pidfd/SCM-credential joins, the real
five-frame state machine, worker output reread, two direct reaps, final
same-OFD peak and identity-bound empty-tree cleanup. Only after that live
envelope exists may independent nine-path semantic receipt construction begin.
