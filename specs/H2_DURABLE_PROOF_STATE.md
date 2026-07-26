# H2 same-query durable proof state (V0-054A)

Status: normative implemented control

Contract version: `1.17.0`

Schema version: `1.0.0`

Profile: `lmb_h2_same_query_durable_proof_state_v0`

Passing status:
`CERTIFIED_REGISTERED_H2_SAME_QUERY_DURABLE_PROOF_STATE_CONTROL`

## 1. Purpose and exact claim

V0-054A checks that reusable lower H2 proof state can cross a real process
boundary. It consumes the owner-bound V0-053 result, reconstructs that result's
final V3 model-only proof workload, writes a canonical content-addressed
checkpoint, and loads the checkpoint in two separately launched Python
processes.

The sole positive claim is:

> For the exact registered V0-053 final model, query, thresholds, formulas,
> source implementation digests and five-request H2 workload, the 30 lower
> proof nodes can be serialized, loaded and reused by two fresh processes. No
> complete request root is persisted, and the warm workers make no target
> ground-kernel transition, catalogue or optimizer call.

This is a same-query persistence control. It is not authority for generic
persistent caches, cross-query reuse, changed thresholds/rewards/models,
`H > 2`, semantic policy change, sample reduction, total-work reduction,
learned dynamics, coordinate invention, workload economics or official
execution.

## 2. Source ownership and frozen identity chain

The producer accepts only the runtime-authority-bearing V0-053 result with:

```text
source result =
  5e46f0eda3f6d9c96e955315034829913dc248d09ed1a73ca8384d4cbcd65d44
final V3 model =
  a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315
thresholds =
  019ee51eed8dc413dfecf11de033657dcb97caa3e03187e9051f8c732e28ed70
build result =
  1789f7cb364bc7012fe392df494057dec6bee29614e8ffb281338e04f7ab4dc9
threshold rebase =
  1f15a26ad654249fea95af7813930ccf68b5677f92ee99ad3930495d3eac2e13
evidence request =
  dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf
evidence bundle =
  9da973649ab05959fc3855467d3a314017a659ff0feb61dd0ab18c0c4824c20a
source proposal =
  fb23e41d80f2597622443fe71ac57516ed12298f66a2ad2e56d4c6c8344a8acb
source selected plan =
  0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb
source selected request =
  961f01d6fd9bcf603372db1fc773932913cb17610758d09f1fb9f39da863bf47
source selected receipt =
  ee518c66dd4850db1ccc35a391b977d22798987c4154f56e18a962b8c41bf8d0
source selected inner audit =
  6a68944dba08b7b2266cd1376d60569de753d02cbcfab29f7edc34c337926d54
source selected wrapper audit =
  81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529
source final execution =
  3cbe43d106be12824e8d15a27a8fc0e82d37cf37a8c772a191eacd2b5fb77279
```

The four candidate request IDs and their recomputed inner-audit IDs are also
frozen in Gray order. The checkpoint manifest binds all of these identities,
the transported model and thresholds, and source SHA-256 digests for the live,
temporal, planner, auditor, multistep and transport modules.

V0-054A does not independently reconstruct V0-053 from its original eight
ground authorities. It relies on V0-053's owner-bound result and V0-053's own
verification/regression contract, then independently validates its downstream
checkpoint bytes and model-only proof calculation within this Gate.

## 3. Persisted proof graph

The eleven-slot H2 dependency graph is:

```text
U1 -> U0
P1 -> P0
C0 -> C1
D  <- U0,P0,C0,C1
E,F <- D
G  <- C0,C1
R  <- U1,U0,P1,P0,C0,C1,D,E,F,G
```

Only `U1,U0,P1,P0,C0,C1,D,E,F,G` may be persisted. Exact cardinalities are:

| Slot | Entries |
|---|---:|
| `U1`, `U0` | 1 each |
| `P1`, `C0` | 2 each |
| `P0`, `C1`, `D`, `E`, `F`, `G` | 4 each |
| **Total lower entries** | **30** |
| **Persisted `R` entries** | **0** |

Every value stores its typed node key, ordered parents, typed proof entry and
exact rational/Boolean payload. The loader requires exact topological order and
recomputes the complete expected 30-node payload from the transported model.
Thus a merely self-consistent re-sign of a hidden value or parent topology is
not accepted.

`R` remains request-, role-, occurrence- and proposal-bound. Each process must
construct five new roots.

## 4. Store and commit protocol

The store contains exactly:

```text
blobs/<payload-id>.json
blobs/<manifest-id>.json
commits/<commit-id>.json
```

There is no mutable `HEAD`. The expected commit ID is supplied externally.
Payload, manifest and commit use distinct domain tags and:

```text
SHA256(domain-tag || 0x00 || canonical-json)
```

The writer:

