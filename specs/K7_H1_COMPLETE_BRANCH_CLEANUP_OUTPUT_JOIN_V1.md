# K7 H1 Complete Branch Cleanup and Output Join V1

Status: construction-only component of contract `2.0.59-D`.

This stage closes two structural omissions after the anchored lifecycle
dispatcher: every row in the registered branch-analysis universe now has a
deterministic registered-resource cleanup continuation plan, and every
registered output serializer leaf has an exact structural projection onto the
eight lifecycle readback sites. It does not cover no-event crash/interleaving
failures, execute cleanup, or select a production terminal/output leaf.

## Exact branch universe

The complete analysis independently replays the pinned legacy branch-analysis
identity and preserves its `62` transitions, `143` declared failure edges and
`144` branches including full success. It then adds exactly ten supplemental
branches for observed overruns at mount-open ordinals
`7,9,11,13,15,17,19,21,23,25`.

Those overruns were already charged without clipping by Owner V3, but the
anchored table had no corresponding `OBSERVED_UPPER_BOUND_VIOLATION` edge. The
dispatcher therefore records the explicit non-anchored outcome:

```text
ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
```

It is a provisional protocol abort, not a newly invented transition-table
edge. The old `143`-edge identity remains unchanged. The registered analysis
universe is consequently `154` rows: `143` declared candidate failures, ten
dispatcher-emitted supplemental protocol aborts and one full success. Two of
the declared candidates remain unreachable through the construction dispatcher
and are listed explicitly rather than removed:

- memory-bind native-existence ambiguity; and
- output-finalize `PROTOCOL_FAILED`.

## Cleanup continuation derivation

Each branch folds the exact successful prefix and failed current site into a
typed registered-resource obligation frontier. The plan uses this fixed order
when the corresponding resource is actually present:

```text
resolve ambiguous native existence/callback completion
  -> reap BUSINESS then WORKER descendants
  -> settle retained memory accounting reservation
  -> reconcile and close mounts in reverse-open order
  -> settle retained output accounting reservation
```

Cap rejection never fabricates the failed current operation. An ambiguous
mount or launch is never silently treated as absent. A supplemental mount
overrun records the mount as known open because its callback returned an
observed magnitude. A failed mount close retains a reconciliation obligation.
The memory/output origins in 59C are admission-only: they create accounting
reservations but no native memory hierarchy, output stream or owner. An early
failure therefore settles those reservations conservatively without inventing
a same-OFD read, output readback/finalize or output-owner close. The
dispatcher-specific deferred completions settle memory or output reservations
even when their callback fails or overruns. Native cleanup actions can appear
only after a later live activation proves the corresponding object exists.

The primary failure is immutable. Every future cleanup error must be an
ordered secondary cause, and later safe cleanup remains required. Full success
has an empty continuation.

The content-addressed `CleanupPassV1` currently records a selected plan with:

```text
execution_status = NOT_RUN
cleanup_pass_complete = false
cleanup_execution_authority_present = false
```

This is intentional. Owner V3 can settle an existing reservation after poison,
but the attempt gate has no durable one-way `NORMAL -> CLEANUP_ONLY` phase or
cleanup-only lease for native reap, mount-close and output-close operations.
Dispatcher events are also not yet durable exactly-once records. An executable
cleanup stage must add those authorities before changing these fields.

## Append-only Owner prefix verification

The original dispatch verifier still requires the trace to end at the exact
current Owner journal tail. A separate prefix verifier now permits later Owner
records only after it:

1. replays the full current append-only journal;
2. replays the exact trace cutoff sequence and head;
3. verifies charged/outstanding values and every record-role set at that
   cutoff; and
4. applies the unchanged dispatch semantic verifier to the cutoff.

Thus later records cannot be inserted into, replace, or retroactively satisfy
the dispatch prefix. This is a synchronous read-only check, not cleanup
authorization. It emits no content-addressed attestation binding the durable
tail observed under lock, so its returned trace cannot authorize later work.

## Output role-presence join

The output join binds the anchored source/topology/output-DAG identities and
the registered serializer universe. It derives exactly:

- ten registered output contexts;
- ninety terminal leaves;
- sixteen distinct role-presence sets; and
- eight readback transitions at ordinals `53..60`.

For every leaf, each present role maps to exactly one readback site and every
absent role has an explicit typed skip. Finalize/close obligations and the
candidate leaf's effective terminal metadata are retained. The current linear
62-site dispatcher still requires every ordinal `53..60`; it has no leaf-bound
conditional skip/advance event, so it cannot execute the typed skips.

This proves only the registered role-presence/readback projection. The current
lifecycle prefix does not select a unique production terminal context for all
failures, and the callback's integer return cannot prove durable commit versus
readback failure. Therefore:

```text
output_role_presence_join_bound = true
output_terminal_context_join_complete = false
production_output_leaf_authority_present = false
```

## Python-minor-tolerant anchored cross-check

The caller-pinned Git snapshot remains the authority. The loaded candidate's
exact path and whole source bytes must match the anchored Git blob. The mutable
candidate is then structurally equality-checked, but its source-manifest and
program IDs are substituted with the anchored values for that comparison
because Python's normalized AST dump is not stable across supported minor
versions. No other program field is excluded. This permits verification on
Python 3.10 and 3.12; it does not claim cross-minor artifact-ID equality because
handler bytecode identities remain runtime-specific.

## Explicit remaining blockers

Contract `2.0.59-D` does not provide:

- a durable attempt-wide `CLEANUP_ONLY` phase or cleanup-only native lease;
- durable cleanup intent/result/snapshot records or crash reconciliation;
- recovery for admitted Owner work lost before a dispatch event is appended;
- a tail-bound prefix-verification attestation;
- output terminal-context selection or durable role-commit/readback evidence;
- conditional absent-role skip/advance semantics in the lifecycle dispatcher;
- production loaded-byte/TOCTOU hooks and OS credential binding;
- an atomic current-access plus output/read fixed point;
- formal V7 route uppers/decision;
- formal `CounterRecord -> WorkVector -> ComparisonVector` materialization;
- terminal/campaign closure or a complete bundle verifier; or
- workload-economics or sample-efficiency evidence.

Native cleanup work also lacks a frozen FQ11 accounting leaf. It must be
registered or normatively projected before Counter Completeness can run.

The lock state remains:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## Next construction boundary

The next stage must make cleanup executable: durably recover any admitted
no-event prefix, close the normal lane, issue a non-forgeable cleanup-only
lease, journal each reconciliation step, and bind existing-reservation
settlement to the selected cleanup pass. It must also emit a tail-bound prefix
attestation, select the actual output leaf before the first role readback and
implement conditional skip/advance events for absent roles. Only then
can production hooks/current-access and the joint output/read fixed point feed
formal V7 routing and native accounting artifacts.
