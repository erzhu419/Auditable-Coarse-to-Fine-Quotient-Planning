# K7 H1 WAL and Tail-Bound Prefix Attestation V1

Status: construction-only component of contract `2.0.59-E-A`.

This stage closes two crash/audit gaps left by Contract `2.0.59-D`: an exact
next-record payload is now durable before the Owner pending cursor, and one
caller-pinned observed Owner tail can be bound to the verified lifecycle
prefix by a content-addressed attestation. It does not recover an admitted
normal lifecycle operation for which no dispatch event was emitted, execute
cleanup, or issue production/accounting/terminal authority.

## Mandatory pending-payload WAL

The V4 wrapper upgrades one historical Owner-V3 runtime without relabelling
any V3 artifact. Activation creates a private runtime-scoped WAL namespace and
records a zero-valued `io.read_bytes` control reservation plus its complete
cell/evidence/settlement/receipt/event/snapshot unit. The binding marker is
published only after that seven-record intent is durable. Once the intent
exists, deleting the marker or namespace cannot downgrade the runtime to V3;
trusted replay repairs an exact missing marker and rejects conflicting state.

For every later Owner append, canonical next-record bytes are linked into the
WAL and fsynced before pending cursor `P`. Replay accepts only the exact
WAL/cursor/journal/committed-cursor chain, repairs every registered crash
frontier idempotently and removes the payload only after the committed cursor
is durable. Actual subprocess `SIGKILL` controls cover WAL temporary creation,
WAL link, `P`, journal publication, committed cursor, cursor cleanup and WAL
unlink. Runtime-scoped binding-marker temporaries are also recovered.

Public initialization and four-way concurrent initialization converge to one
binding. A crash after namespace creation but before the first durable intent
leaves no monotonic activation fact: trusted replay removes that directory
only when it is exactly empty, under the Owner lock. This remains safe even if
the attempt gate later closes. A nonempty intentless namespace fails closed.
Once the intent is durable, recovery no longer requires the gate to reopen.

## Runtime semantic closure

The prefix/attestation closure binds exact loaded source bytes and live object
identity for the actual attestor, V4 replay, V3 index, dispatcher, rejection
gate, canonical-ID helpers and registered domain extension. It recursively
closes registered Python globals and closure-cell original functions, deep
projects mutable containers, binds project-type behavior namespaces including
implicit protocol methods, and explicitly binds the registered
`contextlib` generator-context-manager protocol. Mutating helpers, nested
callable registries, sentinels, descriptors, dataclass constructors,
cross-function properties, V4 replay or attestor helpers invalidates the
closure.

The closure is deliberately runtime-specific. It is not a cross-process
loaded-byte authority and does not claim completeness against arbitrary
interpreter or unregistered standard-library monkeypatching:

```text
cross_process_source_authority_present = false
hostile_stdlib_or_interpreter_monkeypatch_complete = false
```

The new domain tags live in a construction extension registry; the frozen
central Phase-3E registry remains unchanged.

## Observed-tail attestation

Issuance first verifies the exact dispatch prefix, then double-collects the V4
Owner/gate replay around an independently indexed record view. Both replay
documents must be equal, and sequence, head, charged/outstanding values,
overrun count and gate-owner join must agree with the index and the
caller-pinned tail. This rejects a gate closure or Owner append interleaved
between the observations.

The attestation binds the complete ordered record-ID chain, prefix cutoff,
extension after that cutoff, state digest, exact lifecycle/profile/runtime/WAL
and gate identities, and the last consumed event. Appending later work makes
the old artifact fail exact-current reconstruction. An explicit successor
attestation must retain the predecessor ID and exact old record prefix.

Its scope is intentionally:

```text
verification_scope = EXACT_TAIL_OBSERVED_DURING_ISSUANCE
atomic_future_consumer_lease_present = false
exact_current_use_authority_present = false
future_append_validity = false
```

It therefore proves an observed issuance window, not a lease preventing an
append after the final observation.

## Remaining blockers

Contract `2.0.59-E-A` does not provide:

- durable normal-site intent/result records or admitted no-event recovery;
- the one-way `NORMAL -> CLEANUP_ONLY` phase and cleanup-only lease;
- crash-reconciled cleanup execution and conditional absent-role skips;
- production terminal-context, output commit/readback or current-access fixed
  point authority;
- formal FQ11 cleanup/source records or
  `CounterRecord -> WorkVector -> ComparisonVector` materialization;
- V7 route authority, terminal/campaign closure or complete-bundle verification;
  or
- workload-economics or sample-efficiency evidence.

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

The next stage must journal normal-site intent before native admission can be
lost, recover a missing dispatch event without re-executing ambiguous effects,
enter cleanup-only exactly once, and execute the selected continuation through
durable step intents/results. Only those results may select the terminal output
leaf and feed the formal nine-source accounting chain.
