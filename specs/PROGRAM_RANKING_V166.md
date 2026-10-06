# V166: same-program ranking and terminal-risk decomposition

One retrospective routing analysis, with zero new environment samples.
V165 already exposed the selected-program subset; this is not label-blind
confirmation. Freeze this specification, metadata roster and code before
computing the additional ranking decomposition. Keep V164/V165 unchanged.

The candidate universe is the union of V165's eight selected original
candidate semantics: `(first_action, probe_action, A suffix, B suffix)`.
Deduplicate within query in target-life order. The metadata universe has two
risk1 strata and one risk8 stratum; never pool their A/B rankings as one rule.
For every stratum and every history, use its four V164 TRAIN_SOURCE roots and
all four suffixes. Choose the smallest exact-semantic donor fold excluding
the root's history, then original candidate order, without using outcomes.

Frozen coverage: 3 strata, 48 semantic-root entries, 192 H2/A/B triplets,
576 logical branch references and 512 unique physical rows. The two risk1
strata share 64 H2 records; there are 32 distinct physical root states.
Keep all non-entering prefixes. Missing, duplicate, nonterminal, mismatched
seed/predicate or inconsistent terminal vectors make the affected roster
incomplete; retain it without replacement or dropping unfavorable roots.
Full physical replay is inherited from the settled V164 audit.

Compute A−B, A−H2 and B−H2 separately for suffix halves [0,1], [2,3], and the
full [0,1,2,3]. Full reuses both halves and is not independent evidence.
Use each whole observed component vector. Utility effects are reward,
`-failure_penalty * failure`, and `goal_bonus * success`; combine the latter
two as the risk effect. Count a discordant terminal pair once, even when
the utility assigns it two component contributions. Keep pair/root/history
effects, terminal-discordance counts and contribution sums.

Average suffixes within root, four roots within history, four histories
within stratum equally. Report paired conditional normal CI95 per stratum
and history, propagating root sample variance/n and the fixed averaging
weights. Report variance of reward and risk and their covariance, so that
`Var(utility) = Var(reward) + Var(risk) + 2*Cov(reward,risk)` at every level.
Do not compute an independence-based pooled query CI for shared risk1 H2.

Label each root/history half rank as positive, negative or tied; report
strict sign reversals and tie transitions separately. Half agreement is a
description of these retained draws, not proof of stable underlying ranking.
Show whether utility ranking conflicts with the observed failure preference.
H2 contrasts establish candidate relevance only on this retained roster.

No new learner, candidate, hyperparameter search or repeated LOO fitting:
V164 GLOBAL already learned a cross-history fixed rule. Independently
reconstruct semantic matching, paired arithmetic, signs, variance and counts
from compact V164 records. Retain targeted synthetic test attempts, one
main/audit execution, inherited costs and one final frozen-byte comparison.
No hashes, checkpoints or physical rollout traces are needed.

After this one pass, choose the next substantive method experiment by
judgment: repeatable opposing history ranks motivate a single observable
context transfer test; within-history reversals associated with terminal
discordance motivate stabilizing same-candidate consequence estimation;
weak candidate-versus-H2 evidence motivates candidate-generation work.
Do not convert inconclusive intervals into proof of absent headroom.
No method adoption; H2 remains incumbent, U005 FAIL and U006 unstarted.
