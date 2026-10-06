# V276 — bounded coverage and online factor repair

Frozen 2×2 run: four retained source histories and fresh target streams,
288 START opportunities per arm/lifecycle. Regret is the exact expected utility
gap of the executed route, including coverage cost. Source cost is 720 fit/240
audit rows once per arm/lifecycle; only reached operators supply target data.

| Arm | Mean actual cumulative regret | A | B | A_prime |
|---|---:|---:|---:|---:|
| PASSIVE_FIXED | 27.35720 | 8.64200 | 10.07320 | 8.64200 |
| PASSIVE_REVISED | 27.35720 | 8.64200 | 10.07320 | 8.64200 |
| COVERED_FIXED | 14.52500 | 6.24100 | 4.72800 | 3.55600 |
| COVERED_REVISED | 3.29365 | 3.18725 | 0.10640 | 0.00000 |

Combined repair reduces regret by 87.96% here: 1 improved, 3 equal, 0 worse.
All benefit is in known source 275402 (109.1096→12.8554). Sixteen lawful
SHORT probes cost 12.749 in A; SHORT drops its spurious retry-service field at
A episode 2 and wet contexts then select SHORT. There are no further probes
in B/A_prime. Passive reselection alone never obtains SHORT feedback.

## Limits and next step

This is known-source repair; the final DETOUR grouping stays global and B's
support error remains 0.1064 per lifecycle. Next, confirm the unchanged method
on all new source/target histories without filtering or quota tuning. Natural
full-game transfer remains unresolved; U005 stays FAIL and U006 unstarted.

Receipt: [summary.json](</home/erzhu419/mine_code/Auditable Coarse-to-Fine Quotient Planning/workspaces/acfqp-controlled-predictive-quotient-exploration/reports/online_factor_repair_v276/summary.json>).
Main exit 0, stderr 0 bytes; 51 related tests pass. Independent receipt review
confirms complete lifecycles, committed-event accounting and paired outcomes.
