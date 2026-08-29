# V180r12r4r5 ordinal10 pre-campaign failure

This directory retains the seven canonical artifacts emitted by the consumed
ordinal10 measurement identity on `jtl110gpu2`.

Ordinal10 successfully materialized all 24 required source roots with full
source conformance, entered the production transient systemd service, and
completed the T1 service-ownership observation.  The source-bound child then
failed its final pre-ATTEMPT revalidation with the generic exception
`pre-attempt cgroup or runtime capability fact drifted`.  No scientific
campaign ATTEMPT, event, output, terminal, verification, CounterRecord,
WorkVector, ComparisonVector, or execution gate result was produced.

The runtime failure artifact does not contain the reobserved cgroup/runtime
property snapshots, per-field mismatch rows, or a dimension identifying
cgroup versus runtime capability drift.  Later Delegate diagnostics are not
part of these ordinal10 runtime artifacts and must not be presented as if they
were.  A successor must record the paired expected/observed snapshots and the
exact mismatch cause before attempting a fresh identity.

Raw artifacts:

- `raw/external_root.json`
- `raw/prelaunch/materialization_terminal.json`
- `raw/prelaunch/launch_manifest.json`
- `raw/prelaunch/outer_service_attempt.json`
- `raw/prelaunch/inner_launch_attempt.json`
- `raw/outer_service_failure.json`
- `raw/inner_launch_failure.json`

Ordinal10 is consumed and must not be rerun.
