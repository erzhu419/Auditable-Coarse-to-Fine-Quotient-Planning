# V83: learn a single terminating policy fragment with matching continuation

Frozen before new V83 source games, branch samples, or evaluation. V82 found that
continued P1 execution harmed every retained root. V83 changes both the learned
choice and its deployment: select a complete bounded controller once, execute
its commitment, then permanently return to H2 for that game.

## Controller and acquisition

Candidate options in tie order: H2, SPACE_1, SNAKE_1, SPACE_4, SNAKE_4. SPACE and
SNAKE are the existing V77 deterministic action policies. A fragment executes that
policy for exactly one or four active decisions, unless the game terminates first.
These primitives and durations are supplied; the learner selects them, not invents
them. At most one initiation is allowed per episode, including choosing H2.

Before initiation the controller runs H2. Initiation is the first active observed
board with at most six empty cells, immediately before its action. This same
observable trigger defines acquisition and deployment; no retrospective middle-game
root is substituted. H2 at initiation means no intervention for the rest of the
game. After a fragment the controller never re-enters a fragment in that game.

Each lifecycle 0/1/2 collects 12 new full H2 natural games per query, episode 0..11,
with checkpoints after 6 and 12 games per query. Reward=(1,0,0) and risk_goal=(1,4,4)
as before. Source environment seed=8300000+lifecycle*10000+episode; model seed adds
1000000. Record the first trigger root while playing, but finish and charge the
complete source game. A source game without a trigger supplies no root, with no
replacement game. Before the trigger, all methods use the same H2 behavior, so
acquisition does not depend on the previously learned option selector.

At every source root, run every option with eight paired terminal replicas.
Environment seed=8310000000+lifecycle*10000000+query_index*100000+episode*100+replica;
model seed adds 1000000000000. Unlike V82's conditioned first actions, these are
actual option policies at the root. Every active step consumes four model uniforms:
H2 uses its usual draws; a deterministic primitive discards four draws, recorded
separately, keeping subsequent H2 random streams aligned by environment step.
All games stop WON/LOST or after 2000 actions. Raw histories and work are retained.

For each replica difference the full (score/2048, failure, success) vector against
its H2 branch, then average eight differences to produce one label per non-H2
option/root. Include all fragment and subsequent H2 rewards. Any censored branch
censors the whole root's fitting labels, while retaining every trajectory and cost.
Episode%5==4 is heldout and never fits or selects a model. Thus checkpoint 6 holds
out episode 4, and checkpoint 12 holds out episodes 4 and 9, separately per query.

## Learned selection and matched evaluation

Fit one vector-valued tree per query, shared across four options. Inputs are the
36 V77 observed-board features, two primitive one-hot values and duration/4 (39
values). Fit cumulative labels at checkpoints 6/12: max_depth=3,
min_samples_leaf=8, random_state=8301. Targets remain comparable across checkpoints
because each option has a fixed complete continuation. Select the greatest
query-weighted predicted vector; H2 has exact zero advantage and wins zero ties.
Save both snapshots; the checkpoint-6 selector remains frozen.

After each checkpoint run H2_ONLY, ONE_STEP, FRAGMENT, FROZEN_6 and FIXED_SPACE4.
ONE_STEP restricts the very same current selector to H2/SPACE_1/SNAKE_1.
FRAGMENT permits all options; FROZEN_6 uses the first selector; FIXED_SPACE4 always
uses one SPACE_4 fragment at the same trigger. Every method starts a new natural
game, with two replicas/query/lifecycle: seed=8390000+lifecycle*100+replica,
model seed+1000000. Share seeds across methods, queries, checkpoints and rotate
method execution order. Evaluation never affects fitting or source selection.

Primary final contrasts: FRAGMENT minus H2_ONLY, ONE_STEP, FROZEN_6, FIXED_SPACE4,
first per lifecycle/query, then equally across three lifecycles. Report learning
curves, all outcomes, chosen options/durations, and whether any learned gain
comes from choosing H2 throughout. Confirm actual intervention count, committed
length, return to H2, common pre-trigger histories and fixed controls. These
execution checks do not certify scientific improvement.

## Budget and limits

Ceilings: 72 full source games, 72 roots, 2880 branch trajectories, 5,760,000 branch
transitions, and 120 full evaluation games. Charge actual source, branch and
evaluation interactions separately. Learned methods share cumulative acquisition
and fitting costs; FROZEN_6 pays only first-batch construction. Neither fixed
baseline pays learned-source cost. These attributions must not be added as actual
wall time. Three independent lifecycle processes run concurrently; controls
within a lifecycle run sequentially in rotated order. Report outer wall time and
per-lifecycle elapsed costs separately; this is not a standalone speed benchmark.

One chosen fragment per game is a bounded test of learned selection and duration,
not unrestricted recurring strategy. The six-empty-cell trigger, two supplied
primitives and two supplied lengths constrain coverage. Eight replicas and a small
state sample leave estimation error. All learned methods pay the complete joint
acquisition, not their hypothetical minimum separate sampling cost. Retain all
negative results without retuning options, trigger, fitter or evaluation after
seeing them. No V81 promotion; U005 remains FAIL and U006 remains unstarted.
