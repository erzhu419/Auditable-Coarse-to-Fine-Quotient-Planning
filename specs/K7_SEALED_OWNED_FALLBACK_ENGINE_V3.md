# K7 sealed owned-fallback engine V3

Status: proposed Contract `2.0.54`, additive construction authority. Contract
`2.0.53` remains a frozen prerequisite and its legacy V4 construction harness
and typed owner blocker retain their original claims. This document does not
bump the global contract or unlock official execution or either accounting
Gate.

## Purpose and exact source

Contract `2.0.54` adds the separate module
`acfqp.phase3e_fallback_owned_v3`. Its search is a mechanical copy of the
exhaustive deterministic-Markov algorithm in `phase3e_fallback_v1`; it does
not call that historical solver. The exact sealed member is:

```text
relative path: phase3e_fallback_owned_v3.py
byte count:    37568
SHA-256:       27a0e116ba7f1e11246590796393030991c8093d743f11d81ccff24180e2a595
```

The module imports only these runtime names from V4:

```text
OWNED_ROUTE_EVENT_ACK_V4
bind_owned_fallback_search_v4
emit_owned_route_operation_v4
finish_owned_fallback_search_v4
seal_owned_fallback_engine_import_v4
verify_owned_fallback_engine_import_seal_v4
```

It imports no V3 route-segment runtime, historical owned runner, operation
manifest, live source-archive loader, or repository path authority.

## Sealed authority

`verify_sealed_owned_engine_authority_v4` accepts caller-supplied bytes only.
It checks the full extent and digest, parses those bytes, and requires exactly
one bind call, seven literal unit gateway calls, and exactly one finish call.
The seven sites are the real methods of `_OwnedFallbackLedgerV3` and map to:

```text
control.cap_checks
control.cap_rejections
fallback.states_expanded
fallback.actions_evaluated
fallback.ground_steps
fallback.outcome_rows
fallback.bellman_backups
```

Every boundary is rejoined to the V6 registry and `DIRECT_FALLBACK` stage
profile. The authority freezes each method AST, call AST, literal dispatch,
target path, source symbol, and call location. Contract `2.0.54` uses new
Phase-3E domains for the sealed source, boundaries, authority, and owned
start/event/terminal/transcript nodes. It does not reuse or reinterpret the
Contract `2.0.53` construction domains.

The search-entry, bind-call, and finish-call AST hashes and locations are
independently frozen constants rather than digests trusted from a supplied
authority object. The bind is the direct statement at `(478, 4, 478, 41)`,
immediately after construction of
`ledger` and immediately before `validate_query`. The finish is the direct
statement at `(690, 4, 690, 54)`, immediately after construction of
`execution` and immediately before `return execution`. Bind takes the one
local `ledger`; finish takes the exact local `ledger` and `execution`; neither
uses keyword arguments. Moving either call into another function, branch,
wrapper, or callback fails sealed replay even before runtime frame checks.

The verifier also compiles, but never executes, the exact member. It computes
line/path-independent recursive code fingerprints for all eight ledger
methods plus the search, work helper, source validator, and engine validator.
At session construction and every later revalidation, V4 independently
recomputes the same 12 fingerprints from the actual live code objects. It
requires equality among sealed compilation, independently observed live code,
and the binding's claimed tuple. A preloaded module cannot satisfy this check
by merely returning self-consistent digest strings.

The engine validator's function object, globals, code, exact 14-element
defaults tuple, null keyword defaults, global/builtin mathematical
dependencies, callable defaults/closures and class surfaces are placed in a
one-shot V4-owned seal while the owner module is executing its top-level
import frame. Later validation compares against that external snapshot, not
against the validator's current defaults. Replacing a mathematical dependency
and synchronizing `_runtime_globals`, replacing the defaults tuple with an
equal tuple, or changing validator object/code/globals/keyword defaults is
rejected.

`verify_sealed_owned_engine_authority_v4` accepts exactly one source-bytes
argument. Its internal implementation has no caller-overridable expected-pin
parameters. Its internal immutable pin tuple is held in frozen defaults; its
object, globals, code, exact defaults and null keyword defaults are frozen,
while the public entry has null defaults/keyword defaults. A modified source
plus attacker-selected size, digest or AST pins cannot publish the frozen
source identity.

## Exact live binding and lifecycle

The owner module freezes at import time:

- the exact ledger class, constructor, seven owner methods, globals and code;
- the V4 event gateway, acknowledgement, bind and finish objects/globals/code;
- the exact search entry and legacy-work transport helper; and
- both source-binding and engine-binding validators;
- every directly referenced module-global and builtin object together with
  function code identity; and
- the invoked surfaces of the cap, registry, result, work, policy and Pareto
  classes.

An `OwnedEngineFallbackRouteSegmentSessionV4` accepts only the replayed sealed
authority and an exact live binding independently reproduced by the frozen
engine validator. It revalidates that binding at activation, bind, every event,
finish, and completion.

