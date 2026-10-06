# V255: joint-unresolved type acquisition

The frozen qualification **passes**. Only type selection changes: the treatment
skips currently joint-certified types; both arms keep the same direct evidence,
paired fresh streams, batch checks and stopping rule.

| Terminal public projections / actual cost | DIRECT_RR | DIRECT_JOINT_UNRESOLVED |
|---|---:|---:|
| All queries certified | 56/72 | 72/72 |
| Goal certified | 59/72 | 72/72 |
| Risk certified | 64/72 | 72/72 |
| Total paid observations, including source | 48,112 | 30,208 |
| Source observations, fully charged per arm | 13,824 | 13,824 |
| Model computation, summed process CPU | 180.68 s | 47.93 s |

Sixteen paired combined gains, zero losses and zero false certificates. Total
observations fall by17,904 (**37.21%**). All treatment lives stop early at
9,728/11,520/8,960; control costs14,144/17,072/16,896. Filtering concentrates
acquisition on the remaining query gaps instead of already-certified types.

Nineteen focused tests pass once. Independent audit is valid, zero failures:
36,026 complete rounds, 2,460 intermediate decisions, 360 public projections
and 11,736 independently evaluated direct comparisons. Science/audit run once,
exit0, wall72.65/386.14s, stderr0. Actual physical total is78,320 observations.
See [verification](v255_runtime_tmp/verification_summary.json) and
[independent analysis](joint_unresolved_trajectory_v255/analysis.json).

Next freeze fresh full A/B/A reuse versus strong history-retaining rebuilding,
both using this direct/filter mechanism. Use legal native trajectories, original
execution-risk rules and all source/acquisition/fallback fees; measure query,
execution and combined completion through drift and return.

Limits: stationary known A types; 72 projections reuse36 type/cost judgments,
not72 independent episodes. Confidence remains separate per life/fixed arm.
Full-lifecycle benefit is untested. V251 remains10/11; original Gate FAIL,
U006 unstarted.
