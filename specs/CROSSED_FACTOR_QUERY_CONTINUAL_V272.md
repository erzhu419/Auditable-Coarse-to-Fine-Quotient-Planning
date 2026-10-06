# V272 continual query-shift protocol

V271 tested a changed retry law. V272 isolates the other change named in the
multi-episode plan: the dynamics and factor learner stay fixed while the query
preference changes through `A -> B -> A_prime`.

The V270 source L, source fit/audit split, selector, seeds, target corners,
factor projections, phase order, and three arms are reused without retuning.
Each target phase has 48 fit rows and 16 held-out suffix rows per operator.
The source selector runs once per seed, before target rows are read; suffixes
are excluded from fitting and are counted separately, not scored as a new audit
set.

All three phases use the original V270 generator law and independent streams.
Only the evaluator's `risk` query changes in B:

* A and A_prime: `(reward, failure_penalty, goal_bonus) = (1,4,4)`;
* B: `(1,1,4)`.

The `reward` and `goal` queries remain unchanged. A_prime restores the complete
A query bank. The phase marker is evaluator metadata and is not a learner
feature. Since the generator law is unchanged, a factor model should replan
under the new query without relearning its consequence probabilities.

`RESET`, `FROZEN_FACTOR`, and `CONTINUAL_FACTOR` receive identical streams and
prefixes. The primary diagnostic is whether the frozen factor model changes its
risk action in B despite receiving no new rows, then restores the A action in
A_prime. Continual updates are retained as a control for accidental estimation
drift; they must not be credited as necessary for a query-only change.

This is an exploratory diagnostic. It does not reopen the original Gate or
start U006.