1. writes and fsyncs the payload;
2. rereads and reconstructs it;
3. writes and fsyncs the manifest;
4. rereads and reconstructs it;
5. writes and fsyncs the final commit.

This is a producer ordering guarantee. A later loader cannot prove historical
write order; it proves that the current three-file state is complete, canonical
and exactly linked. It rejects extra/missing files, symlinks, hard links,
noncanonical bytes, unstable inode snapshots, wrong sizes, wrong hashes and
wrong externally supplied commit IDs.

The filesystem is not claimed immutable. The campaign records a
content-addressed byte snapshot and requires the three artifact bytes to remain
identical before and after both warm occurrences. The verifier checks the
original snapshot both before and after its evaluation replay.

## 5. Strict model-only loader

The loader parses the exact transported V3 model, thresholds and four
model-derived candidate requests. It then performs a candidate-only semantic
replay:

```text
44 resolutions
34 computed
10 reused
```

This replay must reproduce:

- the exact four frozen candidate request IDs;
- the exact four frozen candidate inner-audit IDs;
- the exact canonical 30-node lower payload byte for byte.

Only then is a verified lease minted and the 30 bindings seeded into a new
child-local cache. The manifest does not supply expected candidate audit
documents or the selected certificate to the worker. Occurrence artifacts
retain load receipts, all resolution documents, root commitments and audit
IDs; full audit payloads are recomputed by the verifier rather than copied as
trusted expected answers.

The warm process imports the matching-buffer module so a fail-closed guard can
replace its ground entry points. Therefore V0-054A does **not** claim
kernel-module-import freedom. It claims:

```text
target kernel instance available = false
kernel access guard installed = true
warm transition calls = 0
warm action-catalogue calls = 0
warm ground-optimizer calls = 0
```

Tests exercise the guard against `initial_distribution`, `actions` and `step`
and verify that the original methods are restored afterward.

## 6. Fresh-process execution and untrusted output

Two stable logical occurrence IDs are preregistered:

```text
warm occurrence 1 =
  6291c9f3e29ce6bd782d1fbdfc1d05eb016aef10b0b69e8605acbbd9c079177c
warm occurrence 2 =
  44ba0b14093527880475a57689f6bfd828af7451fc4342e860bc938a35429cac
```

Each uses a separate `python -I -s -B` process with a sanitized environment.
The parent verifies the actual child PID from the process handle. PIDs are not
included in deterministic content IDs.

Each process evaluates three matched arms:

| Arm | Cache rule | Computes | Hits |
|---|---|---:|---:|
| `REQUEST_RESET` | reset before every request | 55 | 0 |
| `OCCURRENCE_RESET_GLOBAL_DAG` | one empty DAG for the occurrence | 35 | 20 |
| `DURABLE_CROSS_PROCESS_CONTINUATION` | seed the committed 30 lower nodes | 5 | 50 |

Across the two occurrences the totals are respectively:

```text
110 / 0
70 / 40
10 / 100
```

The durable arm constructs five fresh `R` roots per occurrence and zero lower
nodes. Relative to occurrence-reset, it avoids 60 lower constructions **inside
the two worker executions**. This is not a total-work saving: checkpoint
construction, loader replay, process/I/O work and trusted host verification
remain real work.

Child output is untrusted. Before minting the campaign success, the parent:

1. loads the checkpoint itself into a verified lease;
2. derives every load receipt, request, resolution, root, proposal and audit
   commitment with the same pinned proof implementation;
3. byte-compares each entire child occurrence document to that lease-bound
   derivation.

The host verification telemetry is reported separately:

```text
parent checkpoint semantic replay = 34 computes / 10 hits
parent worker-output verification = 190 computes / 140 hits
```

This duplicate operational validation is intentionally visible. A
structurally valid but lease-foreign candidate audit commitment must be
rejected before a success artifact exists.

Both occurrences derive:

```text
selected schedule = A0A0
semantic key = (0,1,0,1,0,1,0,1)
selected plan =
  0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb
selected inner audit =
  6a68944dba08b7b2266cd1376d60569de753d02cbcfab29f7edc34c337926d54
```

The V0-053 wrapper audit ID is a different identity layer and is not
substituted for the inner audit ID.

## 7. Evaluation replay and its limit

The evaluation verifier:

1. strictly loads and snapshots the original checkpoint;
2. checks its identity chain against the claimed campaign and V0-053 source;
3. reruns the V0-054A producer in a new temporary store with two new child
   processes;
4. requires exact deterministic campaign-document equality;
5. snapshots the original store again and rejects concurrent mutation.

This is fresh-store/fresh-process deterministic evaluation replay, not an
independently implemented proof algorithm or a separate codebase. It calls a
private producer core rather than trusting the public wrapper, but shares the
same pinned semantic implementation. The specification must not describe this
as algorithmic independence.

