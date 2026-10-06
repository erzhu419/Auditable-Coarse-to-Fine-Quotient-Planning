# V130: paired action-gap learning from a spatial value prior

V129 removed mean cross-policy bias without improving complete games. Learn
local action differences with the existing spatial representation instead.
U005 remains FAIL; U006 stays unstarted. This is one exploratory improvement
round, with no tuning on its evaluation results.

## Parent and learner

Keep the four V120 final4096 source histories read-only. For risk1=(1,1,1)
use source reward=(1,0,0); for risk8=(1,8,8) use risk_goal=(1,4,4). These are
the nearest source queries in failure/goal-weight space. The declared parent
is the single-source V127 CONSTANT readout, using its final1024 global success
frequency, without loading event-count tables. For non-winning actions:

    Q_parent = Q_source + f_source - f_target
               + (f_target+g_target-f_source-g_source)*constant.

Winning actions have exact value score/2048+g_target. Lexicographic action
ties are unchanged. No V129 offsets, V128/V129 returns or test outcomes enter
learning. This parent is explicit: passing a new query to the original scalar
model alone would not retarget its learned continuation values.

Fit separate target-query heads using the four six-cell n-tuples and eight
symmetries from V120. PRIOR starts with Q_parent and adds a zero-initialized
spatial residual. SCRATCH has the same residual representation but starts
only with current score/2048 and the analytic winning bonus. SCRATCH uses the
same identified swipe rules, without reading source value weights.

At every training root use the parent's action as reference. For every other
legal action, average eight paired terminal utility differences under the
same frozen parent continuation. Retain all labels, including disagreements,
zero differences and identical-feature pairs. In fixed root-ID/action order,
make 20 passes at rate .1, independently for both heads:

    error = mean(U_action - U_reference) - base_gap - w dot feature_difference
    w += .1 * error * feature_difference / sum(feature_difference squared).

Merge repeated/shared feature addresses before the update; winning afterstates
have zero residual features. Zero denominator means no update, counted as
unidentifiable. A pair with any cutoff is ineligible; keep all its samples and
costs. No clipping, shrinkage, early stopping or fitted hyperparameters. Save
and freeze all eight pairs of heads before collecting held-out outcomes.

## Fixed acquisition and evaluation

Four lives, two target queries, p4=.1, goal rank11, maximum2000 swipes per
episode/continuation. BASE=130*100000000; seed namespaces are disjoint:

- Acquire16 complete parent games per life/query (128 actual games), seed
  BASE+10000000+life*100000+episode, paired across queries. Take pre-action
  boards at zero-based indices128,256,512,768. Episodes0..11 train;12..15
  held out as complete episodes. Keep all512 slots, without replacement.
  root_id=life*128+query_index*64+episode*4+index_index. No deduplication:
  each slot has its own continuation streams; report exact board overlaps.
  Freeze the full roster before sampling any action branches.
- At available TRAIN roots, sample every legal action eight times, forced
  once then following the parent. Seed=BASE+50000000+root_id*1000+replica,
  paired across actions. At most12,288 continuations.
- After both heads are frozen, sample every legal action at each HOLDOUT
  root with the same eight-seed formula and fixed parent continuation
  (at most4,096). Reuse these physical branches as PARENT and FIRST_ONLY,
  according to the parent or frozen PRIOR action. Additionally sample the
  PRIOR action followed by PRIOR throughout (FULL_UPDATE), with the same
  eight seeds (at most1,024). Include unchanged first actions.
- Evaluate16 fresh complete games per life/query/method for PARENT, PRIOR
  and SCRATCH:384 actual games. Seed=BASE+90000000+life*100000+replica,
  paired across methods and queries. No online updates.

All requested roots/actions/repetitions remain in the evidence. No outcome-
dependent extensions or replacements. Replay and modeled samples are not
environment samples. Count acquisition, training branches, diagnostic branches,
full games, fitting, predictions, loads, setup and save work separately. Keep
old V120/V126/V127/V128/V129 costs inherited, not free. Generated artifacts
stay under this worktree.

## Analysis and decision

Primary: full-game PRIOR minus PARENT and PRIOR minus SCRATCH, paired by seed,
averaged within life and then equally over four lives. Report each life,
means, terminal statuses and costs. No population significance claims from
four source histories. Cutoffs suppress affected full-return comparisons.

Diagnose training/held-out action-gap RMS errors and sign agreement against
paired Monte Carlo means; these are noisy labels, not exact values. Report
first-four versus last-four sign disagreement. At held-out roots report
FIRST_ONLY minus PARENT, FULL_UPDATE minus FIRST_ONLY and FULL_UPDATE minus
PARENT. This separates the measured first-choice and changed-continuation
effects; parent labels do not prove repeated-control improvement.

Freeze protocol/code before the single main run. Independent analysis checks
rosters, whole-episode splits, seeds, retained transitions, terminal utility,
paired labels, frozen predictions/updates and actual accounting. Tests target
prior double-counting, shared-address gradients, analytic goals, exact zero-
head equivalence and data isolation. No new formal assurance authorization.

## Limitations

Eight suffixes per action can leave noisy labels. Fixed-parent training can
mismatch repeated use of the improved controller. Separate target-query
training does not demonstrate zero-shot query transfer. Four source histories,
small root coverage and one improvement round cannot establish general
strategic learning; the scratch ablation shares the identified dynamics and
the parent's root/sampling distribution.
