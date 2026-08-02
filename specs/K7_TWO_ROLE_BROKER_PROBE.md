# K7 two-role native broker probe

**Milestone:** `V0-110B-2C`
**Contract:** `2.0.6`
**Profile:** `v075_k7_two_role_broker_probe_v1`

## Purpose

This milestone consumes one live V0-110B-2B prepared session and exercises the
minimum real two-role process topology required by the eventual K7 route. One
single-threaded process-local broker performs the only two clone calls in the
fixed order `worker -> business`; each child is born directly into its fixed
sibling cgroup. This probe accepts two caller-supplied immutable sealed
bootstraps and assigns them positionally to worker and business; they are not
yet bound by a production role manifest. The eventual untrusted exec image
receives only its designated bootstrap inputs and socket endpoint.

It is a live launch/cleanup probe, not the production K7 worker and not formal
shared-resource evidence.

## Native role edges

The successor trampoline extends the audited V0-107 child setup path with
parent-only pointers to role-specific aligned edge and clone-result cells. On
a positive `clone3` return, the parent branch stores edge `1` and the returned
PID before returning to Python. Both cells are allocated by the outer broker
frame and outlive the launch helper. The stores precede pidfd validation,
descriptor cleanup, signal unmasking, hashing, object allocation or event
materialization.

The only valid prefixes are:

```text
worker_edge  business_edge  positive prefix
0            0              0
1            0              1
1            1              2
```

`(0,1)`, values outside `{0,1}`, rollback after a later failure and inference
from `pids.current`, `pids.max` or an empty cgroup are forbidden. Each positive
role requires a distinct positive PID and pidfd, and each pidfd must produce
one final direct-child reap.

These cells remain volatile process-local evidence. Broker death can lose the
cells and cleanup authority; without an attempt-preexisting crash-surviving
observer they cannot authorize exact `process.launches`. A surviving run may
report its native prefix only as nonformal probe evidence.

## Session and launch gate

Capability preflight may return a typed blocker without consuming any input.
After admission, the prepared session and both bootstraps are consumed once
before the first clone attempt. The guardian lifecycle lock remains held across
both launches, supervision, final same-OFD peak read and cleanup. Once this
gate closes, no retry may relaunch either role under the same session.

Before session consumption and again immediately before each role clone, the
broker requires guardian state exactly `PREPARED` and replays the frozen
descriptor/spec identities, name-to-inode bindings, cgroup-v2 mounts,
ancestor/leaf controls, enabled controllers, two-descendant topology, target
leaf emptiness and remaining endpoint identity. `CLEANUP_PARTIAL` is never an
executable state.

For the consumed invocation the broker freezes all of the following; no frame
can replace them after the launch gate closes:

- role order and ordinals;
- worker/business cgroup descriptors;
- `CLONE_INTO_CGROUP | CLONE_PIDFD | CLONE_CLEAR_SIGHAND`;
- the caller-supplied sealed executable, argv, environment and inputs;
- role socket endpoint;
- no-spawn sandbox and setup-status channel.

The worker exec image cannot inherit the business endpoint/bootstrap and vice
versa. Linux `clone3` initially copies the broker FD table into the trusted
native pre-exec child; non-role descriptors are CLOEXEC and do not enter the
untrusted exec image. This probe does not claim literal from-birth FD-table
exclusion. The executed image receives no delegated-parent/ancestor/other-leaf
descriptor, `cgroup.kill`, retained `memory.peak`, pidfd or broker/session
authority.

## Child confinement

Before executing untrusted bytes, the native child path installs parent-death
`SIGKILL`, `no_new_privs`, Landlock write denial and the registered seccomp
filter. The filter rejects native and x32 process/thread creation, including
`fork`, `vfork`, `clone` and `clone3`, plus the existing namespace, mount, IPC,
metadata and parent-control surface. A setup record distinguishes sandbox or
`execveat` failure from an executed program's exit code.

## Failure and cleanup

After any positive clone, later failure preserves the already-written prefix.
Before the first clone, the broker installs one guardian-bound cleanup
authority over the caller-owned native cells. Signals remain blocked until
those cells have been recovered into that authority. Prefix hashing and other
failure-artifact allocation occur only afterward, so neither a pending signal
nor failed materialization can erase containment/reap authority. The broker
closes the launch gate, signals every known live role by pidfd, uses ancestor
`cgroup.kill` as an independent containment path even when no known PID remains,
reaps every positive-PID direct child, proves both leaves empty and
descendant-free, reads the final peak through the retained original OFD, and
performs identity-bound monotonic tree cleanup.

An invalid pidfd does not reduce the prefix; empty cgroups, EOF and `ESRCH` are
not reap evidence. Reaped roles retire and clear their native pidfd cells, so a
later retry cannot reinterpret a reused descriptor number. The guardian keeps
the `cgroup.kill` OFD until the owned hierarchy is actually removed. Partial
cleanup carries the native prefix when materializable, the unresolved
obligation mask and the already-installed cleanup authority, and never reopens
launch. Frozen-control mismatches are reported only after safe empty-tree
deletion.

## Deliberate limits

The existing socketpair connects worker and business directly. It does not let
the broker prove which live peer authored each of the five V0-110B-2A frames,
and this probe does not execute or validate that transcript. There is no
operational output commit, complete attempt-wide publication window,
crash-persistent guardian or independent no-loss observer.
The two caller-supplied sealed programs are not registered worker/business
program identities; production must bind their digests, argv, environment and
input roles into the execution spec before launch.

Therefore all of the following remain false or unavailable:

```text
live_five_frame_sender_provenance_verified = false
broker_crash_persistence_verified = false
exact_process_launches_receipt_issued = false
complete_attempt_memory_window_verified = false
shared_resource_value_issued = false
counter_record_authorized = false
work_vector_authorized = false
comparison_vector_authorized = false
attempt_terminal_authorized = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

Contract `2.0.7` now freezes the production role plan and implements the two
role-local protocol/output cores without launching them. The next milestone
must replace the direct peer channel with broker-observable role provenance,
issue and launch a new archive/request/manifest version with present executable
wrappers, retain the worker through the committed output and final supervisor
envelope, and only then close all nine semantic shared-resource paths.
