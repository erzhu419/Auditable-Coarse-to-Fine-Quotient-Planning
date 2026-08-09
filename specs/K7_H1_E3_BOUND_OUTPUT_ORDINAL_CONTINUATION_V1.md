# K7 H1 E3-Bound Output Ordinal Continuation V1

Status: additive construction contract `2.0.59-E-C-E4`.

Profile key:
`construction_k7_h1_e3_bound_output_ordinal_continuation_v1`.

## Narrow claim

E4 closes one construction-only path after an exact successful E3 broker
session.  It proves that a context prepared before E3 can continue the exact
normal ordinal sequence with eight durable witness files at ordinals 53--60,
one finalization event at ordinal 61 and one writer-consumption event at
ordinal 62.  It also closes the exact joint output/readback byte recurrence.

E4 does **not** issue production semantic artifacts, CounterRecords,
WorkVector, ComparisonVector, projection proof, terminal certificate, current
access, formal V7 authority or official execution.  It does not close FQ11,
the Counter Completeness Gate, the Workload Economics Gate, scalar cost or
break-even.  Its eight durable objects use construction-witness schemas that
formal parsers must reject.

## Pre-E3 context and one-shot binding

`H1E3BoundOutputContinuationContextV1` is issuer-created before E3 launch.  It
contains and content-binds:

- a fresh 256-bit cryptographic nonce;
- the exact E3 profile and source-manifest IDs;
- exact retained caller lifecycle snapshot and program payloads, each wrapped
  in an explicitly nonformal construction schema;
- caller binding, logical occurrence and route-attempt IDs;
- the exact eight-role/ordinal/file-name map;
- base read bytes and the frozen role, total, iteration and serializer-buffer
  limits; and
- a newly created, empty, mode-0700 output directory, its parent and basename,
  pinned by retained open directory FDs and device/inode identities.  The
  parent is fsynced immediately after `mkdir`.

Preparation creates the child directory under a caller-supplied parent with a
nonce-derived name.  The context is retained as the exact Python object and
canonical bytes.  Copying, caller construction, content mutation, replay after
consumption, path replacement, directory crossing, a nonempty directory or a
different inode fails closed.  The context also binds its preparer PID and
thread.  Parent, child and every runtime role FD enter one ownership registry
atomically against a registered at-fork `before` hook.  The child hook
definitively closes all inherited registered FDs, including an FD opened before
context publication and O_RDWR role FDs created during the writer program.  A
close that leaves an FD live retains its registry entry and context in a
non-reusable cleanup quarantine.  Cleanup may be retried, but quarantine is
never treated as consumption or success.  Cross-thread, child-process and
copied objects cannot become a second writer.

E3 does not authorize output merely by receiving this ID.  Its exact genesis,
native cleanup barrier and completion must all echo the context ID.  E4
accepts only an issuer-owned exact
`H1ExclusiveBrokerCompletionV1` whose disposition is
`BROKER_EXCLUSIVE_PRESENT`, whose profile/source/session chain is intact and
whose embedded barrier covers exactly ordinals 41--52.  Typed null,
post-hoc contexts, another E3 session, V8/E2 inputs, E3 unavailable results
and E3 crash closures cannot start E4.

## Exact durable role universe

The only durable files and ordinal order are:

| Ordinal | Role | File |
|---:|---|---|
| 53 | `BUSINESS_RESULT` | `53-business-result.json` |
| 54 | `OPERATIONAL_TRACE` | `54-operational-trace.json` |
| 55 | `TERMINAL_ARTIFACT` | `55-terminal-artifact.json` |
| 56 | `COUNTER_RECORD_SET` | `56-counter-record-set.json` |
| 57 | `WORK_VECTOR` | `57-work-vector.json` |
| 58 | `COMPARISON_VECTOR` | `58-comparison-vector.json` |
| 59 | `ACTUAL_PROJECTION_PROOF` | `59-actual-projection-proof.json` |
| 60 | `OUTPUT_MANIFEST` | `60-output-manifest.json` |

Every file is canonical JSON and declares itself a construction witness.  The
manifest lists the first seven roles in order with their construction role ID,
SHA-256 and extent.  It does not contain its own ID, hash or extent.  Fixed
point, finalization, close and completion objects remain in-memory evidence;
none is a ninth durable output.

## Exact joint output/readback fixed point

Let `O` be the sum of the eight durable role extents, `R_base` the registered
pre-output read-byte amount and `R` the total after exactly one inode-pinned
readback of each output role.  Starting from `(0, R_base)`, E4 deterministically
renders the exact eight roles twice and applies

