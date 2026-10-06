# V199 — finite H4 reference feasibility before another learner

Route review closes repeated H3 root-ranking changes as the primary work. V196 supplies useful continuation information; V198's utility objective fails its matched control. V77/V81/V170/V171 already tested persistent learning or whole-game control and failed. This pilot asks a different question: can one smaller, executable, query-family model support its own multistep plans on existing H4 kernels? It is an oracle-assisted development experiment, not a learned method or independent confirmation.

## Fixed inputs and scope

Read and retain five original inputs, in this order, under inputs/:
1. reports/controlled_predictive_composition_v69/manifest.json.
2. reports/controlled_predictive_composition_v69/v69_h4_00/FULL.model.json.
3. reports/controlled_predictive_composition_v69/v69_h4_00/portable_inputs.json.
4. reports/controlled_predictive_composition_v69/v69_h4_01/FULL.model.json.
5. reports/controlled_predictive_composition_v69/v69_h4_01/portable_inputs.json.

These are the first two H4 cases in the old fixed roster; retain them regardless of results. Use all fourteen existing queries, including their original coefficients. Check that both portable query definitions agree. Kernel cells are [state,remaining_layer,status]; rows are [state,action,[[pnum,pden,next,rnum,rden],...]]. Build a disjoint union in case00,01 order, remapping states deterministically and preserving two root mappings. No new games, stochastic samples, neural/parameter/tree fits, native dynamics or teacher tapes. Old acquisition costs remain inherited references. All new kernel reads, value calculations, construction and policy evaluations are paid.

## Oracle reference construction

Use native Fraction probabilities/rewards; query coefficients are Fraction(str(value)). Terminal future vector is (0,LOST,WON); CUTOFF is (0,0,0). For each query, one bottom-up full-kernel DP retains a single achievable joint R/F/S policy vector and each legal first-action vector. Score by wR*R-wF*F+wS*S. Sort action strings; sequential selection requires a gain greater than EPS=Fraction(1,10**12). Never maximize vector components independently. This oracle profile is privileged development information; do not present it as learned from SOURCE.

Fixed widths, in order: 0,1/256,1/64,1/16,1/4,1. Initial/reference cell key is remaining layer, terminal status and ordered legal actions. For ACTIVE cells append all fourteen queries' complete action R/F/S profiles, in sorted query/action order. Width0 preserves exact rational coordinates; positive widths use floor(component/width). Inactive cells have no profile. Deterministically sort keys and members to assign cell IDs. No width/case/query is added after inspecting outcomes.

For each cell and common action, average over all concrete members with equal mass. Its reward is the average expected immediate reward; successor probability is the average original probability pushed to successor cells. Encode this finite quotient explicitly as cells/rows with native rational coordinates. Store mappings and membership, not full oracle profiles. Compile six shared models, each reused across both root mappings and all fourteen queries.

## Own model plans and ground replay

Run the same Fraction DP on each quotient, reading only quotient rows and successor cells. It must not request concrete next boards or oracle boundary vectors. Map every abstract policy back through the state mapping and re-evaluate that policy on the original disjoint FULL kernel. The replay uses that abstract policy at every ACTIVE state, never the oracle's continuation policy.

Report per width and query: predicted and actual complete R/F/S at both roots, oracle and actual utility, root regret, maximum actual regret over all ACTIVE states, and maximum per-component nominal-versus-actual errors over all ACTIVE states. Report total/ACTIVE cells, state-action rows, successor entries, encoded bytes and actual DP/construction/replay work. Record within-cell expected-reward spread and maximum TV from member successor laws to the averaged law. Width0 is the positive control: query-policy values must be preserved to1e-10; legal actions and model layering remain exact. Different tied actions are allowed if their replayed utility is preserved.

For development routing, seek one shared width that halves both ACTIVE-cell and action-row counts while keeping all ACTIVE-state/query regrets and all nominal-versus-actual component errors at most0.01. This criterion routes the next research step; it does not alter any old Gate. Print the whole fixed curve even if no width qualifies. Distinguish exact-value preservation, approximate policy preservation and transition homogeneity. Do not infer strong Markov equivalence or arbitrary-query correctness from small errors on this query family.

## Execution and verification

Output reports/controlled_predictive_reference_feasibility_v199; runtime reports/v199_runtime_tmp. Freeze scripts/spec/tests/wrappers before input reads. Phases are protocol_frozen (0 reads), inputs_retained (5), profiles_frozen (5), curve_complete (5), complete (5). Focused synthetic tests verify joint-policy vectors, member averaging and remapped successors, closed quotient recursion, self-policy ground replay, action legality and quantization. Reuse settled serializer conventions without repeating legacy tests. Run one main and one independent reconstruction; preserve first failures and actual paid work. Source and original-input byte comparisons occur once, without hashes.

Independent reconstruction implements Fraction planning, profiles, partition, average transitions and policy replay separately, and checks saved models, mappings, choices, root/full-state metrics, counts and routing. Numeric exported metrics tolerate1e-10*(1+abs(expected)); native rational models and policies are exact, with the same declared EPS convention. It performs no new physical simulation, solves or training. No broad assurance framework is added for this small pilot.

## Decision and limits

A qualifying reference is a finite feasibility witness: there is useful compressible structure for these exposed H4 kernels and queries. Next try learning its controlled distinctions from chronologically available experience, and bridge the existing V77 update lifecycle with the V171 successor-planning interface. Use forced-action transition data and verify successor closure before a new complete-game study.

Failure only rejects this frozen reference construction/width range. It is not a lower bound proving all strategic abstractions impossible. Reassess the task/query family and acceptable approximation before proposing another learner. Neither outcome demonstrates continual learning, long-game benefit or sample efficiency. Preserve H2, U005 FAIL, U006 unstarted and all previous negative evidence.
