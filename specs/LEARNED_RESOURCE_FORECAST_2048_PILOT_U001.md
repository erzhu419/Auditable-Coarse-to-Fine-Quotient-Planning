# Learned Resource-Forecast 2048 Pilot U001

## Status and scientific question

This document freezes one new exploratory method family. It is not a third
attempt to rescue the failed hand-designed short-signature line.

The natural-opening V1 pilot failed (strategic AUROC 0.3155). The matched
corner-decision V2 pilot also failed (strategic AUROC 0.5754 versus raw
0.5831), and its one-way rule remains binding. Their policies, labels,
decision states, tapes, feature matrices, and outcomes are ineligible for this
pilot's Gate.

U001 asks a different question: can a representation learned without skill
labels from complete goal-terminated 2048 trajectories forecast future
strategic-resource dynamics, and, once frozen, add held-out predictive utility for identifying
stronger machine policies from exactly their first eight accepted actions?

The environment is the exact symbolic 4 by 4 standard-2048 engine. A complete
episode ends on reaching tile 2048 or on having no legal action. It is not a
continue-after-2048 score game, a visual/UI task, or a claim about human
players.

U001 is a feasibility pilot. Its result always records
`scientific_success=false` and `scientific_success_claimed=false`. A positive
provisional signal may only justify a fresh, separately ratified confirmatory
successor.

## Fresh policy population

The ratified protocol registers the 48 fresh base training seeds 781101 through
781148 and the three unchanged u005 policy-generator arms:

- `RAW_BOARD_STANDARD`;
- `RAW_PLUS_ROTATED_RAW_CONTROL`; and
- `RAW_PLUS_RESOURCE_STATE_ONLY`.

Each of the 144 seed-arm jobs runs the unchanged matched Double-DQN training
algorithm for 100,000 environment interactions. It saves inference-only online
network snapshots at exactly 25,000, 50,000, and 100,000 interactions. The
three snapshots are three policy-player identities, not three independent
training runs. All arms and checkpoints sharing a base seed stay in the same
data split and on the same execution host.

Seeds 781101 through 781132 are encoder/classifier train clusters. Seeds
781133 through 781148 are one-time test clusters. Generator arm, checkpoint, seed, host,
model path, training reward, and prior campaign results are never classifier
inputs.

Training tapes, model-training evaluation tapes, self-supervised trajectory
tapes, skill-label tapes, and eight-action probe tapes have distinct frozen
roots. No old u003/u004/u005/V1/V2 evaluation tape is reused.
Within each evidence lane, every player uses that lane's one shared frozen tape
root and the same episode indices. Player identity must not be appended to a
tape root: matched exogenous tile-placement tapes are part of the design.

## Three evidence lanes

All policy execution is greedy and all actions are legal accepted actions.

### Self-supervised trajectory lane

Only the 288 train-split policy players enter this lane. Each plays 16 complete
goal-terminated episodes. A deterministic sampler takes at most 32 windows per
episode, spanning the episode in increasing time order. Each window contains
eight transitions. For an episode with `T` transitions, let `N=T-8+1`. If
`N<=32`, all starts `0..N-1` are used; otherwise start `i` is
`floor(i*(N-1)/31)` for `i=0..31`. Targets are constructed at 1, 4, and 16 accepted actions
after the window endpoint, clamping to the terminal state when necessary.

The input token for each transition contains the 16 physical-orientation board
ranks divided by 11, one four-way action one-hot, and the merge-score rank
`log2(merge_score + 1) / 11`. Thus every encoder input is an 8 by 21 tensor. No D4
canonicalization is applied.

For each of the three future horizons, the target contains the 16 exact
state-only resource coordinates, normalized cumulative future merge-score
rank `log2(sum_of_future_merge_scores + 1) / 11`, and a
terminal-by-horizon indicator: 54 targets in total. The targets
use only that complete trajectory and the public state-only resource encoder;
they never read skill labels.

### Independent skill-label lane

