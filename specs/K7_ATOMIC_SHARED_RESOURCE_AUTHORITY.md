# K7 atomic shared-resource authority

Contract `2.0.1` adds the first production-bound semantic connection from the
real V0-108 atomic executor to the V6 shared-resource registry. It does not
complete the nine-path accounting boundary. No path is attempt-scope
`CONNECTED_EXACT`. `memory.working_bytes_peak` is
`VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE`, `process.launches` is
`VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE`, and the remaining seven paths are
`NOT_CONNECTED`.

## Runtime-owned lifecycle evidence

The V0-107 runtime now issues an immutable lifecycle-evidence object at its
native supervisor call sites. For a successful V0-108 result the exact event
order is:

```text
PROCESS_LAUNCH
-> OUTPUT_EOF
-> PROCESS_REAP
-> CGROUP_EMPTY
-> DESCENDANT_SCAN
-> FINAL_MEMORY_PEAK
-> MEMORY_CONTROLS_VERIFIED
```

The evidence binds the lease, child PID, process-launch count, final
`memory.peak`, configured `memory.max`, EOF/reap relation, empty-cgroup result
and descendant exclusion. Its contiguous sequence numbers are allocated by
the runtime rather than accepted from a caller. The parent run result must
carry the same lease, child, counters, memory values and lifecycle booleans.

This issuer-owned object is raw lifecycle evidence, not a `CounterRecord`.
A path-specific authority must still bind it to the exact request, atomic
execution specification, route identity, source and V6 accounting metadata.

## Production nine-row registry

`V075K7ProductionSharedResourceRegistryV1` derives exactly one row for each V6
shared-resource path:

| Path | Status |
|---|---|
| `memory.working_bytes_peak` | `VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE` |
| `process.launches` | `VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE` |
| `common.hash_invocations` | `NOT_CONNECTED` |
| `common.integrity_checks` | `NOT_CONNECTED` |
| `common.protocol_checks` | `NOT_CONNECTED` |
| `io.mounted_bytes_peak` | `NOT_CONNECTED` |
| `io.output_bytes` | `NOT_CONNECTED` |
| `io.read_bytes` | `NOT_CONNECTED` |
| `io.staged_bytes` | `NOT_CONNECTED` |

The registry accepts neither caller-selected rows nor numeric totals. It binds
the exact request and parent execution spec, independently derived and verified
shared-resource identity, V6 counter registry, stage/execution profiles,
sealed parent/runtime source entries and native trampoline digest. Every row
must retain its registered operational lane, semantics owner and SUM/MAX
reducer. The registry describes connection status; numeric values are issued
only by typed resolutions derived from the runtime evidence.

## Window-local incomplete resolutions

The production verifier first strictly replays the V0-108 two-frame result and
revalidates the route/source/registry graph. It then derives two values without
accepting either from its caller:

- `memory.working_bytes_peak` equals the final cgroup-v2 `memory.peak` observed
  after reap, empty-cgroup verification and descendant scan. Its MAX semantics
  are exact for the child-runtime measurement window. That window does not
  cover all parent bootstrap, prelaunch, replay, publication and close work,
  so attempt scope is incomplete and the value is not yet eligible as a formal
  shared-resource resolution.
- `process.launches` equals the runtime-local native `clone3` launch count of
  one. Its SUM semantics and runtime-local observation are verified, but the
  complete parent attempt launch-site scope has not been independently closed.
  It is therefore not eligible as a shared-resource resolution.

The same-process runtime issuer is verified; standalone bytes-only OS replay is
not completed. In particular, the V0-108 suffix's derived in-memory output byte
count is not upgraded: `io.output_bytes` remains `NOT_CONNECTED`.

## Remaining locks

The production connection vector is exactly `0 attempt-scope exact + 1
child-runtime-window incomplete + 1 runtime-local incomplete + 7 not
connected`. Consequently:

- all-nine shared-resource verification remains false;
- no nine-row semantic receipt set exists;
- no `CounterRecord`, `WorkVector`, `ComparisonVector` or actual-projection
  proof is issued;
- the 202-required-leaf reduction remains unavailable;
- no terminal, certificate, scientific endpoint or official-execution
  authority is issued; and
- all counter-completeness, economics, science and certificate Gates remain
  locked or `NOT_RUN`.

The next Gate must create one unified attempt-scoped supervisor session, close
both the memory measurement window and process-launch scope, and connect the
seven absent hash, integrity, protocol, mount and I/O sources before formal V6
accounting can begin.

## Required verification

Acceptance requires:

- runtime-issued lifecycle ordering and request/result/lease identity replay;
- exact nine-row order, semantics IDs, owners and reducer inheritance from V6;
- exact child-runtime-window peak derivation with no caller numeric input;
- memory-peak retention as attempt-scope incomplete and ineligible;
- process-launch retention as scope-incomplete and ineligible;
- crossed request, altered source, reordered lifecycle and caller-minted
  registry/resolution attacks to fail closed; and
- the authentic delegated-systemd V0-108 integration to produce and verify the
  exact child-runtime observation while every formal and official lock remains
  false.
