# Exact and Parallel Test Execution

## Scope

This document governs repository test execution only. It does not change any
planner, simulator, sample count, confidence statement, artifact schema, or
research claim.

The current V0-067 collection contains 1,516 pytest cases in 123 test
modules. These are not 1,516 independent research Gates: many cases are
attacks and replay checks for the same frozen Gate.

## Formal fresh lane

The release-authoritative command remains:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider
```

It recomputes every content-ID property access. The parallel runner can
execute the same semantics with fresh IDs:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py --fresh-ids -j 4 tests
```

No persistent result cache participates in either command.

## Exact development lane

The default parallel runner starts one pytest process per module and enables
`tests.acfqp_exact_id_cache_v1`. The plugin memoizes only a successful
content-ID property evaluation on the identical frozen Python object:

```text
same object identity
+ same immutable fields
+ same production property implementation
→ return the already computed identical string ID
```

It does not memoize planner calls, kernel transitions, observations, policy
search, audit outcomes, exceptions, or values across distinct objects or
processes. Every test is still collected and executed.

The cache is restricted to an explicit module allowlist. If a collected test
module contains an in-place frozen-object mutation attack, the plugin keeps
all content-ID evaluations fresh for that module. `functools.wraps` preserves
the original property source and signature for implementation-authority
inspection.

Golden content IDs in the historical tests provide end-to-end equality
checks. For example, the formerly slow V0-047 fixture retains exact result ID:

```text
9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42
```

The development command is:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py -j 4 tests
```

## Multi-node sharding

`--shard-count` and `--shard-index` deterministically assign whole test
modules by longest-predicted-processing-time greedy balancing. A six-node
run uses one command per node:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py \
  -j 24 --shard-count 6 --shard-index 0 tests
```

The remaining nodes use shard indices 1 through 5. No test case is split or
weakened. Each module belongs to exactly one shard.

Tests requiring bubblewrap remain on a compatible local isolation lane when
the CPU nodes do not provide bubblewrap. The final Gate is the exact union of
the six compute shards and the local isolation modules, checked against
pytest collection so that missing or duplicate modules cannot be hidden.

## Current measured validation

V0-067 adds eight focused modules and 102 cases. All focused cases pass:

```text
sequential/meta/anytime/direct authorities = 73 / 73
authority-lane wall                         = 76.0 s
factorial Gate unit                         = 23 / 23
factorial Gate unit wall                    = 1.83 s
real campaign and semantic replay           = 6 / 6
real campaign pytest wall                   = 573.47 s
/usr/bin/time real                          = 574.03 s
final V2 identity-snapshot replay            = 6 / 6
final V2 replay wall (contended lane)        = 956.00 s
focused module/case union                   = 8 / 8, 102 / 102
runtime-cap migration targeted lane         = 10 / 10
runtime-cap migration wall                  = 93.78 s
```

The stable direct real-campaign construction plus semantic replay, without
the surrounding pytest attack cases, took `446.651898258` seconds and
reproduced campaign
`8074ae6583b85b9b69ce94aac35f64d1d96afcd51133383d3c9351228f6f1e5a`
and verification
`e6d7be5ef451ab6bc5d711080cc5c132d1d7f51bc07798dc5c0c3fbbca66cc5a`.

V0-067 expands the cache-filtered `src/acfqp` source selection to
`8,703,902` bytes, beyond the historical 8 MiB sealed-runtime cap. The
active sealed-runtime manifest and isolated-fallback source caps therefore
use the registered 16 MiB V2 profile. Historical V1 manifests remain
parseable, but their route uppers are stale under the changed cap-profile ID.
The cap migration changes no test, sample, planner or certificate and does
not unlock official execution or economics.

The final V2 release collection contains `123` modules and `1,516` unique
tests. The parallel release lane executed every module except the separately
isolated real campaign and reported `1,503` passes plus seven Phase-3B errors
after its producer and verifier observed different specification hashes
during the final documentation write. On the frozen final tree, the complete
Phase-3B module then passed `17/17` in `74.88` seconds. The separately isolated
final campaign passed `6/6`. Thus every one of the `1,516` collected tests
passes on the final content snapshot; the split replay is retained instead
of misreporting the transient hash-race run as one clean monolithic process.

