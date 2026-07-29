# Exact and Parallel Test Execution

## Scope

This document governs repository test execution only. It does not change any
planner, simulator, sample count, confidence statement, artifact schema, or
research claim.

The exact current case/module count is refreshed at each release Gate. These
cases are not independent research Gates: many are attacks and replay checks
for the same frozen Gate.

## Formal fresh lane

The V0-072 release-authoritative command is:

```bash
python3 scripts/run_v072_confirmatory_tests.py
```

The wrapper freezes deterministic environment settings, creates a private
temporary root, and runs the exact same test-module collection through 32
isolated module processes with `--fresh-ids --no-timing-cache`. It disables
the pytest-only content-ID property memo and does not consult historical
timings. Parallelism changes scheduling only: every module and case still
runs, every content ID is freshly recomputed, and no planner result,
observation, certificate, sample, or assertion is cached.

The equivalent inner command is:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py \
  -j 32 --fresh-ids --no-timing-cache tests
```

No persistent or cross-process result cache participates in the formal
command. The command, runner bytes, complete test tree, interpreter, and
dependency lock are content-addressed by the V0-072 execution manifest.

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

Observation-support campaigns may coordinate independent contexts in outer
threads. Every process pool created below that thread layer must use the
`spawn` multiprocessing context. Forking a multithreaded parent can deadlock
with every worker idle; changing the start method changes scheduling only,
not observations, exact arithmetic, content identities, or claim scope.

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

### V0-072 nonauthorizing-draft validation

The following focused lanes have actually completed on the current
construction tree:

```text
exact lazy planner + independent verifier + partial robust = 35 / 35, 6.38 s
source archive + preauthorization selector                 = 18 / 18, 0.50 s
later combined lock-regression lane                        = 46 / 46, 0.76 s
earlier registered/synthetic/preregistration focus         = 52 / 52, 0.69 s
post-rotation preregistration/observer/synthetic focus      = 28 / 28, 0.34 s
historical V0-068 full-campaign baseline replay            =  1 /  1, 2632.47 s
current V0-072 prerequisite focused union                  = 135 / 135, 73.54 s
manifest-readiness focused lane                            =  10 /  10, 0.22 s
real V0-068 campaign -> archive -> independent transform   =   1 /   1, 2908.13 s
public adapter + closure + confidence-row projection       =  53 /  53, 15.23 s
draft-ID/no-hidden-law identity regression                 =  62 /  62, 42.95 s
evaluation-only independent exact-ground controls          =  11 /  11, 2.44 s
```

The focused lanes overlap and must not be summed into a repository case
count. The earlier 52-case lane exercised a development fake-placeholder
path; it is retained only as historical lock-debug evidence. All eight
identities touched by that path are retired, no tape/artifact/endpoint was
persisted, and its results are not confirmatory evidence. The 28-case
post-rotation lane uses the clean draft plus the disjoint synthetic-control
API; registered target APIs remain locked.

The final real-data lane above first ran the complete same-implementation
V0-068 campaign verification, then built and replayed the production V0-072
archive, and finally ran the separately implemented V0-072 archive-transform
verifier over that exact archive. The new verifier does not claim that the
upstream V0-068 campaign verifier is an independent algorithm. The
135-case focused union additionally covers exact confidence, source
abstention, evidence-first cardinality, immutable row transcripts,
arm-free pairing, fresh promotion, generic cold H2 closure, manifest
readiness, registered-target locks, and their independent/attack replays.
The newer lanes additionally bind `96/48/96` as context-total rather than
category-subcaps, prevent public/confidence construction from rebuilding the
hidden-law manifest merely to validate the draft identity, and exercise the
separate evaluation-only exact-ground algorithm. They remain development and
lock evidence because every registered evaluation and observation entry is
still hard-locked.
None of these tests changes
`NONAUTHORIZING DRAFT / TARGET LOCKED / GATE NOT RUN`.

### V0-067 release validation

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
