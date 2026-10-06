# V270 crossed observable-factor transfer results

V270 changes the task flow rather than another estimator on the old four
phases. Five source contexts form the connected L shape
`(0,0),(1,0),(2,0),(0,1),(0,2)` and four target contexts are unseen corners
`(1,1),(1,2),(2,1),(2,2)`. The learner observes `road_profile` and
`retry_service`; hidden weather names are used only to generate and score the
synthetic crossed flow. Source selection uses only the first 48 rows of each
source/operator. Target prefixes are fixed at `0,4,8,16,32,48`; target audit
suffixes never update a model.

The learned selector chose the intended factor for all three operators in
three of four seeds. In the fourth seed it selected both visible fields for
`SHORT_PASS`, an over-specific choice that caused one prefix-zero error but did
not prevent later transfer.

| target prefix per operator | RESET | GLOBAL | FULL_CONTEXT | LEARNED_FACTOR | SUPPLIED_FACTOR |
|---:|---:|---:|---:|---:|---:|
| 0 | 6.00 / 16.2145 | 7.25 / 5.6845 | 6.00 / 16.2145 | **11.00 / 1.08025** | 12.00 / 0 |
| 4 | 10.50 / 1.11625 | 7.50 / 5.182 | 10.50 / 1.11625 | **12.00 / 0** | 12.00 / 0 |
| 8 | 11.75 / 0.28625 | 7.50 / 5.182 | 11.75 / 0.28625 | **12.00 / 0** | 12.00 / 0 |
| 16 | 12.00 / 0 | 8.50 / 3.716 | 12.00 / 0 | **12.00 / 0** | 12.00 / 0 |
| 32 | 11.75 / 0.030875 | 9.50 / 2.265125 | 11.75 / 0.030875 | **12.00 / 0** | 12.00 / 0 |
| 48 | 12.00 / 0 | 10.00 / 1.490125 | 12.00 / 0 | **12.00 / 0** | 12.00 / 0 |

Each cell is `mean policy-correct queries / mean exact regret` over four seeds
and four target pairs. `FULL_CONTEXT` equals RESET because every target pair is
unseen in the source L; a full-pair lookup has no transferable source group.
GLOBAL pools incompatible factor combinations and transfers the wrong laws.
The learned factor selector nearly reaches the supplied-factor reference with
zero target observations and reaches 12/12 after only four target rows per
operator.

The normalized policy-correctness area over the fixed prefix curve is 11.9583
for `LEARNED_FACTOR`, versus 11.5104 for RESET/FULL_CONTEXT and 8.8229 for
GLOBAL. The exact-regret curve area is 0.0450, versus 0.8147 for RESET and
3.2488 for GLOBAL. The learner used 720 source fit rows per seed, so this is
evidence of transfer after paying a source-learning cost, not a claim of lower
total observations than RESET.

This is a synthetic crossed task-flow diagnostic built by independently
recombining V205 numeric laws. It demonstrates a measurable early-transfer
effect when the factor is observable and the source covers each factor level;
it does not establish performance on the original 2048 Gate or complete
continual strategic learning. The next step is to repeat the same frozen
learner over a longer task flow with a genuinely persistent context variable,
while retaining the source-cost accounting.

The run exited 0 with zero-byte stderr; the focused V263–V270 suite passed
30/30 tests. Raw evidence is in
[`summary.json`](crossed_factor_transfer_v270/summary.json).

V270 is exploratory only. The original Gate remains FAIL and U006 remains
unstarted.

Protocol: [`CROSSED_FACTOR_TRANSFER_V270.md`](../specs/CROSSED_FACTOR_TRANSFER_V270.md).
Implementation: [`crossed_factor_transfer_v270.py`](../src/acfqp/science/crossed_factor_transfer_v270.py).
