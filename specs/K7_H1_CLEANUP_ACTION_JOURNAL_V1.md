# K7 H1 Cleanup Action Journal V1

Status: additive construction contract `2.0.59-E-C-E2`.

Profile key: `construction_k7_h1_cleanup_action_journal_v1`.

## Closed boundary

E2 joins one exact committed V2 `CLEANUP_ONLY` transition to:

- the exact selected C-B branch and cleanup pass;
- one terminal V6 native-receipt cutoff for the primary failure event;
- the independently replayed V8 Guardian marker and its process-local slot
  states;
- the exact C-D selected branch and five-dimensional admitted budget; and
- C-C conservative Owner release for memory/output accounting reservations.

The join and ordered action manifest are content addressed in the disjoint V9
domain registry.  The action journal has one route-attempt allocation, immutable
intent/preobservation/result records and a chained cursor.  The allocation is
sealed by a hard link in the phase base, preventing a second child root from
creating an independent spend for the same route attempt.

This profile handles the failure-continuation obligations corresponding to the
registered ordinal-41 descendant reap, ordinal-42 retained-memory settlement
and ordinal-43..52 reverse mount-close region.  It never appends synthetic
normal-lane success events and never advances the failed normal cursor.

## Exact cutoff join

The V6/E1 join has only these positive cases:

| V6 cutoff | E1 Guardian | E2 disposition |
| --- | --- | --- |
| present receipt | exact live binding and verified triple | `PRESENT_LIVE` |
| explicit absence | exact E1 absence binding | `ABSENT_EXPLICIT` |
| future site control-flow absence | no E1 start/binding/cell | `ABSENT_CONTROL_FLOW` |

A direct V6 present or absence record without its E1 binding remains
unresolved.  A V6 unresolved row remains unresolved only when E1 also has no
binding/cell/resolved status; an E1 PRESENT/ABSENT binding beside V6 unresolved
is a contradiction and fails closed.  Contradictory live and absent states
fail closed.  No unresolved callback is replayed.

The E1 initialization marker ID used by E2 comes from the public E1 snapshot.
E2 then independently and read-only reopens both the C-D admission and E1
marker primary/seal pairs, verifies their two-link topology, canonical bytes,
content domains and public identities, and finally rechecks every pinned
directory mapping.  Deleting either durable prerequisite makes manifest freeze
fail.  E2 does not accept a private publisher return as marker authority.

## State machine and budget

```text
V2_CLEANUP_ONLY
  -> V6_CUTOFF_DURABLE
  -> E2_JOIN_AND_MANIFEST_FROZEN
  -> JOURNAL_READY(i=1)

READY(i)
  -> INTENT_DURABLE(i)       # one C-D category unit is debited here
  -> [PIDFD_PREOBS_DURABLE]
  -> EFFECT_OR_TYPED_SKIP
  -> RESULT_DURABLE(i)
  -> READY(i+1)

all selected actions visited
  -> DRAINED
  or DRAINED_WITH_UNRESOLVED_OR_PARTIAL_EFFECT
```

Each intent stores the entire five-component budget before and after its exact
unit debit.  Skipped, blocked and failed selected actions retain their debit;
an intent that was not durable consumes nothing.  Replay recomputes action
order, previous-result chaining and every component.  No category may exceed
the selected branch count or C-D availability.

C-D units are construction action-admission units.  They are not FQ11 counters
and are not the same quantity as a C-C Owner charged value.

## Action semantics

### Resolution

`RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION` records the frozen join
disposition.  It performs no callback or native syscall and does not consume a
live cell.  An unresolved resolution becomes an ordered secondary cause while
later independent cleanup continues.

### Descendant reap

`REAP_DESCENDANT` maps the cleanup target to its predeclared launch-callback
PIDFD slot.  This establishes the identity of the guarded callback slot, not
the semantic identity of a BUSINESS/WORKER executable or workload.  E2 never
counts descriptor close as process reap.  A positive result
requires:

1. a live exact PIDFD Guardian cell;
2. successful `waitid(P_PIDFD, ..., WEXITED|WNOHANG|WNOWAIT)`, which establishes
   that the target is a waitable child of this broker;
3. a durable preobservation of the exited child; and
4. consuming `waitid(P_PIDFD, ..., WEXITED|WNOHANG)` followed by closure of the
   Guardian PIDFD aliases.

An unexited child yields `PIDFD_NOT_EXITED`; E2 sends no signal and invents no
termination policy.  A non-child, externally reaped child or lost live token is
blocked or uncertain, never certified as reaped.

### Conservative Owner release

The memory and output conservative actions uniquely select the exact
outstanding deferred-origin reservation and invoke the C-C allocation,
single-spend release and combined-state verifier.  No memory read, output
readback, output finalization or output-owner close occurs.