Hash chains establish canonical bytes and linkage. Semantic authority comes
from strict typed parsing, source identity pins, exact model-derived replay,
parent-output binding and the registered regressions—not from hashes alone.

## 8. Attack and regression requirements

Required negative controls cover:

- wrong external commit; extra, missing, truncated or tampered artifacts;
- symlink and hard-link substitution;
- fully re-signed `R` injection, missing node, hidden-value poison and wrong
  parent topology;
- fully re-signed source build/rebase/evidence/request/audit/execution identity
  substitutions;
- copied owner authority;
- reordered/foreign roots, proposal mismatch and occurrence collision;
- deleted, reordered or forged cache-resolution documents;
- a structurally valid but untrusted worker result;
- original-store mutation during evaluation replay;
- actual guarded calls to ground-kernel entry points.

Two fresh canonical runs must yield identical deterministic IDs before the IDs
in section 10 are frozen.

## 9. Work-accounting boundary

V0-054A exposes diagnostic proof-node compute/hit counts, process-launch count,
occurrence artifact sizes, upstream source call counts, and explicit zero
ground-call fields. It does **not** yet implement the complete
`CounterRegistryV1`/`WorkVectorV1` coverage required by Phase 3E.

Consequently:

- no complete native route-cost vector is claimed;
- hard-coded structural zero fields are backed by process isolation, exact
  replay and negative guard tests, but are not a substitute for future
  production-wide counter instrumentation;
- no scalar, amortization, sample-efficiency or break-even claim may be
  inferred from `10/100` or the 60 avoided worker-local constructions.

All economics and counter Gates remain `NOT_RUN`.

## 10. Canonical V0-054A identities

The production run and the verifier's fresh-store/two-fresh-process replay
produced byte-identical campaign documents and freeze:

```text
durable protocol ID =
  764fc56721c2b65fc3c55b644053814715b2bb2507046f4af80e34c7d8eed13e
lower proof payload ID =
  cdba69f2520255561ad7708b2037faae36d64ca69189328e4d50e70de172f6aa
checkpoint manifest ID =
  3cec7e67f116cc9ec94166e9340afd463b8fca7116872d1f0549aace7312ba7d
checkpoint commit ID =
  a4f5ef9fa083d04c9e3e8bc847c137588433b804e7c4f9c423a8cf64c08fbaa3
checkpoint byte snapshot ID =
  74510d7e4ec5fbcb701ac9dbeed8c5d9ad718059c8fe2c6e65ab98d69feb922f
warm occurrence 1 result ID =
  dbee0b5aa0eddcad7a1fba64b1d40469fe4d78c2e92c90dc539cebf1ab97e5fb
warm occurrence 2 result ID =
  3155b7b9420a04a55f353a2f0f5e61d311340df8dc2a5017216917664d186d4d
warm occurrence 1 request-reset arm ID =
  cf76a93b886e06e1d4a824c15174ae869e83ef808e3d4c9ef77820c110579f09
warm occurrence 1 occurrence-reset arm ID =
  fe18be01e1d8c7f0c5155bc7b463f02339407ee478d33cf215a56c5241062af2
warm occurrence 1 durable arm ID =
  9b27ed49fb66d76c89e9681782609d8dea40b14e06dee8e4959f3c61ddb7d6f1
warm occurrence 2 request-reset arm ID =
  31037707c15d424f058c1374a2216b3c7696ab2a913765521e1d5d0b30eb2ffa
warm occurrence 2 occurrence-reset arm ID =
  ec97730ed42458e13312f2859c6bdc9eb1424135b3f47ef110d8b69f0a228526
warm occurrence 2 durable arm ID =
  c4d71ed835b17f437158b1bdeafaa8552729958ce3deeb34a2a1e6b2ad4df940
campaign result ID =
  80a97998c5ef1c0a8323615b51ea9c8abcd786587ef877d84c00257eded43ce0
evaluation replay report ID =
  d4396c5b6207a31d8babf706a7481577b4a732ee0916bdb779580e1094560ce0
```

These IDs prove identity and integrity only within the semantic controls above.

## 11. Locked claims

Passing sets exactly:

```text
registered_h2_same_query_durable_proof_state_claimed = true
```

The implementation must keep all broader claim fields false and:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The sample-efficiency Gate does not block mainline construction. It remains a
later evidence-driven operator/meta-prior design problem.

## 12. Subsequent construction status

V0-054B has now separately passed on the registered six-tile seed-4 LMB
fixture. Its one-row action-local overlay, unrestricted-challenger frontier and
pre-execution action-indexed invalidation change the reachable semantic action
strictly from `A0A0` to `A0A1`; details are frozen in
`specs/H2_ACTION_LOCAL_SEMANTIC_SWITCH.md`.

That result does not overwrite this same-query persistence control. The next
Gate must compose the semantic switch with durable proof storage or a
preregistered multi-occurrence workload, without claiming sample/work
reduction before matched accounting exists.
