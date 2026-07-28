# Observation-Driven Cross-Geometry Relational RAPM

## Frozen status

Contract `1.29.0`, schema `1.0.0`, and profile
`observation_driven_cross_geometry_relational_rapm_v0` define the completed
V0-065 construction Gate. The registered campaign passed with status
`CERTIFIED_REGISTERED_CROSS_GEOMETRY_RELATIONAL_RAPM_FAMILY`.

This is not a relabelled V0-064 result. The implementation constructs a
source-only relational coordinate proposal from three graph geometries,
builds three structurally disjoint target-local statistical RAPMs, replans
inside each target model, and performs one certificate-triggered coordinate
repair on Diamond. No source transition row or probability narrows a target
model.

The frozen implementation authority and top-level artifact identities are:

| Artifact | Content ID |
|---|---|
| foundation implementation SHA-256 | `6be5d16937c46ca4acc326e0b8150755546b52faf9118bd2bfd3620c7788aedb` |
| registered family | `2b1f0bdd691af61ecc237335418f7dbda982201e25cbfea8d2e96c32abec6537` |
| source observation bundle | `e57130992f9ce5fd6827b2375b44d6b6162b5b881dceedef93f7c5a4f4c29aea` |
| campaign source log | `831f3fe1ce9f478b27646e8ee0514416887ac2af1e594240c99a4ec2c66bcf5b` |
| source program registry | `a510772b71112eea06b0c23a6ac201aab9bf2a2f50ca46265a1a6a68c40f7bc0` |
| source coordinate proposal | `97a9fe1e1bb8a28e52f87ae702ec8d06f4e01597109e76500b3dcbb39775e736` |
| source synthesis metrics | `82522065485cc2d32287a978c4629bacbaa0c6d885ac3aa9358f25f5f242ae10` |
| statistical calibration | `76e63db69595cd0fb1bd995f523d98d554df18ff776dd22e0ad7475e38865c46` |
| campaign | `2399c56dd7378429cc08dabb52d7bb76c61bc26f7541dccb535badfe193a7d7a` |
| same-implementation verification | `ea29a7e0c885166c1b321df24a53edc37975fe680f9bc97f4fa38288830ea329` |

## Registered challenge split

Every registered context uses four vertices, rank cap 6, rank-relative spawn
support `{low, low+1}`, `P(low)=99/100`, `H=2`, risk tolerance `1/20`,
uniform post-merge spawn position, post-spawn failure checking, and exact
rational reward accounting. Source/target rank identities and realized
closure sizes are:

| Split | Context | Low rank | Motifs | Complete H2 ground rows |
|---|---|---:|---:|---:|
| source | path `P4` | 1 | 6 | 36 |
| source | star `K1,3` | 2 | 6 | 36 |
| source | paw | 3 | 8 | 48 |
| target | cycle `C4` | 2 | 8 | 48 |
| target | diamond `K4-e` | 3 | 10 | 60 |
| target | complete graph `K4` | 4 | 12 | 72 |

All nine source-target graph pairs were exhaustively checked over the 24
vertex bijections and have zero isomorphism mappings. Source and target
structural IDs are disjoint.

A motif is generated mechanically from every graph edge carrying two equal
low-rank tiles and every possible third vertex carrying the high-rank anchor.
This deliberately includes geometrically unfavorable embeddings. Enumeration
uses graph incidence only: no D4 orbit, graph-key branch, named frontier,
graph automorphism prior, or target value signature enters the constructor.

## Frozen source-only synthesis result

The source closure contains 51 ground states and 120 complete state-action
rows. Its depth-two typed relational grammar enumerated 262 syntactic
programs and retained 42 distinct semantic programs, cumulatively
`(6, 12, 24)` at depths `(0, 1, 2)`.

The complete candidate search evaluated all 25 pairs formed by five
state-integer and five action-integer programs. Two pairs were admissible.
The deterministic selection rule chose:

```text
state  = cardinality_actions(legal_actions)
action = cardinality_cells(
           adjacent_filter(survivor_cell, occupied_cells)
         )
```

