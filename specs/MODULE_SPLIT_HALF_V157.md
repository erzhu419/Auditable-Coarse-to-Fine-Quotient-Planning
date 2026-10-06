# V157: fixed suffix split-half selection

Frozen before outcome extraction, 2026-09-27. Reuse all 64 V153 roots:
four independent training histories × two queries × H2/LEARN8 source policies
× four fixed source slots. Reuse all 16 paired suffixes and four terminal
branches per root. V156's audited root roster and all-suffix component targets
must agree with V153. No new games, model fits, or native planner calls.

A is suffix 0–7; B is suffix 8–15. The two directions are A→B and B→A.
For each suffix define component differences H2 = M_H2 − H_H2 and
GATE = M_GATE − H_GATE. Utility is score/2048 − p·failure + p·success,
where p is 1 or 8 for the query. For each root and target, the selector
accepts only if its training-half mean utility difference is strictly positive.
Zero rejects. OLD accepts according to the frozen V153 root prediction.
Evaluation-half outcomes never enter that direction's selection decision.

Primary: GATE-target selection evaluated on opposite-half GATE outcomes.
For decision s, OLD decision o, and evaluation advantage d:
gain versus OLD = (s−o)d; versus reject = sd; versus accept = (s−1)d.
Report both directions and their equal mean. Secondary: H2-target selection,
both targets' evaluations, source-policy and history strata, decision-change
rate and strict-positive sign agreement between half means. Apparent gain
uses the training-half evaluation-target mean with the same decision; selection
optimism is apparent minus opposite-half gain. No clipping or root exclusion.

Means weight roots equally within each history and then histories equally.
The ALL-direction view first averages two directions per root. All unchanged
decisions contribute zero gain versus OLD. Include all 72 query × selection
target × evaluation target × source (ALL/H2/LEARN8) × direction views and
their four history results. No split search, parameter tuning, or naive
independent-fold confidence intervals: both directions reuse the halves and
the full retained labels were inspected in earlier experiments.

This is a root-local empirical selector with access to eight extra outcomes
at that root. It is not a deployable cross-root policy or a true-value oracle.
Opposite halves have separate suffix streams conditional on a common root,
teachers and prefix; they do not create independent root histories. A stable
positive heldout signal would motivate more independently visited roots at a
fixed acquisition budget. Unstable gains or signs instead motivate improving
label precision before reducing the number of suffixes per root. These
descriptive outcomes do not alone explain full-game decline or general
unlearnability.

Read the four V153 compressed branch files once for compact extraction and
once for independent extraction audit. Preserve only branch identities and
terminal outcomes in the new data package. The original physical acquisition
cost is 2,017,530 environment transitions, counted once, with the full pool
charged to each comparison view. Record extraction/arithmetic/audit time and
raw-row reads separately. Preserve earlier cost references. Freeze this
protocol, root/branch roster and source files before reading outcomes; audit
terminal identities/components, all-suffix means, half selection and group
accounting without replaying trajectories. Focused tests use synthetic data.
Keep H2; U005 FAIL and U006 unstarted.
