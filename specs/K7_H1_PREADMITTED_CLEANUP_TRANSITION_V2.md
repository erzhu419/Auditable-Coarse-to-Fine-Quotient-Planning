# K7 H1 Pre-Admitted Cleanup Transition V2

Status: construction-only component of contract `2.0.59-E-C-B`.

Profile key:
`construction_k7_h1_preadmitted_cleanup_transition_v2`.

## Closed scope

Before normal-prefix ordinal 1, this profile freezes one content-addressed
structural cleanup envelope for every failure branch that ordinals `1..40`
may select. The envelope is derived from the exact anchored normal contracts
and the complete lifecycle cleanup analysis. It contains 112 registered
branches, of which 111 are dispatcher-reachable; the one declared memory
ambiguity edge remains an explicit negative control.

Every action in the envelope is a non-executable structural plan. The only
admitted kinds are mount close, descendant reap, native-existence resolution,
and conservative memory/output reservation settlement without native read or
output finalization. Readback, finalization and output-owner close are
forbidden. The envelope retains no PIDFD/OFD/native capability and admits no
cleanup budget.

## Failure boundary and phase transition

The integrated normal entrypoint validates the durable envelope before it may
invoke a site callback. A successful site remains on the normal path. A first
durable non-success event is never returned alone: under the same retained

```text
PHASE -> GATE -> NORMAL JOURNAL -> OWNER
```

outer lease, it is rebound to the exact reachable envelope branch and cleanup
pass, then published as a tagged V2 transition through

```text
NORMAL -> CLEANUP_INTENT_DURABLE -> CLEANUP_ONLY.
```

The transition binds the normal event, Owner tail, gate state, attempt,
transaction, normal-prefix allocation, structural envelope and selected
cleanup pass. Cap rejection must match the retained acknowledged gate and its
exact commit/ACK; lifecycle failure must match an OPEN gate with typed-null
rejection references. Recovery of a normal intent whose native cell is durable
does not invoke its callback again and converges the resulting failure into the
same V2 boundary.

V2 intent, root seal and commit must remain the same immutable inode. A
terminal `CLEANUP_ONLY` cursor without that commit is rejected. The four
registered transition publication windows converge through successor replay.
Persisted envelope honesty fields and transition-to-envelope/gate bindings are
revalidated rather than accepted from a self-consistent content hash alone.
Successor replay retains the live gate and completes this read-only preflight
before it may repair a phase cursor or create the commit. The preflight also
reloads the immutable normal-prefix spec/allocation and rebinds the envelope's
Owner pre-admission cutoff to that independent baseline.

## Compatibility and lease boundary

Historical V1 source bytes and parsers are unchanged. Successor replay
dispatches an actual V1 transition back to the exact V1 recovery path and
handles only the disjoint tagged V2 schema itself. A V2 cleanup-only lease
requires the exact committed V2 transition ID and retains only the phase and
gate barrier. Failed nested acquisition clears its successor context state.

The lease is deliberately not a cleanup executor. It exposes no native
resource, Owner continuation, callback, output role, counter issuer or route
authority. A later additive contract must join separately registered resource
receipts, cleanup-budget admission and crash-safe action records before any
planned action can execute.

The private hard-link layout supplies crash consistency inside the trusted,
bound root namespace. It does not claim protection against an actor able to
coherently rewrite or relink that namespace; such a threat still requires an
external monotonic witness.

## Claim boundary

The exact positive claims are:

- pre-ordinal-1 admission of the complete `112/111` structural branch set;
- integrated first-failure/cap-rejection transition to `CLEANUP_ONLY`;
- exact V2 commit, envelope, branch and retained-gate rebinding;
- deterministic registered recovery without callback replay after native
  start;
- exact historical V1 delegation without modifying V1/C-A source bytes.

The following remain false or absent:

- cleanup action execution or cleanup-budget authority;
- retained PIDFD/OFD/native resource capabilities;
- Owner conservative-release continuation in this profile;
- broad real-process-exit proof for the normal-prefix boundary;
- ordinals `41..62`, conditional output skips, finalization and readback;
- production current-access and formal V7 route authority;
- formal `CounterRecord -> WorkVector -> ComparisonVector` issuance;
- terminal/campaign closure and complete-bundle verification;
- official execution, scalar break-even, economics, Counter Completeness and
  sample-efficiency Gates.
