# V271 continual crossed-factor protocol

V270 showed that an observable factor can transfer to an unseen context, but
it did not test a law change after transfer. V271 keeps the V270 source
selector and tests one persistent target context at a time through the
continual sequence `A -> B -> A_prime`.

## Frozen data and selector

The five V270 source contexts are retained:
`(0,0),(1,0),(2,0),(0,1),(0,2)`. The four V270 target corners are evaluated
independently, each against the same immutable source snapshot. For each seed, source
selection sees only the first 48 rows for each of the three operators in each
source context. The V270 Jeffreys Dirichlet likelihood and candidate subsets
`(), (road_profile), (retry_service), (road_profile,retry_service)` are used
without retuning. The selected subset for each operator is frozen before any
target row is read. Source held-out suffixes (the last 16 rows) remain untouched
and are counted separately; this run does not claim an additional audit score.

The source cost is 720 fit observations per seed (`5 contexts x 3 operators x
48`) and 240 held-out observations. The source snapshot is read-only for
each target corner; updates from one target corner never enter another.

## Continual task flow

Each target corner keeps its visible `(road_profile,retry_service)` labels
unchanged through all three phases. The phase marker is evaluator metadata,
not a learner feature. Thus the learner can use the observable factor labels,
but cannot solve the test by looking up `A`, `B`, or `A_prime`.

* `A` uses the original V270 law for the target corner.
* `B` changes exactly one law entry:
  `RECOVERY_RETRY.DELIVERY = 1/20` and
  `RECOVERY_RETRY.LOST = 19/20`. All `SHORT_PASS` and `DETOUR_PASS`
  probabilities and all visible labels stay unchanged.
* `A_prime` restores the exact `A` law, including the original retry
  probability for that target's `retry_service` value.

Each phase has 64 rows per operator. Prefixes `0,4,8,16,32,48` are the only
fit points; the final 16 rows of every phase and operator are held-out and
excluded from every model. A
continual arm carries its posterior from the completed earlier phase and then
adds the current phase prefix. At `B` prefix zero it therefore contains all
48 `A` fit rows; at `A_prime` prefix zero it contains all 48 `A` and 48 `B`
fit rows. No audit suffix is ever fitted.

## Arms

* `RESET`: starts an empty target posterior at every phase and uses only the
  current phase prefix. It pays no source-learning cost and is a lower-bound
  adaptation control.
* `FROZEN_FACTOR`: uses the V270 source posterior grouped by the frozen
  selected factor and never incorporates target rows. It tests transfer without
  continual updating.
* `CONTINUAL_FACTOR`: starts from the same V270 source posterior and updates
  only with target fit prefixes in chronological `A -> B -> A_prime` order.

All three arms receive identical streams and prefixes. `RESET` is not treated
as a total-cost win merely because it skips the source selector; source cost
and target observations are reported separately.

## Measurements and decision rule

For every seed, target corner, phase, prefix, arm, and the fixed V270 queries
`reward`, `risk`, and `goal`, record exact policy correctness, optimal-action
set agreement, and exact regret against the generator law for that phase.
Report means and seed-level rows, with denominators explicit.

The primary diagnostic is the paired `FROZEN_FACTOR` versus
`CONTINUAL_FACTOR` curve on `B`: a lower continual regret at later B prefixes
is evidence of adaptation to the changed retry law. The retention diagnostic is
the `A_prime` curve: compare prefix-zero carry-over regret and later recovery
to the frozen A reference. A method that adapts in B but remains biased after
restoration is recorded as a retention failure.

The run is exploratory and does not reopen the original Gate or start U006.
It tests whether V270's factor transfer survives a visible-context law change
and restoration after the source cost has been paid.
