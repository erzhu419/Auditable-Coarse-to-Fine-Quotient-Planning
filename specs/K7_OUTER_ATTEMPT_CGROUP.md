# K7 outer attempt cgroup authority

**Milestone:** `V0-110B-1`  
**Proposed contract:** `2.0.3`  
**Profile:** `v075_k7_outer_attempt_cgroup_v1`

## Purpose

This milestone introduces the intended attempt-local cgroup-v2 hierarchy needed to measure
the complete K7 attempt rather than only the inner business child.  It is a
scope and lifecycle authority, not yet a production attempt executor or a
formal accounting bundle.

The external supervisor is measurement infrastructure and remains outside the
charged attempt.  It creates a fresh empty hierarchy:

```text
delegated root
└── A                         empty attempt domain
    ├── worker               complete parent/worker process
    └── business             fixed successor business leaf, created later
```

`A` enables the `memory` and `pids` controllers before any process enters its
subtree.  A future external broker—not the worker—must create or retain the
business sibling and launch both the worker and business process into their
respective cgroups from birth.  The worker receives no writable descriptor for
`A`.  Existing V0-107/V0-108 execution cannot be silently reused for this
topology; it needs a brokered successor or explicit refactor.  Only that later
runtime can make final hierarchical `A/memory.peak` cover worker preparation,
request replay, business execution, parent replay, final publication/output
work and attempt-owned cleanup, including simultaneous worker and child
residency.

Contract `2.0.5` selects the fixed sibling name `business`; the earlier
V0-104-style random name was illustrative and is not reused as the successor
identity.

## Frozen hierarchy

The outer attempt domain and worker leaf are new authorities; the V0-104 inner
lease is not reinterpreted or relabelled.

The outer profile freezes these controls:

| node | control | value |
|---|---|---:|
| `A` | `memory.max` | registered finite outer-attempt cap |
| `A` | `memory.swap.max` | `0` |
| `A` | `pids.max` | `2` |
| `A` | `cgroup.max.depth` | `1` |
| `A` | `cgroup.max.descendants` | `2` |
| `A` | `cgroup.subtree_control` | `memory pids` |
| `A/worker` | `pids.max` | `1` |
| `A/worker` | `cgroup.max.depth` | `0` |
| `A/worker` | `cgroup.max.descendants` | `0` |

Both directories are opened with no-follow descriptor-relative operations and
bound by filesystem, device and inode identity.  Before the worker leaf is
created, the fresh ancestor reports `memory.peak=0`; after the complete empty
hierarchy is created, both nodes are rechecked as unpopulated and empty, with
the exact one-descendant topology and frozen controls. Descendant metadata may
already have raised the ancestor peak, so this value is not an
immediate-prelaunch zero baseline. Contract `2.0.3` therefore deferred the
exact window placement. Contract `2.0.5` supersedes its proposed reset order:
the retained measurement window now begins at the descendant-free zero state
and charges later topology/session preparation. This milestone itself issues
no such successor authority.

The ancestor's `cgroup.kill` is opened with write authority during preparation,
but no cleanup guardian holds that authority after supervisor failure.  Name
and descriptor identities are compared immediately before deletion, although
Linux supplies no atomic `rmdir`-by-fd operation and this milestone has not
proved exclusive write authority over the delegated parent.  These facts keep
the hierarchy at `PREP_ONLY`; it is not safe for exact runtime consumption yet.

The count `2` is only a concurrency and containment cap.  Neither `pids.max`
nor a future `pids.peak` is a cumulative launch counter, so this milestone does
not promote `process.launches`.

## Finalization

The future shared-resource window may close only after all attempt-owned final
publication/output writes and cleanup are complete, both processes have been
reaped and the hierarchy is empty.  Finalization must verify, through the
originally bound descriptors:

1. `A` and `A/worker` are unpopulated and have zero current processes;
2. every `cgroup.procs` and `cgroup.threads` view is empty;
3. the V0-104 business child directory has already been removed;
4. `nr_descendants=1` and `nr_dying_descendants=0` before removal of the
   worker leaf, followed by zero descendants after removal;
5. every frozen controller and cap readback is unchanged; and
6. the final value comes from the ancestor `A/memory.peak`, not the maximum or
   sum of leaf peaks.

Cleanup removes only the identity-matched worker and attempt directories. Once
cleanup starts, the lease moves from `ACTIVE` to `CLEANUP_PARTIAL`; every
consumer API is then permanently disabled and only cleanup retry/state queries
remain. Identity, emptiness or descendant failures retain the remaining
descriptors so cleanup can be retried. A control mismatch is recorded as a
protocol failure but cannot prevent safe deletion of an empty identity-matched
tree and raises a typed protocol error with `cleanup_complete=true`. Failed
acquisition after inode identity capture transfers all remaining descriptors to
an unpickleable process-local cleanup guard carried by the exception. The
unavoidable `mkdir -> identity capture` gap is explicitly
`IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD` and is not locally retryable without
unsafe name trust. A production runtime therefore needs a separately bound
crash-surviving parent cleanup guardian. Caller-provided memory totals are never
accepted.

## Exactness boundary

The cgroup authority can issue an exact hierarchical peak only for a lifecycle
that a later outer runtime proves was launched into the worker leaf from birth
and fully completed before finalization.  The lease alone cannot claim that a
production K7 attempt ran.  Until that runtime joins the exact request, route,
worker output, pidfd reap and final hierarchy evidence, the production status
remains:

```text
memory.working_bytes_peak = OUTER_HIERARCHY_PREP_ONLY
process.launches          = EXTERNAL_BROKER_NOT_IMPLEMENTED
```

For an exact process SUM, the external supervisor must broker both successful
creates: the outer worker and the inner business child. Worker and business
code must be unable to call `clone`, `clone3`, `fork` or `vfork` themselves.
`ptrace` fork/clone events alone are insufficient because `CLONE_UNTRACED` and
thread/process classification otherwise leave bypasses.  Normal successful
execution will therefore cost two launches, not the old inner-runtime value
of one.

## Acceptance tests

The implementation must reject caller-minted profiles, non-cgroup2
descriptors, crossed request/admission/nonce identities, duplicate nonce use,
missing delegation, nonempty or nonzero-peak initial state, controller/cap
readback changes, inode replacement, unexpected descendants, lingering dying
descendants, early finalization and double close. Cleanup must remain retryable
after a partial removal. A real positive test must
run only inside an explicitly delegated systemd user scope; a temporary-file
fixture may test parsing and fail-closed logic but may not stand in for kernel
cgroup evidence.

## Locked claims

V0-110B-1 does not yet connect the worker runtime, process broker, output
writer or the remaining seven shared resources.  It emits no complete receipt
set, `CounterRecord`, `WorkVector`, `ComparisonVector`, projection proof,
terminal, certificate, scientific result or official authority.  The locks
remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The profile also freezes
`exclusive_parent_writer_verified=false`,
`atomic_name_to_inode_delete_verified=false`,
`guardian_cleanup_authority_bound=false`,
`launch_baseline_memory_peak_reset_verified=false`, and
`safe_for_exact_runtime_consumption=false`.