The start node additionally freezes the route-decision context, decision
point, route decision, selected upper, route attempt, query, recorder, ground
fallback cap profile, legacy search-counter registry, occurrence, stage
profile, and sealed-engine authority identities. Bind inspects those exact
locals in the actual sealed search frame before `validate_query` or the first
event. It also requires the exact cap object held by the zero-valued ledger
and the exact search registry ID. A different attempt/query/recorder/cap or a
different route identity therefore cannot splice its search into a registered
segment.

Before the ledger can bind, the session independently derives a ground-free
canonical semantic package from the actual `kernel` and `query` locals. The
start commits exact structural, kernel-code/configuration, query, threshold,
reward, deterministic-policy-class and complete-search-profile IDs plus their
combined semantics ID. Bind rederives the package from the actual objects and
requires canonical equality. The legacy caller `query_id` remains only a
route-chain label and is explicitly not semantic authority. Changing delta,
initial law, reward, horizon, kernel configuration/type or semantic method
code while retaining that label fails before the first owned event.

This Contract profile is intentionally narrower than the underlying Python
search signature. It registers only the exact class
`acfqp.domains.g2048.G2048Kernel` with `size == 2`; subclasses, wrappers and
duck-typed kernels are rejected. Contract `2.0.54` therefore makes no claim
that a caller-supplied kernel interface is semantically sealed merely because
four public method fingerprints happen to match.

At V4 import, an explicit G2048 adapter manifest builds a live recursive
transition-semantic closure. Its roots include the four search entry methods
`actions`, `step`, `is_terminal` and `reward_upper_bound`, the private
`_adjacent` and `_validate_state` helpers, the `size` slot descriptor, and the
property getters used for rank, horizon, spawn, reward-feature, goal and cell
semantics. The closure additionally retains the distinct state/action/status,
outcome and exact-rational class surfaces required by those roots. It walks
all recursively referenced code objects and module globals across module
boundaries, retains builtin identities, and follows executable values held in
function defaults, keyword defaults and closure cells. Every callable is
bound by object, globals, code, exact defaults/keyword-defaults/closure
objects and their retained values; every registered descriptor and class
surface is rebound by identity.

The registered `G2048Kernel`, state, action, status, outcome and `Fraction`
classes additionally retain their complete direct class-dictionary shape and
every value/descriptor identity, exact metaclass, MRO and bases. This includes
the `__slots__` descriptors and proves the import-time absence of direct
`__getattribute__`/`__getattr__` overrides; their inherited attribute lookup
and metaclass lookup/call surfaces are also rebound by identity. All modules
participating in the recursive closure retain exact module type, globals
object, inherited module lookup descriptors and direct
`__getattribute__`/`__getattr__` presence or absence. A stateful
`G2048Kernel.__getattribute__` installed after start therefore cannot return
one `actions` method during semantic derivation and another during ground
search: activation or bind fails with an empty event prefix.

The canonical closure document and content ID are embedded in both structural
and kernel semantic documents and in the owned start. Live closure validation
runs during session construction, activation/revalidation and again while
deriving the actual kernel/query package at bind. The semantics deriver,
canonical-ID functions/domains, recursive-code helper and all semantic helper
objects are independently frozen. Replacing `_adjacent`, or replacing
`actions` together with the fingerprint helper that might otherwise mask the
new code, closes the session before the first owned event. The sealed owned
source hash is necessary but explicitly not sufficient evidence for this
external transition closure.

These checks define checkpoint semantics for ordinary single-threaded Python
construction: registered class/module surfaces must remain unchanged between
session construction, activation, bind and each later revalidation. Contract
`2.0.54` does not claim resistance to a concurrent same-process attacker that
mutates and restores Python classes between individual bytecode operations;
native process isolation remains a later production boundary.

The lifecycle is exact-once:

```text
activate exact owned-engine session
  -> construct exact ledger inside the sealed search
  -> bind once from that exact search frame
  -> validate query and perform ground/planning work
  -> emit unit events only from bound ledger methods descending from that frame
  -> finish once with the same ledger, execution and search frame
  -> compare all seven ledger values with the immutable positive transcript
  -> freeze the exact finished execution/result/work/policy document binding
  -> bind result/work IDs and native values back to the frozen start
  -> require composed-candidate count == Bellman-backup count
  -> explicitly complete the session
```

The bind occurs before `validate_query`, kernel access, outcome enumeration,
or planning. A missing active session therefore fails before query or kernel
access. Events before bind, after finish, from another ledger, from another
search frame, from a same-name function, or through a replaced gateway fail
before the corresponding counter mutation. A second bind is rejected. Search
exceptions abort the session while retaining its exact positive prefix.

Readable private issuer objects are not sufficient to mint a start, event,
terminal, or transcript: issuance requires exact session-method frame ancestry
and a retained, single-owner runtime mint. `object.__new__`, copied mint state,
`object.__setattr__`, or constructor-frame spoofing cannot produce a node whose
document is accepted. Bind, event, finish, completion and serialization all
recheck the retained nodes. This is Python-API spoof resistance, not a
native-code isolation claim.

