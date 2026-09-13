# Controlled predictive quotient: development V1

## Question and scope

Can a finite model of standard 4×4 2048 merge state distinctions while preserving action-conditioned multi-step reward, failure and goal predictions? The deliverable is an executable stochastic quotient consumed repeatedly by a planner. This is a new development method, distinct from the frozen U005 GRU representation used to classify player skill.

Source base: `8dcd411b9c662448f283a8bc83c736e148bb3f54`. Worktree: `acfqp-controlled-predictive-quotient-exploration`. Branch: `codex/controlled-predictive-quotient-exploration`. The [diagnosis review](GPT6_DIAGNOSIS_REVIEW_20260908.md) records the evidence and rationale.

## Data and method

Use explicitly declared public dense rank-valued boards from the same standard 4×4 swipe/spawn engine as U005, with every legal UP/DOWN/LEFT/RIGHT action and every positive-probability spawn outcome. Each state includes remaining horizon. Expand the entire declared finite horizon, retaining goal and failure terminal distinctions. Reaching the node budget stops with an error instead of silently trimming action/outcome coverage. Horizon cutoffs are not loss events.

The reference model enumerates the public mechanics. Independently sample a fixed number of outcomes for every active state/action row. Both the complete-state empirical model and learned quotient receive exactly those sampled rows and the same state/status/legality coverage. An exact full-state model and exact reference quotient remain privileged development comparators. Construction, sampling, reference planning and audit costs are separately visible.

Learn the partition backwards in horizon. States can share a cell only when they have identical terminal status and legal actions, and each action has similar expected reward and next-cell probability distribution. Compare each proposed member with every existing member of its cell; do not accept a chain of pairwise-neighbor links as a diameter bound. Compile the uniform mean of member transition rows into nominal cell transitions. Preserve stochastic distributions rather than matching individual random outcomes.

This is tabular learning of controlled predictive equivalence on supplied coverage, not a neural encoder or a claim to discover unseen-state features. The exact reference is the zero-tolerance version of the action-response construction (subject to ordinary floating-point numerical precision), not a global optimum over all approximate abstraction classes.

## Comparisons and planning

| Model | Available transition probabilities | Role |
| --- | --- | --- |
| Full-state empirical | Shared sampled rows | Matched information planning baseline |
| Controlled predictive quotient | The same sampled rows | New state-merging method |
| Action-outcome shuffled quotient | The same rows with action/outcome association rotated within each state | Mechanism perturbation |
| Full-state exact | Public exact kernel | Finite ground comparator and audit source |
| Reference quotient | Public exact kernel | Privileged development existence diagnostic |

The action perturbation keeps legal action names but rotates their complete outcome rows within each state with at least two legal actions. A degradation is an empirical observation, not guaranteed in every board/query; invariant or symmetric actions can make a control uninformative. Opaque state renaming is checked separately for unchanged planning results and partition membership up to relabeling.

Plan several fixed reward/risk/goal queries after compiling each model once. A query maximizes expected normalized merge reward, minus a terminal-failure penalty, plus a terminal-goal bonus. These scalar preferences do not implement a chance-constrained policy frontier. The planner traverses only its compiled cells and rows; future decisions consume predicted cells, without re-encoding a true board between planning steps.

Then freeze that abstract policy and evaluate its lift on the exact development model. Report predicted versus realized expected reward, failure and success, and scalar objective difference from the exact comparator. Auditing may read ground rows; those reads are separate from planning. The first cut measures finite errors instead of integrating repair/fallback.

## Run the local development slice

From this exploratory worktree:

```bash
PYTHONPATH=src python3 scripts/run_controlled_predictive_2048_development_v1.py \
  --output reports/controlled_predictive_development_v1.json
```

The defaults are horizon 3, at most 30,000 layered states, 64 samples per legal
state/action row, local sampling RNG seed 73129, reward tolerance 0.01 in
`merge_score / 2048` units, and total-variation tolerance 0.2. These are
development settings, not a registered confirmation Gate. The three public
boards are printed in the output JSON. No transition closure, checkpoint or
training matrix is written; the small report records the actual observations.

The complete policy is solved for all compiled cells. This also covers cells
that an exact audit can reach through incoming transitions missed by finite
sampling. All of that DP work is charged. The same compiled models answer the
three queries; component prediction and independent exact policy audit are
separate from the optimization.

## Measurements and interpretation

Record active cells, state/action entries, successor entries, actual DP traversal counts, serialized nominal model bytes, and mapping storage separately. Include preprocessing/enumeration counts, sampled transition draws, partition-construction time, per-query planning time and audit work. Query count shows reuse of the same compiled model. A small rule program or zero mechanics calls in the planner does not itself establish small total work.

Report both empirical information-matched comparisons and exact reference comparisons. State compression only counts reductions in the active decision layers; do not inflate it using the many horizon-zero leaves. Total storage also includes the ground-to-cell map needed to lift a policy. No scalar cost conversion, break-even or full-pipeline sample-efficiency claim is made from these counts.

There is no PASS threshold in this exploratory slice. Report the observed joint behavior of quality, compression and planning effort. Keep unfavorable controls and any lack of actual speedup. Threshold selection or a model picked from these observations would require independent confirmation to establish a scientific claim.

## Validation and scope limits

Focused regression cases exercise a real abstraction failure: states with identical best value but reversed preferred actions must remain distinct; an aliased state pair with equal immediate responses but different later risk must split through successor responses. Also verify probability conservation, stochastic multi-step evaluation, preservation of goal/loss versus horizon cutoff, matching samples across primary arms, and all-action closure on the supported 2048 fixtures. A failed check changes the implementation before development results are interpreted.

Frozen U005 remains the original historical FAIL. Its classifier has no planning interface, so it is not represented as a nominal planning arm. No U002–U006 training/evidence artifacts are inputs, no old encoder is retrained, and no formal identities or tapes are created. This local development run does not launch a new confirmation campaign.

This scope has no unseen-state generalization, natural-opening full episodes, independently held-out query families, deployment certificate or integrated local repair. Exact coverage enumeration is expensive privileged setup and must remain in the reported construction cost. The first experiment supports only decisions about what to develop next.
