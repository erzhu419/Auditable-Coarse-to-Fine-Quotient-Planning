# V275 Online Support Continual Lifecycle

## Purpose

V275 moves the V270–V274 crossed-factor diagnostic from pre-generated target
prefixes to execution-only route trials. It tests whether one learner can
retain and revise action-consequence support across a fixed A→B→A' lifecycle.
It is a development diagnostic and does not reopen U005 or launch U006.

## Frozen protocol

- Seeds: 275401–275404; the independent unit is one complete seed lifecycle.
- Phases: A, B, A_prime. B introduces the "DELAYED" successor on
  "RECOVERY_RETRY" with probability 1/5, and adds cost 2; A_prime restores
  A's law.
- Each phase has 12 episodes and each episode has 8 START opportunities.
  The four target contexts are traversed twice per episode. The query is fixed
  within an episode and cycles "goal", "risk", "reward".
- Only an operator reached by the selected route is sampled. The outcome is
  appended to the learner history after the sample. No target operator rows or
  audit suffix are preloaded.
- Common random numbers pair arms at the same seed, context, phase, episode,
  trial, visit, and operator key. Contexts are repeated opportunities, not
  independent seeds.

## Arms and accounting

- "PHASE_RESET_ONLINE": no source model; uses the two visible context fields
  ("road_profile", "retry_service") and clears phase-local history at each
  phase boundary.
- "FROZEN_FACTOR_ONLINE": uses the learned V270 source factor model and ignores
  online updates.
- "CONTINUAL_FACTOR_ONLINE": uses the same source factor model and admits
  observed categories into its posterior.
- "LEGACY_COERCE_ONLINE": uses the same source model but maps unknown categories
  to "LOST".

The source corpus is 720 fit and 240 audit observations for factor arms, paid
once per seed and reported separately from online executed events. The reset
arm uses no source observations. The online budget is the number of actual
operator events, not the number of possible operators.

## Endpoints

The primary descriptive endpoint is cumulative exact oracle regret over the 96
START opportunities in B, summarized per seed and paired across arms. A_prime
retention and recovery are secondary endpoints. Support exposure is reported as
the number of observed "DELAYED" outcomes and the first episode in which one was
actually reached; no discovery is treated as right-censored exposure, not as
evidence of absence.

This finite synthetic route-trial cohort is not a natural full-game 2048
episode, a formal Gate, or a claim of total-cost superiority.

