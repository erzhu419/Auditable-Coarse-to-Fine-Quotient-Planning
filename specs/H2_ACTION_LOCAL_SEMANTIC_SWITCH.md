# H2 action-local semantic switch (V0-054B)

Status: registered finite construction control
Contract version: `1.18.0`
Schema version: `1.0.0`
Profile key: `lmb_h2_action_local_semantic_switch_v0`
Model-only proof subprofile:
`lmb_h2_action_indexed_semantic_switch_v0`

## 1. Purpose

V0-054B closes a narrower but more semantic construction gap than V0-054A.
It checks that a failed H2 proof can identify one missing unrestricted
challenger action, acquire exactly that ground row, append it to an immutable
query-local model epoch, invalidate exactly the action-indexed proof cone, and
then replan to a **strictly different** certified contingent action.

The control implements the project-level loop:

```text
partial reusable model
  -> abstract H2 planning and sound audit
  -> failed unrestricted-value obligation
  -> non-authorizing challenger frontier
  -> one frozen row request
  -> one authoritative ground transition
  -> immutable model epoch
  -> reverse-closure proof invalidation
  -> replanning and recertification
```

It does not claim automatic coordinate invention, learned dynamics, a generic
minimality theorem, cross-query reuse, sample savings, total-work savings, or
workload economics.

## 2. Registered exact fixture

The authoritative LMB kernel is the literal:

```text
tile_types = (1, 0, 0, 0, 1, 1)
blockers = ({4,5}, {4}, {4}, {4,5}, {}, {})
type_count = 2
capacity = 3
max_layers = 4
```

The query is:

```text
x0 = LMBState(mask=32, buffer=(0,1), ACTIVE)
H = 2
delta = 0
normalized-regret tolerance = 0
R_max = 4
match reward = 1
terminal-clear reward = 1
```

The exact canonical state IDs are:

```text
x0 = 923ac69167104293200e5f71263951ec6207d04b576d759fa28f589ce5940c37
x1 = 52acc4ceec0b25ef96c6c039e39adfdd5cbd728d9b974b7ebb029e4a7ec62226
```

At `x0`, the only legal action is `S = tile 4`; it deterministically reaches
`x1` with zero reward and zero failure. At `x1`, four actions are legal:

- `M = tile 0`, which completes the buffered type-1 triple and yields reward 1;
- `N_1 = tile 1`, `N_2 = tile 2`, and `N_3 = tile 3`, each yielding reward 0.

All five transitions are deterministic, safe, and nonterminal at this H2
boundary. Their exact ground-row IDs are:

```text
S   = cf0ebe94dc11825e0f1aa820487a5439efd1615d5fd2b95b16346f61c9b8274b
M   = a5bf62ceb55ad0f6624a52b21a0d5f52739d5b2fbd3db8198536ccb250aa4ae0
N_1 = a5a288985739f75fc7540a5d0df7b0d4a5e6d56b12989fb596b9dcdf4712b8d6
N_2 = c4566f8e43470f739188052a430a58cf8e3b956025f9d548885bbd1b64c40aa3
N_3 = db320fcc2bc7f7ad0fdbd4199f974574d581181e377f04c2c9465ffd3aab5503
```

The first model contains `S` and all three `N` rows but not `M`, hence its
coverage is `4 observed / 1 missing`. The final model appends only `M`, hence
its coverage is `5 observed / 0 missing`. The first model and its observations
must be constructed without calling `kernel.step`.

## 3. First planning and audit epoch

The deterministic supported policy chooses the canonical lowest-ID supported
`N` action at `x1`. Its reachable H2 value and failure probability are:

```text
V_supported = 0
P_failure = 0
```

Because the trusted complete action catalogue still contains the missing
challenger `M`, the unrestricted H1 upper at `x1` and propagated H2 upper at
`x0` are both 3 under the registered reward bound. Therefore:

```text
normalized regret = (3 - 0) / 4 = 3/4
audit outcome = FAILED
```

The old selected-policy support frontier is insufficient: `M` is not on the
selected supported path. It must not authorize the acquisition.

## 4. Unrestricted challenger frontier

V0-054B introduces `UnrestrictedChallengerFrontierV1`. It is derived from the
failed normalized-regret root through the exact obligation chain:

```text
failed REGRET_N root
  -> U0(x0, h=2)
       |- S row
       `- U1(x1, h=1)
            `- Q_M
                 `- unique missing maximizing challenger M
