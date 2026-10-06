# V81: paired terminal action advantages and two policy-improvement rounds

Frozen 2026-09-13 before V81 behavior games, branch labels or evaluations.
V80's terminal-value regression deteriorated with more fixed-policy data. V81
instead learns action differences relative to the current behavior policy and
collects the next batch under the updated policy.

## Behavior and matched action consequences

Run three independent lifecycles 0/1/2, each with two improvement rounds 1/2.
Start from V77 H2_ONLY, using supplied V69 dynamics. In each round and each
query, play 12 fresh natural behavior games under the current policy. Queries
remain reward=(1,0,0) and risk_goal=(1,4,4). Environment seed is
8100000 + lifecycle*10000 + round*1000 + episode, episode=0..11; model seed adds
1000000. Queries share behavior seeds. All games start with two ordinary tiles
and stop at WON, LOST or 2000 actions.

From each completed behavior trace select the observations before actions at
floor(length/3) and floor(2*length/3), with duplicate indices removed. Retain the
actual behavior action as the reference. No evaluation observation enters this
selection. These roots sample the current policy's middle and later game states.

For every legal first action, including the reference, run two complete paired
continuations under the same current policy. Force only the first action; all
later actions come from the unchanged incumbent. Environment seed is
8110000000 + lifecycle*10000000 + round*1000000 + query_index*100000 +
root_index*100 + replica. Model seed adds 1000000000000; the first forced action
consumes no model uniforms, and the remaining policy stream is shared across
actions. Each branch stops at a true terminal or 2000 actions from its root.

Include the first action reward in every branch return. For each replica form
the complete vector difference (reward/2048, failure, success) between candidate
and reference. Average these paired differences over the two replicas, yielding
one label per nonreference action per root. If any action/replica is censored,
omit that entire root's fitting labels and retain its trajectories and cost.
Episode%5==4 is heldout; it never fits or selects the candidate. With 12 games
per query, this reserves episodes 4 and 9 and their selected roots.

## Executable policy update

Fit one three-output regression tree per query using only the current round's
labels: max_depth=4, min_samples_leaf=8, random_state=8101. Targets from different
incumbent policies are not pooled. Features are the current board's 36 V77 board
features, 36 candidate-minus-reference afterstate features, immediate score
difference/2048, and candidate/reference four-action one-hot vectors: 81 values.

The new policy retains the previous policy as its reference. On a decision,
obtain the reference action, predict each other legal action's entire advantage
vector, and select the maximum query-weighted advantage. The reference action
has exact advantage zero; ties at zero retain it. No separate acceptance gate
or confidence threshold is added. Predicted differences are not probabilities
or certificates and do not receive independent componentwise maximization.

Only the H2 base consumes model randomness (four uniforms per active decision).
Learned layers make deterministic predictions. Save the complete policy chain;
round two's source behavior and continuation policy is exactly round one's
learned chain. Fitting or prediction must not modify the frozen parent.

## Evaluation, cost and interpretation

After each update, evaluate CURRENT, FROZEN_1 (first learned policy), H2_ONLY,
SHORT_REF and TERMINAL_REF. The final two are existing V80 checkpoint-75 models
from the corresponding lifecycle, without refitting. At round one CURRENT and
FROZEN_1 are identical. Each method runs two fresh seeds per lifecycle and both
queries: 8190000 + lifecycle*100 + replica, model seed +1000000. Share these
seeds across rounds/methods/queries and rotate execution order. The 120 natural
evaluation games never affect acquisition, training or model choices.

Primary comparisons are final CURRENT-minus-H2 and CURRENT-minus-FROZEN_1, by
query and independent lifecycle. Report round-one results, wins/losses/cutoffs,
override frequencies, source-policy lineage, label dispersion, heldout errors
and actual new state coverage. Distinguish query response from decision quality.

The fixed ceilings are 144 behavior games, at most 288 selected roots, 2304
branch trajectories, and 120 evaluation games, all with 2000-action caps.
Thus source-branch sampling is at most 4,608,000 transitions; report actual
usage rather than representing this ceiling as expenditure. All V81 behavior,
branch and evaluation interactions are new and counted separately. FROZEN_1
pays only first-round acquisition/fitting plus its evaluation. CURRENT pays the
full chain. Charge retained V80 reference construction costs separately from
their new evaluation; do not sum shared method attributions as actual wall time.

This tests a new acquisition-and-improvement mechanism, not a single-variable
ablation against V80. Sparse paired return estimates can be noisy; the complete
vector target remains policy/query conditional. Middle/late behavior roots do
not cover every deployment state. Three lifecycles cannot establish general
strategic learning or precise superiority. Retain adverse updates and terminal
outcomes without retuning. U005 remains FAIL; U006 remains unstarted.