## Exact finished-execution publication

`finish_owned_fallback_search_v4` freezes one minted,
content-addressed `OwnedEngineFinishedExecutionBindingV4` before marking the
search finished. The binding is published in the terminal and transcript and
is not an object-identity-only assertion. It commits to:

- the route-segment start and exact `GroundFallbackResultV1` ID;
- the canonical full result document SHA-256 and byte count;
- the exact `WorkVectorV1` ID, canonical full document SHA-256 and byte count,
  and every sorted native work value;
- outcome, exhausted-cap name, full frontier digest/count;
- selected-policy object presence and independently recomputed canonical
  policy signature, selected reward and selected failure probability; and
- composed-candidate count; and
- the explicit `NONE_RAW_OWNED_SEARCH` provenance state.

The result, frontier, WorkVector and policy serialization surfaces used for
this commitment are part of the import-time frozen live-engine surface.
Completion recomputes the entire binding from the retained exact execution.
The public read-only verifier
`verify_owned_engine_finished_execution_binding_v4(binding, execution)` does
the same recomputation without kernel or planner work, so a downstream
consumer can prove that the execution object it was passed is exactly the
execution committed by the transcript. A consumer must require a non-null
terminal binding, invoke that verifier, and carry the binding ID in its own
derived artifact; matching only transcript counters or result/work identity
fields is insufficient.

Acceptance attacks replace the exhausted-cap name, infeasible frontier,
actual selected policy, result and self-consistent result/WorkVector pair
after a genuine owned session. Every replacement is rejected against the
unchanged published transcript binding.

The execution-material helper, its code/globals/defaults/keyword defaults and
canonical-JSON/SHA dependencies are frozen. Finish, completion and the public
verifier require that frozen helper before recomputation; replacing the
module-global helper cannot validate an altered execution. Because this owner
is the raw search primitive, any non-null `trusted_provenance` is rejected
rather than silently lying outside the advertised exact-execution claim.

## Mathematical and cap acceptance

For the canonical H1 infeasible G2048 occurrence, the owned engine must match
the V1 reference result, work vector, and selected policy exactly when both
use the same identities, cap, registry, and recorder. The expected completed
owned transcript has 208 unit events:

```text
control.cap_checks          56
fallback.states_expanded     8
fallback.actions_evaluated  16
fallback.ground_steps       16
fallback.outcome_rows       96
fallback.bellman_backups    16
```

With `max_states_expanded = 7`, the search must return `CAP_EXHAUSTED` and
complete the same bound segment with exactly 16 events: eight cap checks,
seven expansions, and one cap rejection. Cap exhaustion is not an
infeasibility certificate.

With `max_cap_checks = 1`, the expected prefix is exactly one cap check, one
state expansion, and one cap rejection; the rejected operation performs no
later counter mutation. Separate attacks cover the action, ground-step,
outcome-row, Bellman-backup, composed-candidate, state and cap-check limits.
Each cap closure retains an exact positive prefix and names the cap; no cap
closure is reclassified as infeasibility.

The focused acceptance suite additionally requires failure closure for wrong
finish values, double finish, event-after-finish, normal scope exit without
explicit completion, dependency replacement (including
`select_constrained`), and replacement of bind, finish, gateway, ledger
methods, or search entry. It covers action-enumeration failure, kernel failure,
positive-outcome overflow with a reconciled partial WorkVector, result/work
materialization failure, finish/complete failure, identity splicing,
preloaded/foreign live binding, copied/unminted nodes and candidate/backup
divergence. Every one of the canonical 208 events must report
`SOURCE_OWNED_RUNTIME`.

Separate isolation attacks prove that a duck-typed wrapper and a subclass are
outside the registered adapter, that a live `_adjacent` rewrite is detected,
and that a synchronized `actions` plus recursive-fingerprint-helper rewrite
cannot preserve the start identity. Both live-code attacks terminate with an
empty owned-event prefix.

The copied recurrence contains the same two `pareto_prune` placements as V1:
one after each H1 per-state partial-frontier extension and one after the full
multi-step candidate family. Exact result/work/policy equality against V1 is
the executable guard against an extra, missing, or relocated prune changing
the mathematics.

## Claim boundary and locks

The V1 result/work objects are retained only as legacy transport for exact
parity. The V4 owned transcript is a separate construction artifact. Neither
object is a V6 CounterRecord, formal WorkVector/ComparisonVector chain, FQ9
terminal, V7 route authority, or official certificate.

```text
construction_only = true
production_owner_source_integrated = true
formal_v7_route_authority_present = false
production_closure_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

The next accounting slice must consume this immutable owned transcript and
add the nine independently supervised shared-resource receipts before it can
materialize the formal `CounterRecord -> WorkVector -> ComparisonVector`
chain. Contract `2.0.54` does not make that later claim.
