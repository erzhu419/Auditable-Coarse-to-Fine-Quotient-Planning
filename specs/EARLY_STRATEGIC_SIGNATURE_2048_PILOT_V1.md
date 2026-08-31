# Early Strategic Signature 2048 Pilot V1

## Status and purpose

This is an outcome-blind **feasibility pilot**, not a confirmatory experiment.
It asks whether eight accepted actions from a natural deterministic-tape 2048
opening contain enough strategic information to distinguish stronger from
weaker policies within the already completed u005 resource-candidate cohort.

The pilot may select or reject a representation for a future fresh
confirmatory experiment.  It cannot establish human expertise recognition,
real-game generalization, causal benefit from the representation, or transfer
to Layered Matching Buffer / Yang Le Ge Yang.

## Frozen parent cohort

- Parent protocol: u005 protocol
  `38c19039d83af72f80333674451ccc968a4df9df834a6e8622af21157bf27393`.
- Parent source commit:
  `70bb7726f220d6ad7eb6ab83f5207186d9f7f42a`.
- Policies: the final `RAW_PLUS_RESOURCE_STATE_ONLY` model for each of the 24
  u005 seeds `760101` through `760124`.
- Parent RAW and rotated-control policies are excluded.  This prevents arm
  identity from acting as an expertise label.
- No u005 evaluation score is used to assign the pilot labels.

The pilot protocol binds the exact candidate job execution IDs and model file
names from the retained u005 launch manifest.  Model files remain on the
server; they are not copied to the local workspace.  Before collection, the
existing u005 evidence join must close the exact 72 parent jobs across worker
status, JSON result, model, and log artifacts.

## Independent evidence tapes and labels

Each policy is evaluated on two new, disjoint deterministic tape roots:

1. `LABEL`: 64 complete games.  Mean total merge score is the independent
   policy-performance quantity.
2. `PREFIX`: 64 games, retaining only the first eight accepted/legal actions
   and the resulting nine observed states.

All policies face the same episode indices within each tape family.  The two
tape roots differ from one another and from all u005 training/evaluation roots.

Policies are sorted by `(mean LABEL score, training seed)`.  The lowest eight
are labelled `NOVICE`, the highest eight `EXPERT`, and the middle eight are
excluded from classifier fitting and scoring.  The policy seed is the
statistical cluster.  Prefix episodes are repeated measurements, not 1,024
independent statistical units.

## Prefix representations

Every representation is computed only from the nine observed prefix states,
the eight selected actions, their merge scores, and deterministic pre-spawn
swipe afterstates.  No future spawn, label-tape score, later state, or terminal
outcome beyond the observed prefix may enter a feature.

No per-state board canonicalization is allowed.  The physical orientation is
held fixed across the trajectory so that moving the maximum tile between
corners remains visible.

### RAW_PREFIX (184 dimensions)

- Nine physical-orientation boards, 16 ranks each, normalized by goal rank:
  144 dimensions.
- Eight actions as four-way one-hot values: 32 dimensions.
- Eight merge scores transformed as `log2(score + 1) / goal_rank`:
  8 dimensions.

### RAW_PLUS_ROTATED_REDUNDANCY (248 dimensions)

Append to `RAW_PREFIX` the normalized 180-degree rotations of prefix states
0, 2, 5, and 8 (64 dimensions).  This is a width-matched deterministic
redundancy control and adds no information.

### RAW_PLUS_STRATEGIC_PREFIX (248 dimensions)

Append to `RAW_PREFIX` a 64-dimensional trajectory block:

- final state-only resource vector (16);
- mean state-only resource vector over the nine states (16);
- cumulative harmful changes for core resource coordinates 0 through 7 (8);
- cumulative beneficial changes for core resource coordinates 0 through 7
  (8); and
- 16 trajectory summaries: maximum-tile corner residence, fixed-corner
  residence, maximum-tile corner switch count, maximum-tile displacement
  count, unique maximum-tile cell count, maximum-rank gain, prefix merge
  score, minimum empty slack, minimum directional-flow liquidity, maximum
  irreversibility risk, mean and maximum chosen-action resource regret,
  resource-optimal action match fraction, action diversity, immediate
  opposite-direction reversal fraction, and observed-prefix terminal flag.

Resource regret compares the selected action with every currently legal action
using only the deterministic swipe afterstate before a random tile spawn.  The
same frozen state-only resource quality is used for all choices.

## Fixed analysis

- One L2-regularized logistic regression per representation.
- Standardization is fitted on training policies only within each fold.
- Each training fold gives the novice and expert labels equal total loss
  weight.  This prevents the fixed 8-versus-8 cohort composition from leaking
  the held-out label through a 7:8 or 8:7 intercept shift.
- Fixed optimizer: SciPy L-BFGS; no hyperparameter search.
- Leave-one-policy-out prediction: all prefix rows of the held-out policy are
  excluded from fitting and standardization.
- Metrics: tie-safe AUROC and Brier score.
- Uncertainty: 2,000 fixed-seed paired policy-cluster bootstrap replicates.
  Whole policies, including all 64 prefix rows, are resampled.

## Provisional design signal

This is explicitly not a scientific success Gate.  The strategic
representation is eligible to freeze for a fresh confirmatory experiment only
when all of the following hold:

- AUROC is at least 0.80;
- the policy-cluster 95% AUROC lower bound is at least 0.75;
- the paired cluster-bootstrap 95% lower bound for AUROC improvement is above
  zero against both `RAW_PREFIX` and `RAW_PLUS_ROTATED_REDUNDANCY`; and
- the paired cluster-bootstrap 95% upper bound for Brier difference is at most
  zero against both controls.

Irrespective of this signal, the result document must state
`scientific_success_claimed=false`, and economics, scalar calibration,
break-even, and official execution Gates remain `NOT_RUN`.

## Decision after the pilot

- If the provisional signal is positive, use the frozen representation and
  power estimate to preregister a fresh-policy, fresh-seed, fresh-tape
  confirmatory experiment before observing its outcomes.
- If it is negative, do not move checkpoints, choose a favorable subset, or
  relabel this pilot.  Diagnose descriptively and either redesign once under a
  new pilot identity or stop this representation line.
- LMB/Yang transfer begins only after a 2048 confirmatory experiment passes;
  it receives a separate domain adapter and separate labels.