Every policy player plays 64 complete goal-terminated episodes on the label
tape. Its fixed skill score is mean total merge score across those 64 episodes.
The train-player 25th and 75th percentiles are computed once using the
`inverted_cdf` rule. A player at or below the lower numeric threshold is
`NOVICE`; a player at or above the upper threshold is `EXPERT`; middle players
are retained for descriptive continuous analyses but excluded from the binary
Gate. The same two numeric thresholds are applied unchanged to test players.

Episodes are measurement repeats. The policy player is the prediction unit,
and the base training seed is the statistical cluster.

Every complete trajectory- and label-lane episode retains its compact full
accepted-action sequence. An independent verifier reconstructs the episode
from the registered lane root and episode index, then checks every transition,
the terminal state, total score, maximum rank, and (for the trajectory lane)
every sampled token and forecast target. It does not require policy argmax
re-execution on a different GPU, which could turn a nearly tied Q value into a
hardware-dependent false failure.

### Eight-action probe lane

Every policy player supplies 16 independent natural-opening probes. Each probe
contains exactly states `s0..s8`, actions `a0..a7`, and the eight merge scores.
No later state, terminal outcome, label-lane record, or trajectory-lane record
is available to a probe feature builder or classifier. An episode ending
before eight accepted actions is an implementation failure, not a replacement
opportunity.

The same 16 registered probe-tape episode indices are shared across train and
test players to form a matched policy challenge. The held-out unit is therefore
the base policy-training seed, not the opening. U001 does not test transfer to
unseen opening tapes; a positive result must reserve that question for a fresh
confirmatory successor.

## Frozen learned representations

The raw prefix is the 184-dimensional flattening of nine normalized physical
boards, eight action one-hots, and eight normalized merge-score ranks.

Both learned encoders are one-layer GRUs with input width 21 and hidden width
64 (16,704 parameters), followed during pretraining by the same linear
54-target forecast head (20,214 parameters total).
They use identical initialization, train-only examples, batching, Adam
optimizer (learning rate 0.001), batch size 256, 50 fixed epochs, and mean
squared error with equal weight over all 54 target coordinates. There is
no early stopping, hyperparameter search, checkpoint selection, or use of test
players. The encoder hidden state after token eight is the 64-dimensional
append block; the forecast head is discarded before skill labels are joined.

- `RAW_PREFIX`: the 184 raw dimensions only.
- `RAW_PLUS_PLAYER_SHUFFLED_FORECAST`: raw plus the 64-dimensional hidden
  state of the capacity-matched control encoder. Before any optimization, its
  complete 54-dimensional target rows are deterministically permuted among
  windows of the same policy player. The fixed permutation has no unchanged
  row when a player has more than one window. This preserves each player's
  target marginal and target-coordinate dependence while removing local
  future alignment.
- `RAW_PLUS_ALIGNED_RESOURCE_FORECAST`: raw plus the hidden state learned from
  the correctly aligned future targets.

The two encoders are frozen before the skill-label files are opened. A retained
encoder receipt records training loss by epoch for diagnosis, but no outcome
can select an epoch because only epoch 50 is eligible.

## Frozen skill classifier and metrics

Each representation receives a separate fixed L2 logistic classifier:

- standardization is fit on eligible train probes only;
- constant coordinates remain zero after centering;
- intercept is not penalized;
- L2 strength is 1;
- optimization is deterministic double-precision L-BFGS with fixed tolerance
  and iteration cap;
- total novice and expert weight is equal, and every player within a class has
  equal total weight regardless of its 16 repeated probes.

Predictions are made once for all eligible test probes. AUROC and Brier score
are computed over probes, while uncertainty uses 20,000 paired resamples of
the 16 test base-seed clusters. The same sampled clusters are used for all
three representations. Point estimates and confidence intervals are also
reported after averaging the 16 probe probabilities per player as a
descriptive robustness analysis; they cannot replace the registered Gate.

## Provisional design-signal Gate

Evaluation fails its prerequisites unless all 144 training jobs and all 432
player-evidence jobs complete with no failed job, 432 model snapshots, 288
trajectory-player artifacts containing 4,608 complete
self-supervised episodes, two forecast-encoder receipts, two frozen encoder
states, 432 label aggregates, and 6,912 exact eight-action probe records are
present with no failed, missing, duplicate, or foreign identity. The test set
must contain at least 16 expert and 16 novice policy players and at least eight
base-seed clusters represented in each class.