```

The frontier is diagnostic and non-authorizing. It must bind the first model,
query, thresholds, failed audit, proof-node addresses, trusted complete action
catalogue, unique missing row, and exact remaining horizon. It cannot itself
call the kernel or grant transition access.

An `ActionLocalRowNecessityProofV1` independently binds that frontier to the
one-row request. Only the frozen request authorizes the exact `(x1, M)` call.

## 5. Exact acquisition and immutable overlay

Before the request is frozen:

```text
ground transition calls = 0
```

After it is frozen, the authority may call `kernel.step(x1, M)` exactly once.
The receipt and evidence bundle record the deterministic successor, reward 1,
failure false, and terminal false. No other state-action pair is authorized.

The operational authority is a live, owner-bound, non-copyable, single-use
capability. During the registered run a process-local non-reentrant gate
temporarily owns `LMBKernel.step`. It verifies the frozen canonical callable,
module source, step source, and the gate execution entry's module/qualname/source
digest before installation; rejects a preinstalled wrapper/fake or replaced
gate entry; rejects every call before request activation, every foreign
state/action, every second call and every concurrent/reentrant run; and records
the actual call inside a guard that closes directly over the frozen canonical
implementation.
Receipt and successful result retain the same live owner. Consequently a
golden-looking receipt or hard-coded access trace without the monitored call
cannot mint a passing result.

The final model:

- preserves every first-epoch row byte-for-byte;
- appends exactly the `M` row;
- keeps the same query and complete action catalogue;
- receives a new content ID and epoch number;
- records exact delta `added={M}`, `removed={}`, `changed={}`.

## 6. Action-indexed H2 proof dependency

The reusable lower proof graph has exactly 18 nodes:

```text
5 ROW
2 Q            (Q_N, Q_M)
2 U            (U1, U0)
2 PLAN         (PLAN_N, PLAN_M)
2 REGRET       (REGRET_N, REGRET_M)
2 RISK         (RISK_N, RISK_M)
2 COVERAGE     (COVERAGE_N, COVERAGE_M)
1 SELECTION
```

Each epoch also rebuilds three noncacheable `R` roots: candidate `N`,
candidate `M`, and selected candidate.

First epoch:

```text
lower computes = 18
lower hits = 0
fresh roots = 3
total computes = 21
```

The direct changed address is `ROW_M`. Reverse-closure invalidation must derive,
not hard-code, the following ten affected lower nodes:

```text
ROW_M
Q_M
U1
U0
PLAN_M
REGRET_N
REGRET_M
RISK_M
COVERAGE_M
SELECTION
```

`REGRET_N` is affected even though `PLAN_N` is not, because its unrestricted
comparison upper depends on `U0`. The graph must contain exactly ten affected
and eight unaffected lower addresses. The eight unaffected addresses are
`ROW_S`, the three `N` rows, `Q_N`, `PLAN_N`, `RISK_N`, and `COVERAGE_N`.

The model delta and its complete 14-edge reverse closure must be derived from
the live first execution and frozen **before** final replanning. The live
runtime independently reconstructs those closure edges from its own 18-node
cache and accepts no incomplete, copied, stale, or foreign plan. Final
execution is unreachable without this pre-execution authority and must
recompute exactly the ten affected addresses while hitting exactly the eight
unaffected addresses. The post-execution manifest verifies the work against
the earlier authority; it does not create that authority after the fact.

Final epoch:

```text
lower computes = 10
lower hits = 8
fresh roots = 3
total computes = 13
```

Every `R` root must be fresh. A cache hit may be accepted only after exact
dependency fingerprints and recomputed semantic values agree.

Every epoch execution also carries exact, non-serialized model/query replay
inputs. A pure model-only evaluator independently reconstructs all 18 lower
node documents, both candidate audits, both candidate roots, the proposal and
the selected root, and requires document equality. Thus an attacker cannot
make a false formula result authoritative merely by re-signing the complete
descendant graph.

## 7. Final policy and certificate

After the `M` row is appended:

```text
V_supported = 1
U_unrestricted = 1
normalized regret = 0
P_failure = 0
audit outcome = CERTIFIED
```

The reachable H1 decision must switch strictly:

```text
first selected action = N
final selected action = M
Q_first(N) = 0
Q_final(M) = 1
```

This is not a tie-breaking change. The final plan must be independently
recomputed from the final model; changing only an action label or copied audit
document is invalid.

## 8. Mandatory attacks

Tests must reject:

1. any generator/literal mismatch in the registered fixture;
2. first-model construction that calls the ground kernel;
3. a support-only frontier pretending to authorize `M`;
4. a challenger frontier with the wrong state, action, horizon, or proof path;
5. evidence acquired before request freeze or more than one ground call;
6. a copied, foreign, overbroad or reused authority/receipt/result;
7. an overlay that changes, removes, or adds any row other than `M`;
8. a missing, post-hoc, hand-written or incomplete pre-execution reverse
   closure;
9. reuse of any affected proof node or any `R` root;
10. a policy-label switch without exact value improvement;
11. a copied final audit or a verifier that simply calls the public runner;
12. a preinstalled fake `LMBKernel.step`, an early/duplicate call, or a
    concurrent/reentrant gate;
13. a replaced gate execution entry that returns golden outcomes without
    calling the canonical step;
14. a fully re-signed DAG whose row semantics contradict the exact model/query
    replay.

## 9. Canonical identities

The passing registered run freezes:

```text
structural           55a22b7617349c2d89bd7b9be940597cd851fc2e9e2a04ec6444e21bfbc83bc0
fixture              c62be2d328d5a5ffc86d9b844c920b251345031e2667507ca7cc728e3c51cd92
query                aa6f149330c798d2650fea28d7d5b489389cb5a80d24f6feb8fc06fdececc7f8
first model          ba0da7534a75a20f3c77a1cd097c6864a60bb8778df0ef2de6b57089767e0f32
first DAG model      b986f0b8f1864e2139eabc3979fb9448f2fc39554ee4a80a734ca664ef525dab
first execution      cf36bf88a5cc41e3962e3b51bc87ba39eadb61827aabd909844934717eb51975
support frontier     a2f64571975a5047772cd7a2ca41469ad5d46b67851cc47cb01ba778e4588907
challenger frontier  ed6e64de6382eba3de37e64a4eec19aedca4461ab9f34c7870e7867aec4cfd37
necessity proof      0da69443e0be5a9f3c14dbcc854f72e11aaa561a756388e719763fe21840288f
request              2b48e517f78b32c0f63ed658b6b55e9cbdeeb896681d8ba48be95dc4d3c4630d
receipt              0dc2ac0508694145021721f73b7c068da371d879acf6e150fab764baa151cdad
evidence bundle      76b4d028d9cda285ed6692d940d7d5a2062f9bf7859eb5f01fe01426a3f2f85c
final model          764b2a8b754d22edc7356238f461b823db3bf4b206227cdb7c6a19751288dcff
final DAG model      da7f9fba48cd455dd1a7c68db4daa5ddba36040aed64a27aa57f54f2a9f28d2d
delta                fbd6a5e89f363b45f0198c55d2b63342fb053cb83e1ae3302aa06189185b5c73
pre-invalidation     fb6112135f098fc4144b24cbe9dec7ec4c727eabb0484f9ed8e4dbcf218d11c0
final execution      5d65fd780ca38a9e6c21314156eee9f94b9777566ec42737762e5ecec2cdd240
invalidation         f69fbdd143e68f19dc42d0f2a1c7ab76876433ebdca960770204fe689c0c1c17
overlay              0614d53923d44abae6ffbea765743bb11524ae33096dbe282eb9f4d2dc9824a2
switch witness       84848291d930d2390e5985839feb9f743be2ae6ccbe631f0e2db6cb56f5ec1c8
access trace         5754c78ec80163abdfdbb5a7b8f85c1a772f77e91710a436b2442e210449d721
result               1389019bf1b5eddd088246ec591a100fef243069615294d1c686e1242b24ffa1
verification         6d94adcc5a3a0605e6e9e1599c9861e1a96fcea6aa2c0413ae260a513a1cb41f
```

These are binding/integrity regressions for the registered semantics. A matching
hash is not, by itself, transition authority or a semantic certificate.

## 10. Claim locks

The positive claim is limited to the registered H2 fixture:

> A failed unrestricted-value proof identifies one off-policy challenger row;
> exactly that row is acquired and appended; action-indexed dependency
> invalidation preserves eight unaffected proofs, recomputes ten affected
> proofs, and changes the reachable contingent action from reward 0 to reward
> 1 before exact recertification.

The following remain false, null, or `NOT_RUN`:

- generic action-local minimality;
- generic H>1 completeness;
- durable or cross-query persistence;
- automatic coordinate/predicate invention;
- partial or learned dynamics beyond the registered exact row;
- sample, byte, CPU, wall-clock, or total-work savings;
- official execution;
- official scalar cost and break-even;
- workload-economics and counter-completeness Gates.

The serialized lock schema names these separately, including
`partial_dynamics_claimed`, `learned_dynamics_claimed`,
`byte_savings_claimed`, `cpu_savings_claimed`,
`wall_clock_savings_claimed`, `total_work_savings_claimed`, and the normative
case-sensitive `official_N_break_even = null`.

The next Gate must connect this semantic switch to durable proof storage or to
a preregistered multi-occurrence workload before any reuse or sample-tax claim
is widened.
