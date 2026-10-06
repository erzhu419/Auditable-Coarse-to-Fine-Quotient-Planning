# V132: retained-update attribution of risk8 action changes

V131's risk8 PRIOR loses utility between the fixed131072 and524288
checkpoints. Diagnose the actual parameter updates on retained histories.
No new environment samples, no new controller, and no replacement of V131's
preselected final result. U005 remains FAIL; U006 stays unstarted.

## Fixed histories and probes

Use all four V131 risk8 PRIOR histories, their two saved checkpoints, all16
paired full-game evaluation seeds per history, and every retained training
segment after131072 through524288 (393216 transitions per life;1572864 total).
Keep the pending afterstate across the131072 boundary. Model sources remain
read-only; replay updates a private copy.

Freeze two separate groups of64 probe slots before replaying any update:

- FIRST: reconstruct the common prefix of the two actual evaluation
  histories, stopping at their first different action. No divergence is a
  missing probe, with the seed retained.
- FEATURE: follow the131072 model's retained evaluation trajectory from its
  initial board. At every pre-action board compare both frozen models; take
  the first different choice with a nonzero signed n-tuple feature vector
  phi(new action afterstate)-phi(old action afterstate). If absent, retain
  the missing slot. This fixed supplement handles first divergences that
  arise only from floating summation of equivalent features.

No probe is chosen by win/loss, return, gap size, update category or whether
it helps the explanation. Deduplicate available probes by (life,board), but
keep all slot-to-probe aliases and summarize the two groups separately.
At each probe retain all legal action values and afterstates from both models.
The signed gap always means new model's selected action minus old model's
selected action. Goal afterstates have no learned features; known immediate
reward, goal and fixed query-offset terms are retained as the analytic base.

Classify exact feature ties (signed feature counts and base gap both zero)
separately from nonzero feature differences. Record D4 equivalence and a
canonical gap computed with math.fsum over merged signed features plus the
base. A strict canonical flip requires old gap<0 and new gap>0. Actual action
choices always use the unchanged V131 arithmetic and tie rule; no tolerance
or canonical-policy substitution is introduced.

## Exact replay and attribution

Replay the learned line-table transitions and retained spawns, without RNG.
Preserve choose-before-update order. Recompute stored chosen values, targets,
raw targets, TD errors and updates using the original alpha=.0025 and n-tuple
multiplicity. The final private weights must equal the saved524288 weights
element by element, with matching update counts. Failure prevents a complete
attribution claim; never repair it by fitting a new model or dropping records.

Partition actual updates into exactly three categories:

- LOSS: the final explicit update after a real loss.
- WIN_BOUNDARY: the preceding pending afterstate's update whose target is
  the value of the immediately winning chosen action.
- BOOTSTRAP: every other pending-afterstate update.

For each parameter write retain its actual double change new_weight-old_weight.
Accumulate by category and project onto each probe's merged signed feature
counts. Repeated/shared addresses must cancel correctly. Also separate writes
from exactly either probe afterstate from other boards sharing its features,
and count updates with nonzero signed feature overlap. Retain category counts,
signed net contributions, linear gap changes and actual prediction rounding
residuals. Floating residuals are reported, not assigned to a category or
erased with an epsilon.

## Reporting and accounting

For each group report all64 slots, available probes, feature ties and strict
flips, with each life shown and four-life means equally weighted when all
four have available probes. Preserve aliases; do not treat them as independent
samples. Report signed category contributions and update counts without
turning cancellation-sensitive percentages into causal shares.

Charge roster reconstruction, predictions, file reads, native setup, private
weight copies, every replayed transition/update and the final weight comparison.
Inherited V131 sampling stays historical; this diagnosis adds zero environment
and model-generated samples. Retain a code/protocol copy before one main run,
segment summaries and all probe results, under the research worktree.
Tests target exact replay, pending boundaries, category semantics, repeated
feature cancellation, rounding and missing/aliased probes. Independent
analysis checks the fixed roster, replay totals and contribution arithmetic;
it does not repeat the full weight replay.

## Limitations

These are contributions on the actual recorded training trajectory, not
counterfactual training with categories removed. Bootstrap targets propagate
earlier terminal information. FEATURE probes after the actual paths diverge
describe rankings along the old path; they do not alone explain whole-game
outcomes. Four histories and post-V131 diagnosis cannot establish a successful
new learning method or general strategic learning.
