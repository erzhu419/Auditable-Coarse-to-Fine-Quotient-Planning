# V279 — structure uncertainty on retained prefixes

Replayed all 64 V278 sources on PASSIVE and RELEVANT histories: 36,864
decisions, no new environment observations. Hard-MAP replay exactly restores
every original recommendation and its regret. Four candidate structures use
uniform priors and normalized marginal-likelihood weights; row-update timing,
local observed support and the real feedback history are preserved.

| Fixed history | Mean MAP recommendation regret | Weighted | Sources better / equal / worse |
|---|---:|---:|---:|
| PASSIVE | 4.093156 | 3.958889 | 7 / 52 / 5 |
| RELEVANT | 0.715370 | 0.661514 | 7 / 52 / 5 |

Changed recommendations: 70 on PASSIVE (48 better, 22 worse), 35 on RELEVANT
(21 better, 14 worse). Source 27842400's RELEVANT recommendation regret drops
3.4789→2.4966, but only one of its five later wrong A/risk RETRY choices is
fixed; two new B/risk errors appear. One SHORT self-lock source remains entirely
unchanged. Model averaging is not adopted as the default learner.

The largest new harm is source 27842300 (+3.1): two A/risk choices change from
correct SHORT to RETURN. Source 27846000 adds +1.55 despite 85% weight on the
correct road grouping; the sparse joint row pulls down the mixed estimate.
Both precede DELAYED discovery: global structure evidence does not resolve
the reliability of an unseen or sparsely sampled target row.

## Limitations and next direction

These are fixed-history recommendation scores, not executed-route returns or
fresh validation. Inherited global scoring and local outcome support do not
form one coherent Bayesian model after new-category discovery. The modest
gains and five adverse sources do not establish a generally better learner.
Next, model local-row uncertainty when evaluating acquisition's expected
effect on subsequent revision and decisions; do not tune weights or quota.

For the original multi-episode strategic-learning paper, three scientific
milestones remain: independently validated net gains over natural execution
and matched learning baselines; transfer to natural long episodes/unseen task
structures with a fixed learner; and isolated structure/planning contributions
with full source, online and compute costs. A manuscript must then integrate
the final method and main experiment. V278's quota improvement is established;
natural-game strategic superiority remains open. U005 FAIL/U006 unstarted.

Exit 0, stderr 0 bytes; 8 focused tests pass. Independent review reconstructs
all 105 changed recommendations and confirms all paired source totals. Receipt:
[summary.json](</home/erzhu419/mine_code/Auditable Coarse-to-Fine Quotient Planning/workspaces/acfqp-controlled-predictive-quotient-exploration/reports/evidence_weighted_prefix_v279/summary.json>).
Changed-decision traces occupy 14.3 KB; V278 is unchanged.