## Historical V0-066 measured validation

The V0-066 2026-07-28 validation used the exact single-process fresh lane for
all new tests and the unchanged 24-worker exact development lane for the full
repository:

```text
V0-066 fresh focused tests             = 62 / 62
V0-066 fresh focused elapsed           = 232.27 s
full repository modules                = 115 / 115
full repository tests                  = 1412 / 1412
full parallel elapsed                  = 361.5 s
failed modules                         = 0
```

The development-lane memoization returns only the identical content ID for
the same frozen object and does not alter a sample, fraction, planner,
certificate, fallback or attack. Mutation-attack modules remain fresh, and
all 62 newly added tests were separately run without the memoization plugin.

## Historical V0-061 measured validation

The V0-061 2026-07-27 validation used node001–node006, each with 24 module workers:

```text
cluster-compatible critical path       = 208.1 s
local isolation pass (94 cases)        = 129.9 s
post-bytecode-clean rerun (10 cases)   = 98.1 s
covered modules                        = 104 / 104
covered tests                          = 1273 / 1273
final nonpassing modules               = 0
```

The extra local rerun was caused solely by generated `src/**/__pycache__`
bytes exceeding the preregistered 8 MiB sealed-runtime cap. Removing those
generated bytecode directories restored the frozen source tree to 7,176,533
bytes and all ten affected tests passed. Test commands therefore set
`PYTHONDONTWRITEBYTECODE=1`; generated bytecode is never part of a valid
runtime-tree artifact.

Representative exact-memoization improvements were:

```text
V0-047 multistep module         458.5 s → 45.9 s
V0-049 held-out family         1002.4 s → 148.5 s
V0-057 interleaved epoch        745.8 s → 167.6 s
full six-node critical path   16–19 min → 208.1 s
```

These are test-harness runtime improvements only. The formal fresh lane
remains mandatory before a release or a new frozen research claim.

The V0-062 validation added one module and 13 cases. Its focused lane passed
in 89.49 seconds and its fresh-ID lane passed in 87.5 seconds. The complete
collection is now:

```text
ordinary compatible lane       = 95 modules / 1192 cases / all pass
isolation-compatible lane      = 10 modules /   95 cases / all pass
module/case union              = 105 / 105, 1287 / 1287
V0-062 fresh-ID focused lane   = 13 / 13
single 24-worker full lane     = 456.9 s / all pass
```

The ten isolation modules fail inside the Codex filesystem sandbox only
because bubblewrap cannot create a `NETLINK_ROUTE` socket there. The same
unchanged modules pass in the approved namespace-capable execution layer.
The final 24-worker run executed all 105 modules together and passed all
1,287 cases in 456.9 seconds.

Concurrent nested workers can create live `src/**/__pycache__` files even
when the parent pytest process disables bytecode. Runtime-tree snapshot
selection therefore canonically omits `__pycache__`, `.pyc`, and `.pyo`
products. Only source selection has this filter: the materialized CAS tree
and private execution lease still use exact-file-set verification, and an
extra cache file injected after snapshotting remains an integrity failure.
This removes a test-order race without increasing the frozen 8 MiB cap or
weakening runtime verification.

The V0-063 validation adds one module and 13 cases. Its standard lane passes
in 47.1 seconds and its fresh-ID lane passes in 46.9 seconds:

```text
ordinary compatible lane       = 96 modules / 1205 cases
isolation-compatible lane      = 10 modules /   95 cases
module/case collection         = 106 / 106, 1300 / 1300
V0-063 standard focused lane   = 13 / 13
V0-063 fresh-ID focused lane   = 13 / 13
single 24-worker full lane     = 266.9 s / 1300 passed
```

The V0-063 module independently replays the complete V0-061 target/direct
control in addition to its sequential source trace. The namespace-capable
106-module lane passes all 1,300 cases in 266.9 seconds with no nonpassing
module.
