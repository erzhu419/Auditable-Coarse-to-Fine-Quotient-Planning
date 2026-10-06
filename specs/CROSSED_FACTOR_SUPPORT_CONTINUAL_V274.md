# V274 continual successor-support protocol

V273 changed action availability. V274 tests a genuine consequence-support
change while keeping the action available. The V270 source L, source selector,
visible factors, seeds, target corners, query bank, and `A -> B -> A_prime`
flow remain fixed.

In A and A_prime, `RECOVERY_RETRY` has the old support
`{DELIVERY, LOST}`. In B, one new successor `DELAYED` is added with fixed
probability `1/5`; the old delivery/lost probabilities are both scaled by
`4/5`. `DELAYED` is predeclared as a timeout failure with an additional retry
cost of `2`. Thus the B law is a three-category law, and A_prime restores the
old two-category law. All three operators remain available and are sampled in
all phases.

The learner does not know the phase or hidden weather. It discovers the new
support only when `DELAYED` appears in the current fit prefix. The arms are:

* `RESET_DYNAMIC`: current phase prefix only, with a dynamic support;
* `FROZEN_STATIC`: source factor posterior with the old support, abstaining
  after an unknown B successor is observed;
* `CONTINUAL_FACTOR_EXPANDING`: source plus chronological fit prefixes, with
  support expanded when a new category appears;
* `LEGACY_COERCE`: same observations but maps `DELAYED` to `LOST`, a fixed
  negative control.

The source cost is 720 fit plus 240 held-out observations per seed. Each target
phase acquires 576 fit plus 192 held-out observations per seed; the B retry
stream is acquired because the action remains available.

Unknown categories, abstentions, coercions, support discovery, and ordinary
policy regret are recorded separately. The final 16 rows per operator remain
held out from fitting. This is an exploratory support-expansion diagnostic; it
does not reopen the original Gate or start U006.
