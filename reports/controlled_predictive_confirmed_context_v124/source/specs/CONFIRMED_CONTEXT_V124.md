# V124: confirm changes before identifying a context

V123 suppressed switching but created duplicates that could capture a returning
context. Freeze a bounded two-block detector and separate its decision from
historical identity matching. Preserve V122/V123 outcomes; U005 FAIL and U006
unstarted remain unchanged.

## Fixed learner

Keep Beta(1,1), the original 256-observation source warmup, block64 and log64.
For each block compute predictive scores of every stored module and a NEW
Beta(1,1) candidate. A block is suspicious iff the best inactive/NEW raw score
exceeds the active raw score by more than log64.

On the first suspicious block, quarantine its count and number of fours; update
no module and keep the active identity. Evaluate the next block independently
against those same frozen module statistics. If it is not suspicious, commit
both blocks to the active module. If it is suspicious, use their pooled128
observations to match all stored modules without a switching penalty; compare
the best old module against NEW minus log64. Existing wins an exact tie and
the smallest existing ID wins ties among existing modules. The active old
module may itself win this pooled match. Commit both blocks once to that winner.
An ordinary nonsuspicious block commits immediately to the active module.

Every complete64 block emits an event. Report its current block counts separately
from the64/128 committed observations. Hold at most64 completed observations
plus an incomplete next block. Memory crosses games and experimental phases.
Never force a flush at a known boundary or the end. Account for committed,
quarantined and incomplete observations exactly, including their fours.

This is one fixed mechanism comparison, not an isolation of each of confirmation,
quarantine and historical matching. It has no direction filter, search over
block sizes/thresholds, source-ID exception, merger or pruning rule.

## Replay and comparison

Use all eight V123 retained block streams: four existing source histories,
two separate query models, B524288 then A_RETURN524288. Use the exact256
warmup ranks for each stream. Control is unchanged V123 PERSISTENT; new method
is CONFIRMED. Each router receives only ranks, never phase, query or true p4.

V123 blocks are sufficient because both algorithms predict a constant
probability and active ID until the end of each64-rank block. Expand each
retained count as fours followed by twos when calling the rank API; this is
equivalent for these algorithms but does not reproduce original within-block
rank order. It is processing existing observations, not sampling new ones.
Check the control's pre-block probability/ID, full event, source probability
and both phase-final payloads against V123 exactly. A mismatch invalidates the
replay. Preserve the original source files and keep outputs project-local.

Use V123's exact causal block formulas for log loss, Brier score, source-bank
action fraction, first correct activation and last wrong action. Report source
posterior drift in B, module births/counts, subsequent switches, quarantine
confirmations/rejections, outstanding observations and predictive-score work.
ID0 is the evaluator's desired returning identity; the learner is not told
that. First activation alone does not establish stable recovery. Return
prevalence .1 and B prevalence .5 are available only to evaluation.

Primary evidence is every life/query, not pooled treats of eight independent
histories. Inspect consistent identity preservation and recovery alongside
latency and prediction costs before deciding whether to reattach value learning.
No scientific Gate, significance claim or fixed claim of a128-step detection
bound. If it fails, retain the failure and identify its first uncorrected event;
do not tune this replay. If it supports the mechanism, the next stage uses new
streams and explicitly accounts for delayed value updates.

## Cost and limitations

No new environment acquisition, TD update, model rollout or weight load.
Reuse8388608 training ranks and2048 warmup ranks, count processing for both
methods separately and record source/trace bytes and execution time. Freeze
code/protocol before one main run; targeted tests use synthetic ranks.

The traces belong to V122's policy, changes are large and block aligned, and
the source posterior can be poorly calibrated by its short warmup. Two
successive noisy blocks may still confirm falsely. Correct routing does not
imply correct or improved strategy; future TD integration must handle the
observations and actions before detection, not only freeze router statistics.
