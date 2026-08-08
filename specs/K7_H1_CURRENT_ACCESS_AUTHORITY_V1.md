# K7 H1 predecision current-access authority V1

Status: Contract `2.0.57` production current-access component. The retained
one-shot authority is implemented; the later formal-V7 join and official
route execution remain locked.

Profile: `construction_k7_h1_current_access_authority_v1`

## Purpose and non-circular boundary

This contract closes the current-access half of the H1 predecision chain
without consuming any object that it is later supposed to authorize. The
ordered construction is:

```text
Contract-2.0.52 current source + claimant-proof match
  -> current-access execution profile
  -> semantic predecision context
  -> six-row predecision input set / launch context
  -> fresh-exec observed runtime facts + exhaustive capability closure
  -> context-bound append-only access log
  -> exact current-log-head cutoff
  -> observed evidence
  -> retained one-shot production current-access authority
```

The authority has no decision point, selected plan or route, common-prefix
work, route-upper, route-decision, or route-freeze field. It records
`downstream_route_authority_join_present = false`; the formal V7 decision join
is a future stage. Consequently current access cannot be justified by a route
decision that itself depends on current access.

## Frozen identity

`H1CurrentAccessPredecisionContextV1` accepts the exact retained Contract-2.0.52
`H1CurrentSourceFixtureV1` and `H1DurableProofMatchAttestationV1`. It binds:

- current-source fixture and claimant-proof-match IDs;
- the H1 recipe, current-identity candidate and its structural verification;
- deterministic fresh-exec profile, standalone-source manifest and exact
  interpreter/runtime manifest;
- the exact infeasibility aggregate ID;
- structural, query, BuildEpoch, kernel, threshold, reward, deterministic
  policy-class, and complete-search IDs;
- logical occurrence, route attempt, and a fresh session nonce; and
- the current-access execution-profile ID.

The occurrence and attempt must equal the values observed in the retained
proof-match recipe chain. BuildEpoch is taken from the current-source identity,
not supplied separately. Therefore a caller cannot splice a new attempt or
epoch while preserving the upstream identity.

The semantic context also binds exact digest/extent rows for the five inputs
that already exist before it: current source, proof match, recipe, current-
identity candidate and candidate verification. It cannot contain its own
digest without a cycle. Therefore a second
`H1CurrentAccessPredecisionInputSetV1` adds the exact canonical context row and
freezes all six sealed inputs in this order:

```text
PREDECISION_CONTEXT
CURRENT_SOURCE_FIXTURE
PROOF_MATCH_ATTESTATION
H1_TWO_ROLE_RECIPE
CURRENT_IDENTITY_CANDIDATE
CANDIDATE_VERIFICATION
```

Every row is exactly `{role, artifact_id, sha256, byte_count}`. The input set
binds the execution profile and all three prelaunch manifest IDs. Its ID is
never written back into the semantic context. Runtime facts and the eventual
authority bind both the context and input-set IDs.

## Append-only recorder and cutoff

`H1PredecisionAccessLogRecorderV1` is bound to exactly one execution profile
and context. Every event carries the context, occurrence, attempt, BuildEpoch,
nonce, monotone sequence, predecessor event ID, operation, and resource ID.
The certificate sequence is exactly:

1. `CURRENT_SOURCE_FIXTURE_REPLAYED`;
2. `PROOF_MATCH_ATTESTATION_REPLAYED`;
3. `FRESH_EXEC_RUNTIME_VERIFICATION_ACCEPTED`;
4. `EXHAUSTIVE_CAPABILITY_CLOSURE_VERIFIED`.

The same recorder pre-registers two later phase events,
`FORMAL_V7_DECISION_VERIFIED` and `ROUTE_DECISION_FROZEN`. They are legal
append-only continuations for the future downstream stage, but neither belongs
to this current-access cutoff. Appending the first one immediately makes the
four-event authority stale. Unknown phase events remain forbidden.

