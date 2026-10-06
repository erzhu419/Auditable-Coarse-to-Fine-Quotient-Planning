# V306 — current-policy experience for repeated A adaptation

V305 protects inactive task parameters but a second A fit still harms A.
Intervene on experience generation, rather than retuning its learning rate or
selecting a checkpoint. Use the same 64 retained A1 histories/four original
SOURCE parents. Reconstruct and reproduce each original V303 LOCAL A1 fit.

Four arms: original SOURCE, A1_FROZEN, SOURCE_DATA and CURRENT_DATA. The last
two receive identical copies of the frozen A1 reward and risk parameters.
SOURCE_DATA acquires new A trajectories with original SOURCE weights and zero
risk logits; CURRENT_DATA acquires new A trajectories with the complete frozen
A1 LOCAL policy. Both collectors call the unchanged full split H2 chooser.
Original SOURCE plus zero risk must reproduce the scalar SOURCE policy exactly.
The old scalar-only trajectory API cannot execute a nonzero risk head.

For each actor/lifecycle acquire exactly 131,072 raw tiles, including two initial
tiles per game and the paid unfinished tail. Both actors use the same continuous
mt19937_64 stream seed 306200000000+lifecycle*10000000 and fixed original A1
observed planning p. True world p_four is 0.1; it is not a planning input.
There is no new warmup: the paid A1 belief is available before collection.
Collect raw ranks/actions/scores and natural complete games in 256-raw chunks.
Neither actor learns or changes its belief during acquisition. A POOLED
observational tracker records new prefix statistics, without choosing actions.

Split complete games chronologically floor(0.8*N) FIT / remaining HELDOUT.
Fit the corresponding A1 copy once with unchanged V301 LOCAL alpha 0.0025,
factual future rewards and complete-game win labels; tails are excluded from
labels but remain paid. Game counts and fitted sample counts may differ between
policies: actual acquisition raw budgets, not numbers of games, are matched.
Old V303 A2 data is not a comparator or new fitting input.

Evaluate all four arms on 32 new paired A seeds per lifecycle:
306900000000+lifecycle*1000000+episode, fixed A1 planning p, static full H2,
max 8,192 steps. Retain every cutoff. Sole primary: CURRENT_DATA minus
SOURCE_DATA whole-game utility, 20,000 paired lifecycle bootstrap draws within
the four fixed parent groups, seed 30600001. CI lower >0 with no cutoff
supports the experience-generation intervention. Separately compare CURRENT
and SOURCE_DATA to A1_FROZEN and SOURCE. CI lower >=0 is required to support
no degradation relative to A1; absence of significant loss is not retention.

Charge SOURCE/dynamics and all retained A1 raw economically to every arm,
then its own new cohort to each updating arm. Two physically separate streams
produce 16,777,216 new training raw; all 8,192 evaluation games are new.
Count A1 reconstruction/refit, SOURCE initialization, both A1 parameter copies,
full-policy acquisition and representation, new reconstruction/fits, evaluation,
compiler and processing costs without double-counting contained CPU. Persist
raw traces and completed lifecycle receipts; freeze before new collection.

B parameters are outside this intervention and are not refit or reevaluated;
V305 B preservation is inherited evidence. Initial A1 histories remain fixed,
so this is new A-cohort causal evidence conditional on them and four sources,
not an independent full-sequence confirmation. Policy data changes state coverage
and factual return labels together, not the labels alone. U005 stays FAIL and
U006 remains unstarted. Retain failure without seed, actor or alpha tuning.