The proposal compresses 51 ground states to 4 abstract state cells and 120
ground rows to 7 anonymous support keys. It records 1,092 aliased row pairs,
four availability variants, transition alias width `99/100`, reward alias
width zero, and sound alias width `99/100`. These widths are intentionally
retained: the base coordinates are a sound coarse proposal, not an exact
cross-geometry homomorphism.

The exported proposal contains the coordinate ASTs, support-key schema and
the source-frozen optional program registry. It contains no source dynamics,
source decisions, target/query identity, target probabilities, or
certificate authority.

## Frozen chronology and accounting

The accepted execution order is:

1. Freeze the six-context family, nine nonisomorphism witnesses, source
   acquisition protocol, optional program registry and statistical
   calibration.
2. Acquire all 120 source H2 rows and complete the source-only coordinate
   search before accessing a target row.
3. Create an all-missing RAPM separately for each target structural ID.
4. Run a model-only audit. `FAILED_MISSING_SUPPORT` authorizes only the root
   stage, yielding respectively 16, 20 and 24 C4/Diamond/K4 ground rows.
5. Rebuild the partial target model and audit again.
   `FAILED_MISSING_SUPPORT` authorizes the observed continuation catalogues,
   yielding respectively 32, 40 and 48 additional rows.
6. Freeze a base target RAPM and run target-local abstract planning. C4 and
   K4 certify. Diamond fails closed with
   `FAILED_RISK_OR_REGRET`.
7. From that failed Diamond audit only, evaluate all four registered
   source-frozen refinement candidates. Select the smallest certifying pair,
   create a new immutable profile/model epoch, replan, and certify.
8. Audit two registered occurrences per target against the final
   context-local RAPM. Both occurrences add zero ground rows.
9. Run cold-ground, no-transfer, semantic-OOD, unregistered-OOD,
   permutation, transplant and raw-draw-tamper controls.
10. Replay the source proposal, six base/final model-epoch positions, six
    occurrence audits, six evidence attestations, six cold controls and six
    campaign controls with the frozen same-implementation verifier.

The three positive targets use 180 ground rows and
`180 × 65,536 = 11,796,480` replayable generative draws:

| Target | Root rows | Continuation rows | Total rows | Draws |
|---|---:|---:|---:|---:|
| C4 | 16 | 32 | 48 | 3,145,728 |
| Diamond | 20 | 40 | 60 | 3,932,160 |
| K4 | 24 | 48 | 72 | 4,718,592 |

The semantic-OOD path is included in the preregistered calibration and adds
48 rows and 3,145,728 draws. Thus the frozen statistical family covers 912
atom obligations. With 65,536 draws per row, radius `1/110` and per-atom
tail bound `1/25,000`, the exact finite-union tail upper bound is
`114/3,125` and the family confidence lower bound is `3,011/3,125 > 0.95`.

This accounting is evidence of statistical soundness, not sample
efficiency. In particular K4 materializes its complete 72-row H2 closure.

## Target results

Every registered target has exact cold-ground optimal failure probability

```text
99 / 5000 = 0.0198 < 1 / 20
```

and the target-local final plans have zero normalized reward regret. The
exact normalized two-merge rewards are `3/32`, `3/16`, and `3/8` for C4,
Diamond, and K4 respectively.

| Target | Base audit | Recovery/replanning result | Final failure upper | Final result ID |
|---|---|---|---:|---|
| C4 | `CERTIFIED` | no refinement | `230656215/5905580032` (`≈0.0390573`) | `2c8642f2b2bda9d638b0d171d4cc18d183ed6bf56c322c4284279259b692a6c5` |
| Diamond | `FAILED_RISK_OR_REGRET`, upper `1710883045099/3248069017600` (`≈0.526739`) | one failed-proof-triggered refinement, then `CERTIFIED` | `516701257/10737418240` (`≈0.0481216`) | `5699ef4f57794cfdd5c9d25a1466d8b91bc50fecea198a69062fcf6f21afa3fc` |
| K4 | `CERTIFIED` | target-local action availability drives a replan selecting action coordinate 2 for state coordinates 2 and 6 | `839745981/21474836480` (`≈0.0391037`) | `13a8c612ac977e7df650e45434f86c887a36514f4fe4f5a8a9325e3fb7658f13` |

