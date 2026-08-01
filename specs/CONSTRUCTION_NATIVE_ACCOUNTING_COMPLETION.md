# Construction native-accounting completion

Status: construction contract `1.91.0`; no production or official Gate claim.

## Purpose

This contract defines the evidence boundary between the K7 owner-bound
`PARTIAL_NATIVE_ONLY` transcript and any future formal
`CounterRecord -> WorkVector -> ComparisonVector` bundle.  It does not permit
an implementation to turn an absent event into a native zero.

The exact upstream identities are the V6 counter registry, stage profile,
comparison profile and actual-projection profile, the K7 V3 operation-boundary
manifest, the V0-075 execution-identity overlay, and one terminal partial-native
transcript.

## Resolution state

Replay begins with every one of the 202 required V6 leaves in `UNRESOLVED`.
Each leaf must be resolved exactly once by one of the following mutually
exclusive evidence kinds:

1. `POSITIVE_EVENT_STREAM`: owner/code-bound unit events plus a complete
   owner/site closure for every stage in which the path could execute;
2. `SHARED_RESOURCE_RECEIPT`: a trusted resource monitor receipt for one of
   the nine shared-resource paths;
3. `PROFILE_NATIVE_ZERO`: an exact stage/branch/execution-profile exclusion,
   or an owner-local monitor that was active for the complete possible-use
   interval and observed zero;
4. `DERIVED_RECONCILIATION`: one registered exact equation whose inputs have
   already been resolved.

`UNKNOWN`, `NOT_AVAILABLE`, a missing event, a missing stage, a caller total,
an object-size estimate, or a historical custom counter is not a resolution.
Duplicate evidence and one evidence identity consumed by two paths are invalid.

## Shared-resource receipts

The shared-resource registry contains exactly:

| path | reducer | trusted owner | required measurement boundary |
|---|---|---|---|
| `common.hash_invocations` | SUM | chargeable hash facade | business SHA-256 completions, with accounting hashes suppressed |
| `common.integrity_checks` | SUM | named integrity-obligation meter | registered obligation evaluations, including failing evaluations |
| `common.protocol_checks` | SUM | named protocol-obligation meter | registered state/access-order obligation evaluations |
| `io.read_bytes` | SUM | outer I/O supervisor | actual or verified upper-bound input bytes read |
| `io.staged_bytes` | SUM | sandbox stager | bytes copied or bound into the execution sandbox |
| `io.output_bytes` | SUM | unique artifact writer | bytes committed before the frozen accounting cutoff |
| `process.launches` | SUM | process supervisor | actual child/isolated-worker launches |
| `io.mounted_bytes_peak` | MAX | sandbox supervisor | peak simultaneously visible mounted payload |
| `memory.working_bytes_peak` | MAX | worker supervisor or enforced cap | verified peak or enforced preregistered cap |

A receipt structurally binds the occurrence/route IDs, execution profile, V6
registry and stage profile, measurement window, registered monitor, method,
reducer, source claim, evidence IDs, and a unique charge key. A later
`ConstructionOccurrenceIdentityJoinV1` separately binds that receipt set to
the exact transcript and terminal chain; neither layer alone is semantic
measurement authority. A zero is valid only when the
registered monitor explicitly observed zero over the complete window.
`UNKNOWN` and `NOT_AVAILABLE` remain typed blockers and cannot carry value
zero.

The current same-process K7 wrapper cannot issue complete receipts.  In its
narrow preloaded inner body, process and staging may be conditionally zero,
but caller-supplied iterable/signer code is not sealed; mounted peak is
unknown and working peak is nonzero but unmeasured.  Therefore the current
partial transcript must fail formal finalization.

## Hash and output cutoffs

Hash accounting is non-reentrant.  Business hashes are counted by a mutable
primitive meter; hashes used to content-address the accounting records
themselves are generated only after the operational cutoff and do not feed
back into their own value.

The unique artifact writer similarly freezes an operational payload set and
byte cutoff before it writes accounting/provenance suffix objects.  Model,
epoch and capability serialized-byte fields are verifiable subsets of
`io.output_bytes`, never additional cost leaves.

A caller-provided ordered marker list proves only its own structural order.
Until an outer supervisor independently replays complete source-event and
output-byte logs, absence of post-cutoff business work and exclusion of tail
bytes remain typed `UNKNOWN`, never affirmative cutoff facts.

## Native-zero and failure closure

For a completed root-cap occurrence, the exact route reconciliation is:

```text
route.attempts  = 1
route.successes = 0
route.failures  = 1
```

Process and solver reconciliation values are derived only from their trusted
source receipts.  `CHILD_ACTION_ROW_CAP_EXCEEDED` maps to
`ATTEMPT_CLOSURE_NONCERTIFICATE / ATTEMPT_BUDGET_EXHAUSTED`; it is never an
infeasibility certificate.

On validation failure, exception, timeout, resource exhaustion, partial
write, cache-clear failure, or terminalization failure, all work observed
before the failure is retained.  Unentered suffix stages require typed
not-executed evidence; they are not silently materialized as zero.

## Formal materialization rule

Formal materialization is allowed only after independent replay has proved:

- the exact `ProfileNativeZeroRuleRegistryV1`, its 114-row readiness identity,
  and the exact `OwnerBoundaryCoverageProfileV1` are bound into the same
  occurrence prerequisite manifest;
- all 89 registered owner sites have complete loaded-code/stage/runtime-window
  closure, and their path union is exactly the registered 71-path set;
- all 202 required paths have exactly one valid resolution;
- every positive production event is unit-valued, ordered, owner/code/stage
  bound, and consumed exactly once;
- every zero has an explicit complete-window or exact-profile proof;
- all eight derived reconciliation leaves satisfy their registered equations;
- all nine shared-resource receipts are present and valid;
- the terminal identity and measurement cutoff agree;
- all 182 operational leaves project exactly once and non-operational leaves
  do not project.

The verifier then derives, in order:

```text
raw events / receipts / exclusions
    -> resolved CounterRecords
    -> occurrence WorkVector
    -> exact eight-axis ComparisonVector
    -> actual-projection proof
```

Caller-supplied record values, vectors, comparison totals, or hashes are never
authoritative.  If any prerequisite is missing, the only result is
`INCOMPLETE_EVIDENCE`; no formal vector is emitted.

## Required negative controls

At minimum, verification must reject missing or duplicated receipts; typed
unknown presented as zero; stale/cross-occurrence/cross-stage identities;
wrong owner, reducer, semantics or measurement method; reordered or non-unit
events; SUM/MAX substitution; duplicated charge keys; output-byte double
charging; launch/exit mismatch; accounting-hash recursion; post-cutoff work;
forged native zero; failure-prefix loss; and any attempt to finalize the
existing `PARTIAL_NATIVE_ONLY` transcript without the new evidence.

## Locked claims

This contract is an evidence-completion prerequisite.  Until a fresh sealed
worker and trusted outer supervisor produce a complete bundle and an
independent verifier accepts it, all of the following remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
plan_certificate = false
infeasibility_certificate = false
```
