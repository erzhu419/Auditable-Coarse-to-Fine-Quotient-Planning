# K7 H1 Failed-Prefix Cleanup Budget Admission V1

Status: additive construction contract `2.0.59-E-C-D`.

Profile key:
`construction_k7_h1_failed_prefix_cleanup_budget_admission_v1`.

## Closed boundary

Before normal-prefix ordinal 1, this profile freezes one immutable,
content-addressed admission for the complete C-B failed-prefix cleanup
universe. The admission replays the exact 112 registered C-B branches and 111
dispatcher-reachable branches, including the one unreachable negative
control. Each row binds:

- the C-B envelope and pristine Owner/gate cutoff;
- the exact cleanup-pass ID;
- every exact planned action, action ordinal, target, and budget category;
- the per-branch category counts.

The maxima are recomputed over the branch rows rather than accepted as caller
totals:

| Category | Conservative branchwise maximum |
| --- | ---: |
| `RESOLVE` | 1 |
| `REAP` | 2 |
| `MOUNT_CLOSE` | 10 |
| `MEMORY_RELEASE` | 1 |
| `OUTPUT_RELEASE` | 1 |
| Total | 15 |

Caller-provided availability must name exactly these five categories and meet
every component. A scalar total of 15 is not sufficient if any component is
underfunded. Missing, extra, Boolean, negative, or insufficient values fail
closed before admission storage is created or repaired.

## V5 versus V6 binding

The V6 native-resource receipt journal is an actual pre-ordinal-1 artifact.
The admission therefore binds its exact issuer-owned spec ID, allocation ID,
normal allocation, 12-slot declaration, and genesis cursor. Admission is
forbidden after any receipt record, native start, cutoff, normal intent, or
normal event exists.

An actual V5 Owner-cleanup sidecar spec/allocation cannot honestly exist at
this point: V5 requires the later failed transition, selected pass/action,
and stable failure-time Owner cutoff. This profile instead freezes a separate
content-addressed prospective V5 baseline containing:

- the V5 profile, spec/allocation schemas and disjoint domain tags;
- the exact attempt, phase, gate, Owner and C-B envelope context;
- the unique phase-base realpath/device/inode and prospective sidecar root;
- the rule that the eventual V5 spec must bind the exact selected
  transition/pass/action and failure-time Owner cutoff;
- typed-null actual V5 spec/allocation IDs.

The prospective baseline is embedded in the admission together with its own
content ID. It is not relabelled as a V5 spec or allocation.

## Timing and durability

All artifact types, cross-context identities, branch maxima and componentwise
budget sufficiency are validated before the admission root can be mutated.
Admission requires one exact live phase-aware normal lease; stale, inactive,
foreign-thread and caller-minted leases fail before admission mutation. The
caller therefore already retains `PHASE -> GATE -> NORMAL`. The admission then
acquires the stable read-only Owner and native-receipt locks in the order
`OWNER -> native receipt`, verifies the live gate remains pristine `OPEN`, and
requires the live stable Owner sequence/head to equal the exact C-B
preadmission cutoff. This complete composite authority is retained through
durable admission publication. No ordinal-1 intent, Owner append, gate closure,
or native `START` can cross the validation-to-seal window.

Normal and native receipt replay are read-only at this gate: a repairable
cursor/high-water frontier is rejected rather than changed by admission. The
stable V4 Owner preflight likewise rejects WAL, pending, temporary or adjacent
frontiers without repairing them. Late, stale, crossed, underfunded or
repair-requiring requests cannot create an admission artifact.

The phase-base directory is opened with `O_NOFOLLOW`, pinned by descriptor and
revalidated against its frozen device/inode under the retained locks. All
root, attempt, primary and seal operations are relative to that descriptor.
A mode-`0600` base-root coordination lock serializes first publication. One
canonical admission file is hard-linked to a route-attempt seal stored in the
pinned phase base, so replacing the child admission root cannot create an
independent spend. Before success, the phase-base pathname and the opened
root/attempt name-to-inode mappings are revalidated.

Replay requires identical canonical bytes, content ID, inode, mode, and exact
two-link topology. Repeating the same request returns the same immutable
admission; a changed budget or context conflicts rather than replacing it.

## Explicit nonclaims

The 15 admitted units are construction admission tokens only. FQ11 has not
ratified a cleanup counter leaf, so this profile issues no formal
`CounterRecord`, `WorkVector`, or `ComparisonVector`.

This slice does not provide:

- a later native cutoff/receipt evidence join;
- an actual V5 sidecar spec or allocation;
- a cleanup action journal, executor, or native effect;
- memory read, descendant reap, mount close, output finalization/readback, or
  output-owner close authority;
- ordinals `41..62`, attempt closure, or terminal classification;
- production current-access or formal V7 route authority;
- production/official execution or any economics Gate result.

All corresponding authority flags remain false.
