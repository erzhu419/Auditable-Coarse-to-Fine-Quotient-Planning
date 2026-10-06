# V267 held-out query transfer results

V267 replayed the paired V266 streams with the same four seeds, 48 fit
observations and 16 audit observations per operator. The original reward,
risk and goal queries controlled `PRIMARY_AGREEMENT`. Three predeclared utility
weight vectors were kept out of that assignment rule and scored separately by
`HELDOUT_QUERIES`. `ALL_QUERY_AGREEMENT` additionally required agreement on
those held-out queries before reuse. RESET and GLOBAL were retained as controls.
No new environmental data were collected.

The held-out bank is a narrow probe: in this finite route grammar its exact
optimal actions fall in the same action regions already represented by the
primary risk and goal queries. It therefore tests unseen utility weights in
known action regions, not a new decision family.

| arm | primary policy correct | primary set agreement | primary regret | held-out policy correct | held-out set agreement | held-out regret |
|---|---:|---:|---:|---:|---:|---:|
| `RESET` | 11.5/12 | 95.83% | 0.105 | 11.0/12 | 91.67% | 0.31 |
| `GLOBAL` | 9.5/12 | 79.17% | 1.9885 | 8.25/12 | 68.75% | 3.184 |
| `PRIMARY_AGREEMENT` | **11.5/12** | **95.83%** | **0.105** | **10.75/12** | **89.58%** | **0.357** |
| `ALL_QUERY_AGREEMENT` | **11.5/12** | **95.83%** | **0.105** | **10.75/12** | **89.58%** | **0.357** |

`PRIMARY_AGREEMENT` and `ALL_QUERY_AGREEMENT` made the same 16 assignment
decisions across the four streams: four initial modules, four reuses on
`A_prime`, and eight local splits. Requiring held-out agreement did not change
reuse, accuracy or regret. Relative to RESET, the reusable-module arm lost
0.25 held-out correct decisions per seed and increased mean held-out exact
regret by 0.047; this is a small finite diagnostic difference, not a gain.

The result closes the current query-agreement refinement. It does not show
that the representation generalizes to a new action region, and it does not
repair the original scientific Gate. The next substantive route is a longer
composable consequence outcome (or a separately frozen query bank with a
predeclared new action region), rather than another reuse threshold or another
replay of these phases.

The final replay exited 0 with zero-byte stderr. The focused V263--V267 suite
passed 16/16 tests. The raw final record is
[`summary_final.json`](persistent_consequence_v267/summary_final.json); the
earlier metric-only record is retained as `summary.json`.

V267 is exploratory only. The original Gate remains FAIL and U006 remains
unstarted.

Protocol: [`PERSISTENT_CONSEQUENCE_LIBRARY_V267.md`](../specs/PERSISTENT_CONSEQUENCE_LIBRARY_V267.md).
Implementation: [`persistent_consequence_library_v267.py`](../src/acfqp/science/persistent_consequence_library_v267.py).
