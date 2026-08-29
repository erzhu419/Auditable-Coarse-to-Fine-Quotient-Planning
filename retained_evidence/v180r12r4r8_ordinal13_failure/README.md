# V180r12r4r8 ordinal13 precompiled-source binding failure

This directory retains the thirteen canonical `0400` formal artifacts emitted
by the consumed ordinal13 measurement identity on `jtl110gpu2`, plus one
explicitly labelled post-failure typed diagnostic.  The diagnostic is derived
only from the exact manifest and the complete, untruncated child stderr.  It is
not a campaign event, CounterRecord, preregistered host fact, or scientific
result.

Ordinal13 materialized 27 source roots with full source conformance.  Its
pre-ATTEMPT host artifact is also fully conformant, including the newly bound
socket-buffer capability snapshot: `mismatch_count` is zero, `mismatch_rows`
is empty, and `cause` is null.  T1 joined the expected transient systemd
service and completed before bootstrap child creation.  T1 unit ownership is
therefore true, but that fact is kept separate from later full topology and
source-binding conformance.

The formal ledger contains exactly `ATTEMPT_OPEN`, `PROCESS_BIRTH_INTENT`, and
`PROCESS_BIRTH_OUTCOME`.  The third event records one successful OS process
birth.  The new process then rejected its sealed precompiled bundle before its
internal target could start.  The formal parent-side failure classified the
result as `INPUT_DRIFT` with `ConnectionResetError: (104, 'Connection reset by
peer')`; this is a secondary transport observation.  The exact child stderr
records the primary error:

`RuntimeError: V180r12r4 precompiled source binding changed`

The manifest binds 85 `acfqp` source modules beneath the ordinal13 repository
and 21 `packaging`/`tomli` modules beneath the sibling third-party root.  The
legacy bootstrap predicate required every absolute source path to begin with
the repository-root prefix.  All 21 manifest-bound third-party rows violate
that predicate; the first rejected row is `packaging` at source-record index
85.  The typed diagnostic preserves the relevant property snapshots and all
21 per-field prefix mismatches.  It separately records T1 unit ownership as
true, source-binding full conformance as false, and formal full cgroup topology
conformance as not recorded (`null` diagnostic).

Formal raw artifacts:

- `raw/external_root.json`
- `raw/prelaunch/materialization_terminal.json`
- `raw/prelaunch/launch_manifest.json`
- `raw/prelaunch/outer_service_attempt.json`
- `raw/prelaunch/inner_launch_attempt.json`
- `raw/outer_service_failure.json`
- `raw/inner_launch_failure.json`
- `raw/host_conformance.json`
- `raw/campaign/scientific_attempt.json`
- `raw/campaign/measurement_failure.json`
- `raw/campaign/EVENTS/000000.json`
- `raw/campaign/EVENTS/000001.json`
- `raw/campaign/EVENTS/000002.json`

Post-failure typed diagnostic:

- `raw/post_failure_precompiled_source_binding_observation.json`

Cleanup records show the measurement root, transient unit, and related
processes absent.  No CounterRecord, WorkVector, ComparisonVector, terminal,
independent replay, or scientific effect was produced.  Counter completeness,
workload economics, scalar calibration, and break-even remain `NOT_RUN`;
official execution remains false.

Ordinal13 is consumed and must not be rerun.  This freeze records an
engineering failure boundary only and makes no claim about accuracy, sample
efficiency, or superiority over general reinforcement learning.
