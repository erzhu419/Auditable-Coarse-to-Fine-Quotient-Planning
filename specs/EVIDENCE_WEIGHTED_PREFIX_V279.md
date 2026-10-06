# V279 — retained-prefix structure uncertainty

Replay all 64 V278 source lifecycles on both PASSIVE_REVISED and
RELEVANT_REVISED histories. The other two histories are duplicates of these
or test the superseded quota controller. No new source or target outcomes.
This diagnostic compares recommendations on fixed data, not online returns.

Keep V276 episode-start structure scores and V275 local-support row posteriors.
Each operator's four candidate field subsets have a uniform structure prior.
Normalize exp(score−maximum score), without temperature or thresholds. Freeze
weights at episode start, but update every candidate row with each actual
committed event. Average each operator's predictive row with its own weights,
then calculate policy consequence vectors and choose the greedy policy.

Reconstruct source streams from V278's original source seed and read only
the 48-row fit prefixes. Read saved episode-start scores, which use only the
committed prefix. Candidate DELAYED support appears only in projections that
have actually observed it. Absent category probabilities are zero when mixing.
Score support and row support are inherited from different existing rules;
call this evidence-weighted prediction, not a fully coherent Bayesian model.

For every retained decision, reconstruct hard-MAP recommendation before
committing that decision's original events. It must reproduce the original
recommendation and exact recommendation regret. Evaluate the weighted
recommendation on the same prefix, with exact-law regret only for diagnostics.
Never execute the weighted action or invent its counterfactual feedback.

Report all sources, phase and whole-lifecycle recommendation-regret differences,
changed/better/equal/worse decisions and paired source counts. Retain changed
decisions with episode weights and utility estimates, including all adverse
sources. Preserve V278 untouched; no scientific Gate or online-benefit claim.
If supported mechanistically, freeze a new prospective comparison of the
learner change, preserving controller, quotas, queries and natural execution.
