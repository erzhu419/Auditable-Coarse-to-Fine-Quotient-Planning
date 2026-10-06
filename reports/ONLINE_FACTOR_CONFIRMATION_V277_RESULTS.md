# V277 — independent-source confirmation

The unchanged V276 method completed on all 32 new source/target lifecycles,
with four arms and 288 START opportunities each. Source RNG sets are disjoint.

| Arm | Mean executed-policy cumulative regret |
|---|---:|
| PASSIVE_FIXED | 7.250056 |
| PASSIVE_REVISED | 7.250056 |
| COVERED_FIXED | 3.607259 |
| COVERED_REVISED | 1.915053 |

Primary paired difference: **-5.335003**, bootstrap 95% CI **[-14.371478,
0.916275]**; **2 improved, 29 equal, 1 worse**. The frozen confirmation
criterion is not met. No histories were excluded or added after results.

The adverse source (27741100) spends 53 A-stage coverage opportunities to
obtain 16 retry outcomes; 37 attempts never reach retry. Wet contexts alone
incur 22.077 regret from overriding already optimal recommendations. Combined
actual regret is 25.3574 versus passive 10.697 (+14.6604), despite later repair
and zero A_prime regret. This exposes a cost failure in outcome-count coverage.

Next: test query-relevant coverage using whether an unresolved operator can
change the decision, accounting for the cost of reaching it. Keep this failed
cohort immutable; quota tuning or cohort expansion is not the follow-up.

Receipt: [summary.json](</home/erzhu419/mine_code/Auditable Coarse-to-Fine Quotient Planning/workspaces/acfqp-controlled-predictive-quotient-exploration/reports/online_factor_confirmation_v277/summary.json>).
Full traces are compressed to 618 KB. Main exit 0, stderr 0 bytes, 17 related
tests pass. Independent review confirms complete ledgers, paired outcomes,
exact regret totals and compact/full receipt agreement. Natural full-game
transfer remains unresolved; U005 stays FAIL and U006 unstarted.
