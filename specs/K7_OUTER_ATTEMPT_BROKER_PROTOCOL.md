# K7 outer-attempt broker protocol

**Milestone:** `V0-110B-2A`  
**Proposed contract:** `2.0.4`  
**Profile:** `v075_k7_outer_attempt_broker_ipc_v1`

## Purpose

This milestone freezes the successor protocol required to replace the old
worker-owned inner launch with one external, attempt-preexisting broker `O`.
It closes message roles and the future kernel/evidence obligations. It does not
yet execute the broker and therefore issues no shared-resource value.

The intended topology is:

```text
delegated parent (exclusively controlled by O)
├── O                         trusted broker/guardian; outside charged attempt
└── A                         charged attempt ancestor
    ├── worker                long-lived planning/replay/output process
    └── business              one K7 business process
```

`O` is not launched per occurrence. It is the only component allowed to call
`clone3`; worker and business are no-spawn. Existing V0-107/V0-108 artifacts
remain historical and are not relabelled as attempt-wide evidence.

## Fixed protocol

One session has exactly five ordered roles:

```text
WORKER_READY
BUSINESS_REQUEST
BUSINESS_RESULT
PARENT_OUTPUT
WORKER_EOF
```

Every frame binds the same:

- successor request ID;
- accounted route identity ID;
- broker execution-spec ID;
- session nonce;
- protocol profile ID; and
- zero-based role index.

Frames use a bounded lowercase-hex length prefix followed by strict canonical
JSON. Missing, repeated, reordered, extra, binding-mismatched or transplanted,
noncanonical, nonfinite, unknown-field and `bool`-for-integer inputs fail
closed. The transcript is immutable and content addressed only after all five
roles have closed.

The structural request can name only ordinal zero and contains no
caller-selected executable, argv, environment, cgroup, process flags, FD
number or launch count. A future live `O` may interpret it only as a request
for its already sealed business bootstrap and already bound business cgroup.

This version deliberately has no live endpoint authority. Its binding and
complete byte stream are caller-constructible values for deterministic offline
validation. Replaying the same bytes under the same expected binding in a
later verifier call is therefore accepted. The verifier proves neither which
process sent a role nor that a session nonce was minted or consumed exactly
once. Consequently, a valid transcript is never launch authority. A runtime
successor must make `O` own the session, recompute the broker execution spec,
bind each direction to the intended peer, consume the nonce and ordinal once,
and reject a second live use before any launch can be authorized.

## Future launch contract

The executable successor must satisfy all of the following before either
process resource path can become exact:

1. `O` is single-threaded across each native launch critical section and owns
   the delegated parent before `A` is created.
2. `A/worker` and `A/business` exist, are empty and are bound by directory FD,
   device and inode before launch.
3. `O` alone performs exactly one
   `clone3(CLONE_INTO_CGROUP|CLONE_PIDFD|CLONE_CLEAR_SIGHAND)` for each role.
4. A successful positive PID advances the role-specific write-ahead launch
   edge before pidfd validation or any fallible descriptor cleanup.
5. `WORKER` and `BUSINESS` role tokens are single-use. A normal run has exactly
   two successful edges; failed prefixes retain truthful counts `0`, `1` or
   `2` and never roll them back.
6. Both native trampolines install `no_new_privs`, Landlock and a seccomp filter
   denying x86-64 and x32 `clone`, `clone3`, `fork` and `vfork` before exec.
7. Neither child inherits a writable ancestor/leaf control FD, `cgroup.kill`,
   a pidfd belonging to the other child or broker launch authority.
8. `pids.max` and any peak task count are containment evidence only and never
   substitute for cumulative `process.launches`.

The existing high-level V0-107 runtime may remain the business launcher after
being placed under `O`. It cannot launch the worker: it synchronously owns and
deletes one leaf, whereas the worker must remain alive while `O` services the
business request.

## Future memory window

Linux `memory.peak` reset is tied to one open file description. The executable
successor must therefore:

1. finish topology, IPC, sealed-input and controller preparation;
2. open one `A/memory.peak` read/write handle and retain that exact open file
   description;
3. write the reset command once;
4. read the reset baseline through the same handle and compare it with
   `A/memory.current`;
5. require exact baseline zero for the exact profile—otherwise block or retain
   only an upper bound, never subtract a nonzero baseline;
6. never reopen or reset the handle during the attempt; and
7. read the final peak through that same handle only after all charged work is
   complete.

The charged window includes worker replay/planning, business execution,
business-result handling, parent suffix construction, the complete operational
output commit/fsync/rename and attempt-owned cleanup. A supervisor envelope
created by `O` after final peak is measurement/provenance work, not charged
operational output.

## Future cleanup contract

`O` must already be the cleanup guardian before the first `mkdir`. It retains
the parent, ancestor, both leaf and `cgroup.kill` descriptors plus every
published pidfd. On any failure it forbids later launches, kills/reaps known
children by pidfd, invokes ancestor `cgroup.kill` as the independent containment
path, waits for empty process/thread/populated views and zero live/dying
descendants, then performs identity-matched removal.

Partial cleanup is monotonic and retryable. A control mismatch cannot prevent
safe empty-tree deletion and must close as a typed protocol failure with
`cleanup_complete=true`. If `O` itself crashes before a separately preexisting
guardian or durable write-ahead authority is installed, that occurrence is a
noncertificate failure; this contract does not claim crash-persistent exactness.

## Current authority boundary

Contract `2.0.4` closes only an immutable typed offline IPC representation and
the future broker contract. It does not establish live sender ownership,
cross-verifier replay prevention, session-nonce consumption or broker-spec
authority; it never authorizes a launch. It also does not launch worker or
business, reset/read a real peak handle, count a process, write operational
output, close any of the nine shared-resource receipts or materialize
`CounterRecord -> WorkVector -> ComparisonVector`.

The following remain false or unavailable:

```text
broker_runtime_executed = false
process_launches_connected_exact = false
memory_working_bytes_peak_connected_exact = false
shared_resource_receipt_set_complete = false
counter_records_issued = false
work_vector_issued = false
comparison_vector_issued = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
