# V266 query-action agreement results

V266 replaced V265's Brier threshold and margin with a direct applicability
rule. Before adding the current phase to any module, it compares the historical
module with the current local posterior on the frozen reward, risk and goal
queries. Reuse is allowed only when all three optimal-action sets agree;
otherwise the learner abstains and creates a separate local module.

The paired V265 streams were replayed with identical 48-observation fit
prefixes and 16-observation audit suffixes. This isolates the applicability
rule and does not create new independent environmental data.

| arm | policy-correct counts | mean correct | mean exact regret |
|---|---:|---:|---:|
| `RESET` | 12, 12, 11, 11 | 11.5/12 | 0.105 |
| `GLOBAL` | 10, 10, 9, 9 | 9.5/12 | 1.9885 |
| `V265_GUARDED` | 12, 12, 11, 11 | 11.5/12 | 0.105 |
| `ACTION_AGREEMENT` | **12, 12, 11, 11** | **11.5/12** | **0.105** |

The new rule abstains on `B` in all four streams, reuses a prior module on
`A_prime` in all four, and abstains on `C` in all four. It therefore prevents
the harmful transfers seen in GLOBAL and the legacy splitter, but it does not
beat rebuilding or reduce work. The current representation route has reached a
safe-reuse plateau: changing the applicability test no longer produces a
quality or cost gain on this task.

The run exited 0 with zero-byte stderr; the focused V266 suite passed 4/4
tests. Candidate checks, assignment reasons and per-seed regrets are retained
in [`summary.json`](persistent_consequence_v266/summary.json). A replay after
adding candidate-check bookkeeping is retained as `summary_replay.json` with a
zero-byte stderr log.

The next substantive change must add information that the current three-query
consequence vector does not contain, such as a predeclared held-out query family
or a longer composable continuation outcome. Further module-assignment rules,
Brier thresholds or replaying these same phases are closed. V266 is exploratory
only; the original Gate remains FAIL and U006 remains unstarted.

Protocol: [`PERSISTENT_CONSEQUENCE_LIBRARY_V266.md`](../specs/PERSISTENT_CONSEQUENCE_LIBRARY_V266.md).
Implementation: [`persistent_consequence_library_v266.py`](../src/acfqp/science/persistent_consequence_library_v266.py).