Diamond selects exactly these already source-registered refinements:

```text
state refinement  = rank_degree_signature
action refinement = cardinality_cells(
                      adjacent_filter(survivor_cell, all_cells)
                    )
```

It evaluates four frozen candidates and performs zero target-time program or
primitive generation. The refinement trace ID is
`912b8af3be2f5c70a7998b233f3ac4e93c2fc6b299719252ef717517d768814c`.

The target identity and final proof chain is:

| Target | Structural ID | Context ID | Final profile ID | Final model ID | Final audit ID |
|---|---|---|---|---|---|
| C4 | `651dc6de911c771dac77dcd01b57c0c748696575cf77a4c789d756f6ad6158a1` | `962c47e77371ba8fda47d88bb71dd47981877fe2182dc3adbb732416c6507e94` | `3877a588ed1de8e1e59016a38668550231b908851daf7df5205c83c25be7cfa1` | `f42b2b19dedbb0362e20e0a237cdcd291886974f0716e94289c36760565f0f55` | `6807785a60b732db74052cc90a22cc07463ef58df510eeaff8bb61c9d4dffb3f` |
| Diamond | `ca273e5ebe70021f9ba87f3302356db0db78bdd0a36f63cb6415e65efeb5572d` | `dc17f34a033d12c0d94af923c7c01dc8fdccc2c8913aa2653c863d09b941d33d` | `5c6d11eaa1c671b1e638c24767392183eb8a921a30dadf6f5de1827023a108c5` | `45d1040efc4b6f0b44645ec2664217abe272a53f3d281ce767fc47c69d3494f6` | `b2169116f12b4583c787253c72a3adb87fd954e229224e8d3c15d94ea87cffcd` |
| K4 | `a8517c11e5310db97ffa7a87dabb5578585811fa18b48a61d3d71a668dfd2086` | `a536a894b0b712a609a77e29f1b91f85ec81c013f3f3d281d900c4c05a7aa231` | `3877a588ed1de8e1e59016a38668550231b908851daf7df5205c83c25be7cfa1` | `052e09b7b085d66e761053b016c1a91fc765efc989b486cff9a20a609cce6a02` | `efa03c530b571193a65a330c8513135e13b7ec0385bd688b2ffe84454ba3ed1e` |

C4 and K4 require no refinement, so their base and final profile/model/audit
IDs content-collapse. Diamond changes from base model
`3bf60454c7a5f02eeb83d84beb65a3fbc3b65e23504ee6d24f3f35cdbede98de`
to the final model shown above.

## Frozen control outcomes

The controls are Gate obligations, not optional diagnostics.

| Control | Frozen outcome |
|---|---|
| legacy V0-064 schedule | C4 `CERTIFIED`; Diamond `FAILED_RISK_OR_ALIAS`; K4 `FAILED_ACTION_UNAVAILABLE`; 1 certificate, 2 rejections, 0 false certificates |
| no transfer | three targets route to exact cold fallback; 0 abstract certificates; every fallback returns failure `99/5000` and matches its registered cold control |
| semantic OOD | 48 rows and 3,145,728 draws are charged; hidden vertex-colour mechanism verification fails; model construction is forbidden; fallback required; 0 certificates and 0 false certificates |
| unregistered topology | rejected before ground access; ground-access count 0 |
| identity isolation | pre-authorization, foreign-context evidence/model, stale-profile and cross-structural transplants fail closed |
| vertex permutation | permutation `(2,0,3,1)` preserves program IDs, support multiset, mapped certificate risk/value and policy; graph identity is not a feature |
| raw-draw tamper | one changed outcome nibble fails semantic replay |
| cold exact comparator | six campaign occurrences use no RAPM reuse and all reproduce failure `99/5000`; the full foundation additionally checks every target motif |

The top-level control IDs are:

