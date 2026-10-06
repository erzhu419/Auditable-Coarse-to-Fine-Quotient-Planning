# V144: learn paired consequence advantages and test new closed-loop games

V143 supplies realized H1_CONT versus H2 first-action consequences under one
frozen query-specific H2 continuation. This experiment converts that experience
into a fixed, testable learner. Regression fit or returning to H2 alone cannot
establish strategic improvement.

## Data, split and model

Use all 256 V143 roots and their eight paired terminal suffixes. For each root
average the realized H1_CONT minus H2 components (score/2048, LOST, WON).
Subtract the exact difference between the two first-action scores from the
reward target, leaving a three-component continuation-difference target.
Methods selecting the same action reuse the same physical outcome and remain
zero-target examples. No selection by outcome sign, disagreement or prediction.
V143 has already completed full trajectory validation; here reconstruct the
paired targets and references without replaying its 1.88 million transitions.

For each of four histories and two queries independently, train on original
game replicas 0,1,2,3 and reserve replicas 4,5,6,7 for diagnostic validation.
All four roots and all eight suffixes of an original game remain on one side,
including across queries. There are 16 training and 16 validation roots per
model. Validation is previously acquired evidence, not a sealed new test, and
cannot select hyperparameters, update count, snapshots or a deployment rule.

Keep V120's four six-cell n-tuples and eight symmetries. The input x is the
exact signed multiplicity difference phi(candidate afterstate)-phi(H2 afterstate).
Store only nonzero weights at their original full addresses; this is the
zero-initialized dense linear model represented sparsely, with no new features
or address compression. Predict three signed components with the same x.

Freeze 32 ordered passes over the 16 training roots, sorting by original game
then root slot. Each update uses one shared pre-update three-component error,
and w_i += .1*x_i*(target-prediction)/sum(x_i*x_i). Zero-feature examples are
retained and counted but do not change weights. No clipping, intercept,
validation-driven stopping, shuffled order or repeated favorable fits. Save
the final sparse model and freeze it before validation and new control. An
independent feature calculation reconstructs the fitted weights.

The inspected V143 cohort contains no immediate-goal afterstate pairs.
Nonterminal difference observations do not identify an absolute terminal
anchor. Thus learned features reject goal ranks; during new control, if either
chosen candidate afterstate reaches the goal, keep H2 without a learned
prediction and count the terminal-pair bypass. Never clip goal ranks into
nonterminal features. This fixes a scope boundary before control results.

## New-game action rule and controls

The LEARNED gate runs the unchanged H2 and V142 H1_CONT candidates on every
decision. If their actions coincide, keep H2 without prediction. Otherwise,
outside the terminal-pair boundary, compute exact immediate score difference
plus predicted remaining reward difference, minus query failure penalty times
predicted failure difference, plus goal bonus times predicted success difference.
Select H1_CONT iff this advantage is strictly positive; ties retain H2.
The predicted value is an H2 proxy plus learned adjustment, not true Q.

Run H2, ZERO and LEARNED on 192 new games: four histories, two queries,
eight replicas, three methods. ZERO has the identical gate and zero weights,
so its rule can select H1 on immediate reward differences. It isolates the
learning contribution from the untrained gate. Use final fixed leaves and
factored dynamics. Charge both planners even when their actions agree or H2
is retained. Do not omit proposal-generation or learning costs.

BASE=144*100000000. Environment seed=BASE+90000000+life*100000+replica;
H1 simulation seed=BASE+80000000+life*1000000+replica*10000+decision_step.
All methods share their paired environment streams; ZERO and LEARNED share
the H1 model stream coordinates. Use p_four=.1, two initial spawns, goal rank11,
maximum 2,000 actual actions and the existing V115 environment semantics.
Retain cutoffs with utility=None, all costs and no replacement seeds.

Freeze code, sources, examples, split and settings before fitting. Finish all
eight fits, retain frozen_training.json, then start any new-game evaluation.
No control outcomes feed back into these learners.

## Measures, costs and interpretation

Primary paired full-game contrasts are LEARNED-H2 and LEARNED-ZERO by query.
Average the eight paired games within history and the four histories equally.
Report signs by history, wins/losses/cutoffs, candidate disagreement and actual
H1-selection rates. Suppress affected full-return means on incomplete games.
Validation component error and realized single-intervention gate consequences
are diagnostic; they cannot replace closed-loop comparison.

Count update attempts, nonzero updates, feature reads, parameter storage,
source replay, fit/validation costs, both candidate planners, source loads and
new real environment transitions. Original V143 acquisition stays inherited;
there are no new training interactions. Once used for training, those examples
cannot also be called unseen test evidence. Histories remain the independent
learning units. The treatment is a first fixed supervised learning step, not
yet proof of continual self-improvement or a general abstraction mechanism.
Keep H2 unless new control benefits justify a change. U005 FAIL; U006 unstarted.
