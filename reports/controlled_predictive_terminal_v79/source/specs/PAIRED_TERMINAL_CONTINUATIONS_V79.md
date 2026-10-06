# V79: terminal continuations of the fixed V78 acceptance cohort

Frozen 2026-09-13 before any V79 main suffix is sampled. V78's final candidates
lost a small amount of observed 32-step reward on selected validation roots but
improved full natural-game reward over the frozen incumbent. V79 holds roots,
models, queries and random prefixes fixed to isolate the effect of extending
the observation horizon within that selected cohort.

## Cohort and continuation

Include all 712 retained V78 acceptance trajectories: lifecycles 0/1/2,
checkpoints 39/75, both old/new validation strata, both queries, both replicas,
and candidate/incumbent. The 17 LOST prefixes require no simulation. Extend
each of the 695 CUTOFF prefixes from its retained final board until WON, LOST,
or 2000 total actions from the original validation root. Do not regenerate the
22,533 inherited transitions or select roots using their eventual outcomes.
The new transition ceiling is 695*(2000-32)=1,367,760; report actual usage.

The incumbent at checkpoint 39 is life_N/initial_knowledge.json; at checkpoint
75 it is checkpoint_39/DECISION.json. The candidate is the stage's candidate.json.
No fitting, refresh, policy change, acceptance or new natural-game test occurs.
V78 supplied dynamics, V77 planner and both queries remain unchanged.

Restore the environment generator from the retained seed by consuming its
recorded environment_random_draws (two per old transition, no initial spawns).
Restore the model generator from seed+1000000000000 by consuming four uniforms
per old action. RNG restoration is counted separately from new sampling.
Continue ordinary receding-horizon planning at every newly sampled step.
Already terminal prefixes make no ground or planner calls. The sampler records
only new suffix transitions; a link identifies their immutable prefix.

## Analysis and interpretation

Pair candidate/incumbent using lifecycle, checkpoint, stratum, query, root,
replica and seed. For each pair, retain short, extended and suffix-contribution
score/utility differences. Summarize within independent lifecycle before
reporting across-lifecycle means. Report both stages and every stratum/query,
including reversals in either direction. The primary diagnostic is the final
checkpoint's new-root reward-query delta in each of the three lifecycles.

For each stage, calculate what the unchanged V78 acceptance rule would return
on the extended outcomes: every old/new query mean delta nonnegative, with at
least one strictly positive new-query delta. This is a retrospective diagnostic,
not an accepted model update. If any constituent outcome remains CUTOFF, mark
the terminal acceptance result unresolved rather than treating censoring as
success or failure. Preserve these capped pairs in the complete cohort.

The existing V78 full natural-game MSE-minus-FROZEN result is a separate
reference. Compare it only where the stage's candidate actually became MSE
and the incumbent remained frozen. Sign changes from short to terminal at the
same root establish horizon sensitivity for this cohort. Remaining disagreement
with natural games can involve starting-state distribution and finite-sample
variation; this test does not separate those two effects.

This experiment creates terminal outcome evidence, not a newly learned agent.
No new success claim follows from execution completeness. Keep prefix and
suffix costs separate and do not count reused interactions as newly sampled.
U005 remains FAIL and U006 remains unstarted.