| Control artifact | Content ID |
|---|---|
| legacy fixed schedule | `fe48e6d1bf152e24f0dd725f15324b1ef22afa1834f71d0a764ccf5db2b645df` |
| C4 no-transfer | `8ce8d3e34a69bf886d01f24d52728fb9ff529a040ed464418ad7393a13509ac7` |
| Diamond no-transfer | `0cb3bd97d8b94cba86169cc0c7d427c91941430ff7b2a147a8b6771341e04d31` |
| K4 no-transfer | `399e66c90217aa790c04250cf94674045eda531d246d3ca3c2ded90df24b6c25` |
| semantic/unregistered OOD | `1a00fa89770da182b529836b2266b44bb5103b2163444d078a253241ad192185` |
| permutation equivariance | `6d3567e04674bfdb72a5dbc9a7f3523a3c2f99dc3b65b9fcb581cb2fc281f4ab` |

## Verification coverage

V0-065 adds 33 focused tests:

| Layer | Test file | Count |
|---|---|---:|
| source-only relational graph core | `test_relational_graph_core_v1.py` | 12 |
| six-graph physical/statistical foundation | `test_cross_graph_relational_support_v1.py` | 9 |
| target RAPM campaign and controls | `test_cross_geometry_rapm_v1.py` | 12 |
| **V0-065 total** |  | **33** |

Together with the 17 V0-064 observation-driven relational-support tests,
the construction line has 50 focused tests.

The verifier is a same-implementation semantic and model replay. It verifies
raw draws, proposal selection, identity chains, six model-epoch positions,
six occurrence audits, six evidence attestations, six cold controls and six
control outcomes. It is deliberately not labelled an independent algorithm
verification.

## Acceptance boundary

Passing V0-065 licenses only:

> Within this preregistered finite four-vertex graph-merge family, a
> source-observed relational coordinate/support schema can cross three
> non-isomorphic held-out geometries; each target can build its own
> statistical RAPM, instantiate target-local statistical rows, compute a
> target-local contingent plan, and recover one missing relational
> distinction from a source-frozen optional registry only after a sound
> certificate fails.

The positive claim includes automatic source coordinate selection,
target-local dynamics, target-local replanning, exact cold-ground agreement,
one Diamond refinement, K4 action-availability-driven replanning, and
zero-row reuse on a second occurrence. K4's
`legal-action-count=6` base support key already occurs in source Paw; K4 adds
a target-local statistical row and a different target-local decision, not an
unseen base support key. Source-base-unseen support keys arise only after the
Diamond frozen-registry refinement.

It does not license:

- broad or unregistered graph generalization;
- a second-domain or variable-vertex-count claim;
- invention of new primitives or target-time programs;
- raw perception or unknown symbolic outcome support;
- source-to-target or cross-target dynamics transfer;
- cross-structural RAPM reuse;
- sparse target construction or sample efficiency;
- independent algorithm verification;
- official execution, scalar economics, or break-even.

The low-level graph/rank vocabulary, optional refinement registry, H2,
four-vertex topology family, spawn support and complete source observation
closure remain human-registered. All 180 positive target rows are acquired;
the Gate therefore demonstrates reusable relational planning structure, not
reduced first-context sampling cost.

`WORKLOAD_ECONOMICS_GATE`, `COUNTER_COMPLETENESS_GATE`, and
`SAMPLE_EFFICIENCY_GATE` remain `NOT_RUN`. `official_execution_allowed`
remains `false`; `official_scalar_cost` and `official_N_break_even` remain
`null`.

All 33 V0-065 focused tests and the stable 1,350-test repository regression
pass.

## Next construction Gate

The next Gate must remove the two remaining construction crutches rather
than enlarge this claim by wording:

1. replace the source-frozen optional refinement registry with
   observation-driven proposal of a genuinely new relational distinction;
2. avoid complete target H2 closure through proof-frontier-directed sparse
   acquisition on a larger or variable-vertex held-out family;
3. preregister a no-invention/OOD control where the available observations
   cannot support the needed primitive;
4. retain target-local sound envelopes, exact identity invalidation,
   cold/direct matched controls and zero-false-certificate requirements;
5. add an independent implementation/verifier boundary before making a
   broader algorithmic claim.

Only after real adaptive acquisition trajectories exist on that harder Gate
should a Laplace-style heuristic operator or KG-OP-style meta-prior be judged
against a matched no-prior route for sample-tax reduction.
