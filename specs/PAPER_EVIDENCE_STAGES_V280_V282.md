# V280–V282: three paper-evidence stages

Freeze before any new cohort outcomes. Continue the established learner and
test the missing evidence; the rejected V279 mixture and one-step feedback
gate are not promoted. Existing source results remain unchanged.

## V280: independent net-learning campaign

All 128 sources `28040100+100*i` and paired target streams `28090100+100*i`,
i=0..127, are registered without inspecting partitions. The size addresses
the rarity of source-gap cases in V278, not an extension of its cohort.
Keep all three A/B/A_prime laws, four target contexts, goal/risk/reward cycle,
48 source-fit plus 16 reserved rows per operator/context and 288 START trials.

Five actual-execution arms: FULL_CONTEXT_LOCAL ignores source and keeps target
history across phases; FROZEN_FACTOR uses source alone; FIXED_FACTOR_UPDATE
keeps initial source fields with online parameter updates; PASSIVE_REVISED
retains V278 natural execution; RELEVANT_REVISED retains its unchanged
query-relevance coverage and quota4. Only reached operators produce feedback.

Co-primary comparisons: RELEVANT minus PASSIVE and RELEVANT minus LOCAL actual
route cumulative regret, including every intervention and failed reach attempt.
Bootstrap complete paired source lifecycles 20,000 times, seed28000001.
Support requires both upper 95% endpoints below zero; retain every adverse
source. Other arms isolate source, parameter updating and field revision.
Match START budgets; LOCAL pays no source cost, so this is not equal lifetime
raw-observation cost. Report both actual returns and exact-law route regret.

## V281: natural full-game model revision

Reuse the four local V120 risk_goal @4096 trained leaves, without target
selection or new checkpoint downloads. Sixteen new memory lifecycles have
parent=i%4 and source-seed base `28140100+100*i`, i=0..15. Their source spawn
observations come from complete DIRECT games until at least 256 actual swipes;
all observations, including excess ones, are billed and shared by all arms.
FROZEN memories keep statistics from the first 256 observations; updating
memories consume the complete shared warmup under unchanged V115 rules.

Same frozen value parameters and identified swipe program: DIRECT;
FROZEN_H2; POOLED_H2; LIBRARY_H2. H2 uses the existing native V135 kernel.
POOLED/LIBRARY use unchanged V115 spawn-memory updates, inferred only from
real post-action board pairs. Neither receives phase labels or true laws.
Run eight natural games per phase, environment p_four=.1,.5,.1, same paired
game seeds across arms. Keep the same learner alive; do not reset at switches.
Commit final terminal spawn observations. Max8192 is a retained CUTOFF, never
silently counted as a terminal loss or replaced by another game.

Primary comparisons: LIBRARY minus POOLED and FROZEN cumulative utility
(score/2048−4*LOST+4*WON), complete paired memory lifecycles, bootstrap20,000,
seed28100001. Report phases, wins, cutoff counts and parent-level means.
Bootstrap complete paired lifecycles within each fixed parent separately,
retaining four lifecycles per parent and equal parent weights on every draw.
Intervals are conditional on the four frozen source leaves, not evidence
from sixteen newly trained value models. This tests natural world-model
revision; it does not transfer route-specific operators onto chessboard cells.

## V282: contribution and full costs

On all V280 RELEVANT histories, replay LOCAL_FULL, SOURCE_FROZEN,
SOURCE_FIXED_UPDATE and SOURCE_MAP_REVISED from the identical committed
prefix. The latter must reproduce every original recommendation and regret.
No counterfactual feedback or new environment draws; report all source pairs.
These diagnose source/parameter/structure contributions on fixed data.

V281 FROZEN_H2 versus DIRECT isolates planning with identical frozen leaf and
identical frozen source spawn memory. Its added generated successors and
value/table evaluations are paid; differing executed trajectories are expected.

Report source fit versus generated reserve rows, inherited source learning,
warmup interactions, online observations, STARTs/games, simulated successors,
CPU scopes and retained bytes. Physical source is counted once per shared
corpus; arm economic costs are separate. No equal-quality cost extrapolation.
These experiments close evidence only when their measured results support it.
U005 remains FAIL; U006 is outside this research campaign and unstarted.
