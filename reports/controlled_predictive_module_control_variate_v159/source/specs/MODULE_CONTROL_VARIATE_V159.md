# V159: fixed spawn control variate

Freeze before correction computation, 2026-09-27. Reuse all 64 V158 roots,
TRAIN32 and EVAL32, H_GATE/M_GATE paths (8192 retained branches). No new
environment samples, fitted weights, window search, coefficient fitting,
or root/budget selection. The present test is exploratory on inspected data.

For each target query q use its frozen SINGLE QueryTD leaf's DIRECT/H1
state value f_q(s)=choose(s,q).value, including analytic WON/LOST values.
Do not use an afterstate table value as a state value, the other query's
critic, an OLD advantage predictor, or the stored H2 action value.
Load existing parent and leaf; no H2 expansion is needed for f.

For the first min(8,actual branch steps) spawn events, let a be the
afterstate of the action actually selected. Enumerate every empty cell
with equal probability and ranks 1/2 with probabilities .9/.1. Compute
c_t=f_q(actual postspawn)-sum_z P(z|a)f_q(a+z), caching the actual value
from this enumeration. Include the winning swipe's spawn; no later steps
after termination. Set C_branch=sum_t c_t and beta=1. The paired scalar
label is delta_CV=delta_RAW-(C_M-C_H). Do not invent corrected reward,
failure, or success components.

Each term has conditional expectation zero given the selected afterstate:
the critic is frozen and actual spawn follows the enumerated law. A fixed
bounded prefix therefore preserves the expected terminal objective even
when f is inaccurate. This does not guarantee variance reduction: critic
error or weak covariance can make the corrected estimator worse.

Retain budgets n=8,16,32; n32 is primary. Use only the corresponding TRAIN
prefix of corrected labels and accept strictly positive means (zero rejects).
Freeze CV selectors before computing EVAL corrections. Both RAW and CV
selectors are evaluated ONLY with original RAW EVAL32 terminal utilities.
Primary comparisons are n32 CV-minus-RAW paired gain and n32 CV against
OLD, reject, accept. Secondary n8/n16, all source/history strata, paired
label RAW/CV variance, means and covariance are retained. EVAL corrections
are used solely for variance diagnostics, never for selection or scoring.

Average roots equally within each history and then four histories equally.
Use the existing V158 conditional suffix interval formula, computing
CV-minus-RAW per shared evaluation suffix before estimating variance.
Variance diagnostics average sample variances within roots; report the
ratio of averaged CV/RAW variances, not variance across root means.
Training and evaluation labels may have been inspected in earlier turns:
no new confirmatory claim, best-budget choice or automatic fresh sampling.
Cutoffs remain incomplete with all costs retained, including zero-change
decisions; do not remove roots or replace suffixes.

Charge every DIRECT critic call, enumerated outcome, model load, raw-row
read and deterministic audit operation; preserve V158's 4,026,405 physical
transitions and earlier acquisition references without counting them anew.
Retain compact prefix/candidate/value corrections for independent verification
against V158 paths and frozen leaf weights. Reuse the completed V158 full
trajectory audit; do not repeat all four million environment transitions.
Focused tests cover exact centering, query/terminal handling, fixed prefix,
label pairing, TRAIN isolation and RAW-only evaluation. Main and independent
analysis execute once after source/protocol freeze. Keep H2; U005 FAIL and
U006 unstarted. A useful mechanism here still requires fresh confirmation.
