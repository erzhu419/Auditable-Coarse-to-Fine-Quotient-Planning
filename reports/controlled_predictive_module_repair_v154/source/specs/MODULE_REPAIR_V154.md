# V154 — fixed-reference advantage repair

Freeze this protocol, the 64 training-root identities and the evaluation
rosters before fitting. Freeze all 24 resulting controller models before
any new game. V153 becomes exploratory development data; only the new
games are outcome evidence for the repaired policies.

## Controlled update

Use all four histories, both queries and all 64 V153 roots. Each
history/query has four H2-source and four OLD-gate-source roots, including
every accepted and declined root. Retain the V153 source order and all
16 paired suffixes per root. No additional training interaction.

For each root construct three-component means (score/2048, failure,
success), using all four branches from the same retained acquisition:
REPAIR_H2 targets M_H2 minus H_H2; REPAIR_GATE targets M_GATE minus H_GATE.
Each view is charged the entire retained V153 physical pool, counted once
in acquisition accounting. Do not replace its cost with zero merely
because the files are reused.

Initialize each repair independently from the identical final V151 LEARN8
checkpoint. Use unchanged V151 root unary/adjacent-pair features plus bias,
three components, normalized LMS, alpha=0.1 and 32 ordered passes over the
eight root means per history/query. There are 16 fits, 256 updates each,
4096 total. Preserve the original controller (OLD) and its historical
update count. Do not mix the older V151 labels into either fit.

The continuation policy defining every REPAIR_GATE label is the same
frozen OLD gate used in V153. This is one approximate policy-improvement
step; the label is not the exact value under the repaired controller.
Keep this reference fixed throughout. A later reference-policy change
would require labels for that new reference.

## Fresh complete games

Use H2, ALT, OLD, REPAIR_H2 and REPAIR_GATE, without changing the
strict-positive decision, eight-step commitment or one-step fallback.
Each teacher receives its own query. Evaluate all four histories and both
queries on replicas 0–15. The seed is
154*100000000 + 90000000 + life*1000000 + replica,
shared across arms and queries with a fresh RNG for each physical game.

This yields 640 logical results. Execute H2 once per history/query/replica
and bind ALT to the opposite-query H2 trajectory, recomputing target-query
utility. OLD and both repairs execute independently, giving 512 physical
games. Preserve both rosters and every physical identity.

Keep the existing environment: p_four=0.1, two initial spawns, goal rank11,
spawn after the winning swipe, maximum 2000 transitions. Retain every
cutoff and its cost; affected comparisons remain incomplete, with no
replacement games, parameter changes or optional stopping.

## Analysis and decision

Independently rebuild training means from the retained V153 components,
verify both warm fits with the V151 numerical oracle, and check frozen
states. Reuse V153's completed branch audit rather than replaying that
environment again. Independently replay each new physical game once.
Charge retained-data reading, training, model loading, evaluation and
audit work separately. Logical ALT references do not duplicate costs.

Report all arms and both queries, with mean utility, score, steps and
terminal counts per history. Primary paired contrasts are REPAIR_H2−OLD,
REPAIR_GATE−OLD and REPAIR_GATE−REPAIR_H2. Also report each learned arm
against H2 and ALT, and ALT−H2.

Average the 16 paired seed differences within each history and give all
four histories equal weight. Report the four predetermined replica blocks
0–3,4–7,8–11,12–15 and conditional pointwise approximate 95% intervals:
mean +/- 1.96*sqrt(sum_history(sample_variance(delta)/16)/16).
These intervals condition on the frozen histories and training data and
are not multiplicity-adjusted. Fit accuracy is not control benefit.

Keep H2 as the operational baseline. Compare the two repairs jointly,
retain negative outcomes, and do not choose a favorable arm/query after
evaluation as a confirmed solution. General strategic learning remains
open; U005 remains FAIL and U006 unstarted.