```text
O' = sum(role_extent[BUSINESS_RESULT .. OUTPUT_MANIFEST])
R' = R_base + sum(readback_extent[ordinal 53 .. ordinal 60])
```

The readback extent of a role is its exact durable extent, so the second sum is
not estimated.  Both components must be monotone before convergence; a
repeated nonterminal pair is a cycle.  The iteration cap is 32, every role is
at most 256 KiB, the total is at most 2 MiB and the simultaneous two-render
byte envelope is at most 4 MiB.  Convergence requires exact componentwise
equality.  Two additional terminal renders must be byte-identical to each
other and to the converged role set.

The implementation releases the second iteration render before either
terminal replay and releases each replay before constructing the next.  One
retained terminal set plus one comparison set is therefore the exact maximum
of two simultaneously live role sets.  The 4 MiB value is only a finite
serializer-byte envelope.  It is not measured or asserted as process, broker,
route or campaign peak working memory.

## Durable writer and ordinals 53--62

After the E3 gate and fixed point, the retained pinned directory FD is the
writer lease.  Each role is created relative to it with
`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, initial mode 0600, exact complete write,
file `fsync`, `fchmod(0400)`, and a second file `fsync`.  All eight files must
be regular, have `nlink=1`, occupy distinct `(device,inode)` pairs and match
their retained inode-pinned handles.  The directory is then `fsync`ed.  Before
ordinal 61 and again immediately before ordinal 62, the retained parent FD must
still resolve the registered basename to the exact pinned child inode and both
retained/path identities and modes must agree.  Rename, unlink or chmod between
allocation and finalization therefore closes as a noncertificate.

Exactly one `pread`-based complete readback through each retained file handle
emits ordinals 53--60 in role order.  Every readback must equal the converged
bytes, hash and extent.  Before and after readback the directory must contain
exactly the eight registered names, with no symlink, hardlink, replacement or
extra entry, and every path identity must equal its pinned handle identity.

Ordinal 61 is emitted only after all eight exact readbacks, directory `fsync`,
directory inventory replay and joint fixed-point equality.  Ordinal 62 is
emitted only after ordinal 61; it consumes the context/writer lease and closes
all retained file handles and both pinned parent/child directory FDs.  The resulting
completion is construction evidence, not a durable ninth file.

The mapping-only completion replay is explicitly structural and
nonauthoritative.  The authoritative verifier requires the exact retained
context object (live or consumed) and exact issuer-owned E3 completion,
revalidates their identity chain, re-renders the complete joint fixed point and
all eight role bytes from those sources, independently derives the persisted
inode inventory without trusting completion rows, and reconstructs byte for
byte every allocation, commit, ordinal event, finalization, close and top-level
completion field.  Coherently changing and re-signing any supplied witness
field therefore cannot substitute for source re-derivation.

## Failure semantics

Any failure after writer allocation closes all retained handles without
minting ordinal 62 success and returns one
`ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE` partial-prefix artifact.
The prefix preserves committed role and emitted ordinal evidence but never
sets completion or authorization flags.  Injected crash, extra file, symlink,
hardlink, path replacement, event reorder, duplicate event, changed bytes,
failed `fsync`, cap violation, cycle or nondeterministic render therefore
cannot upgrade to success.  Rejected upstream/context inputs fail before
writer allocation and do not produce a partial execution artifact.
An FD is removed from the unified registry only after `close` succeeds, an
`EBADF` probe proves that a close which raised nevertheless definitively
closed it, or identity replay proves the original FD was closed and its number
was reused.  A still-live close failure cannot be hidden by local-map clearing.
Its partial artifact says `context_consumed=false`, reports the retained role
labels and remains retryable in quarantine; only a later definitive close may
move it to the consumed registry.

## Peak and downstream locks

The E3 ordinal-42 maximum covers only the two role cgroups.  E4 must not
relabel it as route-wide peak and freezes:

```text
route_wide_peak_authority_present = false
peak_scope_status = PEAK_SCOPE_UNRESOLVED
production_output_leaf_authority_present = false
formal_counter_records_issued = false
formal_work_vector_issued = false
formal_comparison_vector_issued = false
formal_actual_projection_proof_issued = false
current_access_authority_present = false
formal_v7_authority_present = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE = NOT_RUN
WORKLOAD_ECONOMICS_GATE = NOT_RUN
```

The next construction gate must provide a continuously enforced
broker/output-inclusive peak authority and production semantic issuers before
any of these locks can change.
