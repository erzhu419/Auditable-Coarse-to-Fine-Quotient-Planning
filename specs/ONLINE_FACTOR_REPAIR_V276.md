# V276: online factor repair and source-gap coverage

V275 retained trajectories expose a self-confirming source error: seed 275402
has no source rows for its full-context SHORT buckets, never executes SHORT,
and keeps a global DETOUR partition. Of the four-seed B regret 40.2928,
39.8672 is wet-road ranking error; only 0.4256 concerns DELAYED. V276 tests
bounded lawful coverage and factor reselection together, with a 2×2 design.

## Frozen before target sampling

- Reuse source seeds 275401–275404 and exactly their 720 fit rows/240 audit
  rows. Fresh online seeds are 276401–276404, paired to these source seeds in
  order. This is a follow-up on known source errors, not independent source
  confirmation.
- Keep V275's A/B/A_prime laws, four target corners, query cycle
  goal/risk/reward, 12 episodes per phase, 8 START opportunities per episode.
  One learner runs all 288 opportunities. No extra target rows are bought.
- Four arms: PASSIVE_FIXED, PASSIVE_REVISED, COVERED_FIXED, COVERED_REVISED.
  All use the same Jeffreys-smoothed source-plus-committed-history posterior.
- REVISED reselects operator factor subsets at the start of each episode
  using V270's Dirichlet marginal likelihood and deterministic tie rule.
  Only source fit and earlier executed events enter scores. The alphabet can
  grow only from committed observations; phases and oracle labels are absent
  from the selector.
- COVERED uses INITIAL source-selected projection keys. If a target/operator
  group has zero source-fit observations, collect up to four real outcomes for
  that group during existing opportunities. SHORT_PASS uses a legal SHORT
  route; DETOUR_PASS and RECOVERY_RETRY use DETOUR_RETRY, with retry sampled
  only if RECOVERY is actually reached. Committed events across the lifecycle
  count toward the quota; no phase boundary or changed factor resets it.
- Sampling keys include seed/context/phase/episode/trial/operator/visit; arms
  share potential draws for identical executed operator keys.

## Endpoints and decision

Primary: each seed's cumulative exact regret of ACTUALLY EXECUTED routes over
the lifecycle and in B, including forced-route cost. Compare COVERED_REVISED
to PASSIVE_FIXED, and keep all four factorial contrasts. Secondary: pre-action
greedy recommendation regret and first wet-context SHORT recommendation,
operator exposures, coverage count, and retained factor choices.

Source acquisition is paid once (720 fit + 240 audit per seed), separately
from actual online events. Oracle laws score decisions after the selected
action; they never determine coverage, grouping, or posterior updates. All
four source histories are retained regardless of outcome. Results are
descriptive across four paired lifecycles; no formal Gate or U006 launch.

Four observations alone do not guarantee escaping the joint source error.
This experiment asks whether online partition revision plus bounded coverage
does so within the existing budget. The supplied route grammar and finite
trials remain a diagnostic, not natural full-game 2048 evidence.
