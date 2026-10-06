# V165: retained intervention headroom

Freeze matching and this diagnostic before fitting or scoring raw V164 SCREEN
terminal outcomes. Use only
the already audited V164 compact records; acquire zero environment samples.
V164 remains a negative transfer result, and H2 remains the incumbent.

For each of four target histories and two queries, keep its frozen LEARNED
candidate and maps. Match that candidate to another fold by exact
`(first_action, probe_action, A suffix, B suffix)` semantics. Select the
smallest matching donor fold, then original candidate order, using metadata
only. Candidate occurrence counts and donor training returns play no role.
Use all four target-history TRAIN_SOURCE roots and suffixes 0–3, including
non-entering prefixes. Each retained triplet is paired H2/forced-A/forced-B
on the same root and seed. Require 8 cells, 32 roots and 128 triplets; retain
missing or nonterminal records as incomplete, with no replacement or deletion.

Primary selection suffixes are [0, 1], scoring suffixes [2, 3]. The reversed
split is fixed sensitivity evidence, never a substitute for the primary.

* ROOT chooses A or B separately per root by selection mean query utility;
  ties choose A. This is local adaptation with paid outcomes, not a learned
  strategy for unseen roots.
* BIT_REFIT fits AA/AB/BA/BB to the same selection data, per history/query.
  Average suffixes within roots, then the four roots equally. Select the
  highest mean allowed map; ties follow AA, AB, BA, BB. An unobserved bit leaf
  keeps the target's frozen LEARNED assignment, support 0 and estimate null.
* GLOBAL_REFIT chooses AA/BB using exactly the same selection data and
  weighting, with ties choosing A.
* LEARNED and GLOBAL retain the original target maps. H2, fixed A and fixed B
  use their retained physical records. Every mapped decision takes one whole
  observed terminal consequence vector; do not maximize components separately.
* TEST_ROOT_MEAN_ORACLE picks the scoring-mean winner and is an optimistic
  finite-sample diagnostic. Its values cannot justify adopting a method.

ROOT minus BIT_REFIT is the main contrast. Also retain ROOT minus
GLOBAL_REFIT, BIT_REFIT minus GLOBAL_REFIT, and ROOT minus frozen
LEARNED/GLOBAL/H2. Score every method on the two held-back continuations.
The measured probe predicate is available only after the first physical
spawn; A/B must agree on it. A null predicate uses A and requires identical
executed paths and terminal outcomes. Recompute query utility from the
complete component vector and validate paired identity and terminal status.

Report every history and query. Aggregate by equal scoring suffix, root,
and history weights. Pointwise normal CI95 uses each root's paired scoring
variance divided by two and propagates the fixed averaging weights. These
intervals condition on the four histories, fixed roots and fitted selections;
they do not measure new-history generalization or selection uncertainty.

Independent analysis rebuilds matching and arithmetic from compact source
records. Do not repeat the settled V164 physical replay. Retain test attempts,
source cost references, new logical fitting/selection work, and main/audit
times. Freeze executable source/spec/tests before fitting/scoring and compare frozen
bytes once after completion. No hashes, checkpoints, new rollouts or weights.

Interpretation: a held-back ROOT advantage over BIT_REFIT detects useful
root-specific selection beyond this one-bit rule on retained roots. A gain
only over the original map can instead reflect map estimation. Lack of gain
means no headroom detected by this small assay, not proof of absence. These
are held-out-life TRAIN_SOURCE roots, not V164 EVAL roots. Exact donor
semantics support retrospective reuse, not independent confirmation.

Keep U005 FAIL and U006 unstarted. No V164 retuning or method adoption.
