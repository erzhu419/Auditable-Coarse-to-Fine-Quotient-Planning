# K7 parent-owned atomic executor

Contract `2.0.0` is the first real end-to-end execution of the successor
protocol frozen by V0-103. It connects the exact V0-105 fresh-process request
replay, the V0-106 child-owned K7 business body and the V0-107 atomic
`clone3`/pidfd runtime. This is a construction integration milestone; it does
not authorize formal accounting, a terminal result, a certificate or official
execution.

## Bound execution chain

The parent owns one fixed-cap attempt and admits no caller-selected bootstrap,
input order, runtime cap or accounting suffix. It consumes one request-bound
nonce, acquires one V0-104 delegated cgroup lease, freezes a sealed interpreter
and six ordered sealed inputs, and invokes the V0-107 runtime once. The input
roles are exactly:

1. `SOURCE_ARCHIVE`;
2. `TRANSPORT_PROFILE`;
3. `LIFECYCLE_PROFILE`;
4. `SUCCESSOR_PROFILE`;
5. `SUCCESSOR_REQUEST`; and
6. `LIFECYCLE_SECRET`.

The isolated `-I -S -B -c` bootstrap verifies the executable, archive, input
descriptors, environment and private-path inode identities before importing
the child entry from the sealed source archive. Inside that process, V0-105
reconstructs the portable profile/request authorities and V0-106 executes the
registered owned K7 business path exactly once. Every loaded `acfqp` module is
checked by the sealed child to originate from the archive. This is not an
independent parent replay of the module graph and does not prove a complete
stdlib or native-extension graph.

The parent accepts the child bytes only after a successful runtime result:
setup succeeded, the child exited zero, output was not truncated, EOF preceded
reap, the final peak was read, the leased cgroup is empty, no descendant
cgroup remains, and all runtime authorities close. The parent then performs
the public portable replay of the frozen child frame. Failure at admission,
lease acquisition, preparation, runtime, child replay or finalization produces
a typed nonterminal failure object and no two-frame success output.

## Strict two-frame result

The successful in-memory protocol result contains exactly two length-delimited
canonical frames in this order:

```text
CHILD_OWNED_K7_BUSINESS
PARENT_OWNED_ACCOUNTING_SUFFIX
```

The parent suffix is rendered only after child validation and runtime
finalization. A bounded fixed-point calculation makes its
`wrapper_complete_two_frame_output_bytes` field equal the exact length of both
headers and both payloads. Strict replay requires the child payload to equal
the EOF-frozen runtime bytes and reconstructs the expected suffix from the
retained request, execution specification and runtime result. Truncation,
noncanonical lengths, role reversal, an extra frame, trailing bytes, crossed
caps or altered runtime facts fail closed.

`two_frame_output_in_memory_atomic=true` describes one immutable in-memory
result object. It is not a durable filesystem transaction or a
wrapper-complete atomic artifact writer.

## Accounting boundary

The suffix enumerates all nine registered shared-resource paths, but supplies
only three explicitly nonformal values:

- `process.launches` from the atomic runtime;
- `memory.working_bytes_peak` from the final cgroup peak; and
- `io.output_bytes` from the in-memory two-frame fixed point.

The other six paths remain `NOT_AVAILABLE`, and none of the three values is a
semantic receipt. In particular, raw runtime facts and derived byte counts are
not `CounterRecord`s. Contract `2.0.0` therefore issues no:

- shared-resource semantic verification or nine-path receipt closure;
- `CounterRecord`, `WorkVector`, `ComparisonVector` or projection proof;
- complete 202-required-leaf reduction;
- attempt terminal, plan or infeasibility certificate;
- scientific endpoint credit or official execution authority.

`official_execution_allowed=false`, and all counter-completeness, economics,
science and certificate Gates remain locked or `NOT_RUN`. The next Gate must
provide independently replayable semantic sources for all nine shared-resource
paths and then consume the remaining V6 obligations exactly once before formal
vectors can be materialized.

## Required verification

Acceptance requires:

- exact input-role/digest/profile/request binding and single-use lease/nonce
  lifecycle;
- strict child-frame replay and exact request/execution-spec cross-links;
- exact two-frame count, order, framing, fixed point and no trailing bytes;
- cleanup-preserving typed failure on every prelaunch, runtime, replay and
  finalization path;
- source/archive/descriptor/private-path crossing attacks to fail closed; and
- an opt-in real delegated-systemd integration executing the authentic owned
  K7 business once and replaying the resulting two-frame output.
