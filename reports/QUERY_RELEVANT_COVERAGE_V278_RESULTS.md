# V278 — query-relevant coverage

All 64 prospectively registered source/target lifecycles completed, with four
arms and 288 START opportunities each. The learner and quota4 are unchanged;
the new controller skips decision-irrelevant or source-covered requests.
Regret scores the routes actually executed, including acquisition attempts.

| Arm | Mean cumulative regret | Mean forced overrides |
|---|---:|---:|
| PASSIVE_REVISED | 4.093156 | 0 |
| QUOTA_REVISED | 2.277302 | 2.34375 |
| RELEVANT_REVISED | 0.729659 | 0.53125 |
| COST_RELEVANT_REVISED | 0.729659 | 0.53125 |

Primary difference versus QUOTA: **−1.547642**, paired lifecycle bootstrap
95% CI **[−3.522542, −0.138984]**; **4 improved, 60 equal, 0 worse**. The
frozen cohort criterion is met. Both SHORT self-lock histories are repaired,
and both retry-empty histories avoid most costly quota overrides.

## Limitations and next step

Versus PASSIVE, the difference is −3.363497, CI **[−8.473422, 0.020366]**:
**3 improved, 60 equal, 1 worse**. Source 27842400 incurs 2.7664 versus
1.8164 regret (+0.95). Therefore superiority over natural execution remains
unconfirmed. Its probes improve on contemporaneous recommendations by 0.7125,
but extra DELIVERY feedback delays factor revision and causes five later wrong
greedy choices costing 1.6625. The remaining failure concerns feedback's effect
on future learning, not just the immediate probe cost.

The extra cost filter produces exactly the same histories as RELEVANT, with
zero cost rejections; this cohort establishes no additional benefit from it.
Its full-support potential is optimistic, not an expected information value.
Next, compare hard factor selection with evidence-weighted candidate
predictions on retained prefixes, then prospectively test the learner change.
This targets feedback's effect on future decisions; keep natural execution
as the comparator and quota unchanged.

This remains a finite supplied-grammar route task. Natural full-game transfer
is unresolved; U005 remains FAIL and U006 unstarted.

Receipt: [summary.json](</home/erzhu419/mine_code/Auditable Coarse-to-Fine Quotient Planning/workspaces/acfqp-controlled-predictive-quotient-exploration/reports/query_relevant_coverage_v278/summary.json>).
Compressed full traces: 1.24 MB; 61,440 physical source observations,
52,608 online events, 73,728 START opportunities across arms. Exit 0, stderr
0 bytes; 30 related tests pass. Independent receipt review confirms execution,
committed-prefix causality, exact regret totals and all paired intervals.
No sources or adverse outcomes were removed.
