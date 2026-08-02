# K7 production broker runtime

Status: construction contract `2.0.19` (`V0-110B-2E-9`).

This slice consumes the prepared outer cgroup, resource session, immutable
role-launch records and pre-exec sandbox authorities in one broker-owned,
irreversible lifecycle. It proves a real two-process/five-frame execution
prefix and emits only a typed nonformal runtime envelope.

## Joined lifecycle

Under the sole outer guardian lock, the broker:

- permanently retires the historical probe endpoints;
- consumes each prepared authority at most once;
- places worker and business directly into their fixed sibling cgroups with
  native `clone3(CLONE_INTO_CGROUP|CLONE_PIDFD)`;
- authenticates the exact frame order
  `WORKER_READY -> BUSINESS_REQUEST -> BUSINESS_RESULT -> PARENT_OUTPUT ->
  WORKER_EOF` using kernel SCM credentials, expected PID and matching pidfd;
- publicly replays the sealed business bundle before relaying it;
- directly reaps both children through `P_PIDFD` before output inspection;
- replays the worker output from a pinned inode, checks the authenticated
  byte count and digest, and promotes that inode with
  `renameat2(RENAME_NOREPLACE)` plus directory fsync;
- reads final `memory.peak` through the retained prepared OFD; and
- closes the cgroup and resource guardians only after successful cleanup.

Every success identity uses a centrally registered, role-separated content
domain. Failure cleanup retains pidfds, tree-control OFDs and resource
ownership until all known children are reaped. A nonempty failed output is
preserved and exposed through a retry authority instead of being deleted.

## Claim boundary

The runtime envelope is construction-only and nonformal. It reports native
launch/reap facts, authenticated frame observations, output replay/promotion,
same-OFD peak and cleanup completion, but it issues no shared-resource receipt,
`CounterRecord`, `WorkVector`, `ComparisonVector`, terminal or certificate.

At this contract the worker output remains a verified operational wrapper,
not yet the registered first `BUSINESS_RESULT` role of the eight-role output
fixed point. Contract `2.0.20` must adopt and post-reap-seal that exact inode,
then run all nine path-specific semantic replayers. Formal accounting remains
locked until the resulting exact resolutions are joined with every remaining
required V6 path.
