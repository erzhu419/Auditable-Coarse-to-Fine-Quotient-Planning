# K7 output, working-peak, and process raw journals

Status: construction contract `2.0.17` (`V0-110B-2E-7`).

This slice supplies the three remaining raw source families required by the
nine-path shared-resource catalogue. It does not install a semantic verifier
and does not issue a `CounterRecord`, `WorkVector`, or `ComparisonVector`.

## `io.output_bytes`

The output journal models one worker-created immutable first role followed by
seven broker-created roles after both direct children have been reaped. The
broker retains and rereads the same first-role inode (`P == P'`), permits one
exclusive suffix writer, uses no-replace durable writes, and solves the exact
eight-role byte-count fixed point before writing. Only the eight newly created
inode extents are summed; nested serialized-byte aliases are not charged twice.

The construction commit API and renderer are not production provenance. The
live broker must still bind the actual worker commit, authenticated
`PARENT_OUTPUT`, direct reaps, and the fixed production renderer before this
source can become `VERIFIED_EXACT`.

## `memory.working_bytes_peak`

One process-local recorder retains the writable `memory.peak` open-file
description and an independent duplicate witness. It resets and reads zero
before launch, then reads the same OFD after output completion, two direct
`P_PIDFD` reaps, and an empty descendant-free cgroup scan. The raw value is the
exact `MAX(pre, post)` without baseline subtraction or caller-supplied peak.
Same-inode/different-OFD replacement is rejected.

## `process.launches`

The process journal accepts only the two positive native clone write-ahead
edges (`WORKER`, `BUSINESS`) joined to live PID/pidfd identities,
kernel-authenticated SCM senders, fixed post-exec no-spawn attestations, and
actual direct `waitid(P_PIDFD, WEXITED)` reaps. A complete window derives
`SUM=2`. A failure prefix preserves only its observed positive-edge lower
bound and cannot claim an exact value.

## Identity and authority boundary

All component, event, cutoff, fixed-point, and manifest identities use
centrally registered role-separated Phase 3E domains. Raw component bytes are
independently replayable, but structural arithmetic is not source-semantic
authority. Exact nine-path resolution requires one complete production live
envelope plus the fixed path-specific semantic replayers.
