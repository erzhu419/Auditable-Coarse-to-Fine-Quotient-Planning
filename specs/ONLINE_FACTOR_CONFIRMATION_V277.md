# V277: independent-source confirmation of V276

Freeze this cohort before generating source or target outcomes. V276 repairs
one known source failure; V277 tests the unchanged method on new histories.

- Exactly 32 source lifecycles, source seed `27740100 + 100*i` and paired target
  seed `27790100 + 100*i`, for every `i=0..31`. Source operator streams use the
  existing context-index offsets 0..4, so no source RNG seed is reused between
  lifecycles. Do not inspect source partitions to include or exclude histories.
- Import V276's `run_lifecycle` unchanged. Keep all four arms, factor scoring,
  initial-source coverage keys, quota 4, query cycle, source 720 fit/240 audit,
  A/B/A_prime laws and 12×8 opportunities per phase (288 per arm/lifecycle).
- Primary: paired whole-lifecycle executed-policy regret difference
  COVERED_REVISED minus PASSIVE_FIXED, including every forced-route cost.
  Negative values favor the combined repair.
- Summarize all 32 paired differences: exact mean, improved/equal/worse counts,
  per-seed differences, and a 95% percentile bootstrap interval. Resample whole
  source lifecycles (32 draws with replacement), 20,000 times, RNG seed
  27700001. Use linear percentile interpolation. The primary improvement is
  confirmed on this cohort if its interval is wholly below zero. This is a
  finite synthetic confirmation decision, not the original scientific Gate.
- Retain the same five V276 factorial contrasts and phase summaries as
  secondary descriptions. Neither changing the primary contrast nor selecting
  a favorable subgroup is allowed. V276 development results stay separate.
- Save full traces as gzip JSON plus a small summary containing all 32 source
  receipts. Count real source acquisition once per lifecycle and online
  operator outcomes per arm; do not claim a compute-cost advantage.

If confirmation fails, analyze the retained adverse histories and fix the
cause in a separate stage; do not rerun seeds, expand this cohort, or tune quota.
The route grammar remains supplied. Natural full-game strategic transfer and
the frozen U005 FAIL/U006-unstarted state are outside this confirmation.
