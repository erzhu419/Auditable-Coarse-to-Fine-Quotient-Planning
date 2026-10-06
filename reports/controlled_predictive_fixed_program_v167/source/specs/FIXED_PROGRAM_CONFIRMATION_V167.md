# V167: independent continuations for the frozen S0/B candidate

Selected after the exploratory V166 decomposition: risk1 S0 forced B has
retained B−H2 utility +0.634186 CI95 [0.183505, 1.084866]. This selection is
retrospective; only the following fresh continuations test confirmation.

Freeze the original S0 grammar: first DOWN, probe RIGHT, original A suffix
RIGHT/DOWN/RIGHT and original B suffix DOWN/RIGHT/DOWN. Use the existing
V164 forced-B execution (FEEDBACK with map BB), at most four prefix steps,
then the same own-history H2 teacher. Preserve D4 initial-board transport,
probe cost, legal-action checks and same-step H2 fallback unchanged.

Use every risk1 entry in V164 `eval_roots.json`: 32 roots, eight per history,
all four histories. They differ from V166 TRAIN roots but were already used
by V164. Do not choose roots by outcomes. Reuse the frozen teacher/rule
snapshots from V164's source capsule; acquire no source games or new weights.

At each root physically run H2 and S0_B for suffixes 0–15, paired by seed:

`16700000000 + 50000000 + life*1000000 + replica*1000 + slot*100 + suffix`.

Freeze this new seed stream before labels. No optional stopping, suffix
replacement, extra candidates, alternative probes or changed word length.
Total: 512 paired trials, 1,024 physical branches, maximum 2,000 transitions
per branch and 2,048,000 transitions overall. Retain all non-entering roots
and incomplete branches; cutoffs block a complete confirmation claim.

Primary contrast: S0_B−H2 terminal risk1 query utility. Report reward,
failure, success, prefix entry/fallback, every root and history. Average
16 suffixes/root, eight roots/history, four histories equally. Pointwise
paired CI95 conditions on these frozen roots, histories and teachers; it
does not establish new-history generalization. Fresh continuations alone
determine the confirmation result; V166's values are not pooled into it.

Retain per-step outcomes and independently replay the new branches. Account
for actual environment draws, ground/model operations, teacher setup/load,
probe/fallback, test attempts, audit work and inherited V164/V165/V166 costs.
Freeze executable source, protocol and roster before launch; compare frozen
bytes once. No hashes or external checkpoint downloads are needed.

A positive replication supports this bounded candidate and provides an
anchor for subsequent strategy learning. Without replication, prioritize
changing candidate generation rather than extending ranking diagnostics.
Keep H2 incumbent; do not promote a caller or run U006 automatically.
