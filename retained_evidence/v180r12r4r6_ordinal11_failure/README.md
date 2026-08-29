# V180r12r4r6 ordinal11 T1/T2 process-role failure

This directory retains the eleven canonical artifacts emitted by the consumed
ordinal11 measurement identity on `jtl110gpu2`.  The files under `raw/` are
exact byte copies of the remote `0400` artifacts.

Ordinal11 materialized 25 source roots with full source conformance.  Its
pre-ATTEMPT host artifact is also fully conformant: `full_host_conformance` is
`true`, `mismatch_count` is zero, `mismatch_rows` is empty, and `cause` is
`null`.  The scientific ATTEMPT record and ledger event zero (`ATTEMPT_OPEN`)
were then durably written.

The campaign failed on exactly one comparison: `t2.pid` expected `528492` and
observed `528493`.  T1 and T2 nevertheless record the same formal systemd
service, source membership, service-directory device/inode/fd, cgroup
namespace, token, and unit name.  The service entry ran the retained
`launcher.py`; that launcher observed T1 before `Popen`, and its distinct
`bootstrap.py` child observed T2.  The mismatch is therefore the old contract
conflating the service-entry launcher PID with the bootstrap-child PID, not a
service-placement or membership drift.

The retained ordinal11 T2 document uses the predecessor schema
`acfqp.v180r12r4_production_runtime_placement_t2.v1` and its exact 19-field
keyset.  It must not be validated as the successor T2-v2 shape.  Ordinal11 did
not contain a T3 observation; T2-v2 and T3 belong only to the fresh successor.

Only event zero exists.  No CounterRecord, WorkVector, ComparisonVector,
terminal, independent replay, or scientific effect was produced.  The
counter-completeness, economics, scalar-calibration, and break-even gates all
remain `NOT_RUN`, and official execution remains false.  The measurement root
was created during the failed campaign prefix, then cleanup observed the root
absent at `CLEANUP` and `AFTER_CHILD`; the failure says no process may remain,
and the outer receipt confirms the transient service was collected and absent.

Raw artifacts:

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

Ordinal11 is consumed and must not be rerun.  This freeze records an engineering
failure boundary only; it makes no claim about scientific accuracy, effect,
sample efficiency, or superiority over general reinforcement learning.