The result embeds the exact C-C combined-state document.  Journal replay pins
the C-C root and spec directory, concurrently verifies the allocation and
release primary/seal pairs, recomputes their domain-separated IDs, and checks
the embedded combined projection against the durable release and exact E2
action.  Merely substituting another syntactically valid content ID and
rehashing the E2 result/cursor is rejected.

### Mount alias close

For `CLOSE_MOUNT`, E2 verifies the exact live OFD cell and closes the Guardian
master, witness and registry anchor.  It invalidates the old live binding and
records only:

```text
GUARDIAN_ALIAS_SET_CLOSED
underlying_ofd_last_reference_release_proven = false
mount_resource_release_proven = false
external_same_ofd_alias_absence_proven = false
```

The focused regression retains an external duplicate of the same OFD and
verifies that it remains usable after the Guardian triple is closed.  Thus the
profile cannot misrepresent alias closure as destruction of the underlying
resource.  A stronger claim requires a separately specified exclusive
resource broker or ownership capsule.

## Lock discipline

Cutoff construction uses:

```text
PHASE -> GATE -> NORMAL -> V6
release NORMAL/V6
E1 public snapshot / registry verification
PHASE -> GATE -> ACTION_ROOT -> ACTION_JOURNAL
```

Action execution uses three disjoint phases:

```text
PHASE -> GATE -> ACTION_JOURNAL   # durable intent
release ACTION_JOURNAL

Guardian registry
or PHASE -> GATE -> OWNER -> C-C SIDECAR

PHASE -> GATE -> ACTION_JOURNAL   # durable result
```

The implementation never holds ACTION while entering Owner, C-C, V6 or the
Guardian.  It never holds Guardian and V6 simultaneously.

Initialization also requires the exact live V2 cleanup lease and transition;
a stale manifest cannot create an allocation after the PHASE/GATE barrier is
released.  Journal storage is accessed through pinned directory descriptors,
`O_NOFOLLOW`, name-to-inode checks before and after reads, exact modes/link
counts and a root-lock inode frozen into the allocation.  Handle disposal is
explicit; forked children close and poison inherited pins.

## Crash and idempotence boundary

Effects cannot start before the intent cursor is durable.  Recovery recognizes
an immutable record one cursor row ahead and completes only that cursor row.
It also repairs only a nonempty strict prefix of that unique expected row;
every other torn suffix is rejected.  A process-local allocation/ordinal
one-shot rejects recursive or concurrent native effects.  Unknown exceptions
burn that reservation fail-closed; only the explicit same-broker crash harness
may relinquish it for durable reconciliation.
C-C release is replayed by its exact allocation/release.  Same-broker Guardian
consumption carries the exact intent ID so an injected post-effect/pre-result
failure can converge without a second native effect.  A durable result is
returned unchanged for a repeated expected cleanup ordinal.

Positive `GUARDIAN_ALIAS_SET_CLOSED` and `PIDFD_REAPED` results additionally
require a process-local one-shot effect attestation bound to allocation,
intent, slot, broker thread/incarnation and (for PIDFD) the exact durable
preobservation.  A forked child clears these attestations and closes the pinned
journal handle.  Thus coherently rewriting result/cursor bytes into a plausible
positive outcome is insufficient, while broker death remains nonrecoverable.

Recognized windows include intent-file, intent-cursor, PIDFD-preobservation,
effect-before-result, result-file and result-cursor boundaries.  Gapped,
reordered, crossed, relinked or foreign records fail closed.

Durability does not upgrade E1's process boundary.  Broker death, fork,
restart, Guardian poison or loss of a consumed process-local token is
nonrecoverable.  Durable journal integrity may still be inspected, but no new
native token may be minted and no native completion may be inferred.

## Unresolved continuation

An absent dependency is skipped without a native syscall.  An unresolved
dependency records `BLOCKED_UNRESOLVED`; no raw descriptor, numeric PID,
`/proc` guess, callback retry or missing-to-absent conversion is allowed.  The
journal then visits every later independent action, retaining all secondary
causes.  A drained journal with an unresolved or alias-only result is not an
attempt closure or certificate.

## Explicit nonclaims

E2 does not provide:

- proof that closing Guardian aliases released the underlying OFD, mount or
  every external reference;
- a termination policy for a live descendant;
- cross-process Guardian or native-effect recovery;
- normal ordinal 41..52 success events;
- output readback, finalization, output-owner close or ordinals 53..62;
- attempt closure, terminal classification or campaign certification;
- production output-leaf or current-access authority;
- formal `CounterRecord`, `WorkVector` or `ComparisonVector` issuance;
- formal V7 route authority, production/official execution, scalar economics
  or either locked economics Gate.

All corresponding flags remain false.
