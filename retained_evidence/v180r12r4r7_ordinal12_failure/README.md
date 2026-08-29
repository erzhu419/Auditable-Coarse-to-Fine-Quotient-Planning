# V180r12r4r7 ordinal12 pre-child socket-capability failure

This directory retains the twelve canonical `0400` artifacts emitted by the
consumed ordinal12 measurement identity on `jtl110gpu2`, plus one explicitly
labelled post-failure read-only diagnostic.  The formal artifacts under
`raw/` are exact byte copies of the remote files; the diagnostic does not
retroactively become a campaign event, CounterRecord, or preregistered host
fact.

Ordinal12 materialized 26 source roots with full source conformance.  Its
pre-ATTEMPT host artifact was also fully conformant for the fields that the
ordinal12 contract compared: `full_host_conformance` is `true`,
`mismatch_count` is zero, `mismatch_rows` is empty, and `cause` is `null`.
T1 then joined the expected systemd service and completed before child
creation.

The campaign failed in `SOCKET_BUFFER_CONFIGURATION`, before T2 was created.
The frozen frame cap is 1,048,576 bytes and each seqpacket send and receive
buffer must report an effective minimum of 2,097,152 bytes.  The host's
`net.core.rmem_max` and `net.core.wmem_max` were each 212,992 bytes; a fresh
read-only socket probe observed only 425,984 bytes for `SO_RCVBUF` and
`SO_SNDBUF` on both endpoints.  The diagnostic records all six comparisons,
their expected minima, their observed values, and the exact cause.  This is a
missing ordinal12 pre-attempt capability field, not an out-of-memory failure:
the formal failure recorded a 262,144-byte memory peak and zero OOM events.

Because the child was never created, ordinal12 did not exercise the repaired
T2-v2/T3 process-placement path.  The topology diagnostic is `null`, rather
than an empty mismatch list being misread as conformance.  Unit ownership and
full conformance remain separate facts: source conformance and host
conformance passed, T1 unit placement passed, and T2/T3 full conformance was
not reached.

Only `ATTEMPT_OPEN` and `PROCESS_BIRTH_INTENT` exist.  No CounterRecord,
WorkVector, ComparisonVector, terminal, independent replay, or scientific
effect was produced.  Counter completeness, workload economics, scalar
calibration, and break-even remain `NOT_RUN`; official execution remains
false.  Cleanup records and direct inspection both show the measurement root,
transient unit, and all related processes absent.

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

Post-failure diagnostic:

- `raw/post_failure_socket_capability_observation.json`

Ordinal12 is consumed and must not be rerun.  This freeze records an
engineering failure boundary only; it makes no claim about scientific
accuracy, effect, sample efficiency, or superiority over general reinforcement
learning.