The profile forbids kernel steps, outcome enumeration, planners/J0, fallback,
local materialization/compiler/solver/postaudit, claimant-proof production, and
post-run result reads. An additional append is retained rather than erased; it
makes an earlier cutoff stale and prevents a new exact four-event cutoff.

`H1PredecisionCurrentAccessCutoffV1` is the content-addressed current log head,
not a caller-selected prefix. Verification rematerializes the recorder's
current snapshot and requires exact log ID, count and final event. Cross-
context, attempt, epoch, nonce, reordered, missing and extra-event chains fail
closed.

## Runtime evidence and fixture separation

The only production-eligible verification status is:

```text
OBSERVED_RUNTIME_PLUS_EXHAUSTIVE_CAPABILITY_CLOSURE
```

`issue_h1_current_access_child_result_v1` dynamically imports the complementary
fresh-exec verifier to avoid a module cycle. It accepts only the verifier's
exact retained `H1CurrentAccessObservedRuntimeFactsVerificationV1` type and
re-runs its public retention check. The verification must repeat the complete
context binding and expose content-addressed observed-facts, verification,
source-manifest, and runtime-manifest IDs.

The child result and evidence retain the exact runtime-verifier handle in
nonserialized process state. Authority issuance and every subsequent require
or consume revalidate that handle, its six input bytes/input-set replay, and
the recorder's current cutoff. A content ID copied out of a formerly valid
runtime result is insufficient.

`build_h1_current_access_child_result_fixture_v1` is deliberately separate. It
uses construction-only member IDs and the status `CONSTRUCTION_FIXTURE_ONLY`.
An evidence object derived from this fixture is useful for schema, cutoff and
identity attack tests, but `issue_h1_production_current_access_authority_v1`
always rejects it. There is no boolean, environment variable, test mode,
subclass, Protocol mock, or caller-provided status that promotes it.

If the actual fresh-exec runtime is unavailable,
`H1ProductionCurrentAccessAuthorityBlockerV1` records the exact context-bound
`FRESH_EXEC_RUNTIME_EVIDENCE_UNAVAILABLE` blocker. It is a noncertificate
`PROTOCOL_FAILURE`, never an authority or infeasibility certificate.

## One-shot authority

The production authority is retained by exact object identity and canonical
bytes. `require_h1_production_current_access_authority_v1` validates a live,
unconsumed handle. `consume_h1_production_current_access_authority_v1` returns
the frozen canonical bytes and atomically revokes the handle. A second require
or consume fails. `object.__new__` shells, copied/look-alike dataclasses,
construction evidence, unretained runtime results, and mutated payloads fail.

This one-shot handle is intended for the future formal V7 downstream join. It
does not itself authorize route execution.

## Acceptance attacks

Focused tests cover:

- central domain uniqueness and all official locks;
- exact eight-coordinate Contract-2.0.52 reuse;
- absence of decision/common-prefix/upper/selected-route/freeze fields;
- append ordering and predecessor-chain integrity;
- stale cutoff and extra-event rejection;
- cross-context, attempt, BuildEpoch and nonce rejection;
- exact-type and retained-runtime verification requirements;
- construction/fake evidence rejection;
- one-shot retained-authority API rejection of unretained shells; and
- typed blocker semantics.

The integration suite exercises successful production issuance and
consume-once behavior only with real fresh-exec observed facts. A test-only
issuer is forbidden. Independent hardening closed the exact source/helper
mutation boundary and confirmed a real second
`waitid(P_PIDFD, ..., WEXITED)` reap before the positive component flags were
enabled. This is a trusted-process checkpoint contract: it detects changes to
the registered closure at its four checkpoints, but does not claim resistance
to arbitrary mutation of private Python state concurrently between those
checkpoints. The runtime facts state that boundary explicitly.

## Locks and non-claims

The complementary runtime is integrated and independently replayed, but that
closes only the predecision current-access component. The downstream locks
therefore remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

This slice does not provide the formal 182-term V7 upper/decision, execute the
business fallback, issue nine shared-resource receipts or 202 CounterRecords,
materialize WorkVector/ComparisonVector, close a campaign, or claim sample
efficiency.
