# V307 — old/new factual replay at an exact supervised-state budget

V306 establishes the frozen A1 gain but not an incremental benefit from another
current-policy cohort or an actor-based explanation of the old A2 loss. Test
whether retaining old facts helps repeated learning. Reuse all 64 V303 A1 and
V306 CURRENT_DATA histories under the same four frozen SOURCE parents. Both
input canonical audits must pass. No new training acquisition or heldout-based
selection is made. Reconstruct and reproduce the original LOCAL A1 fit.

Four arms: original SOURCE, A1_FROZEN, NEW_ONLY and MIXED_REPLAY. Updating
arms receive identical full A1 reward/risk copies. Unchanged LOCAL representation,
alpha 0.0025, original complete-game reward suffixes and factual win labels,
game-start predictions and per-game selected-address normalization are used.
An explicit mask selects fit states without changing the original future rewards
or terminal labels. Winning afterstates are excluded as in V301. An all-eligible
mask must exactly reproduce all original V301 fit fields and parameters.

For each life, N is the number of nonwinning afterstates in the full V306 current
FIT prefix. NEW_ONLY uses all N in original order and must exactly reproduce
V306 CURRENT_DATA's scientific fit receipt. MIXED uses floor(N/2) old A1 and
N-floor(N/2) current FIT afterstates without replacement. All real old inventories
are sufficient; failure to supply the frozen quota stops execution.

Within each source, prioritize FIT game indices by breadth-first midpoint
traversal: start interval [0,G), take floor((first+end)/2), then queue its left
and right subintervals, skipping empties. Include complete games until the source
quota is met. Only the last contributing game can be partially selected: select
eligible positions floor((2*i+1)*L/(2*k)), i=0..k-1, when k of L are needed.
Preserve that whole game's boards, rewards and natural terminal code to construct
the original suffix targets. Sort selected games chronologically within each
source, alternate old/new games starting old, then append the remaining source.
No reward, win rate, evaluation or fitted prediction chooses a mixing rule.

N supervised reward/risk samples are exactly matched. Natural game counts,
game/address commits, parameter writes, target construction and CPU can differ
and are recorded; this is not identical compute or identical aggregate update
strength. Retain per-game origins, full/partial sample selection and source quotas.

Evaluate all four frozen heads on 32 new paired A seeds per life:
307900000000+life*1000000+episode. Use true p_four=0.1, the original observed A1
planning belief for every arm, full H2 and max 8,192 steps. No evaluation fitting,
belief revision or best-checkpoint selection. Retain cutoffs. Primary:
MIXED_REPLAY minus NEW_ONLY whole-game utility, 20,000 paired lifecycle
bootstrap draws within the four fixed parents, seed 30700001. CI lower >0 and
no cutoffs supports the replay intervention. Separately, mixed minus A1 CI lower
>=0 supports zero-margin nondecrease; upper <0 supports loss; otherwise unresolved.
Benefits versus SOURCE cannot replace either endpoint.

No new training raw is acquired. SOURCE/dynamics/A1 economic history is paid by
all references; both updating arms additionally pay the retained CURRENT_DATA
cohort. Old replay has no extra acquisition cost. Actual old/current reconstruction,
A1 refit, both full parameter copies, selection, masked fitting, all 8,192 new
evaluation games, compiler and processing CPU are counted without double adding
contained components. Historical interrupted V303 total CPU remains unavailable.

This is a retained-experience development intervention with new evaluations,
conditional on four sources and the old A1/current histories, not independent
full-method confirmation. Replay changes old/new state coverage, factual labels,
game groupings and order together. It does not identify a unique cause of old
degradation. B is not updated or reevaluated. No mixing, budget, alpha or seed
tuning is allowed on these facts. U005 remains FAIL; U006 remains unstarted.
