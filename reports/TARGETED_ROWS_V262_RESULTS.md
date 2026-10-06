# V262 targeted-row acquisition results

V262 completed its one-time science run and remained qualification-only. The
three frozen arms used the same `unified_native_joint_row_cs_v262` proof and
the same 648 target decisions (3 lives × 72 targets × 3 arms):

| arm | total samples | query certified | joint completed | execution certified | goal impossible |
|---|---:|---:|---:|---:|---:|
| `DIRECT_ROW_REUSE` | 48,287 | 144/216 | 128/216 | 192/216 | 8 |
| `FULL_UNIT_ROW_CS` | 48,370 | 144/216 | 128/216 | 192/216 | 8 |
| `CONTINUOUS_REUSE` | 48,287 | 144/216 | 128/216 | 192/216 | 8 |

The direct-row arm saved 26, 27, and 30 samples against the full-unit arm in
lives 0, 1, and 2. It produced zero query, joint, execution-resolution, or
impossibility gains or losses. Against continuous reuse it had identical total
cost and identical readiness. The 32 physical direct rows were retained, but
they did not become conditional units or execution-path observations.

The frozen scientific conditions therefore remain false: late-B quality,
A-return quality, and strict acquisition saving all fail; matched quality,
per-life budgets, and certificate truth all pass. The scientific Gate remains
`FAIL`; U006 was not started and no identity or assurance tapes were consumed.

The process evidence is complete. The science wrapper exited 0 with a zero-byte
stderr. The independent audit replayed all 648 targets, 5,400 auxiliary
records, 654 execution-history snapshots, source/row/unit ledgers, certificates,
fees, stopping decisions, and paired comparisons with `valid=true`,
`complete=true`, exit 0, and zero-byte stderr. Focused core/runner/audit tests
pass: 36 tests in 1.14 s.

This result closes the targeted-row question: paying only unresolved operator
rows changes acquisition bookkeeping at most marginally and does not change
the learned readiness bottleneck. It does not justify tuning the current
representation further. Any next experiment must use a substantively different
representation or query-state construction while retaining this negative
result and the frozen Gate boundary.

The frozen protocol is in [`specs/TARGETED_ROWS_V262.md`](../specs/TARGETED_ROWS_V262.md);
machine-readable outputs are [`summary.json`](targeted_rows_v262/summary.json)
and [`analysis.json`](targeted_rows_v262/analysis.json).
