# Decision-Point Strategic Signature 2048 Pilot V2

## Status and question

This is one fresh exploratory feasibility assay. It is not a confirmatory
experiment and cannot repair the failed early-opening V1 Gate.

V1 asked whether the first eight accepted actions immediately after a new
2048 game starts identify stronger policies. Its frozen strategic arm had
AUROC 0.3155 and failed three of six provisional components. Independent
replay found no label, AUROC, grouped-fold, or bootstrap implementation error.
V1 remains `FAIL`.

V2 changes the estimand to match the motivating strategic observation: given
a board on which preserving or moving a unique maximum corner tile is an
actual choice, do the next eight accepted actions distinguish stronger from
weaker policies? A positive V2 result applies only to such matched resource
decision points, never to the first eight actions after reset.

## Frozen policies and labels

- The 24 policy checkpoints are the exact u005
  `RAW_PLUS_RESOURCE_STATE_ONLY` final models, seeds 760101 through 760124.
- No checkpoint, policy subset, or checkpoint ordering changes after V1.
- Labels and mean scores are copied exactly from the retained V1 independent
  64-full-game label lane: bottom eight `NOVICE`, top eight `EXPERT`, and
  middle eight excluded.
- Policy seed is the statistical cluster. The 64 decision states are repeated
  measurements, not independent policies.

The protocol binds the retained u005 protocol and manifest, the retained V1
result identity, the exact label roster, and the clean V2 source commit.

## Policy-independent matched decision-state library

The protocol freezes 64 concrete boards before any V2 policy prefix is run.
They are generated without invoking any of the 24 candidate policies:

1. Start independent deterministic-tape games under the fixed action priority
   `DOWN, LEFT, RIGHT, UP`.
2. Take at most the first eligible state from each generator episode.
3. Scan at most 1,000 episodes and 20,000 accepted decisions per episode.

An eligible state must be active and satisfy all of the following:

- exactly one maximum tile, with rank at least 6 (tile value at least 64);
- that maximum is in a physical board corner;
- at least eight empty cells;
- at least two legal actions; and
- the legal set contains both an action that leaves the original maximum tile
  in its corner and an action that moves it away.

Eight empty cells guarantee that eight accepted actions can be observed even
if none of the first seven actions merges tiles. Each policy starts from the
same 64 frozen boards. For a state index, policies also share the same
deterministic spawn-tape coordinate. No board is selected using candidate
actions, V1 prediction errors, or V2 outcomes.

## Eight-action representations

All representations use the physical board orientation. No D4 or per-state
canonicalization is permitted.

`RAW_PREFIX` has 184 dimensions: nine observed boards (144), eight action
one-hots (32), and eight transformed merge scores (8).

`RAW_PLUS_ROTATED_RAW_PREFIX` appends 64 deterministic redundant dimensions:
the 180-degree rotations of states 0, 2, 5, and 8. It is the width-matched
control and adds no information.

`RAW_PLUS_STRATEGIC_PREFIX` appends a 64-dimensional strategic block:

- final and mean frozen state-resource vectors (32);
- cumulative harmful and beneficial change over the eight core resource
  coordinates (16); and
- 16 fixed decision-trajectory summaries, including maximum-corner residence,
  the frequency of genuine preserve-versus-break opportunities, preservation
  and break choices when such opportunities occur, normalized resource regret,
  resource-optimal action matches, slack, liquidity, irreversibility, movement,
  score, diversity, and terminal status.

For every legal action at an observed state, let the unchanged V1 resource
ordering give pre-spawn quality `U(s,a)`. Chosen-action regret is

```text
(max_legal U(s,.) - U(s,a)) / (max_legal U(s,.) - min_legal U(s,.))
```

when the legal quality span is positive, and zero otherwise. The resource
weights are not refitted. Features can use only the frozen start state, the
next eight observed actions/states/merge scores, and deterministic pre-spawn
swipes. They cannot use V1 labels, later play, or full-game outcomes.

## Fixed analysis and provisional signal

Analysis is unchanged from V1 except for a new fixed bootstrap seed:

- training-fold-only standardization;
- fixed L2 logistic regression, L2 strength 1, SciPy L-BFGS;
- grouped leave-one-policy-out prediction;
- equal total novice/expert training weight inside every fold;
- tie-safe AUROC and Brier score; and
- 2,000 paired stratified policy-cluster bootstrap replicates, seed 180002.

The strategic arm receives a positive provisional design signal only if all
six original requirements hold:

- AUROC at least 0.80;
- policy-cluster 95% AUROC lower bound at least 0.75;
- paired AUROC-difference lower bound above zero against each control; and
- paired Brier-difference upper bound at most zero against each control.

This is not a scientific success Gate. The result must always record
`scientific_success=false`, `scientific_success_claimed=false`, and economics,
scalar calibration, break-even, and official execution as `NOT_RUN`.

## One-way decision rule

- If V2 passes, its representation and a fresh power calculation may be used
  to preregister a new-policy, new-training-seed, new-label, new-state-library,
  and new-tape confirmatory experiment. V2 itself remains exploratory.
- If V2 fails, stop this 2048 short-signature representation line. Do not flip
  labels or probabilities, move the decision threshold, select policies or
  states, change the window, or create a third exploratory rescue.
- Layered Matching Buffer / Yang transfer remains blocked unless a later fresh
  2048 confirmatory experiment passes.
