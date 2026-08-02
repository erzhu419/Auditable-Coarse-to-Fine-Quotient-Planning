# K7 prepared live broker session

**Milestone:** `V0-110B-2B`
**Contract:** `2.0.5`
**Profile:** `v075_k7_outer_attempt_broker_preparation_v1`

## Result

This milestone converts one active V0-110B-1 outer hierarchy into one
process-local, live broker-owned prelaunch session. The transfer is irreversible
and serialized against unused cleanup. After transfer, the old lease cannot
expose descriptors or remove the hierarchy.

The lease commits a process-local object-identity token for the exact guardian
under the same lifecycle lock. On an interrupted handoff, cleanup authority is
resolved atomically by that token: an uncommitted guardian cannot close a later
service's committed session, and only the matching committed guardian may own
transferred descriptors. A context-manager exit performs its state check under
the same lock and becomes a no-op after transfer.

The prepared topology is:

```text
delegated parent
└── A
    ├── worker
    └── business
```

The process-local preparation guardian owns descriptor identities for the
parent, `A`, both leaves, `cgroup.kill`, the retained `memory.peak` open file
description and both ends of one noninheritable socketpair. The service also
mints the session nonce and an issuer-owned execution spec that binds the exact
request, route, outer lease, topology, endpoint identities and V0-110B-2A IPC
profile. It rejects a second preparation for the same request.

No child is launched and no IPC frame is sent. Endpoint ownership by a worker
process, ordinal consumption and launch authority therefore remain false.

## Exact memory-window correction

The real delegated-cgroup test showed that creating the empty worker and
business descendants charges kernel memory to `A`. Resetting `memory.peak`
after topology preparation therefore returned the valid nonzero pair:

```text
memory.peak    = 253952
memory.current = 253952
```

Consequently, requiring a zero baseline after descendant creation is not an
implementable exact profile. Contract `2.0.5` starts the window earlier:

1. create and validate the fresh descendant-free `A`;
2. open `A/memory.peak` once with read/write authority;
3. reset and read that same open file description while both
   `memory.peak` and `memory.current` are exactly zero;
4. retain the OFD while configuring `A`, creating both leaves and preparing
   the broker session; and
5. transfer the same OFD to the future runtime for its final read.

Thus hierarchy and session preparation are charged inside the window. The
prelaunch peak may legitimately be nonzero and must dominate the contemporaneous
`memory.current`. No baseline subtraction is allowed. A later runtime must read
the final peak from this retained OFD; reopening or resetting it invalidates the
exact path.

The execution-spec descriptor mapping records only the control file's
device/inode/mode/owner identity; those bytes cannot distinguish a reopen and
do not prove per-OFD reset state. Same-OFD authority comes exclusively from the
live process-local guardian retaining and transferring the original descriptor.
It cannot be reconstructed from the execution-spec document.

## Cleanup boundary

The process-local guardian owns every descriptor after transfer. Before any
launch, it verifies empty leaves, descriptor/name identities, controls and
descendant counts, then removes `business`, `worker` and `A`. Partial removal is
monotonic and retryable. The writable `cgroup.kill` OFD remains retained until
all emptiness checks pass and the owned hierarchy is removed, so an unexpected
tree occupant cannot turn a partial cleanup into permanent authority loss. A
frozen-control mismatch is reported only after safe empty-tree deletion and
carries `cleanup_complete=true`.

If creation fails between `mkdir("business")` and inode capture, cleanup is
explicitly `IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD`; name-based deletion is not
trusted. Broker crash persistence, exclusive delegated-parent write authority
and atomic name-to-inode deletion are not proved.

## Verified scope

Unit tests cover immutable spec fields, same-request replay rejection,
concurrent preparation, nonzero/inconsistent observations, transfer/cleanup
races, stale-request cleanup, safe control-mismatch deletion and retry after a
partial removal, including preservation of tree-kill authority across a failed
emptiness check. An opt-in `systemd-run --user --scope -p Delegate=yes` test
passes on a real cgroup-v2 hierarchy and replays the retained zero-reset
path.

The current locks remain:

```text
process_launch_implemented = false
live_peer_role_ownership_verified = false
ipc_frame_sent = false
complete_attempt_memory_window_verified = false
shared_resource_value_issued = false
counter_record_authorized = false
work_vector_authorized = false
comparison_vector_authorized = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

Contract `2.0.6` implements the successor two-role native probe with
role-specific write-ahead edges, kernel no-spawn enforcement, pidfd lifecycle
and truthful `0/1/2` failed-prefix counts. It remains nonformal. The next
contract, `2.0.7`, freezes the production role plan and role-local
business/worker/output cores but does not mutate this historical prepared
session. A v2 preparation/runtime must issue a new source/request/manifest with
present archive-loading wrappers, add broker-observed live-frame provenance
and launch those new entries before any shared-resource receipt can close.