The provisional design signal is `PASS` only if all of the following hold:

1. aligned candidate probe-level AUROC is at least 0.80;
2. its paired cluster-bootstrap 95% AUROC lower bound is at least 0.75;
3. the 95% lower bound for aligned minus raw AUROC is above zero;
4. the 95% lower bound for aligned minus shuffled-control AUROC is above zero;
5. aligned Brier point estimate is no greater than each control; and
6. the 95% upper bound for each aligned-minus-control Brier difference is at
   most 0.01.

No component substitutes for another. A failure does not authorize label
flipping, alternate windows, post-hoc checkpoint subsets, new feature targets,
or another pilot with the same learned representation. A positive pilot only
authorizes a fresh confirmatory experiment with new training seeds, tapes,
identities, encoder initialization, and classifier predictions.

Because the self-supervised target jointly contains resource coordinates,
future merge score, and terminal timing, a positive Gate attributes utility to
the registered aligned forecast representation as a whole. It does not isolate
the resource-coordinate block by itself and does not support a human-player
claim.

## Execution and evidence boundaries

Formal identities are generated only after source, protocol, seeds, tapes,
architecture, and Gate are frozen. Before launch, one retained three-host
receipt scans `/home/erzhu419/mine_code` outside only the current source and
launch roots. The blocking tokens are the exact pilot identity, all 576
execution IDs, the five frozen tape roots, and the fixed results, status, log,
analysis, and retained paths. The 48 integer seeds remain in the receipt roster
but are not global execution identities: an unrelated project using the same
integer does not share this pilot's initialization, tapes, or execution
context. A consumed identity is never retried.
Failures are retained under their original identity; any authorized successor
uses a new ordinal and new execution IDs.

The manifest fixes the source, launch, results, status, logs, analysis, and
retained roots. Preparation, launch, workers, postprocessing, and retention
must use those paths exactly; substituting a fresh empty root cannot restore a
consumed identity. Training starts only when the fixed results/status/log roots
are absent on each host. Evidence starts only from each worker's exact 24 JSON
plus 72 snapshot training roster, with no foreign file or subdirectory.

Large trajectory arrays and model files remain on the execution servers.
Cross-host gathering uses a direct source-SSH tar stream into a gpu2-SSH tar
stream; bytes pass through the controller pipe but no large local archive is
written. Local inspection uses status streams, logs, manifests, result JSON,
and Gate summaries. Retention includes the ratified protocol, manifest, source
commit, gather receipt, status streams, logs, all result JSON, inference
snapshots, encoder states, predictions, Gate result, and an independent replay
report.

After all three hosts close their owned workers, a separate evidence-gather
authority runs on the local controller, where all three SSH aliases are
available. It validates each source host, then streams registered tar members
directly from `ssh source` stdout into `ssh jtl110gpu2` tar stdin; no checkpoint,
trajectory array, or archive is written to the controller disk. A fixed marker
allows only an interrupted evidence transport to resume. The exclusive gather
receipt is written only after a gpu2-side inspector sees six exact worker
directories, twelve closed status streams, twelve successful logs, and the two
closed dispatch streams. This transport never executes a training or evidence
job.

Postprocessing validates the history receipt, gather receipt, clean central
runtime and CUDA device, and the complete central inventory before creating its
one-shot status stream. Missing or foreign input evidence therefore remains a
retryable preparation failure. After analysis and the independent verifier,
the status stream closes with
`ANALYSIS_VERIFICATION_COMPLETED_RETENTION_READY` and explicitly does not claim
retention completion. The closed status is copied with all evidence; the final
exclusive retention inventory is the sole authority whose
`retention_complete=true` means retention finished.

LMB/Yang transfer is outside this Gate. It may begin only after a later fresh
2048 confirmatory experiment passes, and it would establish symbolic-domain
method transfer rather than human/UI transfer.
