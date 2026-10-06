# V278: query relevance and acquisition-cost filtering

V277's retry-empty source spends 53 opportunities acquiring 16 retry outcomes,
including 25 wet-context detours where the recommendation is already optimal.
V278 changes only the coverage controller; the learner and factor scoring stay
at V276. Freeze this specification before new cohort outcomes.

- Register all 64 sources `27840100+100*i` and paired target streams
  `27890100+100*i`, i=0..63. This is a new cohort, not an extension of V277.
  Coverage was active in only 3/32 V277 sources, motivating the larger
  prospective cohort. Do not select sources by their partitions or results.
- Keep source 720 fit/240 audit, A/B/A_prime laws, four contexts, query cycle,
  12×8 START opportunities per phase and quota4. All four arms reselect factors
  at episode start from source fit plus earlier committed events.
- Arms: PASSIVE_REVISED; QUOTA_REVISED (unchanged V276 coverage);
  RELEVANT_REVISED; COST_RELEVANT_REVISED.
- Both new controllers keep INITIAL source-empty projection keys and count
  their committed outcomes toward quota4. Skip pending coverage when the
  CURRENT selected projection has matching source-fit rows.
- For an unresolved operator, hold other posterior rows fixed and enumerate
  known-support simplex vertices. For each query compute the largest utility
  regret of that query's current greedy recommendation over these vertices.
  Require strictly positive regret D for the CURRENT query; ties do not trigger
  coverage. Known support is old support plus actually observed categories.
- SHORT uses SHORT; DETOUR uses the better posterior-valued DETOUR_RETURN or
  DETOUR_RETRY with lexicographic tie-breaking; RETRY uses DETOUR_RETRY and is
  sampled only after real RECOVERY. Operator priority stays in the old order.
- The extra cost filter estimates attempts as remaining quota divided by
  posterior reach probability (1 for root operators, P(RECOVERY) for retry).
  Expected probe loss is current greedy utility minus probe utility. Remaining
  budget counts the CURRENT and later START opportunities with the same exact
  visible context pair in the full public lifecycle schedule. Potential gain
  is the sum of each remaining query count times its frozen-model vertex D.
  Reject an active override if expected attempts exceed remaining opportunities
  or attempts×probe loss exceeds potential gain. A probe identical to the
  recommendation remains natural execution. This is an optimistic acquisition
  heuristic, not a value-of-information estimator or a no-harm certificate.
- Oracle laws enter only post-execution regret scoring. No future outcomes,
  audit suffixes or phase laws enter coverage or factor selection.

Primary: COST_RELEVANT_REVISED minus QUOTA_REVISED whole-lifecycle actual-route
regret, including every failed acquisition attempt. Secondary: versus passive,
RELEVANT versus quota, and COST_RELEVANT versus RELEVANT. Keep all per-source
differences and adverse cases. Bootstrap complete paired lifecycles 20,000
times with seed27800001; primary support requires the 95% interval upper bound
below zero. Do not change the comparison, seeds or rule after inspecting data.

Save compressed full traces and a small all-source receipt in the project.
Natural full-game strategic transfer and the original U005/U006 are unchanged.
